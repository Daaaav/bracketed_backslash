#!/bin/bash

# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

if [[ -t 1 ]]; then
	GRAY='\033[90m'
	NOCOLOR='\033[0m'
else
	GRAY=''
	NOCOLOR=''
fi

for i in $( ls *.py ); do
	printf "${GRAY}Running ${i} through pyflakes...${NOCOLOR}\n"
	pyflakes3 "$i"
done
