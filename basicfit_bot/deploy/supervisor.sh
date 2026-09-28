#!/bin/bash
# À planifier toutes les 15-30 minutes dans le Task Scheduler DSM.
# Relance le bot s'il ne tourne plus (ex: après un crash ou un reboot manqué).
cd "$(dirname "$0")/.."
if ! pgrep -f "python3 main.py" > /dev/null; then
    nohup python3 main.py >> logs/stdout.log 2>&1 &
fi
