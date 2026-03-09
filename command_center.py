#!/usr/bin/env python3
"""
Command Center — daily tool launcher for macOS.

Reads tools_config.json, shows a macOS dialog to pick which tools to run,
and opens them in Terminal. Designed to be triggered by launchd every hour.

Skips silently if:
  - Current time is outside the reminder window (before trigger, after stop)
  - You already ran a tool today (tracked in state/last_acted.txt)

Use --test to bypass both checks and force the dialog.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "tools_config.json"
LAST_ACTED_PATH = SCRIPT_DIR / "state" / "last_acted.txt"


def _escape_applescript(text: str) -> str:
    """Escape quotes and backslashes for safe embedding in AppleScript strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def now_in_tz(tz_name):
    return datetime.now(ZoneInfo(tz_name))


def already_acted_today(tz_name):
    if not LAST_ACTED_PATH.exists():
        return False
    last_date = LAST_ACTED_PATH.read_text().strip()
    today = now_in_tz(tz_name).strftime("%Y-%m-%d")
    # If the state file has unexpected content, treat as "not acted" to avoid
    # suppressing reminders due to a corrupted value.
    if len(last_date) != 10:
        return False
    return last_date == today


def mark_acted(tz_name):
    LAST_ACTED_PATH.parent.mkdir(exist_ok=True)
    today = now_in_tz(tz_name).strftime("%Y-%m-%d")
    LAST_ACTED_PATH.write_text(today)


def in_reminder_window(schedule):
    now = now_in_tz(schedule["timezone"])
    trigger_h, trigger_m = map(int, schedule["trigger_time"].split(":"))
    stop_h = schedule["stop_after_hour"]

    current = now.hour * 60 + now.minute
    trigger = trigger_h * 60 + trigger_m
    stop = 24 * 60 if stop_h == 0 else stop_h * 60

    return trigger <= current < stop


def show_dialog(tools):
    """Show macOS dialog. Returns list of selected tool IDs."""

    if len(tools) == 1:
        t = tools[0]
        name = _escape_applescript(t["name"])
        desc = _escape_applescript(t["description"])
        script = (
            'display dialog '
            f'"Daily Tools\\n\\n{name}\\n{desc}\\n\\nRun it now?" '
            'buttons {"Not now", "Run"} default button "Run" '
            'with title "Command Center"'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0 and "Run" in result.stdout:
            return [t["id"]]
        return []

    else:
        escaped_names = [_escape_applescript(t["name"]) for t in tools]
        names = '", "'.join(escaped_names)
        script = (
            f'set toolList to {{"{names}"}}\n'
            'set chosen to choose from list toolList '
            'with title "Command Center" '
            'with prompt "Daily Tools\\n\\nSelect tools to run:" '
            'OK button name "Run Selected" '
            'cancel button name "Not now" '
            'with multiple selections allowed\n'
            'if chosen is false then\n'
            '    return "CANCELLED"\n'
            'else\n'
            '    set AppleScript\'s text item delimiters to "||"\n'
            '    return chosen as text\n'
            'end if'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0 or "CANCELLED" in result.stdout:
            return []
        selected = [n.strip() for n in result.stdout.strip().split("||")]
        return [t["id"] for t in tools if t["name"] in selected]


def launch_tool(tool):
    """Open Terminal and run the tool."""
    working_dir = os.path.expanduser(tool["working_dir"])

    parts = [f"cd {working_dir}"]
    if tool.get("venv"):
        parts.append(f"source {tool['venv']}/bin/activate")
    parts.append(tool["command"])

    full_cmd = " && ".join(parts)

    if tool.get("terminal", True):
        apple_script = (
            'tell application "Terminal"\n'
            '    activate\n'
            f'    do script "{full_cmd}"\n'
            'end tell'
        )
        subprocess.run(["osascript", "-e", apple_script])
    else:
        subprocess.Popen(full_cmd, shell=True, cwd=working_dir)


def log(msg):
    """Print a timestamped status line."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def set_time(new_time):
    """Update trigger time in config."""
    try:
        h, m = map(int, new_time.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except ValueError:
        print(f"❌ Invalid time format: {new_time}")
        print("   Use HH:MM, e.g. 17:00 or 09:30")
        sys.exit(1)

    config = load_config()
    old_time = config["schedule"]["trigger_time"]
    tz = config["schedule"]["timezone"]
    config["schedule"]["trigger_time"] = new_time
    save_config(config)
    print(f"✅ Trigger time changed: {old_time} → {new_time} ({tz})")


def show_status():
    config = load_config()
    schedule = config["schedule"]
    tz = schedule["timezone"]
    now = now_in_tz(tz)
    acted = already_acted_today(tz)
    in_window = in_reminder_window(schedule)
    stop = "midnight" if schedule["stop_after_hour"] == 0 else f'{schedule["stop_after_hour"]}:00'

    print()
    print("═══ Command Center Status ═══")
    print()
    print(f"  ⏰ Trigger time:   {schedule['trigger_time']} ({tz})")
    print(f"  🔁 Retry every:    {schedule['retry_interval_minutes']} min")
    print(f"  🛑 Stop after:     {stop}")
    print(f"  🕐 Current time:   {now.strftime('%H:%M')} ({tz})")
    print(f"  📍 In window:      {'yes ✅' if in_window else 'no ⏸'}")
    print(f"  ✅ Acted today:    {'yes — done for today' if acted else 'no — will remind'}")
    print()
    print(f"  🛠 Tools ({len(config['tools'])}):")
    for t in config["tools"]:
        print(f"     • {t['name']}")
        print(f"       {t['description']}")
        print(f"       dir: {t['working_dir']}  cmd: {t['command']}")
    print()


def self_check():
    """Print a quick diagnostic summary for troubleshooting."""
    config = load_config()
    schedule = config["schedule"]
    tz = schedule["timezone"]
    now = now_in_tz(tz)
    in_window = in_reminder_window(schedule)
    acted = already_acted_today(tz)

    print("═══ Command Center Self-check ═══")
    print(f"  Timezone:         {tz}")
    print(f"  Current time:     {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Trigger time:     {schedule['trigger_time']}")
    stop_label = "midnight" if schedule["stop_after_hour"] == 0 else f"{schedule['stop_after_hour']}:00"
    print(f"  Stop after:       {stop_label}")
    print(f"  In window now?:   {'yes' if in_window else 'no'}")
    print(f"  Acted today?:     {'yes' if acted else 'no'}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Command Center — daily tool launcher for macOS.\n"
            "\n"
            "Triggered by launchd every hour. Shows a macOS dialog\n"
            "to pick tools to run, then opens them in Terminal.\n"
            "Stops reminding after you run something or the day ends."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 command_center.py                 normal run (launchd calls this)\n"
            "  python3 command_center.py --test           force dialog, ignore time & acted state\n"
            "  python3 command_center.py --set-time 18:30 change trigger to 18:30 Moscow time\n"
            "  python3 command_center.py --reset          clear today's state, re-enable reminders\n"
            "  python3 command_center.py --status         show config, time window, acted state\n"
            "\n"
            "config:  ~/command-center/tools_config.json\n"
            "state:   ~/command-center/state/last_acted.txt\n"
            "logs:    /tmp/command-center.log (when run via launchd)"
        ),
    )
    parser.add_argument(
        "--test", action="store_true",
        help="bypass time window and acted check — force dialog to appear now"
    )
    parser.add_argument(
        "--set-time", metavar="HH:MM",
        help="set new daily trigger time in configured timezone (e.g. 17:00, 09:30)"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="clear today's acted status so reminders start again"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="show current settings, time window, and whether you acted today"
    )
    parser.add_argument(
        "--self-check", action="store_true",
        help="quick diagnostic: show timezone, current time, window status, and acted-today flag"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # --- Utility commands ---
    if args.set_time:
        set_time(args.set_time)
        return

    if args.status:
        show_status()
        return

    if args.self_check:
        self_check()
        return

    if args.reset:
        if LAST_ACTED_PATH.exists():
            LAST_ACTED_PATH.unlink()
        print("✅ Acted status cleared. Next run will show dialog.")
        return

    # --- Normal run ---
    config = load_config()
    schedule = config["schedule"]
    tools = config["tools"]
    tz = schedule["timezone"]
    now = now_in_tz(tz)

    log(f"Command Center started")
    log(f"Current time: {now.strftime('%H:%M')} ({tz})")
    stop_label = "midnight" if schedule["stop_after_hour"] == 0 else f"{schedule['stop_after_hour']}:00"
    log(f"Trigger window: {schedule['trigger_time']} — {stop_label}")
    log(f"Tools available: {len(tools)}")

    # Time window check
    if not args.test and not in_reminder_window(schedule):
        log(f"Outside reminder window. Exiting.")
        sys.exit(0)
    elif args.test:
        log(f"--test mode: skipping time window check")
    else:
        log(f"Inside reminder window ✅")

    # Acted today check
    if not args.test and already_acted_today(tz):
        log(f"Already acted today. Exiting.")
        sys.exit(0)
    elif args.test:
        log(f"--test mode: skipping acted check")
    else:
        log(f"Haven't acted today — showing dialog")

    # Show dialog
    log(f"Opening macOS dialog...")
    selected = show_dialog(tools)

    if not selected:
        if args.test:
            log("User chose 'Not now' in --test mode (no automatic retry).")
        else:
            log(f"User chose 'Not now'. Will retry in {schedule['retry_interval_minutes']} min.")
        sys.exit(0)

    log(f"Selected: {', '.join(selected)}")

    # Launch tools
    for tool in tools:
        if tool["id"] in selected:
            log(f"Launching: {tool['name']}...")
            launch_tool(tool)
            log(f"  → Terminal opened with: {tool['command']}")

    mark_acted(tz)
    log(f"Marked as acted for {now.strftime('%Y-%m-%d')}. No more reminders today.")
    log(f"Done.")


if __name__ == "__main__":
    main()
