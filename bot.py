import os
from datetime import datetime
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

LOG_CHANNEL_IDS = {1468075184505360394, 1468264499596230718}


# Load token from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Google Sheet config. info
SHEET_ID = "1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI"
SHEET_TAB_NAME = "Sheet1"
SERVICE_ACCOUNT_FILE = None

# Set up intents (permissions)
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

def allowed_channel(ch):
    # allow the channel itself OR threads under it
    if ch.id in LOG_CHANNEL_IDS:
        return True
    parent_id = getattr(ch, "parent_id", None)  # threads have parent_id
    if parent_id and parent_id in LOG_CHANNEL_IDS:
        return True
    return False

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not allowed_channel(message.channel):
        return

    await bot.process_commands(message)

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    import json
    import os

    google_creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

    creds = Credentials.from_service_account_info(
      google_creds,
      scopes=scopes
    )

    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SHEET_ID)

    return sh.worksheet(SHEET_TAB_NAME)

@bot.command()
async def BBR(ctx, *, message):

  import re

  def normalize_key(raw: str) -> str:
    k = raw.strip()

    # Remove markdown characters
    k = re.sub(r"[*_~`>]", "", k)

    # Normalize spaces
    k = re.sub(r"\s+", " ", k)

    return k.lower()
  
  def parse_fields(message: str) -> dict:
     data = {}

     # In case people try to use other words. Won't catch all, but will def catch some
     ALIASES = {
        "format": "format",
        "type": "format",
        "game format": "format",
        "hosting format": "format",
        "game type": "format",
        "hosting type": "format",
        "mode": "format",
        "game mode": "format",


        "cast": "cast",
        "size": "cast",
        "count": "cast",
        "cast size": "cast",
        "cast count": "cast",
        "player size": "cast",
        "player count": "cast",

        "log": "log",
        "link": "log",
        "hosting log": "log",
        "hosting link": "log",
        "log link": "log",
        "logs link": "log",
        "link to hosting log": "log",
        "link to hosting logs": "log",
        "hosting log link": "log",
        "hosting logs link": "log",
     }

     for line in message.splitlines():
        if ":" not in line:
           continue
        
        left, right = line.split(":", 1)

        key = normalize_key(left)
        value = right.strip()

        canonical = ALIASES.get(key)

        if canonical and value:
           data[canonical] = value

        return data
  await ctx.send("DEBUG RAW: \n" + ctx.message.content.replace("`", "'"))
  data = parse_fields(ctx.message.content)
  await ctx.send(f"DEBUG PARSED: {data}")

  format_name = data.get("format")
  cast = data.get("cast")
  log = data.get("log")

  missing = []
  if not format_name: missing.append("Format / Type")
  if not cast: missing.append("Cast / Players")
  if not log: missing.append("Log / Link")

  if missing:
     await ctx.send("❌ **Submission not logged. Missing: " + ", ".join(missing))

  # Checking if the host's message has all parts
  if not all([format_name, cast, log]):
    await ctx.send("""
    ❌ **Submission not logged. Please double check your message format includes the following**:
    
    !BBR
    Cast: [Cast size, only include number]
    Format: [Big Brother, Instant BB, BB FF, Survivor, etc.]
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
        "**✅ Log received! View your activity [here](https://docs.google.com/spreadsheets/d/1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI/edit?usp=sharing)**\n "
        
        
  )

  await ctx.send(response)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # ignore unknown commands
    raise error

# Run the bot
bot.run(TOKEN)