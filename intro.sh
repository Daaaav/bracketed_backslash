#!/bin/bash
until python main.py; do
	echo "bot crashed with exit code $? also restarting" >&2
	sleep 1
done
