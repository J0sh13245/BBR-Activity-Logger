import os
from datetime import datetime
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

LOG_CHANNEL_ID = 1468075184505360394

# Load token from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Google Sheet config. info
SHEET_ID = "1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI"
SHEET_TAB_NAME = "Sheet1"
SERVICE_ACCOUNT_FILE = "service_account.json"

# Set up intents (permissions)
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
  print(f"Logged in as {bot.user}")

# Make bot ignore other Discord channels
@bot.event
async def on_message(message):
  if message.author.bot:
    return
  
  if message.channel.id != LOG_CHANNEL_ID:
    return
  
  await bot.process_commands(message)

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=scopes
    )

    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SHEET_ID)

    return sh.worksheet(SHEET_TAB_NAME)

@bot.command()
async def BBR(ctx, *, message):

  lines = message.split("\n")

  data = {}

  for line in lines:
    if ":" in line:
      key, value = line.split(":", 1)
      key = key.strip().lower()
      value = value.strip()

      data[key] = value

  format_name = data.get("format")
  cast = data.get("cast")
  log = data.get("log")


# Checking if the host's message has all parts
  if not all([format_name, cast, log]):
    await ctx.send("""
    ❌ **Submission not logged. Please double check your message format matches the following**:
    
    !BBR
    Cast: [Cast size, only include number]
    Date: [YYYY-MM-DD]
    Log: [Must include link to #hosting-logs]
    """)
    return
  if not log.startswith("http"):
    await ctx.send("**❌ Submission not logged. Log must be a valid URL to your #hosting-logs**")
    return
  
# Making sure cast is a number 
  m = re.search(r"\d+", cast)
  if not m:
    await ctx.send("**❌ Submission not logged. Cast must be a valid number**")
    return
  cast_num = int(m.group())

  sheet = get_sheet()

  timestamp = datetime.now().isoformat(timespec="seconds")
  host = ctx.author.display_name
  message_link = ctx.message.jump_url

  sheet.append_row(
    [
          timestamp,
          host,
          format_name,
          cast_num,
          log,
          message_link
    ],
    value_input_option="USER_ENTERED"
  )
  
  response = (
        "✅ Log received!\n"
        f"Format: {format_name}\n"
        f"Cast: {cast_num}\n"
        f"Log:  {log}"
        
  )

  await ctx.send(response)

# Run the bot
bot.run(TOKEN)