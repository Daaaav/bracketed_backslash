# encoding=utf-8

import json
import copy
import logging

# types can be:
# bln: boolean
# int: integer
# str: string
# rti: relative time (number of seconds, but input by user as [Xd][Xh][Xm][Xs] string like 7d12h or 1h)
# did: generic Discord ID
# uid: user/member Discord ID (members can be searched)
# rid: role ID
# cid: channel ID (channels can be mentioned)
# gid: guild ID
# dic: dictionary
# not added/ideas:
# ati: absolute time (unix timestamp)
configs = {
	'gamestatus': {
		'default': '​',
		'type': 'str',
		'is_array': False,
		'expl': 'Sets the game status for the bot.',
		'detachable': False,
		'shown': True,
	},
	'timeformat': {
		'default': '%Y-%m-%d %H:%M:%S (%Z)',
		'type': 'str',
		'is_array': False,
		'expl': 'The date format used in messages.',
		'detachable': True,
		'shown': True,
	},
	'blacklist': {
		'default': [],
		'type': 'uid',
		'is_array': True,
		'expl': 'A list of users that will be ignored by the bot.',
		'detachable': True,
		'shown': True,
	},
	'disabledcommands': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Commands that cannot be used.',
		'detachable': True,
		'shown': True,
	},
	'globalcommands': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Commands that can be used by anyone in any channel, even if alloweverywhere is false and outside of allowedchannels.',
		'detachable': True,
		'shown': True,
	},
	'rolecachemode': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': 'Sets the mode for the role cache. If enabled, any member who rejoins the server will be given back the roles they had before they left. Make sure to run `\\rolesync` after enabling this! `0` = disabled. `1` = enabled, and give default roles when new member hasn’t been seen on the server before. `2` = enabled, but if a new member hasn’t been seen on the server before, don’t give default roles.',
		'detachable': True,
		'shown': True,
	},
	'defaultroles': {
		'default': [],
		'type': 'rid',
		'is_array': True,
		'expl': 'The default roles that members will get upon their first entry. If `rolecachemode` is set to 1, these roles will be given instantly - if that option is set to `2`, they will be given after sending a message in the join channel.',
		'detachable': True,
		'shown': True,
	},
	'defaultbotroles': {
		'default': [],
		'type': 'rid',
		'is_array': True,
		'expl': 'The default roles that bots will get upon entry, if the rolecache is enabled.',
		'detachable': True,
		'shown': True,
	},
	'restrictiveroles': {
		'default': [],
		'type': 'rid',
		'is_array': True,
		'expl': 'Roles that are considered to be restrictive roles that should be removed when resetting a member’s roles.',
		'detachable': True,
		'shown': True,
	},
	'joinchannel': {
		'default': 0,
		'type': 'cid',
		'is_array': False,
		'expl': 'The channel in which new members have to send a \join message before being given the default role(s).',
		'detachable': True,
		'shown': True,
	},
	'specialchannel': {
		'default': 0,
		'type': 'cid',
		'is_array': False,
		'expl': 'Log channel',
		'detachable': True,
		'shown': False,
	},
	'enabledlogs': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Identifiers for log messages that will be shown. `disabledlogs` takes priority, though.',
		'detachable': True,
		'shown': False,
	},
	'disabledlogs': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Identifiers for log messages that will not be shown, no matter what, even if in `enabledlogs`.',
		'detachable': True,
		'shown': False,
	},
	'votevmute_minmembers': {
		'default': 4,
		'type': 'int',
		'is_array': False,
		'expl': 'The minimum amount of users needed to be in any voice channel before a vote voice mute can be started.',
		'detachable': True,
		'shown': True,
	},
	'votevmute_threshold': {
		'default': 51,
		'type': 'int',
		'is_array': False,
		'expl': 'The percentage of users needing to vote in favor of muting before the mute is carried out.',
		'detachable': True,
		'shown': True,
	},
	'deleted_message_resend_timer': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': 'The time, in seconds, of how much to wait to not resend a deleted message.',
		'detachable': True,
		'shown': False,
	},
	'deleted_message_resend_content': {
		'default': False,
		'type': 'bln',
		'is_array': False,
		'expl': 'Set to True to include the content of a deleted message when resending it before the `deleted_message_resend_timer` runs out, set to False to not include the original content.',
		'detachable': True,
		'shown': False,
	},
	'voicechat_channel_text': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'The text channels that accompany the voice channels.',
		'detachable': True,
		'shown': True,
	},
	'voicechat_channel_voice': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'The voice channels to have text channels to accompany them.',
		'detachable': True,
		'shown': True,
	},
	'notify_invalidcmd': {
		'default': False,
		'type': 'bln',
		'is_array': False,
		'expl': (
			'If the bot should message on an invalid command,'
			' instead of failing silently.'
		),
		'detachable': True,
		'shown': True,
	},
	'tntgb': {
		'default': {},
		'type': 'dic',
		'is_array': False,
		'expl': 'Config options for the TNTGB gamemode.',
		'detachable': True,
		'shown': False,
	},
	'allowedchannels': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'The allowed channels non-staff members can use the bot in.',
		'detachable': True,
		'shown': True,
	},
	'alloweverywhere': {
		'default': True,
		'type': 'bln',
		'is_array': False,
		'expl': 'Whether to take into account the allowedchannels option or not.',
		'detachable': True,
		'shown': True,
	},
	'maxarchive': {
		'default': 5000,
		'type': 'int',
		'is_array': False,
		'expl': 'The maximum amount of messages that may be requested via `\\archive` in any server.',
		'detachable': False,
		'shown': True,
	},
	'prefixes': {
		'default': ['slash '],
		'type': 'str',
		'is_array': True,
		'expl': 'The prefixes of the bot.',
		'detachable': True,
		'shown': False,
	},
	'edited_message_resend_timer': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': (
			'The time, in seconds, of how much to wait to not resend'
			' the older and newer content of an edited message.'
		),
		'detachable': True,
		'shown': False,
	},
	'edited_message_resend_threshold': {
		'default': 10,
		'type': 'int',
		'is_array': False,
		'expl': (
			'The amount of changed characters between the older and newer content of'
			' a message in order to resend both contents.'
		),
		'detachable': True,
		'shown': False,
	},
	'starboard_active': {
		'default': False,
		'type': 'bln',
		'is_array': False,
		'expl': 'Whether the starboard feature is active on this server.', # "For more info, see gitgud wiki article?"
		'detachable': True,
		'shown': True,
	},
	'starboard_channel': {
		'default': 0,
		'type': 'cid',
		'is_array': False,
		'expl': 'The starboard channel, only used if the feature is active.',
		'detachable': True,
		'shown': True,
	},
	'starboard_threshold': {
		'default': 5,
		'type': 'int',
		'is_array': False,
		'expl': 'The minimum number of stars before a message will be on the starboard. Note that changing the threshold will not change existing starred messages, unless their number of stars changes.',
		'detachable': True,
		'shown': True,
	},
	'starboard_star': {
		'default': '⭐',
		'type': 'str',
		'is_array': False,
		'expl': 'The emote that is used as star for the starboard. Can be a unicode emoji, or a custom emote ID (as string). You can not use custom emotes from other servers.',
		'detachable': True,
		'shown': True,
	},
	'starboard_nostar': {
		'default': '❌',
		'type': 'str',
		'is_array': False,
		'expl': 'The emote that is used as nostar for the starboard. Can be a unicode emoji, or a custom emote ID (as string). You can not use custom emotes from other servers.',
		'detachable': True,
		'shown': True,
	},
	'starboard_nostar_barrier': {
		'default': 2,
		'type': 'int',
		'is_array': False,
		'expl': 'The amount of nostars that will have no effect, and are needed as a \'staircase\' or buffer before nostars will subtract from the amount of stars. For example, if this value is 2, then a message having 5 stars and 3 nostars will total to having 4 stars. Set to -1 to disable nostars altogether.',
		'detachable': True,
		'shown': True,
	},
	'starboard_timelimit': {
		'default': '172800',
		'type': 'rti',
		'is_array': False,
		'expl': 'The maximum age of a message before starring or unstarring it no longer has effect. Deleting a starred message older than this will also no longer remove it from the starboard.',
		'detachable': True,
		'shown': True,
	},
	'starboard_ignoredchannels': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'List of channels from which messages will never end up on the starboard. Be sure to think of NSFW channels, for example. Do not list the starboard channel, as the starboard will be ignored automatically.',
		'detachable': True,
		'shown': True,
	},
	'starboard_author_nostar_mode': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': 'The way nostars by a message author are treated. `0` = If a user nostars their own message, it cannot be starboarded at all (because maybe the author would rather delete the message altogether than have it be starboarded by others?). `1` = If a user nostars their own message, it\'s treated just like when other people nostar the message. `2` = A user nostarring their own message is \'forbidden\', and will not be counted.',
		'detachable': True,
		'shown': True,
	},
	'starboard_bans': {
		'default': [],
		'type': 'uid',
		'is_array': True,
		'expl': 'A list of users that will not be able to star/nostar messages, to be used in case of shitstarring. Their existing star reactions will still count.',
		'detachable': True,
		'shown': True,
	},
}

s = {}

def get_s(skey, guildid=None):
	if guildid is not None and guildid in s[skey]:
		return s[skey][guildid]
	return s[skey]['master']

def set_s(skey, value, guildid=None):
	if is_array(skey):
		raise TypeError('Array options cannot be set using the standard config.set_s() function!')
		return
	if get_type(skey) == 'dic':
		raise TypeError(
			'Custom options cannot be set using the standard config.set_s() function!'
		)
	if guildid is not None and guildid in s[skey]:
		s[skey][guildid] = input_to_type_key(value, skey)
	else:
		s[skey]['master'] = input_to_type_key(value, skey)

def insert_s(skey, value, guildid=None):
	if not is_array(skey):
		raise TypeError('You cannot insert something into an option that isn\'t an array')
		return
	if guildid is not None and guildid in s[skey]:
		s[skey][guildid].append(input_to_type_key(value, skey))
	else:
		s[skey]['master'].append(input_to_type_key(value, skey))

def remove_s(skey, value, guildid=None):
	if not is_array(skey):
		raise TypeError('You cannot remove something from an option that isn\'t an array')
		return
	if guildid is not None and guildid in s[skey]:
		s[skey][guildid].remove(input_to_type_key(value, skey))
	else:
		s[skey]['master'].remove(input_to_type_key(value, skey))

def insert_dic_s(skey, indice, value, guild_id=None):
	if not is_dic(skey):
		raise TypeError("cannot insert an indice into an option that isn't a dic")
	if guild_id is None or guild_id not in s[skey]:
		guild_id = 'master'
	base = s[skey][guild_id]
	base[indice] = input_to_type_key(value, skey)

def remove_dic_s(skey, indice, guild_id=None):
	if not is_dic(skey):
		raise TypeError("cannot remove an indice from an option that isn't a dic")
	if guild_id is None or guild_id not in s[skey]:
		guild_id = 'master'
	del s[skey][guild_id][indice]

def restore_default(skey, guildid=None):
	if (is_array(skey) or is_dic(skey)) and guildid is not None and guildid in s[skey]:
		s[skey][guildid] = copy.deepcopy(get_default(skey))
	elif is_array(skey) or is_dic(skey):
		s[skey]['master'] = copy.deepcopy(get_default(skey))
	else:
		set_s(skey, get_default(skey), guildid)

def detach(skey, guildid):
	if not is_detachable(skey):
		raise ValueError('Setting {} is not detachable'.format(skey))
		return
	if not is_detached(skey, guildid):
		s[skey][guildid] = copy.deepcopy(get_default(skey))

def reattach(skey, guildid):
	if is_detached(skey, guildid):
		del s[skey][guildid]

def is_detached(skey, guildid):
	return guildid in s[skey]

def exists(skey):
	return skey in configs and skey in s

def is_array(skey):
	return configs[skey]['is_array']

def is_dic(skey):
	return configs[skey]['type'] == 'dic'

def is_detachable(skey):
	return configs[skey]['detachable']

def get_default(skey):
	return configs[skey]['default']

def get_type(skey):
	return configs[skey]['type']

def get_expl(skey):
	if configs[skey]['expl'] is None or configs[skey]['expl'] == '':
		return None
	return configs[skey]['expl']

def get_shown(skey):
	return configs[skey]['shown']

def input_to_type_key(request, skey):
	output = input_to_type(request, get_type(skey))
	if output is None:
		return get_default(skey)
	return output

def input_to_type(request, category):
	import utils

	if category == 'int' or \
	(category.endswith('id') and category[0] in ('d', 'u', 'r', 'c', 's')):
		return int(request)
	elif category == 'bln':
		# This may look noobish and redundant, but it's actually needed here
		if request == True or request == '1' or request.lower() in (
			'true', 't', 'yes', 'y', 'on', 'enable', 'enabled'
		):
			return True
		else:
			return False
	elif category == 'rti':
		# Relative timestamp, so parse a relative time!
		# This might be None, but in that case it'll be set to default.
		# Maybe raise an error and catch that everywhere idk
		return utils.parsereltime(request, True)

	return request

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
					s[loadedsetting][int(loadedlocalsetting)] = loadedconfig[loadedsetting][loadedlocalsetting]
	except FileNotFoundError:
		logging.info('did not find a config file so making a new one')
		saveconfig()
