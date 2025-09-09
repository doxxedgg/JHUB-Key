import discord
from discord.ext import commands, tasks
from discord.ui import View, Modal, TextInput, Button
import os
import json
from datetime import datetime, timedelta
import random
import string

KEYS_FILE = "keys.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


# ----------------- KEY STORAGE -----------------
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

def generate_key(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ----------------- MODALS -----------------
class RedeemModal(Modal):
    def __init__(self):
        super().__init__(title="Redeem Your Key")
        self.key_input = TextInput(
            label="Enter your 8-digit key",
            placeholder="ABCDEFGH",
            max_length=8,
            min_length=8,
            required=True
        )
        self.add_item(self.key_input)

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.upper()
        keys = load_keys()

        if key not in keys:
            await interaction.response.send_message("❌ Invalid key.", ephemeral=True)
            return

        data = keys[key]

        if data["redeemed_by"] and data["redeemed_by"] != str(interaction.user.id):
            await interaction.response.send_message("❌ This key is already redeemed by another user.", ephemeral=True)
            return

        expires_at = datetime.fromisoformat(data["expires_at"])
        if datetime.utcnow() > expires_at:
            await interaction.response.send_message("❌ This key has expired.", ephemeral=True)
            return

        if not data["redeemed_by"]:
            data["redeemed_by"] = str(interaction.user.id)
            save_keys(keys)

        await interaction.response.send_message(f"✅ Key redeemed successfully! Locked to {interaction.user.mention}", ephemeral=True)


# ----------------- PANEL VIEW -----------------
class Panel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.primary, custom_id="redeem_key")
    async def redeem_key(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(RedeemModal())

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.secondary, custom_id="reset_hwid")
    async def reset_hwid(self, button: Button, interaction: discord.Interaction):
        keys = load_keys()
        user_id = str(interaction.user.id)
        found_key = None

        for key, data in keys.items():
            if data.get("redeemed_by") == user_id:
                found_key = key
                break

        if not found_key:
            await interaction.response.send_message("❌ You have no redeemed key to reset.", ephemeral=True)
            return

        keys[found_key]["redeemed_by"] = None
        save_keys(keys)
        await interaction.response.send_message(f"✅ Your key `{found_key}` has been reset and is now unclaimed.", ephemeral=True)

    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.success, custom_id="get_role")
    async def get_role(self, button: Button, interaction: discord.Interaction):
        role_name = "Member"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(f"❌ Role '{role_name}' not found.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(f"You already have the role '{role_name}'.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ Role '{role_name}' assigned!", ephemeral=True)

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.secondary, custom_id="stats")
    async def stats(self, button: Button, interaction: discord.Interaction):
        keys = load_keys()
        total_keys = len(keys)
        redeemed = sum(1 for k in keys.values() if k["redeemed_by"] is not None)
        await interaction.response.send_message(
            f"📊 **Stats:**\nTotal keys generated: {total_keys}\nKeys redeemed: {redeemed}",
            ephemeral=True
        )


# ----------------- EVENTS -----------------
@bot.event
async def on_ready():
    bot.add_view(Panel())
    prune_expired_keys.start()  # start background task
    print(f"✅ {bot.user} is online and ready.")


# ----------------- COMMANDS -----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def genkey(ctx, days: int):
    """Prefix command: !genkey 7"""
    if days <= 0:
        await ctx.send("❌ Please enter a positive number of days.")
        return

    keys = load_keys()
    new_key = generate_key(8)
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()

    keys[new_key] = {"expires_at": expires_at, "redeemed_by": None}
    save_keys(keys)

    await ctx.send(f"✅ Generated key `{new_key}` valid for {days} days.")


@bot.tree.command(name="genkey", description="Generate an 8-digit key valid for X days (admin only)")
async def slash_genkey(interaction: discord.Interaction, days: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    if days <= 0:
        await interaction.response.send_message("❌ Please enter a positive number of days.", ephemeral=True)
        return

    keys = load_keys()
    new_key = generate_key(8)
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()

    keys[new_key] = {"expires_at": expires_at, "redeemed_by": None}
    save_keys(keys)

    await interaction.response.send_message(f"✅ Generated key `{new_key}` valid for {days} days.", ephemeral=True)


@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="JHUB Key System",
        description="Use the buttons below to redeem keys, reset HWID, get roles, and view stats.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=Panel())


@genkey.error
async def genkey_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use this command.")


# ----------------- BACKGROUND TASK -----------------
@tasks.loop(hours=1)
async def prune_expired_keys():
    keys = load_keys()
    now = datetime.utcnow()
    before = len(keys)

    keys = {
        k: v for k, v in keys.items()
        if datetime.fromisoformat(v["expires_at"]) > now
    }

    if len(keys) < before:
        save_keys(keys)
        print(f"🗑️ Pruned {before - len(keys)} expired keys.")


# ----------------- MAIN -----------------
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Error: DISCORD_TOKEN environment variable not found.")
        exit(1)

    # sync slash commands
    async def main():
        async with bot:
            await bot.start(token)

    import asyncio
    asyncio.run(main())
