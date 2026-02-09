import os
import re
import json
from collections import Counter
from datetime import datetime, date, timezone

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Load token from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

LOG_CHANNEL_IDS = {1468075184505360394, 1468264499596230718}

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
GUILD_OBJ = discord.Object(id=GUILD_ID) if GUILD_ID else None

# Dropdown options for Hosting Format
FORMAT_CHOICES = [
    app_commands.Choice(name="Big Brother", value="big_brother"),
    app_commands.Choice(name="BB Mini", value="bb_mini"),
    app_commands.Choice(name="BB Spinoff", value="bb_spinoff"),
    app_commands.Choice(name="Survivor", value="survivor"),
    app_commands.Choice(name="The Traitors", value="the_traitors"),
    app_commands.Choice(name="Mafia", value="mafia"),
    app_commands.Choice(name="Scandal", value="scandal"),
    app_commands.Choice(name="The Challenge", value="the_challenge"),
    app_commands.Choice(name="Sacrifice Sanctuary", value="sacrifice_sanctuary"),
    app_commands.Choice(name="Endurance", value="endurance"),
    app_commands.Choice(name="The Amazing Race", value="the_amazing_race"),
    app_commands.Choice(name="Obby Race", value="obby_race"),
    app_commands.Choice(name="Purge", value="purge"),
    app_commands.Choice(name="Comp Battles", value="comp_battles"),
    app_commands.Choice(name="Gear Battles", value="gear_battles"),
    app_commands.Choice(name="Guess The Song", value="guess_the_song"),
    app_commands.Choice(name="Drag Race", value="drag_race"),
    app_commands.Choice(name="Top Model", value="top_model"),
    app_commands.Choice(name="The Hunger Games", value="the_hunger_games"),
    app_commands.Choice(name="Other", value="other"),
]

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

@bot.tree.command(
    name="activitylog",
    description="Log a hosting activity",
    guild=GUILD_OBJ  # real server only
)
@app_commands.describe(
    format="Choose the game format",
    cast="Number of players",
    log_url="Link to the hosting log message"
)
@app_commands.choices(format=FORMAT_CHOICES)
async def activitylog(
    interaction: discord.Interaction,
    format: app_commands.Choice[str],
    cast: int,
    log_url: str
):
    # Basic validation
    if cast <= 0 or cast > 100:
        await interaction.response.send_message("❌ Cast must be a reasonable number.", ephemeral=True)
        return

    if not (log_url.startswith("http://") or log_url.startswith("https://")):
        await interaction.response.send_message("❌ Log link must be a valid URL (http/https).", ephemeral=True)
        return

    # Write to Google Sheet
    sheet = get_sheet()

    activity_log_link = (
    f"https://discord.com/channels/"
    f"{interaction.guild_id}/"
    f"{interaction.channel_id}/"
    f"{interaction.id}"
  )

    sheet.append_row(
    [
        datetime.now().isoformat(timespec="seconds"),  # Date Logged
        interaction.user.display_name,                 # Host
        format.name,                                   # Format
        cast,                                          # Cast Size
        log_url,                                       # Hosting Logs Message Link
        activity_log_link,                             # Activity Logs Message Link
    ],
    value_input_option="USER_ENTERED",
  )

    await interaction.response.send_message(
        "**✅ Log received! View your activity here:** "
        "https://docs.google.com/spreadsheets/d/1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI/edit?usp=sharing"
    )

# Helper functions for the /activitystats command

def try_parse_sheet_date(value) -> date | None:
    """
    Your sheet's "Date Logged" column is expected to be something like:
      2026-02-08T17:12:34
    or possibly:
      2026-02-08 17:12:34
    or:
      2026-02-08
    This returns a Python date (YYYY-MM-DD) or None if it can't parse.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Normalize a few common ISO variants
    text = text.replace("Z", "")  # remove Z if present

    # Try ISO datetime first
    try:
        # Accept both "YYYY-MM-DDTHH:MM:SS" and "YYYY-MM-DD HH:MM:SS"
        iso_text = text.replace(" ", "T")
        return datetime.fromisoformat(iso_text).date()
    except ValueError:
        pass

    # Try date-only
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def matches_host(row_host: str, query: str) -> bool:
    """
    Case-insensitive substring match. So query="josh" will match "Josh Whalen".
    """
    return query.lower().strip() in (row_host or "").lower()


def pretty_range(start_dt: datetime | None, end_dt: datetime | None) -> str:
    if not start_dt and not end_dt:
        return "All time"
    s = start_dt.date().isoformat() if start_dt else "…"
    e = end_dt.date().isoformat() if end_dt else "…"
    return f"{s} → {e}"

# Slash command /activitystats starts here
@bot.tree.command(
    name="activitystats",
    description="Get hosting stats for a host (optional date range).",
    guild=GUILD_OBJ,  # real server only, same as /activitylog
)
@app_commands.describe(
    host="Host name (partial match works, ex: josh)",
    start="Optional start (use the date/time picker)",
    end="Optional end (use the date/time picker)",
)
async def activitystats(
    interaction: discord.Interaction,
    host: str,
    start: datetime | None = None,
    end: datetime | None = None,
):
    # Convert picker datetimes into dates (we ignore time)
    start_date = start.date() if start else None
    end_date = end.date() if end else None

    if start_date and end_date and start_date > end_date:
        await interaction.response.send_message(
            "❌ Start date must be on or before end date.",
            ephemeral=True,
        )
        return

    # Load all rows from the sheet (dicts keyed by header names)
    sheet = get_sheet()
    rows = sheet.get_all_records()

    # Filter rows by host + date range
    filtered = []
    for r in rows:
        row_host = r.get("Host", "")
        if not matches_host(row_host, host):
            continue

        d = try_parse_sheet_date(r.get("Date Logged"))
        if not d:
            continue

        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue

        filtered.append(r)

    if not filtered:
        await interaction.response.send_message(
            f"ℹ️ No activity found for **{host}** in range **{pretty_range(start, end)}**.",
            ephemeral=True,
        )
        return

    total = len(filtered)

    # Breakdown by format
    formats = [(r.get("Format") or "Unknown").strip() for r in filtered]
    counts = Counter(formats)
    top = counts.most_common(25)

    lines = []
    for fmt, n in top:
        pct = (n / total) * 100
        lines.append(f"• **{fmt}** — {n} ({pct:.1f}%)")

    response = (
        f"📊 **Activity Stats**\n"
        f"**Host match:** `{host}`\n"
        f"**Range:** **{pretty_range(start, end)}**\n"
        f"**Total hostings:** **{total}**\n\n"
        f"**By format:**\n" + "\n".join(lines)
    )

    await interaction.response.send_message(response, ephemeral=True)
    
# Run the bot
bot.run(TOKEN)