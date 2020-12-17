# [\] Discord bot
# Copyright 2020, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import json
import logging

ids = {}

def load():
	global ids
	try:
		with open('op_ids.json', 'r') as f:
			ids = json.load(f)
	except FileNotFoundError:
		logging.error('op_ids.json not found. A lot of things might be broken.')
