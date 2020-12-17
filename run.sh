#!/bin/bash

# [\] Discord bot
# Copyright 2020, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

if [[ -t 1 ]]; then
	LIGHTBLUE='\033[1;34m'
	LIGHTCYAN='\033[1;36m'
	NOCOLOR='\033[1;0m'
else
	LIGHTBLUE=''
	LIGHTCYAN=''
	NOCOLOR=''
fi

while true; do
	python3 main.py
	if [ $? -eq 4 ]; then
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}$?${LIGHTBLUE}: kill command used!${NOCOLOR}" >&2
		notify-send "[\\] has been stopped"
		exit 0
	elif [ $? -eq 8 ]; then
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}$?${LIGHTBLUE}: restart command used!${NOCOLOR}" >&2
		notify-send "[\\] restarting now"
	else
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}$?${LIGHTBLUE}: unhandled, probably crashed, restarting in 10s${NOCOLOR}" >&2
		notify-send "Bot exited with exit code $?, restarting in 10s."
		sleep 10
	fi
done
