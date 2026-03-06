# Command Center — Daily Reference

## How it works
- launchd runs `command_center.py` every hour
- Script checks: is it 17:00–midnight Moscow time? Did I already act today?
- If both pass → macOS dialog pops up → you choose to Run or Not now
- "Not now" → dialog comes back in 1 hour
- "Run" → Terminal opens with the tool, no more reminders today

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
├── tools_config.json          # tools & schedule config
├── command_center.py          # the brain
├── com.command-center.daily.plist  # launchd scheduler
├── README.md                  # this file
└── state/
    └── last_acted.txt         # tracks "did I act today?"
```
