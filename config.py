# encoding=utf-8

import json
import copy
import logging

configcats = {
	'sysop': {
		'name': 'Global system operation',
	},
	'commands': {
		'name': 'Command usage',
	},
	'datetime': {
		'name': 'Date and time',
	},
	'logging': {
		'name': 'Logging',
	},
	'resending': {
		'name': 'Message resending',
	},
	'roles': {
		'name': 'Roles and role cache',
	},
	'starboard': {
		'name': 'Starboard',
	},
	'tntgb': {
		'name': 'Try Not To Get Banned',
	},
	'voice': {
		'name': 'Voice chat',
	},
}

# types can be:
#   bln: boolean
#   int: integer
#   str: string
#   rti: relative time (number of seconds, but input by user as [Xd][Xh][Xm][Xs] string like 7d12h or 1h)
#   did: generic Discord ID
#   uid: user/member Discord ID (members can be searched)
#   rid: role ID
#   cid: channel ID (channels can be mentioned)
#   gid: guild ID
#   dic: dictionary
# -not added/ideas:
#   -ati: absolute time (unix timestamp)
# access:
#   2: editable by local admins
#   1: read-only for local admins, editable for op
#   0: invisible for local admins
# valid_user_value(newvalue, **kwargs) is used for \config
# and returns a bool indicating a new value's validity.
# This limit also applies to operators.
# valid_user_value can also be True to always allow or False to always disallow changes via \config
configs = {
	'gamestatus': {
		'default': '​',
		'type': 'str',
		'is_array': False,
		'expl': 'Sets the game status for the bot.',
		'detachable': False,
		'cat': 'sysop',
		'access': 0,
		'valid_user_value': True,
	},
	'timeformat': {
		'default': '%Y-%m-%d %H:%M:%S (%Z)',
		'type': 'str',
		'is_array': False,
		'expl': 'The date format used in messages.',
		'detachable': True,
		'cat': 'datetime',
		'access': 2,
		'valid_user_value': True,
	},
	'blacklist': {
		'default': [],
		'type': 'uid',
		'is_array': True,
		'expl': 'A list of users that will be ignored by the bot.',
		'detachable': True,
		'cat': 'commands',
		'access': 2,
		'valid_user_value': True,
	},
	'disabledcommands': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Commands that cannot be used.',
		'detachable': True,
		'cat': 'commands',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue not in ('config')
		),
	},
	'globalcommands': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Commands that can be used by anyone in any channel, even if alloweverywhere is false and outside of allowedchannels.',
		'detachable': True,
		'cat': 'commands',
		'access': 2,
		'valid_user_value': True,
	},
	'rolecachemode': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': 'Sets the mode for the role cache. If enabled, any member who rejoins the server will be given back the roles they had before they left. Make sure to run `\\rolesync` after enabling this! `0` = disabled. `1` = enabled, and give default roles when new member hasn’t been seen on the server before. `2` = enabled, but if a new member hasn’t been seen on the server before, don’t give default roles.',
		'detachable': True,
		'cat': 'roles',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue in (0,1,2)
		),
	},
	'defaultroles': {
		'default': [],
		'type': 'rid',
		'is_array': True,
		'expl': 'The default roles that members will get upon their first entry. If `rolecachemode` is set to 1, these roles will be given instantly - if that option is set to `2`, they will be given after sending a message in the join channel.',
		'detachable': True,
		'cat': 'roles',
		'access': 2,
		'valid_user_value': True,
	},
	'defaultbotroles': {
		'default': [],
		'type': 'rid',
		'is_array': True,
		'expl': 'The default roles that bots will get upon entry, if the rolecache is enabled.',
		'detachable': True,
		'cat': 'roles',
		'access': 2,
		'valid_user_value': True,
	},
	'restrictiveroles': {
		'default': [],
		'type': 'rid',
		'is_array': True,
		'expl': 'Roles that are considered to be restrictive roles that should be removed when resetting a member’s roles.',
		'detachable': True,
		'cat': 'roles',
		'access': 2,
		'valid_user_value': True,
	},
	'joinchannel': {
		'default': 0,
		'type': 'cid',
		'is_array': False,
		'expl': 'The channel in which new members have to send a \join message before being given the default role(s).',
		'detachable': True,
		'cat': 'roles',
		'access': 2,
		'valid_user_value': True,
	},
	'specialchannel': {
		'default': 0,
		'type': 'cid',
		'is_array': False,
		'expl': 'Log channel',
		'detachable': True,
		'cat': 'logging',
		'access': 2,
		'valid_user_value': True,
	},
	'enabledlogs': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Identifiers for log messages that will be shown. `disabledlogs` takes priority, though.',
		'detachable': True,
		'cat': 'logging',
		'access': 2,
		'valid_user_value': True,
	},
	'disabledlogs': {
		'default': [],
		'type': 'str',
		'is_array': True,
		'expl': 'Identifiers for log messages that will not be shown, no matter what, even if in `enabledlogs`.',
		'detachable': True,
		'cat': 'logging',
		'access': 2,
		'valid_user_value': True,
	},
	'nologchannels': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'Events (like edits, deletes and reactions) involving messages in these channels will never be logged in the mod log, and will never cause "Message was edited/deleted" messages.',
		'detachable': True,
		'cat': 'logging',
		'access': 2,
		'valid_user_value': True,
	},
	'votevmute_minmembers': {
		'default': 4,
		'type': 'int',
		'is_array': False,
		'expl': 'The minimum amount of users needed to be in any voice channel before a vote voice mute can be started.',
		'detachable': True,
		'cat': 'voice',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 0
		),
	},
	'votevmute_threshold': {
		'default': 51,
		'type': 'int',
		'is_array': False,
		'expl': 'The percentage of users needing to vote in favor of muting before the mute is carried out.',
		'detachable': True,
		'cat': 'voice',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 0 and newvalue <= 100
		),
	},
	'deleted_message_resend_timer': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': 'The time, in seconds, of how much to wait to not resend a deleted message.',
		'detachable': True,
		'cat': 'resending',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 0
		),
	},
	'deleted_message_resend_content': {
		'default': False,
		'type': 'bln',
		'is_array': False,
		'expl': 'Set to True to include the content of a deleted message when resending it before the `deleted_message_resend_timer` runs out, set to False to not include the original content.',
		'detachable': True,
		'cat': 'resending',
		'access': 2,
		'valid_user_value': True,
	},
	'voicechat_channel_text': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'The text channels that accompany the voice channels.',
		'detachable': True,
		'cat': 'voice',
		'access': 2,
		'valid_user_value': True,
	},
	'voicechat_channel_voice': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'The voice channels to have text channels to accompany them.',
		'detachable': True,
		'cat': 'voice',
		'access': 2,
		'valid_user_value': True,
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
		'cat': 'commands',
		'access': 2,
		'valid_user_value': True,
	},
	'tntgb': {
		'default': {},
		'type': 'dic',
		'is_array': False,
		'expl': 'Config options for the TNTGB gamemode.',
		'detachable': True,
		'cat': 'tntgb',
		'access': 1,
		'valid_user_value': False,
	},
	'allowedchannels': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'The allowed channels non-staff members can use the bot in.',
		'detachable': True,
		'cat': 'commands',
		'access': 2,
		'valid_user_value': True,
	},
	'alloweverywhere': {
		'default': True,
		'type': 'bln',
		'is_array': False,
		'expl': 'Whether to take into account the allowedchannels option or not.',
		'detachable': True,
		'cat': 'commands',
		'access': 2,
		'valid_user_value': True,
	},
	'maxarchive': {
		'default': 5000,
		'type': 'int',
		'is_array': False,
		'expl': 'The maximum amount of messages that may be requested via `\\archive` in any server.',
		'detachable': False,
		'cat': 'sysop',
		'access': 0,
		'valid_user_value': True,
	},
	'prefixes': {
		'default': ['slash '],
		'type': 'str',
		'is_array': True,
		'expl': 'The prefixes of the bot.',
		'detachable': True,
		'cat': 'commands',
		'access': 2,
		'valid_user_value': True,
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
		'cat': 'resending',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 0
		),
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
		'cat': 'resending',
		'access': 2,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 0
		),
	},
	'starboard_active': {
		'default': False,
		'type': 'bln',
		'is_array': False,
		'expl': 'Whether the starboard feature is active on this server. Use `\starboard init` to create a starboard, or use `\starboard suspend` or `\starboard unsuspend` on an existing starboard.', # "For more info, see gitgud wiki article?"
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': True,
	},
	'starboard_channel': {
		'default': 0,
		'type': 'cid',
		'is_array': False,
		'expl': 'The starboard channel, only used if the feature is active.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': True,
	},
	'starboard_threshold': {
		'default': 5,
		'type': 'int',
		'is_array': False,
		'expl': 'The minimum number of stars before a message will be on the starboard. Note that changing the threshold will not change existing starred messages, unless their number of stars changes. Use `\starboard set threshold <value>` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 1 and newvalue <= 99999
		),
	},
	'starboard_star': {
		'default': '⭐',
		'type': 'str',
		'is_array': False,
		'expl': 'The emote that is used as star for the starboard. Can be a unicode emoji, or a custom emote ID (as string). You can not use custom emotes from other servers. Use `\starboard set star` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': True,
	},
	'starboard_nostar': {
		'default': '❌',
		'type': 'str',
		'is_array': False,
		'expl': 'The emote that is used as nostar for the starboard. Can be a unicode emoji, or a custom emote ID (as string). You can not use custom emotes from other servers. Use `\starboard set nostar` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': True,
	},
	'starboard_nostar_barrier': {
		'default': 2,
		'type': 'int',
		'is_array': False,
		'expl': 'The amount of nostars that will have no effect, and are needed as a \'staircase\' or buffer before nostars will subtract from the amount of stars. For example, if this value is 2, then a message having 5 stars and 3 nostars will total to having 4 stars. Set to -1 to disable nostars altogether. Use `\starboard set nostar_barrier <value>` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= -1 and newvalue <= 99998
		),
	},
	'starboard_timelimit': {
		'default': 345600,
		'type': 'rti',
		'is_array': False,
		'expl': 'The maximum age of a message before starring or unstarring it no longer has effect. Deleting a starred message older than this will also no longer remove it from the starboard. Use `\starboard set timelimit <value>` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue >= 0 and newvalue <= 863999999
		),
	},
	'starboard_ignoredchannels': {
		'default': [],
		'type': 'cid',
		'is_array': True,
		'expl': 'List of channels from which messages will never end up on the starboard. Be sure to think of NSFW channels, for example. Do not list the starboard channel, as the starboard will be ignored automatically. Use `\starboard ignore #channel` to ignore a channel, and `\starboard unignore #channel` to stop ignoring a channel.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': True,
	},
	'starboard_author_nostar_mode': {
		'default': 0,
		'type': 'int',
		'is_array': False,
		'expl': 'The way nostars by a message author are treated. `0` = If a user nostars their own message, it cannot be starboarded at all (because maybe the author would rather delete the message altogether than have it be starboarded by others?). `1` = If a user nostars their own message, it\'s treated just like when other people nostar the message. `2` = A user nostarring their own message is \'forbidden\', and will not be counted. Use `\starboard set author_nostar_mode <value>` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue in (0,1,2)
		),
	},
	'starboard_bans': {
		'default': [],
		'type': 'uid',
		'is_array': True,
		'expl': 'A list of users that will not be able to star/nostar messages, to be used in case of shitstarring. Their existing star reactions will still count. Use `\starboard ban <member>` to stop a user from interacting with the starboard, use `\starboard unban <member>` to unban.',
		'detachable': True,
		'cat': 'starboard',
		'access': 2,
		'valid_user_value': True,
	},
	'starboard_permalink': {
		'default': 2,
		'type': 'int',
		'is_array': False,
		'expl': 'How the permalinks for starboarded messagese are displayed. `0` = Permalink is not displayed. Message ID is displayed in the message content instead. `1` = Permalink is displayed in full, in the message content, as second line. `2` = Permalink is added to the embed and masked with "Go to message". Use `\starboard set permalink <value>` to change this setting.',
		'detachable': True,
		'cat': 'starboard',
		'access': 1,
		'valid_user_value': (
			lambda newvalue, **kwargs: newvalue in (0,1,2)
		),
	},
	'nitrobooster': {
		'default': 0,
		'type': 'rid',
		'is_array': False,
		'expl': 'The Nitro Booster role for this server. This will be set automatically upon creation of the role.',
		'detachable': True,
		'cat': 'logging',
		'access': 2,
		'valid_user_value': True,
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

def get_cat(skey):
	return configs[skey]['cat']

def input_to_type_key(request, skey):
	output = input_to_type(request, get_type(skey))
	return output

def input_to_type(request, category):
	import utils

	if category == 'int' or \
	(category.endswith('id') and category[0] in ('d', 'u', 'r', 'c', 's')):
		return int(request)
	elif category == 'bln':
		# This may look noobish and redundant, but it's actually needed here
		if request == True or request == '1' or (
			type(request) is str and request.lower() in (
				'true', 't', 'yes', 'y', 'on', 'enable', 'enabled'
			)
		):
			return True
		else:
			return False
	elif category == 'rti':
		# Relative timestamp, so parse a relative time!
		# This might be None, in that case raise an error
		rti = utils.parsereltime(request, True)
		if rti is None:
			raise ValueError('Invalid relative time')
		return rti

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
