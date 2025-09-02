import discord
from discord.ext import commands
import os
import json
import random
import string
from datetime import datetime, timedelta

# ===== CONFIG =====
TOKEN = os.getenv("DISCORD_TOKEN")  # Set this in Railway or your .env
KEY_FILE = "keys.json"
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# ===== KEY UTILS =====
def load_keys():
    if not os.path.exists(KEY_FILE):
        return {}
    with open(KEY_FILE, "r") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEY_FILE, "w") as f:
        json.dump(keys, f, indent=4)

def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def parse_expiration(duration_str):
    unit = duration_str[-1]
    num = int(duration_str[:-1])
    if unit == 'm':
        return timedelta(minutes=num)
    elif unit == 'h':
        return timedelta(hours=num)
    elif unit == 'd':
        return timedelta(days=num)
    else:
        raise ValueError("Invalid time format. Use `m`, `h`, or `d`.")


# ===== BOT EVENTS =====
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


# ===== ADMIN COMMANDS =====
@bot.command()
@commands.has_permissions(administrator=True)
async def generatekey(ctx, duration: str):
    try:
        expires_delta = parse_expiration(duration)
    except:
        await ctx.send("❌ Invalid time format. Use `10m`, `2h`, or `1d`.")
        return

    key = generate_key()
    keys = load_keys()

    now = datetime.utcnow()
    keys[key] = {
        "created_at": now.isoformat(),
        "expires_at": (now + expires_delta).isoformat(),
        "redeemed_by": None
    }

    save_keys(keys)

    try:
        await ctx.author.send(f"🔐 Your key: `{key}`\n⏰ Expires at: `{(now + expires_delta).isoformat()} UTC`")
        await ctx.reply("✅ Key sent in DMs.", ephemeral=True)
    except discord.Forbidden:
        await ctx.send("❌ I couldn't DM you the key. Please enable DMs.")


@bot.command()
async def redeem(ctx, key: str):
    key = key.upper()
    keys = load_keys()

    if key not in keys:
        await ctx.send("❌ Invalid key.")
        return

    if keys[key]["redeemed_by"]:
        await ctx.send("⚠️ Key already redeemed.")
        return

    expires = datetime.fromisoformat(keys[key]["expires_at"])
    if datetime.utcnow() > expires:
        await ctx.send("⌛ Key expired.")
        return

    keys[key]["redeemed_by"] = str(ctx.author.id)
    save_keys(keys)

    await ctx.send(f"✅ Key `{key}` redeemed successfully. It is now locked to you.")


@bot.command()
@commands.has_permissions(administrator=True)
async def keyinfo(ctx, key: str):
    key = key.upper()
    keys = load_keys()

    if key not in keys:
        await ctx.send("❌ Key not found.")
        return

    info = keys[key]
    embed = discord.Embed(title=f"🔐 Key Info: `{key}`", color=0x00ff00)
    embed.add_field(name="Created At", value=info["created_at"], inline=False)
    embed.add_field(name="Expires At", value=info["expires_at"], inline=False)
    embed.add_field(name="Redeemed By", value=info["redeemed_by"] or "❌ Not redeemed", inline=False)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def revokekey(ctx, key: str):
    key = key.upper()
    keys = load_keys()

    if key not in keys:
        await ctx.send("❌ Key not found.")
        return

    del keys[key]
    save_keys(keys)
    await ctx.send(f"🗑️ Key `{key}` has been revoked and deleted.")


# ===== START BOT =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN not set. Set it in Railway or your environment.")
    else:
        bot.run(TOKEN)
