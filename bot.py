import os
import re
import json
from collections import Counter
from datetime import datetime, date
from typing import Optional, Tuple, List

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

# ========= Helper functions =========

def parse_yyyy_mm_dd(s: Optional[str]) -> Optional[date]:
    """
    Accepts 'YYYY-MM-DD' and returns a date object, or None if s is None/empty.
    Raises ValueError if provided but invalid format.
    """
    if not s:
        return None
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def parse_sheet_date(cell_value: str) -> Optional[date]:
    """
    Your sheet uses ISO like '2026-02-08T17:26:18' (or similar).
    This extracts the date portion safely.
    """
    if not cell_value:
        return None

    raw = str(cell_value).strip()

    # If it's ISO datetime: 'YYYY-MM-DDTHH:MM:SS'
    if "T" in raw:
        raw = raw.split("T", 1)[0]

    # If it's ISO-ish with space: 'YYYY-MM-DD HH:MM:SS'
    if " " in raw:
        raw = raw.split(" ", 1)[0]

    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def host_matches(sheet_host: str, query: str) -> bool:
    """
    Flexible matching:
    - ignores case
    - ignores leading/trailing spaces
    - supports partial match (so "Josh" matches "JOsh13245")
    """
    a = (sheet_host or "").strip().lower()
    b = (query or "").strip().lower()
    if not b:
        return False
    return b in a


def load_activity_rows(sheet) -> List[list]:
    """
    Returns all rows except header.
    gspread: sheet.get_all_values() returns list[list[str]]
    """
    values = sheet.get_all_values()
    if not values or len(values) < 2:
        return []
    return values[1:]  # skip header


def filter_rows_for_stats(
    rows: List[list],
    host_query: str,
    start: Optional[date],
    end: Optional[date],
) -> List[list]:
    """
    Filters rows by host substring + optional inclusive date range.
    """
    out = []
    for r in rows:
        # Defensive: ensure row has at least the columns we expect
        # Date Logged (0), Host (1), Format (2)
        if len(r) < 3:
            continue

        row_date = parse_sheet_date(r[0])
        row_host = r[1]
        if not row_date:
            continue

        if not host_matches(row_host, host_query):
            continue

        if start and row_date < start:
            continue
        if end and row_date > end:
            continue

        out.append(r)

    return out


def format_breakdown_message(total: int, counts: Counter) -> str:
    """
    Produces a nice breakdown string.
    """
    if total == 0:
        return "No activity found."

    lines = []
    for fmt, c in counts.most_common():
        pct = (c / total) * 100
        lines.append(f"• **{fmt}** — {c} ({pct:.1f}%)")
    return "\n".join(lines)


# ========= /activitystats command =========
# IMPORTANT: this uses ONLY supported slash types:
# host: str, start_date: str, end_date: str

@bot.tree.command(
    name="activitystats",
    description="Get hosting stats for a host (optional date range).",
    guild=GUILD_OBJ  # real server only (same style as /activitylog)
)
@app_commands.describe(
    host="Host name (or partial) e.g. Josh",
    start_date="Start date YYYY-MM-DD (optional)",
    end_date="End date YYYY-MM-DD (optional)"
)
async def activitystats(
    interaction: discord.Interaction,
    host: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    # Defer if your sheet can be slow (prevents Discord 'interaction failed')
    await interaction.response.defer(ephemeral=True)

    # Parse date inputs safely
    try:
        start = parse_yyyy_mm_dd(start_date)
    except ValueError:
        await interaction.followup.send("❌ Start date must be in `YYYY-MM-DD` format.", ephemeral=True)
        return

    try:
        end = parse_yyyy_mm_dd(end_date)
    except ValueError:
        await interaction.followup.send("❌ End date must be in `YYYY-MM-DD` format.", ephemeral=True)
        return

    if start and end and start > end:
        await interaction.followup.send("❌ Start date cannot be after end date.", ephemeral=True)
        return

    # Load sheet rows
    sheet = get_sheet()
    rows = load_activity_rows(sheet)

    # Filter
    matches = filter_rows_for_stats(rows, host_query=host, start=start, end=end)

    total = len(matches)
    if total == 0:
        # Show what range was used for clarity
        range_txt = ""
        if start or end:
            range_txt = f"\nDate range: `{start_date or '…'}` → `{end_date or '…'}`"
        await interaction.followup.send(
            f"❌ No activity found for **{host}**.{range_txt}",
            ephemeral=True
        )
        return

    # Count by format (Format column index = 2)
    fmt_counts = Counter((r[2] or "Unknown").strip() for r in matches)

    # Build response
    range_part = ""
    if start or end:
        range_part = f"\n**Date range:** `{start_date or '…'}` → `{end_date or '…'}`"

    breakdown = format_breakdown_message(total, fmt_counts)

    msg = (
        f"📊 **Activity Stats**\n"
        f"**Host:** {host}\n"
        f"**Total hostings:** {total}"
        f"{range_part}\n\n"
        f"**By format:**\n{breakdown}"
    )

    await interaction.followup.send(msg, ephemeral=True)
    
# Run the bot
bot.run(TOKEN)