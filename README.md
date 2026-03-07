# Command Center — Daily Reference

## How it works
- launchd triggers `command_center.py` at fixed hours (14:00–21:00 local time)
- Script checks: is it 17:00–midnight Moscow time? Did I already act today?
- If both pass → macOS dialog pops up → you choose to Run or Not now
- "Not now" → dialog comes back at the next hour
- "Run" → Terminal opens with the tool, no more reminders today
- If Mac was asleep at trigger time, launchd catches up when Mac wakes

## Daily commands

```bash
# Check what's going on
python3 ~/command-center/command_center.py --status

# Force the dialog right now (ignores time & acted state)
python3 ~/command-center/command_center.py --test

# Change trigger time (Moscow time)
python3 ~/command-center/command_center.py --set-time 18:30

# Re-enable reminders after you already ran today
python3 ~/command-center/command_center.py --reset

# Check the log (what launchd runs look like)
cat /tmp/command-center.log

# Clear old log
echo "" > /tmp/command-center.log
```

## Scheduler management

```bash
# Stop the scheduler
launchctl unload ~/Library/LaunchAgents/com.command-center.daily.plist

# Start the scheduler
launchctl load ~/Library/LaunchAgents/com.command-center.daily.plist

# Check if it's running
launchctl list | grep command-center
```

## Timezone note

The plist fires at 14:00–21:00 **local Mac time** (Lithuania). The script itself checks Moscow time (always UTC+3) to decide whether to show the dialog. Lithuania shifts between UTC+2 (winter) and UTC+3 (summer), so during winter the plist covers 16:00–23:00 Moscow, during summer 17:00–00:00 Moscow. The script handles this correctly — extra runs outside the Moscow window just exit silently.

## Adding a new tool

Edit `~/command-center/tools_config.json`, add to the `tools` array:

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
~/command-center/
├── tools_config.json               # Tools registry & schedule config
├── command_center.py               # Reminder logic, macOS dialogs, tool launcher
├── com.command-center.daily.plist  # launchd scheduler (fires hourly 14–21 local)
├── README.md                       # This file
└── state/
    └── last_acted.txt              # Tracks "did user act today?"
```