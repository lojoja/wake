#!/usr/bin/env bash
#
# Initializes the devolpment environment
#

VENV=".venv"

if [[ -d "$VENV" ]]
then
  /usr/local/bin/python3 -m venv --copies --upgrade "$VENV"
else
  /usr/local/bin/python3 -m venv --copies "$VENV"
fi

$VENV/bin/pip3 install -r requirements.txt
