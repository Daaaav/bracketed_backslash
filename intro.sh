#!/bin/bash

#	[\] bot, will be used for tolp server
#	Copyright (C) 2016  Info Teddy
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
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

while true; do
	python main.py
	if [ $? -eq 42 ]; then
		exit 0
	fi
	echo -e "${LIGHTBLUE}bot exited with exit code ${LIGHTCYAN}$?${LIGHTBLUE} also restarting${NOCOLOR}" >&2
	sleep 1
done
