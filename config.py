# encoding=utf-8

import json

# types can be int/str/arr
configs = {
	'test': {
		'default': 2,
		'type': 'int',
		'expl': 'A testing setting to see whether everything works'
	},
	'timeformat': {
		'default': '%Y-%m-%d %H:%M:%S (%Z)',
		'type': 'str',
		'expl': 'The date format used in messages.'
	},
}

s = {}

def saveconfig():
	with open('config.json', 'w') as outfile:
		json.dump(s, outfile)

def loaddefaultsettings():
	for default in configs:
		s[default] = configs[default]['default']

def load():
	loaddefaultsettings()

	try:
		with open('config.json', 'r') as infile:
			loadedconfig = json.load(infile)
		
		for loadedsetting in loadedconfig:
			# Overwrite the defaults piece by piece
			s[loadedsetting] = loadedconfig[loadedsetting]
	except FileNotFoundError:
		print('Making new config file')
		saveconfig()
