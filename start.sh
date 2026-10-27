#!/bin/bash
# Double-click to start aichivist – no installation needed.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is missing / Python 3 fehlt: https://www.python.org/downloads/"
  xdg-open "https://www.python.org/downloads/" 2>/dev/null
else
  python3 -m aichivist start
fi
read -r -p "Enter …"
