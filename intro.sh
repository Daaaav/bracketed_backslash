#!/bin/bash

#	[\] bot
#	Copyright (C) 2020  Info Teddy
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, only version 3 of the License.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

# colors xd
if [[ -t 1 ]]; then
	LIGHTBLUE='\033[1;34m'
	LIGHTCYAN='\033[1;36m'
	NOCOLOR='\033[1;0m'
else
	LIGHTBLUE=''
	LIGHTCYAN=''
	NOCOLOR=''
fi

#export PYTHONPATH=discord.py:websockets/src

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
