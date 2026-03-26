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

# Loading token from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Establishing #activity-logs as the only allowed channel for the bot to work in
LOG_CHANNEL_ID = 1468264499596230718
ALLOWED_CHANNEL_ID = 1468264499596230718

# Establishing that only real messages from #hosting-logs can be used for the Log Link: part of /activitylog bot
HOSTING_SERVER_ID = 123456789012345678
HOSTING_LOG_CHANNEL_ID = 234567890123456789

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

# Dropdown Options for Host Type
HOST_TYPE_CHOICES = [
    app_commands.Choice(name="My Own Hosting", value="My Own Hosting"),
    app_commands.Choice(name="Co-Hosting", value="Co-Hosting"),
    app_commands.Choice(name="Hosting Takeover", value="Hosting Takeover"),
]

# Dropdown Options for Casting Selection Process
CASTING_PROCESS_CHOICES = [
    app_commands.Choice(name="Standard", value="Standard"),
    app_commands.Choice(name="Handpicked", value="Handpicked"),
    app_commands.Choice(name="All", value="All"),
]

# Creates dropdown for Cast Size (from 5 to 30 with an option for 30+)
CAST_SIZE_CHOICES = [
    *[app_commands.Choice(name=str(i), value=str(i)) for i in range(5, 28)],
    app_commands.Choice(name="28+", value="28+"),
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
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global command(s).")

        if GUILD_OBJ:
            guild_synced = await bot.tree.sync(guild=GUILD_OBJ)
            print(f"Synced {len(guild_synced)} command(s) to guild.")
        else:
            print("No GUILD_ID set; skipping guild sync.")
    except Exception as e:
        print("Sync failed:", e)

@bot.tree.command(
    name="activitylog",
    description="Log a hosting activity",
    guild=GUILD_OBJ
)

@app_commands.describe(
    host_type="Choose the host type",
    format="Choose the game format",
    casting_process="Select casting process",
    cast="Select cast size",
    log_url="Link to the hosting log message"
)

@app_commands.choices(
    host_type=HOST_TYPE_CHOICES,
    format=FORMAT_CHOICES,
    casting_process=CASTING_PROCESS_CHOICES,
    cast=CAST_SIZE_CHOICES
)

async def activitylog(
    interaction: discord.Interaction,
    host_type: app_commands.Choice[str],
    format: app_commands.Choice[str],
    casting_process: app_commands.Choice[str],
    cast: app_commands.Choice[str],
    log_url: str
):
    # ACK immediately so Discord doesn't timeout
    await interaction.response.defer()

    # Restricting the command for just #activity-logs channel
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ This command can only be used in the activity log channel.",
            ephemeral=True
        )
        return

    # URL validation
    if not (log_url.startswith("http://") or log_url.startswith("https://")):
        await interaction.followup.send("❌ Log link must be a valid URL (http/https).", ephemeral=True)
        return

    activity_log_link = (
        f"https://discord.com/channels/"
        f"{interaction.guild_id}/"
        f"{interaction.channel_id}/"
        f"{interaction.id}"
    )

    try:
        sheet = get_sheet()
        sheet.append_row(
            [
                datetime.now().isoformat(timespec="seconds"),
                interaction.user.display_name,
                format.name,
                host_type.value,
                casting_process.name,
                cast.value,
                log_url,
                activity_log_link,
            ],
            value_input_option="USER_ENTERED",
        )

        await interaction.followup.send(
            "**✅ Log received! View your activity here:** "
            "https://docs.google.com/spreadsheets/d/1oI3CNAzxhC8GvMPYoBpnQcTRY_OwKrKMiAhg_uOn5YI/edit?usp=sharing",
            
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Something went wrong while logging to Google Sheets:\n`{type(e).__name__}: {e}`",
            ephemeral=True
        )

# ========= Helper functions =========

DISCORD_MESSAGE_LINK_RE = re.compile(
    r"^https://discord\.com/channels/(\d+)/(\d+)/(\d+)$"
)

def parse_discord_message_link(url: str):
    match = DISCORD_MESSAGE_LINK_RE.match(url.strip())
    if not match:
        return None

    guild_id, channel_id, message_id = map(int, match.groups())
    return guild_id, channel_id, message_id

# Helper for breaking down Discord datetime. Accepts 'YYYY-MM-DD' and returns a date object, or None if s is None/empty. Raises ValueError if provided but invalid format.
def parse_yyyy_mm_dd(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


# Flexible date parsing helper function for multiple formats
def parse_sheet_date(cell_value: str) -> Optional[date]:
    if not cell_value:
        return None

    raw = str(cell_value).strip()

    # Try ISO datetime: 2026-03-23T15:00:00
    if "T" in raw:
        try:
            return datetime.strptime(raw.split("T", 1)[0], "%Y-%m-%d").date()
        except ValueError:
            pass

    # Try ISO-ish with space: 2026-03-23 15:00:00
    try:
        return datetime.strptime(raw.split(" ", 1)[0], "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try pretty formatted date: Monday, March 23, 2026 @ 3:00 PM
    try:
        return datetime.strptime(raw, "%A, %B %d, %Y @ %I:%M %p").date()
    except ValueError:
        pass

    # Try shorter pretty formatted date just in case
    try:
        return datetime.strptime(raw, "%a, %b %d, %Y @ %I:%M %p").date()
    except ValueError:
        pass

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
    await interaction.response.defer()

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