#!/bin/bash
# Script to launch the JobIt autonomous local daemon in background
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "=================================================="
echo "⚡ Starting JobIt Local Autonomous Daemon..."
echo "Directory: $DIR"
echo "Log file:  $DIR/reports/local_daemon.log"
echo "=================================================="

nohup python3 scripts/local_daemon.py >> "$DIR/reports/local_daemon.log" 2>&1 &
PID=$!
echo "Daemon started successfully with PID: $PID"
echo "To check live logs: tail -f reports/local_daemon.log"
echo "To stop daemon: kill $PID"

