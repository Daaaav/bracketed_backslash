# encoding=utf-8

import json

# types can be int/str/arr
configs = {
	'test': {
		'default': 2,
		'type': 'int',
		'expl': 'A testing setting to see whether everything works',
		'detachable': True
	},
	'timeformat': {
		'default': '%Y-%m-%d %H:%M:%S (%Z)',
		'type': 'str',
		'expl': 'The date format used in messages.',
		'detachable': True
	},
}

s = {}

def get_s(skey, serverid=None):
	if serverid != None and serverid in s[key]:
		return s[skey][serverid]
	return s[skey]['master']

def set_s(skey, value, serverid=None):
	if serverid != None and serverid in s[key]:
		s[skey][serverid] = value
	s[skey]['master'] = value

def is_detached(skey, serverid):
	if serverid in s[key]:
		return True
	return False

def saveconfig():
	with open('config.json', 'w') as outfile:
		json.dump(s, outfile)

def loaddefaultsettings():
	for default in configs:
		s[default]['master'] = configs[default]['default']

def load():
	loaddefaultsettings()

	try:
		with open('config.json', 'r') as infile:
			loadedconfig = json.load(infile)
		
		for loadedsetting in loadedconfig:
			# Overwrite the defaults piece by piece
			s[loadedsetting] = {}
			s[loadedsetting]['master'] = loadedconfig[loadedsetting]['master']
			for loadedlocalsetting in loadedconfig[loadedsetting]:
				if loadedlocalsetting != 'master':
					s[loadedsetting][loadedlocalsetting] = loadedconfig[loadedsetting][loadedlocalsetting]
	except FileNotFoundError:
		print('Making new config file')
		saveconfig()
