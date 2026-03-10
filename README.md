# Command Center — Daily Reminder for Important Tools

### What this does

- **Reminds you once per day** (around 17:00 Moscow time) to run your important tools.
- **Opens a simple macOS dialog** where you choose to run the tool now or later.
- **Stops reminding after you run it** once per Moscow day.

---

## How it works

- **Scheduler (`launchd`)**: macOS `launchd` runs `command_center.py` every hour from 14:00–21:00 **local Mac time**.
- **Moscow-time window**: the script only shows a dialog if the time in `Europe/Moscow` is between **17:00 and midnight**.
- **Once per day**: after you press **Run** at least once, the date is written to `state/last_acted.txt` and reminders stop until the next Moscow day.
- **“Not now” during real runs**: if you press **Not now** while in the window, the next hourly run (still in the window) will show the dialog again.
- **Sleep / wake**: if the Mac was asleep at a scheduled hour, `launchd` runs the script shortly after wake. The script checks the Moscow window and your “acted today” state each time.

---

## Daily commands (manual use)

Run these from Terminal:

```bash
cd ~/Projects/command-center

# Show config, current Moscow time, window status, and whether you already acted today
python3 command_center.py --status

# Minimal self-check (good quick sanity test)
python3 command_center.py --self-check

# Force the dialog right now (ignores time window and acted-today flag)
python3 command_center.py --test

# Change the daily trigger time (Moscow time, HH:MM)
python3 command_center.py --set-time 18:30

# Clear today's "already acted" state so reminders start again
python3 command_center.py --reset

# Look at what launchd runs have logged
cat /tmp/command-center.log

# Clear the old log
echo "" > /tmp/command-center.log
```

---

## Scheduler management (launchd)

You only need to do this when installing or changing the plist.

```bash
# Copy (or recopy) the plist into LaunchAgents if needed
cp ~/Projects/command-center/com.command-center.daily.plist \
   ~/Library/LaunchAgents/com.command-center.daily.plist

# Stop the scheduler
launchctl unload ~/Library/LaunchAgents/com.command-center.daily.plist 2>/dev/null || true

# Start (or reload) the scheduler
launchctl load -w ~/Library/LaunchAgents/com.command-center.daily.plist

# Check if it's loaded for the current user
launchctl list | grep command-center
```

If `launchctl list` shows `com.command-center.daily`, Command Center is loaded and will run hourly.

---

## Timezone details

- **Scheduler timezone**: the plist uses 14:00–21:00 **local Mac time** (e.g. Lithuania).
- **Logic timezone**: the Python script uses `Europe/Moscow` (UTC+3) from `tools_config.json` to decide whether to show the dialog.
- **DST shifts**:
  - When Lithuania is UTC+2 (winter), 14:00–21:00 local ≈ 16:00–23:00 Moscow.
  - When Lithuania is UTC+3 (summer), 14:00–21:00 local ≈ 17:00–00:00 Moscow.
- **Extra hourly runs**: if `launchd` fires outside the Moscow window, the script logs “Outside reminder window. Exiting.” and does nothing visible.

You normally do not need to think about this—just set your desired Moscow trigger time with `--set-time`.

---

## Adding a new tool

Command Center reads from `tools_config.json`.

1. Open `~/Projects/command-center/tools_config.json`.
2. Add a new entry under the `tools` array:

```json
{
  "id": "my_new_tool",
  "name": "My New Tool",
  "description": "What it does",
  "working_dir": "~/path/to/tool",
  "venv": "venv",
  "command": "python main.py",
  "terminal": true
}
```

Notes:
- `working_dir` is where the tool lives.
- `venv` is the virtualenv folder name inside that directory (or omit it if you don’t use venvs).
- `terminal: true` means “open a Terminal window and run this command there”.

No code changes are needed — the dialog picks up new tools automatically.

---

## Files in this project

```text
~/Projects/command-center/
├── tools_config.json               # Tools registry & schedule config
├── command_center.py               # Reminder logic, macOS dialogs, tool launcher
├── com.command-center.daily.plist  # launchd scheduler (fires hourly 14–21 local)
├── README.md                       # This file
└── state/
    └── last_acted.txt              # Tracks "did user act today?" in Moscow time
```

Keep this folder where the plist expects it (in `/Users/serj/Projects/command-center/`) so the scheduler can always find `command_center.py`.