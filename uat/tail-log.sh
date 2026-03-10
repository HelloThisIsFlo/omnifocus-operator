#!/usr/bin/env bash
# Tail the omnifocus-operator log file

LOG_FILE=~/Library/Logs/omnifocus-operator.log

# Parse args
CLEAR=false
for arg in "$@"; do
  case "$arg" in
    --clear)
      CLEAR=true
      ;;
  esac
done

# Ensure file exists
touch "$LOG_FILE"

# Optionally clear contents
if [ "$CLEAR" = true ]; then
  : > "$LOG_FILE"
fi

tail -f "$LOG_FILE"
