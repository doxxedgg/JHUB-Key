import discord
from discord.ext import commands
from discord.ui import View, Button
import os
import json
from datetime import datetime, timedelta
import random
import string

KEYS_FILE = "keys.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Load keys from file
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

# Save keys to file
def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

# Generate 8-digit random key
def generate_key(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Persistent Panel View
class Panel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.primary, custom_id="redeem_key")
    async def redeem_key(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Please use the command `!redeem <key>` to redeem your key.", ephemeral=True)

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.secondary, custom_id="reset_hwid")
    async def reset_hwid(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Placeholder: You can add actual HWID reset logic here
        await interaction.response.send_message("HWID reset is not implemented yet.", ephemeral=True)

    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.success, custom_id="get_role")
    async def get_role(self, button: discord.ui.Button, interaction: discord.Interaction):
        role_name = "Member"  # Change to your role name
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role:
            if role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Role '{role_name}' assigned!", ephemeral=True)
            else:
                await interaction.response.send_message(f"You already have the role '{role_name}'.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Role '{role_name}' not found on this server.", ephemeral=True)

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.secondary, custom_id="stats")
    async def stats(self, button: discord.ui.Button, interaction: discord.Interaction):
        keys = load_keys()
        total_keys = len(keys)
        redeemed = sum(1 for k in keys.values() if k["redeemed_by"] is not None)
        await interaction.response.send_message(
            f"**Stats:**\nTotal keys generated: {total_keys}\nKeys redeemed: {redeemed}", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(Panel())
    print(f"✅ {bot.user} is online and ready.")

@bot.command()
@commands.has_permissions(administrator=True)
async def generatekey(ctx, duration: str):
    """Generate an 8-digit key that expires after a duration (e.g. 10m, 2h, 1d)"""
    keys = load_keys()

    # Parse duration
    try:
        unit = duration[-1]
        amount = int(duration[:-1])
        if unit == 'm':
            expire = timedelta(minutes=amount)
        elif unit == 'h':
            expire = timedelta(hours=amount)
        elif unit == 'd':
            expire = timedelta(days=amount)
        else:
            await ctx.send("Invalid duration unit! Use m, h, or d.")
            return
    except Exception:
        await ctx.send("Invalid duration format! Example: 10m, 2h, 1d")
        return

    key = generate_key()
    now = datetime.utcnow()
    keys[key] = {
        "created_at": now.isoformat(),
        "expires_at": (now + expire).isoformat(),
        "redeemed_by": None
    }
    save_keys(keys)

    await ctx.send(f"✅ Key generated: `{key}`\nExpires in: {duration}")

@bot.command()
async def redeem(ctx, key: str):
    """Redeem a key and lock it to your Discord ID"""
    keys = load_keys()
    key = key.upper()

    if key not in keys:
        await ctx.send("❌ Invalid key.")
        return

    data = keys[key]

    if data["redeemed_by"] and data["redeemed_by"] != str(ctx.author.id):
        await ctx.send("❌ This key is already redeemed by another user.")
        return

    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.utcnow() > expires_at:
        await ctx.send("❌ This key has expired.")
        return

    if not data["redeemed_by"]:
        data["redeemed_by"] = str(ctx.author.id)
        save_keys(keys)

    await ctx.send(f"✅ Key redeemed successfully! Locked to {ctx.author.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def revokekey(ctx, key: str):
    """Revoke a key"""
    keys = load_keys()
    key = key.upper()

    if key not in keys:
        await ctx.send("❌ Key not found.")
        return

    del keys[key]
    save_keys(keys)
    await ctx.send(f"✅ Key `{key}` revoked and deleted.")

@bot.command()
@commands.has_permissions(administrator=True)
async def keyinfo(ctx, key: str):
    """Get info about a key"""
    keys = load_keys()
    key = key.upper()

    if key not in keys:
        await ctx.send("❌ Key not found.")
        return

    data = keys[key]
    created = data["created_at"]
    expires = data["expires_at"]
    redeemed_by = data["redeemed_by"] or "Not redeemed"

    await ctx.send(f"**Key:** `{key}`\nCreated at: {created}\nExpires at: {expires}\nRedeemed by: {redeemed_by}")

@bot.command()
async def panel(ctx):
    """Show the interactive panel with buttons"""
    await ctx.send("Select an option:", view=Panel())

# Run your bot
token = os.getenv("DISCORD_TOKEN")
if not token:
    print("❌ DISCORD_TOKEN not set in environment variables.")
    exit(1)

bot.run(token)
