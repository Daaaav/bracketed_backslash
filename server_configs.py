# encoding=utf-8

import json

config = {}

def save_config():
	with open('server_configs.json', 'w') as f:
		json.dump(conf, f)

def load():
	try:
		with open('server_configs.json', 'r') as f:
			conf = json.load(f)
	except FileNotFoundError:
		logging.info('server_configs.json not found. Creating a new one.')
