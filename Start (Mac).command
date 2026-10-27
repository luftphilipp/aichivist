#!/bin/bash
# Double-click to start aichivist – no installation needed.
cd "$(dirname "$0")" || exit 1
# a new Mac has /usr/bin/python3 only as a placeholder until the developer tools are installed
if [ "$(command -v python3)" = /usr/bin/python3 ] && ! xcode-select -p >/dev/null 2>&1; then
  echo "macOS now offers to install Python: click Install, wait until it is done, then double-click Start again."
  echo "macOS bietet jetzt an, Python zu installieren: auf Installieren klicken, warten, dann Start erneut doppelklicken."
  xcode-select --install 2>/dev/null
elif ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is missing / Python 3 fehlt: https://www.python.org/downloads/"
  open "https://www.python.org/downloads/" 2>/dev/null
else
  python3 -m aichivist start
fi
read -r -p "Enter …"
