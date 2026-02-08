import os
import re
import json
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

LOG_CHANNEL_IDS = {1468075184505360394, 1468264499596230718}

# Load token from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Google Sheet config. info
SHEET_ID = "1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI"
SHEET_TAB_NAME = "Activity Logs"
SERVICE_ACCOUNT_FILE = None

# Set up intents (permissions)
intents = discord.Intents.default()

# Setting up my function to get the Activity Logger Sheet
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    google_creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

    creds = Credentials.from_service_account_info(
      google_creds,
      scopes=scopes
    )

    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SHEET_ID)

    return sh.worksheet(SHEET_TAB_NAME)

# Create bot instance
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

@bot.event
async def on_ready():
    guild_id = os.getenv("GUILD_ID")
    if guild_id:
        guild = discord.Object(id=int(guild_id))
        await bot.tree.sync(guild=guild)  # fast, server-only
        print(f"✅ Synced commands to guild {guild_id}")
    else:
        await bot.tree.sync()  # fallback: global
        print("✅ Synced commands globally")

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="activitylog", description="Test command")
async def activitylog(interaction: discord.Interaction):
    await interaction.response.send_message("✅ /activitylog is working!")
  
sheet = get_sheet()


timestamp = datetime.now().isoformat(timespec="seconds")
# host = ctx.author.display_name
# message_link = ctx.message.jump_url

# sheet.append_row(
#    [
#        timestamp,
#        host,

#        message_link
#    ],
#    value_input_option="USER_ENTERED"
#  )
  
# response = (
#        "**✅ Log received! View your activity [here](https://docs.google.com/spreadsheets/d/1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI/edit?usp=sharing)**\n ")
# await ctx.send(response)

# @bot.event
# async def on_command_error(ctx, error):
#    if isinstance(error, commands.CommandNotFound):
#        return  # ignore unknown commands
#    raise error

# Run the bot
bot.run(TOKEN)