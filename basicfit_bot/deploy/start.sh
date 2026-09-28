#!/bin/bash
# À utiliser dans une tâche planifiée DSM déclenchée "au démarrage".
# Lance le bot en arrière-plan pour que la tâche planifiée puisse se terminer.
set -e
cd "$(dirname "$0")/.."
nohup python3 main.py >> logs/stdout.log 2>&1 &
