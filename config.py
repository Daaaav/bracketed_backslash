# encoding=utf-8

import json
import copy

# types can be:
# bln: boolean
# int: integer
# str: string
# did: generic Discord ID
# uid: user/member Discord ID (members can be searched)
configs = {
	'test': {
		'default': 2,
		'type': 'int',
		'is_array': False,
		'expl': 'A testing setting to see whether everything works',
		'detachable': True
	},
	'timeformat': {
		'default': '%Y-%m-%d %H:%M:%S (%Z)',
		'type': 'str',
		'is_array': False,
		'expl': 'The date format used in messages.',
		'detachable': True
	},
	'blacklist': {
		'default': [],
		'type': 'uid',
		'is_array': True,
		'expl': 'A list of users that will be ignored by the bot.',
		'detachable': True
	},
}

s = {}

def get_s(skey, serverid=None):
	if serverid != None and serverid in s[skey]:
		return s[skey][serverid]
	return s[skey]['master']

def set_s(skey, value, serverid=None):
	if is_array(skey):
		raise TypeError('Array options cannot be set using the standard config.set_s() function!')
		return
	if serverid != None and serverid in s[skey]:
		s[skey][serverid] = value
	else:
		s[skey]['master'] = value

def insert_s(skey, value, serverid=None):
	if not is_array(skey):
		raise TypeError('You cannot insert something into an option that isn\'t an array')
		return
	if serverid != None and serverid in s[skey]:
		s[skey][serverid].append(value)
	else:
		s[skey]['master'].append(value)

def remove_s(skey, value, serverid=None):
	if not is_array(skey):
		raise TypeError('You cannot remove something from an option that isn\'t an array')
		return
	if serverid != None and serverid in s[skey]:
		s[skey][serverid].remove(value)
	else:
		s[skey]['master'].remove(value)

def restore_default(skey, serverid=None):
	if is_array(skey) and serverid != None and serverid in s[skey]:
		s[skey][serverid] = copy.deepcopy(get_default(skey))
	elif is_array(skey):
		s[skey]['master'] = copy.deepcopy(get_default(skey))
	else:
		set_s(skey, get_default(skey), serverid)

def detach(skey, serverid):
	if not is_detachable(skey):
		raise ValueError('Setting {} is not detachable'.format(skey))
		return
	if not is_detached(skey, serverid):
		s[skey][serverid] = get_default(skey)

def reattach(skey, serverid):
	if is_detached(skey, serverid):
		del s[skey][serverid]

def is_detached(skey, serverid):
	return serverid in s[skey]

def exists(skey):
	return skey in s

def is_array(skey):
	return configs[skey]['is_array']

def is_detachable(skey):
	return configs[skey]['detachable']

def get_default(skey):
	return configs[skey]['default']

def get_type(skey):
	return configs[skey]['type']

def get_expl(skey):
	if configs[skey]['expl'] == None or configs[skey]['expl'] == '':
		return None
	return configs[skey]['expl']

def saveconfig():
	with open('config.json', 'w') as outfile:
		json.dump(s, outfile)

def loaddefaultsettings():
	for default in configs:
		s[default] = {}
		if configs[default]['is_array']:
			s[default]['master'] = copy.deepcopy(get_default(default))
		else:
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
