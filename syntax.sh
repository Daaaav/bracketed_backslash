#!/bin/bash

printf "Creating concatenatedmain.py file..."

cat main.py functions.py commands.py > concatenatedmain.py

printf " Created!\n"

for i in $( ls *.py ); do
	if [[
		"$i" != "main.py" &&
		"$i" != "functions.py" &&
		"$i" != "commands.py"
	]]; then
		printf "Running ${i} through pyflakes...\n"
		pyflakes "$i"
	else
		printf "Skipped ${i}.\n"
	fi
done

rm concatenatedmain.py
