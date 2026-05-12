#!/bin/bash
# Run Phase 2 overnight, unattended.
# Output goes to logs/phase2.log; safe to close the terminal.
#
# Usage:  bash run_phase2.sh
#         tail -f logs/phase2.log   (to watch progress)

cd "$(dirname "$0")"
mkdir -p logs

echo "Starting Phase 2 at $(date)" | tee logs/phase2.log
nohup .venv/bin/python src/phase2.py >> logs/phase2.log 2>&1 &
PID=$!
echo "PID $PID — output → logs/phase2.log"
echo "Monitor: tail -f logs/phase2.log"
echo "Stop:    kill $PID"
echo $PID > logs/phase2.pid
