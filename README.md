# Command Center — Daily Reference

## How it works
- **Scheduler**: macOS `launchd` runs `command_center.py` every hour from 14:00–21:00 **local Mac time**.
- **Time window**: the script decides to show a dialog only if the current time in `Europe/Moscow` is between **17:00 and midnight**.
- **Once per day**: after you choose **Run** at least once, it remembers this in `state/last_acted.txt` and stays quiet until the next day (Moscow date).
- **“Not now” during real runs**: if you click **Not now** during the window, you will be asked again on the next hourly run while the window is still open.
- **Sleep handling**: if the Mac was asleep at a scheduled time, `launchd` will run the job shortly after wake; the script re-checks the Moscow window and state then.

## Daily commands

```bash
cd ~/Projects/command-center

# Check what's going on (config, window, acted-today flag)
python3 command_center.py --status

# Quick self-check (Moscow time, window, acted-today)
python3 command_center.py --self-check

# Force the dialog right now (ignores time & acted state)
python3 command_center.py --test

# Change trigger time (Moscow time)
python3 command_center.py --set-time 18:30

# Re-enable reminders after you already ran today
python3 command_center.py --reset

# Check the log (what launchd runs look like)
cat /tmp/command-center.log

# Clear old log
echo "" > /tmp/command-center.log
```

## Scheduler management

```bash
# Stop the scheduler
launchctl unload ~/Library/LaunchAgents/com.command-center.daily.plist

# Start (or reload) the scheduler
launchctl load ~/Library/LaunchAgents/com.command-center.daily.plist

# Check if it's running
launchctl list | grep command-center
```

## Timezone note

- **Scheduler timezone**: the plist fires at 14:00–21:00 **local Mac time** (e.g. Lithuania).
- **Logic timezone**: the Python script always uses `Europe/Moscow` (UTC+3) from `tools_config.json` to decide whether to show the dialog.
- **DST effects**: when Lithuania is UTC+2 (winter), 14:00–21:00 local covers roughly 16:00–23:00 Moscow; when Lithuania is UTC+3 (summer), it covers 17:00–00:00 Moscow.
- **Extra runs**: if `launchd` runs the script outside the Moscow window, it simply logs “Outside reminder window. Exiting.” and does nothing.

## Adding a new tool

Edit `~/Projects/command-center/tools_config.json`, add to the `tools` array:

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

No other changes needed — the dialog picks it up automatically.

## Files

```
~/Projects/command-center/
├── tools_config.json               # Tools registry & schedule config
├── command_center.py               # Reminder logic, macOS dialogs, tool launcher
├── com.command-center.daily.plist  # launchd scheduler (fires hourly 14–21 local)
├── README.md                       # This file
└── state/
    └── last_acted.txt              # Tracks "did user act today?"
```