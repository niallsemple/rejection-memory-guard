#!/bin/bash
# Run on the Mac. Step 1 (stop night-shift) + Step 2 scaffolding.
set -u
UIDN=$(id -u); PL=~/Library/LaunchAgents/com.nightshift.launcher.plist
echo "== before =="; launchctl list | grep -i nightshift
launchctl bootout gui/$UIDN/com.nightshift.launcher 2>&1 || launchctl unload "$PL" 2>&1
sleep 2; pkill -f nightshift.py; sleep 2; pkill -9 -f nightshift.py
echo "== after =="; launchctl list | grep -i nightshift; pgrep -fl nightshift.py || echo "no nightshift.py procs"
ls -l "$PL"
echo "RESTORE: launchctl bootstrap gui/$UIDN $PL"
R=~/Documents/rejection-memory-guard; mkdir -p "$R"; cd "$R"
[ -d .git ] || git init -q
python3 -m venv .venv && .venv/bin/pip -q install -U pip pytest pytest-timeout
