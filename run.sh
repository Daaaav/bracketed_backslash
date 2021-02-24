#!/bin/bash

# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
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
	python3.9 main.py

	# Copy $? to a separate variable. If we don't do this,
	# it'll be overwritten by `echo` when we do the `notify-send`
	EXITCODE=$?

	if [ $EXITCODE -eq 0 ]; then
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}${EXITCODE}${LIGHTBLUE}: Ctrl-C used!${NOCOLOR}" >&2
		notify-send "[\\] has been stopped"
		exit 0
	elif [ $EXITCODE -eq 4 ]; then
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}${EXITCODE}${LIGHTBLUE}: kill command used!${NOCOLOR}" >&2
		notify-send "[\\] has been stopped"
		exit 0
	elif [ $EXITCODE -eq 8 ]; then
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}${EXITCODE}${LIGHTBLUE}: restart command used!${NOCOLOR}" >&2
		notify-send "[\\] restarting now"
	else
		echo -e "${LIGHTBLUE}Bot exited with exit code ${LIGHTCYAN}${EXITCODE}${LIGHTBLUE}: unhandled, probably crashed, restarting in 10s${NOCOLOR}" >&2
		notify-send "Bot exited with exit code ${EXITCODE}, restarting in 10s."
		sleep 10
	fi
done
