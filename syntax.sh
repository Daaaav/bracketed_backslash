#!/bin/bash

for i in $( ls *.py ); do
	printf "Running ${i} through pyflakes...\n"
	pyflakes "$i"
done
