#!/usr/bin/python3.5
# encoding=utf-8

"""
[\] bot, will be used for tolp server
Copyright (C) 2016  Info Teddy

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import discord
import asyncio
from aiohttp import ClientSession
import os
import os.path
import sys
import warnings
import random
import time
import json
import logging
import math
import subprocess

import config

config.load()

# set bot version
botversion = '1.0'

# sets up logging
# level can be logging.DEBUG, logging.WARNING, et cetera
# see https://docs.python.org/3/library/logging.html for more info.
logging.basicConfig(level=logging.INFO)

client = discord.Client() # defines all client.* commands

cachelocation = './.cache'
attachcache = cachelocation + '/' + 'attach' # define attachment caching location

invoker = '\\' # command invoker
altinvoker = 'ok glass, ' # alt command invoker
hangmaninvoker = '-'

# Hangman stuff
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
hangmanchosenword = ''
hangmanattempts = 0
hangmantotalattempts = 0
hangmanactive = False
hangmanstarter = None
guessedletters = [False]*26
algeraden = False

os.environ['TZ'] = 'UTC'
time.tzset()

boottime = time.strftime(config.get_s('timeformat'))
boottimeunix = time.time()

token_config = open('bot_token.conf', 'r')

token = token_config.readline(60).split('\n')[0] # read sixty characters also FUCKING NEWLINES

token_config.close() # this is probably a good idea i should do

specialchannel_prod = discord.Object(id='234185735266238464')
specialchannel_aperture = discord.Object(id='243176655101755392')
botschannel = discord.Object(id='201130047736643584')
productionserver = '153368829160849408'
server = client.get_server(productionserver) # defines all server.* commands

memberroles = {}
minutemessageedits = {}

rules = {}
disabledrules = []

modificationtimes = [
	os.path.getmtime('main.py'),
	os.path.getmtime('functions.py'),
	os.path.getmtime('config.py'),
]
modificationtimecache = time.strftime(config.get_s('timeformat'), time.gmtime(max(modificationtimes)))

client.max_messages = None

t = {
	'op_only': 'Permission denied. This command can only be used by Info Teddy or Dav999.',
	'mod_only': 'Permission denied. This command can only be used by a moderator or administrator.',
	'specify_user': 'Please specify a user ID, a username, a username and discriminator, or a nickname.',
	'no_permission': 'There are missing permissions required to execute this.',
	'accepts_user': 'Accepts as an argument a user ID, nickname, username, discriminator, or username and discriminator.',
	'production_only': 'Production server only!',
	'noprivate': 'This command cannot be run inside a private conversation! You can probably guess why.',
	'its_meme': 'It’s a meme command.',
}

cmds = [
	{
		'cat_name': 'General Commands',
		'cat_slug': 'general',
		'cat_desc': '',
		'cat_shown': True,
		'commands': [
			{
				'name': 'help',
				'short': 'Lists commands and their descriptions.',
				'extra': 'Any arguments passed to `\help` will make `\help` try to look up more in-depth description of the command.'
			},
			{
				'name': 'source',
				'short': 'Gives the link to the source code to the bot.',
				'extra': 'It’s hosted on __https://gitgud.io/__.'
			},
			{
				'name': 'echo',
				'short': 'Echoes your input.',
				'extra': 'Now, you could say that the bot echoed your input already, but it’s still better to have a dedicated echo command.'
			},
			{
				'name': 'info',
				'short': 'Gives information about a user.',
				'extra': ''
			},
			{
				'name': 'findu',
				'short': 'Find a user by (part of) their nickname/username case-insensitively, or their discriminator, or whatever.',
				'extrafull': 'Find a user by (part of) their nickname/username case-insensitively, or their discriminator, or whatever. Shows ID, nickname, username, and discriminator.'
			},
			{
				'name': 'findup',
				'short': 'Same as `\\findu`, but also pings the user.',
				'extrafull': 'Find a user by (part of) their nickname/username case-insensitively, or their discriminator, or whatever. Shows ID, nickname, username, and discriminator. Warning: This pings the user.'
			},
			{
				'name': 'hangman',
				'short': 'Initiate a game of hangman. Send via private message with a custom word. Use `\stophangman` to stop.',
				'extra': 'Ported from DavBot!'
			},
			{
				'name': 'stophangman',
				'short': 'Stop the current game of hangman.',
				'extra': 'Can only be done by the one who started the game or a moderator.'
			},
			{
				'name': 'invite',
				'short': 'Links to the servers `[\]` can be used on.',
				'extra': '`[\]` can only be used on these servers.'
			},
			{
				'name': 'countpins',
				'short': 'Count the amount of pins in a channel.',
				'extra': 'You can supply the channel via a channel mention, if not given it will use the current channel.'
			},
		]
	},
	{
		'cat_name': 'Bot Commands',
		'cat_slug': 'bot',
		'cat_desc': '',
		'cat_shown': True,
		'commands': [
			{
				'name': 'botok',
				'short': 'Pings the bot.',
				'extra': 'If the bot is okay, the bot will respond with “Bot is okay”.'
			},
			{
				'name': 'version',
				'short': 'Gives the bot version and `discord.py` version.',
				'extra': ''
			},
			{
				'name': 'uptime',
				'short': 'Prints the time the bot was booted.',
				'extra': 'Doesn’t yet give the amount of time between the boot and now, but does give those timestamps.'
			},
			{
				'name': 'restart',
				'short': 'Restarts the bot.',
				'extra': ''
			},
			{
				'name': 'kill',
				'short': 'Kills the bot. This method does not kill it cleanly.',
				'extra': ''
			},
			{
				'name': 'config',
				'short': 'This command is used to manage the settings in the bot.',
				'extra': (
					'You can use the following options:\n'
					'`\config list` – Show all the settings and their values.\n'
					'`\config reload` – Reloads the config file.\n'
					'`\config get <key>` – Show extended information about a specific setting and how it is configured, given its key.\n'
					'`\config set <key> <value>` – Update the value of a given non-array setting. Don’t use quotes or anything fancy.\n'
					'`\config insert <key> <value>` – Insert a value into an array setting.\n'
					'`\config remove <key> <value>` – Remove a value from an array setting.\n'
					'`\config detach <key>` – No longer make this setting use the master value, and use a server-specific value instead.\n'
					'`\config reattach <key>` – Start using the master value for this setting again.\n'
					'`\config default <key>` – Changes the value of a given setting back to default.\n'
				)
			},
		]
	},
	{
		'cat_name': 'Moderation Commands',
		'cat_slug': 'mod',
		'cat_desc': '',
		'cat_shown': True,
		'commands': [
			{
				'name': 'softban',
				'short': 'Gives a user the `Banned` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'nononly',
				'short': 'Gives a user the `Nonsense-Only` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'nogenmen',
				'short': 'Gives a user the `No General Mentions` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'nocedule',
				'short': 'Gives a user the `No CE/DU/LE` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'notts',
				'short': 'Gives a user the `No TTS` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'noreact',
				'short': 'Gives a user the `No Reactions` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'nonick',
				'short': 'Removes from a user the `tOLPer` role, and gives them the `tOLPer who can’t change nickname` role.',
				'extra': t['accepts_user']
			},
			{
				'name': 'voicemute',
				'short': 'Mutes a user in a voice channel.',
				'extra': t['accepts_user']
			},
			{
				'name': 'voiceunmute',
				'short': 'Unmutes a user in a voice channel.',
				'extra': t['accepts_user']
			},
			{
				'name': 'rolerst',
				'short': 'Resets the roles for a user back to the normal state.',
				'extra': 'Removes all restrictive roles from a user, and gives back the `tOLPer` role if necessary.\n' + t['accepts_user']
			},
			{
				'name': 'rolecacherst',
				'short': 'Removes a member who has left the server from the role cache.',
				'extra': 'Only accepts a user ID!'
			},
			{
				'name': 'rolesync',
				'short': 'Re-syncs the roles cache with the current roles everyone has, if the bot missed role additions/removals',
				'extra': 'Does not remove members from the cache who have left the server.'
			},
			{
				'name': 'getrawmessagecontent',
				'short': 'Gets the raw content of a message.',
				'extra': (
					'Syntax: `\getrawmessagecontent CHANNEL MESSAGEID`\n'
					'`CHANNEL` must be in `<#ID>` form, i.e. a highlighted channel link.\n'
					'`MESSAGEID` must be the ID of the message.'
				)
			}
		]
	},
	{
		'cat_name': 'Contributor Moderator Commands',
		'cat_slug': 'contribmod',
		'cat_desc': '',
		'cat_shown': True,
		'commands': [
			{
				'name': 'addcontrib',
				'short': 'Makes a member a tOLP Contributor.',
				'extra': t['accepts_user']
			},
			{
				'name': 'removecontrib',
				'short': 'Makes a member not a tOLP Contributor.',
				'extra': t['accepts_user']
			}
		]
	},
	{
		'cat_name': 'Rules Commands',
		'cat_slug': 'rulesystem',
		'cat_desc': '',
		'cat_shown': True,
		'commands': [
			{
				'name': 'rules',
				'short': 'View the rules.',
				'extra': 'Rules can be different for each server the bot runs on. You can get a specific rule by its number with `\\rule X`.',
			},
			{
				'name': 'rulefind',
				'short': 'Find rules that contain a given search term.',
				'extra': 'Example:\n`\\rulefind spam`'
			},
			{
				'name': 'ruleadd',
				'short': 'Insert a given rule string (2) to position (1). If no position is given, it’s added at the end.',
				'extra': 'Examples:\n`\\ruleadd No trolling`\n`\\ruleadd 1 The most important rule is not to follow this rule.`'
			},
			{
				'name': 'ruleedit',
				'short': 'Edit a given rule.',
				'extra': 'Example:\n`\\ruleedit 2 No trolling`'
			},
			{
				'name': 'rulemove',
				'short': 'Move a given rule to a different slot. (nothing gets overwritten)',
				'extra': 'Example:\n`\\rulemove 2 4`'
			},
			{
				'name': 'ruleremove',
				'short': 'Remove a given rule.',
				'extra': 'Example:\n`\\ruleremove 2`'
			},
			{
				'name': 'rulemaint',
				'short': 'Enable/Disable the rules system for this server.',
				'extra': ''
			},
		]
	},
	{
		'cat_name': 'Meme Commands',
		'cat_slug': 'useless',
		'cat_desc': 'You found a secret, congratulations. The command to get this help message will change sometimes.',
		'cat_shown': False,
		'commands': [
			{
				'name': '',
				'short': 'Mentions you.',
				'extra': 'Don’t type this command in if you don’t want to be mentioned.'
			},
			{
				'name': 'teddy',
				'short': 'The obvious counterpart to `\info`.',
				'extra': t['its_meme']
			},
			{
				'name': 'samar',
				'short': 'The true name.',
				'extra': t['its_meme']
			},
			{
				'name': 'lui',
				'short': 'Obligatory “pretty cool guy” meme.',
				'extra': t['its_meme']
			},
			{
				'name': 'shiny',
				'short': 'He’s a shiny trinket.',
				'extra': t['its_meme']
			},
			{
				'name': 'tainy',
				'short': 'Unobtaining is his name.',
				'extra': t['its_meme']
			},
			{
				'name': 'kys',
				'short': 'Will the bot listen?',
				'extra': t['its_meme']
			},
			{
				'name': '*formatting*',
				'short': 'This is an example of italicized formatting.',
				'extra': t['its_meme']
			},
			{
				'name': '/r/undertale',
				'short': 'This is going to give my bot cancer.',
				'extra': t['its_meme']
			},
		]
	},
]

permissionlabels = [
	['administrator', 'Administrator'],
	['manage_server', 'Manage Server'],
	['manage_channels', 'Manage Channels'],
	['manage_roles', 'Manage Roles'],
	['ban_members', 'Ban Members'],
	['kick_members', 'Kick Members'],
	['move_members', 'Move Members'],
	['deafen_members', 'Deafen Members'],
	['mute_members', 'Mute Members'],
	['manage_webhooks', 'Manage Webhooks'],
	['manage_nicknames', 'Manage Nicknames'],
	['manage_emojis', 'Manage Custom Emotes'],
	['manage_messages', 'Manage Messages'],
	['change_nickname', 'Change Nickname'],
	['mention_everyone', 'Mention General Mentions'],
	['external_emojis', 'Use Custom Emotes'],
	['attach_files', 'Upload Direct Uploads'],
	['embed_links', 'Embed Link Embeds'],
	['send_tts_messages', 'Use Text-to-Speech'],
	['read_message_history', 'Read Message History'],
	['send_messages', 'Send Messages'],
	['add_reactions', 'Add Reactions'],
	['read_messages', 'Read Messages'],
	['use_voice_activation', 'Use Voice Activity'],
	['speak', 'Speak'],
	['connect', 'Connect'],
	['create_instant_invite', 'Instant Invite'],
]

@client.event
async def on_ready():
	global memberroles, rules, disabledrules

	logging.info('logged in as {} with id {}'.format(client.user.name, client.user.id))
	await client.change_presence(game=discord.Game(name=config.get_s('gamestatus')))

	await client.send_message(specialchannel_prod, '**`>`**🔌`Bot connected. (startup time is {})`'.format(reltime(boottimeunix)))

	try:
		with open('members.json', 'r') as infile:
			memberroles = json.load(infile)

		# Now look what I've woken up to.
		warnings = ''

		for mem in client.get_server(productionserver).members:
			if not str(mem.id) in memberroles:
				warnings += '\nUser {}#{} ({}) is not in the cache! (They’re suddenly in the server.) Adding their roles to the cache now.'.format(mem.name, mem.discriminator, mem.id)
				memberroles[str(mem.id)] = list(rolelist(mem.roles)) # Possibly redundant list() tbh, just making sure since I can't test and I don't know python well enough to know whether it's redundant
				continue
			if set(memberroles[str(mem.id)]) != set(rolelist(mem.roles)):
				warnings += (
					'\n'
					'User {}#{} ({}) has different roles than in the cache! Maybe you want to correct things.\n'
					'    **`Cached:`** {}\n'
					'    **`Seen:`** {}'
				).format(
					mem.name, mem.discriminator, mem.id,
					listroles_id(memberroles[str(mem.id)]),
					listroles(mem.roles),
				)
		if warnings != '':
			logging.warn(warnings)
			warnings = (
				'**User role cache warning.**\n'
				'Full warning output has been sent to the terminal.\n'
				+ warnings
			)
			await client.send_message(specialchannel_prod, warnings[:1900])

	except FileNotFoundError:
		logging.info('members file does not exist yet so creating it now')
		memberroles = {}

		with open('members.json', 'w') as outfile:
			json.dump(memberroles, outfile)

		await client.send_message(specialchannel_prod, 'Members file didn’t yet exist, created a new one. Please run `\\rolesync` to sync up the roles cache.')

	try:
		with open('rules.json', 'r') as infile:
			rules = json.load(infile)
	except FileNotFoundError:
		logging.info('rules file does not exist yet so creating it now')
		rules = {}

		with open('rules.json', 'w') as outfile:
			json.dump(rules, outfile)

		await client.send_message(specialchannel_prod, 'Rules file didn’t exist yet, created a new one.')

	try:
		with open('disabledrules.json', 'r') as infile:
			disabledrules = json.load(infile)
	except FileNotFoundError:
		logging.info('disabledrules file does not exist yet so creating it now')
		disabledrules = []

		with open('disabledrules.json', 'w') as outfile:
			json.dump(disabledrules, outfile)

		await client.send_message(specialchannel_prod, 'Disabledrules file didn’t exist yet, created a new one.')

@client.event
async def on_message(message):
	global msg_start, hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, hangmanstarter, guessedletters, algeraden, memberroles, rules, disabledrules

	if message.author == client.user: # is the message sent by the bot
		return # do nothing

	specialchannel = getspecialchannel_reply(message)
	displaymessagecontent = ('``{}``**`…`**'.format(mdspecialchars(message.content[:100]))) if len(message.content) > 100 else '``{}``'.format(mdspecialchars(message.content)).replace('\n', '``**`\\n`**``​')
	if displaymessagecontent[-12:] == '``**`\\n`**``​':
		displaymessagecontent += '``'
	isprivate = isprivatemessage(message.server) # cant use isprivatemessage = isprivatemessage(), otherwise python will think "holy fuck a variable was referenced before assignment"

	try:
		if not isprivate and str(message.author.status) == 'offline':
			msg_start = '**`>`**👻`user` **``{}``**`#{}` `({}) was invisible when sending message {} in channel` <#{}> `at {} UTC`'.format(mdspecialchars(message.author.name), message.author.discriminator, message.author.id, message.id, message.channel.id, message.timestamp)
			await client.send_message(specialchannel, msg_start)
	except AttributeError:
		return

	if not isprivate and message.tts:
		msg_start = '**`>`**`🎙message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `was sent with TTS.`\n{}'.format(message.id, mdspecialchars(message.author.name), message.author.discriminator, message.author.id, message.channel.id, message.content)
		await client.send_message(specialchannel, msg_start[0:1998]) # Just be very certain that the message isn't too long

	if message.attachments != []:
		actuallyretrieving = await fetch(message.attachments[0]['url'])
		with open(attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename'], 'wb') as f:
			f.write(actuallyretrieving)
			f.close()

	if not isprivate and message.author.id in config.get_s('blacklist', message.server.id):
		return

	if message.content.startswith(invoker): # does the message start with command invoker
		altinvokeractive = False
		hangmaninvokeractive = False
		pass # continue, go on
	elif message.content.startswith(altinvoker): # does the message start with alt invoker
		altinvokeractive = True
		hangmaninvokeractive = False
		pass
	elif message.content.startswith(hangmaninvoker):
		hangmaninvokeractive = True
		pass
	else:
		return

	if isprivate:
		invokesymbol = '@'
	elif is_mod(message.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'
	if hangmaninvokeractive:
		if not hangmanactive:
			return
		if is_mod(message.author):
			msg_start = '**`>`**``{}``**`#`**{}\n'.format(mdspecialchars(message.author.name), displaymessagecontent)
		else:
			msg_start = '**`>`**``{}``**`$`**{}\n'.format(mdspecialchars(message.author.name), displaymessagecontent)
		if isprivate:
			content = 'Guesses are not accepted via PM.'
			msg = msg_start + content
			await client.send_message(message.channel, msg)
		if message.channel.id != '201130047736643584':
			return
		hangmanguessed = message.content[1:]

		if len(hangmanguessed) == 1:
			# Have we already used that letter? And is it a valid letter?
			if alphabet.find(hangmanguessed.upper()) == -1:
				content = 'The character ``{}`` is invalid.'.format(mdspecialchars(hangmanguessed.upper()))
				msg = msg_start + content
				await client.send_message(message.channel, msg)
				return
			if guessedletters[alphabet.find(hangmanguessed.upper())]:
				content = 'The letter **{}** has already been used.'.format(hangmanguessed.upper())
				msg = msg_start + content
				await client.send_message(message.channel, msg)
				return
			# Ok, so does this letter occur in the word?
			if hangmanchosenword.upper().find(hangmanguessed.upper()) != -1:
				# Set the guessed letter correctly
				guessedletters[alphabet.find(hangmanguessed.upper())] = True

				content = '**{}** is correct!\n{}'.format(hangmanguessed.upper(), hangmanworddisp(hangmanchosenword))
				msg = msg_start + content
				await client.send_message(message.channel, msg)

				if algeraden:
					hangmanactive = False
					content = 'You guessed the word correctly! You made {} mistakes in total.'.format(hangmantotalattempts-hangmanattempts)
					await client.send_message(message.channel, content)
					return
			else:
				# Set the guessed letter correctly, and it has to be a letter
				guessedletters[alphabet.find(hangmanguessed.upper())] = True
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					content = '**{}** is incorrect! Game over. The word was: **{}**'.format(hangmanguessed.upper(), hangmanchosenword)
					msg = msg_start + content
					await client.send_message(message.channel, msg)
					return
				else:
					content = '**{}** is incorrect! {} attempts left.\n{}'.format(hangmanguessed.upper(), hangmanattempts, hangmanworddisp(hangmanchosenword))
					msg = msg_start + content
					await client.send_message(message.channel, msg)
					return
		else:
			# We're guessing the entire word. Well, is it the word?
			if hangmanguessed.lower() == hangmanchosenword.lower():
				hangmanactive = False
				content = 'You guessed the word ({}) correctly! You made {} mistakes in total.'.format(hangmanchosenword, hangmantotalattempts-hangmanattempts)
				msg = msg_start + content
				await client.send_message(message.channel, msg)
				return
			elif len(hangmanguessed) != len(hangmanchosenword):
				# We're not even trying. It's not the same length.
				if len(hangmanguessed) == 0: # if before was "not even trying", this is -1 trying
					content = 'You should probably enter in a letter.'
					msg = msg_start + content
					await client.send_message(message.channel, msg)
					return
				content = '**``{}``** isn’t even the same length as the correct word. Please try again.'.format(mdspecialchars(hangmanguessed))
				msg = msg_start + content
				await client.send_message(message.channel, msg)
				return
			else:
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					msg = msg_start + content
					content = '**{}** is not the word! Game over. The word was: **{}**'.format(hangmanguessed, hangmanchosenword)
					await client.send_message(message.channel, msg)
					return
				else:
					content = '**{}** is not the word! {} attempts left.\n{}'.format(hangmanguessed, hangmanattempts, hangmanworddisp(hangmanchosenword))
					msg = msg_start + content
					await client.send_message(message.channel, msg)
					return

		return # make sure it always returns

	elif altinvokeractive:
		command = message.content.split(altinvoker, 1)[1]
		msg_start = '**`>`**``{}``**`{}`**{}\n'.format(mdspecialchars(message.author.name), invokesymbol, displaymessagecontent) # shows what the user put in, without main invoker
	else:
		command = message.content.split(invoker, 1)[1] # removes invoker from the message
		msg_start = '**`>`**``{}``**`{}`**{}\n'.format(mdspecialchars(message.author.name), invokesymbol, displaymessagecontent) # shows what the user put in

	# Prevent access to those who aren't supposed to send messages
	if not isprivate and not is_mod(message.author) and message.channel.id != '201130047736643584' and message.server.id == productionserver and not (is_dev(message.author) and message.channel.id == '238423391571279872'):
		return
	try:
		arguments = command.split(' ', 1)[1]
	except IndexError:
		arguments = None
	command = command.split(' ', 1)[0]
	if not isprivate and command in config.get_s('disabledcommands', message.server.id):
		await reply(message, 'This command is currently disabled{}.'.format(' on this server' if config.is_detached('disabledcommands', message.server.id) else ''))
		return

	if command == 'help':
		content = (
			'`[\]` is a bot written by Info Teddy and Dav999 in Python utilizing `discord.py`, for use on the tOLP Discord server.\n'
			'To get accepted into the developer team, you have to be accepted by eighty-percent of the current members of the team.\n'
			'Special thanks to Format for making the current icon for the bot.\n'
			'The bot is currently hosted on Info Teddy’s personal computer.'
			+ helplist(cmds)
			)

		# General
		if arguments == None:
			pass
		else:
			matched = False
			for cat in (cmds):
				if arguments == cat['cat_slug']:
					content = helplist(cmds, arguments)
					matched = True
					break

				for cmd in cat['commands']: # Maybe have a nested try-except KeyError instead of looping through every command
					if arguments == cmd['name']:
						try:
							content = '`\{}` – {}'.format(cmd['name'], cmd['extrafull'])
						except KeyError:
							content = '`\{}` – {}\n{}'.format(cmd['name'], cmd['short'], cmd['extra'])
						matched = True
						break
				if matched:
					break

			if not matched:
				content = 'Invalid arguments passed, or the command is not in the help list. Input `\help` for a list of valid commands to pass as arguments.'
		await reply(message, content)
	elif command == 'restart':
		if not is_operator(message.author):
			content = t['op_only']
			logging.info('bot restart tried to be called by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		content = 'Restarting. Uptime was {}.'.format(reltime(boottimeunix, True))
		logging.info('bot restart called by {}#{} (uuid {}) at {} utc'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		await reply(message, content)
		await os.execl(__file__, '')
	elif command == 'kill':
		if not is_operator(message.author):
			content = t['op_only']
			logging.info('bot kill tried to be called by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		content = 'Killing.'
		logging.info('bot kill called by {}#{} (uuid {}) at {} utc'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		await reply(message, content)
		await sys.exit()
	elif command == 'config':
		if not is_operator(message.author):
			content = t['op_only']
			logging.info('');
			await reply(message, content)
			return
		if arguments == None:
			content = (
				'You can use the following options:\n'
				'`\config list`\n'
				'`\config reload`\n'
				'`\config get <key>`\n'
				'`\config set <key> <value>` (not for arrays)\n'
				'`\config insert <key> <value>` (only for arrays)\n'
				'`\config remove <key> <value>` (only for arrays)\n'
				'`\config detach <key>`\n'
				'`\config reattach <key>`\n'
				'`\config default <key>`\n'
			)
			await reply(message, content)
			return
		elif arguments == 'reload':
			config.load()
			content = 'Reloaded config.'
			await reply(message, content)
			return
		elif arguments == 'list':
			content = '```css'
			for c in config.s:
				content += '\n{} [{}] = {}'.format(c, config.get_type(c) + ('*' if config.is_array(c) else ''), config.get_s(c, message.server.id) if not config.is_array(c) else '[{}]'.format(len(config.get_s(c, message.server.id))))
				if config.is_detached(c, message.server.id):
					content += ' [local value]'
			content += '\n```'
			await reply(message, content)
			return

		splitargs = arguments.split(' ', 2)

		if splitargs[0] == 'set':
			if not config.exists(splitargs[1]):
				content = 'That setting does not exist'
				await reply(message, content)
				return
			if config.is_array(splitargs[1]):
				content = 'That doesn’t work for an array'
				await reply(message, content)
				return
			if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
				content = 'Integer expected'
				await reply(message, content)
				return
			config.set_s(splitargs[1], splitargs[2], message.server.id)
			config.saveconfig()
			content = 'Set `{}` to `{}`'.format(splitargs[1], mdspecialchars(splitargs[2]))
			await reply(message, content)
		elif splitargs[0] == 'get':
			if not config.exists(splitargs[1]):
				content = 'That setting does not exist'
				await reply(message, content)
				return
			content = 'Key: `{}`   Type: `{}`   Array: `{}`   Detachable: `{}`   Using: `{}`\n'.format(splitargs[1], config.get_type(splitargs[1]), config.is_array(splitargs[1]), config.is_detachable(splitargs[1]), ('Local value' if config.is_detached(splitargs[1], message.server.id) else 'Master value'))
			if config.get_expl(splitargs[1]) != None:
				content += 'Explanation: {}\n'.format(config.get_expl(splitargs[1]))
			content += 'Value:'

			if config.is_array(splitargs[1]):
				for val in config.get_s(splitargs[1], message.server.id):
					content += ' `{}`,'.format(val)
			else:
				content += ' `{}`\nDefault: `{}`'.format(config.get_s(splitargs[1], message.server.id), config.get_default(splitargs[1]))
			await reply(message, content)
		elif splitargs[0] == 'insert' or splitargs[0] == 'remove':
			if not config.exists(splitargs[1]):
				content = 'That setting does not exist'
				await reply(message, content)
				return
			if not config.is_array(splitargs[1]):
				content = 'That doesn’t work for something that is not an array'
				await reply(message, content)
				return
			if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
				content = 'Integer expected'
				await reply(message, content)
				return
			if splitargs[0] == 'insert':
				config.insert_s(splitargs[1], splitargs[2], message.server.id)
				content = 'Inserted `{}` into array `{}`'.format(mdspecialchars(splitargs[2]), splitargs[1])
			else:
				config.remove_s(splitargs[1], splitargs[2], message.server.id)
				content = 'Removed `{}` from array `{}`'.format(mdspecialchars(splitargs[2]), splitargs[1])
			config.saveconfig()
			await reply(message, content)
		elif splitargs[0] == 'detach' or splitargs[0] == 'reattach':
			if not config.exists(splitargs[1]):
				content = 'That setting does not exist'
				await reply(message, content)
				return
			if not config.is_detachable(splitargs[1]):
				content = 'That setting cannot have an independent local value.'
				await reply(message, content)
				return
			if splitargs[0] == 'detach':
				config.detach(splitargs[1], message.server.id)
				content = 'Setting `{}` now uses a local value for this server.'.format(splitargs[1])
			else:
				config.reattach(splitargs[1], message.server.id)
				content = 'Setting `{}` is now using the master value again on this server.'.format(splitargs[1])
			config.saveconfig()
			await reply(message, content)
		elif splitargs[0] == 'default':
			if not config.exists(splitargs[1]):
				content = 'That setting does not exist'
				await reply(message, content)
				return
			config.restore_default(splitargs[1], message.server.id)
			config.saveconfig()
			content = 'Set `{}` back to default value of `{}`'.format(splitargs[1], mdspecialchars(config.get_default(splitargs[1])))
			await reply(message, content)
		else:
			content = '`{}` was not recognized'.format(splitargs[0])
			await reply(message, content)
	elif command == 'echo':
		if arguments == None:
			arguments = ''
		displayarguments = (arguments[:1769]) if len(arguments) > 1769 else arguments
		await reply(message, displayarguments)
	elif command == '':
		content = (
			'<@{}>\n'
			'```fix\n'
			'Luigi: have you ever by accident pressed another key at the same time you have pressed enter?\'\n'
			'Luigi: ugh\n'
			'ShinyWolf07: \\\n'
			'ShinyWolf07: this\n'
			'Luigi: is\n'
			'Luigi: cancer\n'
			'ShinyWolf07: I always do th\n'
			'ShinyWolf07: its so annoyng\n'
			'ShinyWolf07: \\\n'
			'ShinyWolf07: UGh\\\n'
			'Luigi: xd\n'
			'Luigi: x\n'
			'Luigi: d\n'
			'Luigi: d\n'
			'ShinyWolf07: xd\\\n'
			'Luigi: x\n'
			'ShinyWolf07: F***!!!!!|\n'
			'Luigi: XD\n'
			'ShinyWolf07: ARGH\\\n'
			'Luigi: This is funny to watch you\n'
			'Luigi: Did you make popcorn\n'
			'ShinyWolf07: xd ikr \\\n'
			'ShinyWolf07: ...\n'
			'ShinyWolf07: -_-\\\n'
			'ShinyWolf07: GAH\\\n'
			'Luigi: don\'t you mean ...\\\n'
			'ShinyWolf07: ...\n'
			'ShinyWolf07: sigh\n'
			'Luigi: 10/10 would watch again```'
			).format(message.author.id)
		await reply(message, content)
	elif command == 'hangman':
		if hangmanactive:
			content = 'ERROR: Hangman is already running. It can be aborted by the starter or by a mod with `\stophangman`.'
			await reply(message, content)
			return
		if not isprivatemessage(message.server):
			content = 'For now, this can only be run via DM.'
			await reply(message, content)
			return
		if arguments == None:
			content = 'Please specify a word.'
			await reply(message, content)
			return
		if not arguments.isalpha():
			content = 'ERROR: Words can only consist of letters A-Z'
			await reply(message, content)
			return
		if len(arguments) > 50:
			content = 'ERROR: Sorry, but your word is too long. It can be 50 characters max.'
			await reply(message, content)
			return

		hangmanchosenword = arguments
		hangmanattempts = 10
		hangmantotalattempts = 10
		hangmanactive = True
		hangmanstarter = message.author
		guessedletters = [False]*26
		msg_start = '**`>`**``{}``**`{}`**``\{} {}``\n'.format(mdspecialchars(message.author.name), invokesymbol, mdspecialchars(command.split(' ')[0]), '*'*len(hangmanchosenword)) # you will never have mod/admin perms in private messages (probably), where the hangman will be started from, so for now theres no mod/admin check to make the input display different
		content = 'New game of hangman initiated by <@{}> with a custom word. Guess letters by chatting "{}" followed by the letter (for example {}a) or the word. {} attempts left.\n{}'.format(hangmanstarter.id, hangmaninvoker, hangmaninvoker, hangmanattempts, hangmanworddisp(hangmanchosenword))
		msg = msg_start + content
		await client.send_message(botschannel, msg)

		content = 'https://discord.gg/6e3KcEv'
		await reply(message, content)
	elif command == 'stophangman':
		if not hangmanactive:
			content = 'ERROR: Can’t abort hangman because it’s not running.'
			await reply(message, content)
			return
		elif not is_mod(message.author) and message.author.id != hangmanstarter.id:
			content = 'ERROR: Can’t abort hangman because you haven’t started this game.'
			await reply(message, content)
			return

		hangmanactive = False
		content = 'Game of hangman aborted. The word was: **{}**'.format(hangmanchosenword)
		await client.send_message(botschannel, content)
	elif command == 'source':
		content = 'Source code to the bot: __https://gitgud.io/infoteddy/bracketed_backslash__'
		await reply(message, content)
	elif command == 'findu' or command == 'findup':
		targetmember = get_member_input(message.server, arguments)
		if targetmember == None:
			content = 'Unable to find that member. ' + t['specify_user']
			await reply(message, content)
			return
		if targetmember.nick == None:
			displaynick = '**`No Nickname`**'
		else:
			displaynick = '**`Nickname:`** ``{}``'.format(mdspecialchars(targetmember.nick))

		if command == "findup":
			displaymatch = '<@{}>'.format(targetmember.id)
		else:
			displaymatch = '__@{}__'.format(targetmember.display_name)
		if targetmember.game == None:
			memberhasgame = False
			displaygamestatus = 'Not Playing'
			displaygamename = 'Not Playing'
			displaygameurl = 'No Stream Link'
			pass
		else:
			memberhasgame = True
		if memberhasgame:
			if targetmember.game.type == 0 or targetmember.game.type == None:
				displaygamestatus = 'Playing'
				displaygamename = '``{}``'.format(mdspecialchars(targetmember.game.name))
			if targetmember.game.type == 1:
				displaygamestatus = 'Streaming'
			if targetmember.game.url == None:
				displaygameurl = 'No Stream Link'
			else:
				displaygameurl = '``{}``'
		embed = discord.Embed(colour=targetmember.colour)
		embed.set_thumbnail(url=targetmember.avatar_url)
		embed.add_field(name='Nickname' if targetmember.nick != None else 'No Nickname', value='``{}``'.format(mdspecialchars(targetmember.nick)) if targetmember.nick != None else 'No Nickname')
		embed.add_field(name='Username', value='``{}``'.format(mdspecialchars(targetmember.name)))
		embed.add_field(name='Discriminator', value='#{}'.format(targetmember.discriminator))
		embed.add_field(name='User ID', value=targetmember.id)
		embed.add_field(name='Bot', value='Yes' if is_bot(targetmember) else 'No')
		embed.add_field(name=displaygamestatus, value=displaygamename)
		embed.add_field(name='Stream Link', value=displaygameurl)
		embed.add_field(name='Status', value='Do Not Disturb' if str(targetmember.status) == 'dnd' else str(targetmember.status).title())
		embed.add_field(name='Default Avatar', value=str(targetmember.default_avatar).title())
		embed.add_field(name='Joined Server At', value=str(targetmember.joined_at) + ' UTC')
		embed.add_field(name='Joined Discord At', value=str(targetmember.created_at) + ' UTC')
		embed.add_field(name='Color', value='_(default)_' if str(targetmember.colour) == '#000000' else str(targetmember.colour).upper())
		# IMPORTANT: in `embed.add_field()`, `name` or `value` cannot be an empty string or you will get a 400 bad request when sending it
		# (i learned that the hard way)
		# (that was about twenty restarts smh)
		content = 'Matched ' + displaymatch
		await reply(message, content, embed)
	elif command == 'softban':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('softban attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return

		try:
			targetmember = get_member_input(message.server, arguments)
			await client.remove_roles(targetmember,
				discord.utils.get(message.server.roles, id='173240966575161344'), # nonsense-only
				discord.utils.get(message.server.roles, id='216647716531339264'), # no general mentions
				discord.utils.get(message.server.roles, id='222046096216686592'), # no cedule
				discord.utils.get(message.server.roles, id='215954720555139073'), # no tts
				discord.utils.get(message.server.roles, id='241183168269516800'), # no reactions
			)
			await client.add_roles(targetmember, discord.utils.get(message.server.roles, id='220643748508467220')) # The banned role
		except(AttributeError,TypeError):
			content = t['specify_user']
			await reply(message, content)
			return

		content = ':no_entry: <@{}> has been softbanned.'.format(targetmember.id)
		await reply(message, content)
	elif command == 'nononly' or command == 'nogenmen' or command == 'nocedule' or command == 'notts' or command == 'noreact':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('{} attempted by {}#{} (uuid {}) at {} utc but failed'.format(command, message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return
		roletoadd = {
			'nononly': '173240966575161344',
			'nogenmen': '216647716531339264',
			'nocedule': '222046096216686592',
			'notts': '215954720555139073',
			'noreact': '241183168269516800',
		}
		rolelabel = {
			'nononly': 'Nonsense-Only',
			'nogenmen': 'No General Mentions',
			'nocedule': 'No Custom Emotes/Direct Uploads/Link Embeds',
			'notts': 'No TTS',
			'noreact': 'No Reactions',
		}
		try:
			targetmember = get_member_input(message.server, arguments)
			await client.add_roles(targetmember, discord.utils.get(message.server.roles, id=roletoadd[command]))
		except(AttributeError,TypeError):
			content = t['specify_user']
			await reply(message, content)
			return
		content = 'Gave <@{}> the {} role.'.format(targetmember.id, rolelabel[command])
		await reply(message, content)
	elif command == 'nonick':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('nonick attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return
		try:
			targetmember = get_member_input(message.server, arguments)
			await client.add_roles(targetmember, discord.utils.get(message.server.roles, id='236925451216355338'))
			await client.remove_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
		except(AttributeError,TypeError):
			content = t['specify_user']
			await reply(message, content)
			return
		content = 'Gave <@{}> the tOLPer who can’t change nickname role, and removed the tOLPer role from them.'.format(targetmember.id)
		await reply(message, content)
		return
	elif command == 'voicemute' or command == 'voiceunmute':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('voicemute attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		targetmember = get_member_input(message.server, arguments)
		try:
			if targetmember.voice.voice_channel == None:
				content = 'User is not in a voice channel.'
				await reply(message, content)
				return
			if command == 'voicemute':
				await client.server_voice_state(targetmember, mute=1)
			elif command == 'voiceunmute':
				await client.server_voice_state(targetmember, mute=0)
		except AttributeError:
			content = t['specify_user']
			await reply(message, content)
			return
		except discord.errors.Forbidden:
			content = t['no_permission']
			await reply(message, content)
			return
		if command == 'voicemute':
			content = 'Voice muted <@{}>.'.format(targetmember.id)
		elif command == 'voiceunmute':
			content = 'Voice unmuted <@{}>.'.format(targetmember.id)
		await reply(message, content)
	elif command == 'rolerst':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('rolerst attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return

		try:
			targetmember = get_member_input(message.server, arguments)
			await client.remove_roles(targetmember,
				discord.utils.get(message.server.roles, id='173240966575161344'), # nonsense-only
				discord.utils.get(message.server.roles, id='216647716531339264'), # no general mentions
				discord.utils.get(message.server.roles, id='222046096216686592'), # no cedule
				discord.utils.get(message.server.roles, id='215954720555139073'), # no tts
				discord.utils.get(message.server.roles, id='220643748508467220'), # banned
				discord.utils.get(message.server.roles, id='236925451216355338'), # tolper who cant change nickname
				discord.utils.get(message.server.roles, id='241183168269516800'), # no reactions
			)
			if not is_bot(targetmember):
				await client.add_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
		except(AttributeError,TypeError):
			content = t['specify_user']
			await reply(message, content)
			return
		content = 'Reset roles for <@{}> back to normal.'.format(targetmember.id)
		await reply(message, content)
	elif command == 'rolecacherst':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('rolecacherst attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return
		elif get_member_input(message.server, arguments) != None:
			content = 'That member is apparently still on this server! Not removing from the cache.'
			await reply(message, content)
			return

		if removerolecache(arguments):
			content = 'Member {} successfully removed from role cache.'.format(arguments)
			await reply(message, content)
			rolecachesave()
		else:
			content = 'Member {} cannot be found in the role cache. Please note you have to enter an ID, not any form of name!'.format(arguments)
			await reply(message, content)
	elif command == 'rolesync':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('rolesync attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return

		for mem in message.server.members:
			updaterolecache(mem)

		rolecachesave()

		content = 'Synced roles.'
		await reply(message, content)
	elif command == 'rules' or command == 'rule':
		if isprivatemessage(message.server):
			content = 'Rules:\n**1.** I am always right.\n**2.** If I am not right, rule 1 applies.'
			await reply(message, content)
			return
		if message.server.id in disabledrules and not is_mod(message.author):
			content = 'The rules system is currently disabled for this server.'
			await reply(message, content)
			return
		if not message.server.id in rules:
			content = 'Rules are not (yet) set for this server.'
			await reply(message, content)
			return
		if arguments != None and arguments.isdigit():
			try:
				rules[message.server.id][int(arguments)-1]

				# Oh, we survived this? That means the given specific rule exists!
				content = 'Rule **{}** for server `{}`:\n{}'.format(int(arguments), mdspecialchars(message.server.name), rules[message.server.id][int(arguments)-1])
				await reply(message, content)
				return
			except IndexError:
				pass
		n = 1
		content = 'Rules for server `{}`:{}'.format(mdspecialchars(message.server.name), ' (Disabled)' if message.server.id in disabledrules else '')
		for rule in rules[message.server.id]:
			content += '\n**{}.** {}'.format(n, rule)
			n += 1
		await reply(message, content)
	elif command == 'rulefind' or command == 'rulesfind':
		if isprivatemessage(message.server):
			content = 'Alright, this isn’t a server, this is our private conversation. I run on multiple servers with different rules, you know.'
			await reply(message, content)
			return
		if message.server.id in disabledrules and not is_mod(message.author):
			content = 'The rules system is currently disabled for this server.'
			await reply(message, content)
			return
		if not message.server.id in rules:
			content = 'Rules are not (yet) set for this server.'
			await reply(message, content)
			return
		if arguments == None:
			content = 'Please enter a search term.'
			await reply(message, content)
			return
		matched = False
		n = 1
		content = 'Rules for server **``{}``** matching **``{}``**:'.format(mdspecialchars(message.server.name), mdspecialchars(arguments))
		for rule in rules[message.server.id]:
			if rule.lower().find(arguments.lower()) != -1:
				content += '\n**{}.** {}'.format(n, rule)
				matched = True
			n += 1
		if not matched:
			content = 'No rules on server `{}` matching `{}`.'.format(mdspecialchars(message.server.name), mdspecialchars(arguments))
		await reply(message, content)
	elif command == 'ruleadd' or command == 'addrule':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('ruleadd yada yada')

			await reply(message, content)
			return
		if arguments == None:
			content = 'I’m not going to think up any rules by myself.'
			await reply(message, content)
			return
		if not message.server.id in rules:
			rules[message.server.id] = []

		splitargs = arguments.split(' ', 1)
		if splitargs[0].isdigit():
			if int(splitargs[0]) > len(rules[message.server.id]):
				content = '**Why are you mentioning the number if you’re adding this at the end?**\n'
			else:
				content = ''
			rules[message.server.id].insert(int(splitargs[0])-1, splitargs[1])
			content += 'New rule {} inserted:\n{}'.format(int(splitargs[0]), splitargs[1])      # Yes, this one is "inserted"...
		else:
			rules[message.server.id].append(arguments)
			content = 'New rule {} added:\n{}'.format(len(rules[message.server.id]), arguments) # ...and this one is "added". That is on purpose, not an inconsistency.
		rulesave()
		await reply(message, content)
	elif command == 'ruleedit' or command == 'editrule':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('ruleedit yada yada')

			await reply(message, content)
			return
		if arguments == None:
			content = 'This command expects you to enter some more info, maybe read its help entry.'
			await reply(message, content)
			return
		if not message.server.id in rules:
			content = 'No rules to edit.'
			await reply(message, content)
			return

		splitargs = arguments.split(' ', 1)
		if splitargs[0].isdigit():
			try:
				rules[message.server.id][int(splitargs[0])-1]
			except IndexError:
				content = 'Rule {} does not appear to exist.'.format(int(splitargs[0]))
				await reply(message, content)
				return

			content = 'Rule {} successfully edited from:\n{}\nTo:\n{}'.format(int(splitargs[0]), rules[message.server.id][int(splitargs[0])-1], splitargs[1])

			rules[message.server.id][int(splitargs[0])-1] = splitargs[1]
			rulesave()
		else:
			content = 'Invalid rule number given, just check the help entry.'
		await reply(message, content)
	elif command == 'rulemove' or command == 'moverule':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('rulemove yada yada')

			await reply(message, content)
			return
		if arguments == None:
			content = 'This command expects you to enter some more info, maybe read its help entry.'
			await reply(message, content)
			return
		if not message.server.id in rules:
			content = 'No rules to move.'
			await reply(message, content)
			return

		splitargs = arguments.split(' ', 1)
		if splitargs[0].isdigit() and splitargs[1].isdigit():
			try:
				rules[message.server.id][int(splitargs[0])-1]
				rules[message.server.id][int(splitargs[1])-1]
			except IndexError:
				content = 'Either rule {} does not exist or {} is not a slot it can be moved to.'.format(int(splitargs[0]), int(splitargs[1]))
				await reply(message, content)
				return

			rulecontent = rules[message.server.id][int(splitargs[0])-1]
			rules[message.server.id].remove(rules[message.server.id][int(splitargs[0])-1])
			rules[message.server.id].insert(int(splitargs[1])-1, rulecontent)
			rulesave()

			content = 'Rule {} successfully moved to number {}.'.format(int(splitargs[0]), int(splitargs[1]))
		else:
			content = 'Invalid rule number(s) given, just check the help entry.'
		await reply(message, content)
	elif command == 'ruleremove' or command == 'removerule':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('ruleremove yada yada')

			await reply(message, content)
			return
		if arguments == None:
			content = 'This command expects you to enter some more info, maybe read its help entry.'
			await reply(message, content)
			return
		if not message.server.id in rules:
			content = 'No rules to delete.'
			await reply(message, content)
			return

		if arguments.isdigit():
			try:
				rules[message.server.id][int(arguments)-1]
			except IndexError:
				content = 'Rule {} does not appear to exist.'.format(int(arguments))
				await reply(message, content)
				return

			content = 'Rule {} successfully removed:\n{}'.format(int(arguments), rules[message.server.id][int(arguments)-1])

			rules[message.server.id].remove(rules[message.server.id][int(arguments)-1])
			rulesave()
		else:
			content = 'Invalid rule number given, just check the help entry.'
		await reply(message, content)
	elif command == 'rulemaint':
		if not is_mod(message.author):
			content = t['mod_only']
			logging.info('rulemaint yada yada')

			await reply(message, content)
			return
		if message.server.id in disabledrules:
			disabledrules.remove(message.server.id)
			content = 'Rules system enabled for this server.'
		else:
			disabledrules.append(message.server.id)
			content = 'Rules system disabled for this server.'
		with open('disabledrules.json', 'w') as outfile:
			json.dump(disabledrules, outfile)
		await reply(message, content)
	elif command == 'info':
		persontocheck = get_member_input(message.server, arguments)
		yesperm = '☑'
		noperm = '❎'
		try:
			perms = discord.Channel.permissions_for(message.channel, persontocheck)
		except AttributeError:
			content = t['specify_user']
			await reply(message, content)
			return

		leftover = []
		for detected_p in iter(perms):
			leftover.append(detected_p[0])

		content = 'Permissions for **``{}``**`#{}` in <#{}>:\n**`Server Owner:`** {}'.format(persontocheck.name, persontocheck.discriminator, message.channel.id, yesperm if persontocheck == persontocheck.server.owner else noperm)

		for stored_p in permissionlabels:
			if not stored_p[0] in leftover:
				content += '\n**`{}:`** NOT USED'.format(stored_p[1])
			else:
				content += '\n**`{}:`** {}'.format(stored_p[1], yesperm if getattr(perms, stored_p[0]) else noperm)
				leftover.remove(stored_p[0])
			if perms.administrator:
				await reply(message, content)
				return

		for left_p in leftover:
			# Apparently these permissions are new
			content += '\n`{}:` {}'.format(left_p, yesperm if getattr(perms, left_p) else noperm)

		await reply(message, content)
	elif command == 'teddy':
		content = 'xd'
		await reply(message, content)
	elif command == 'samar':
		content = 'Why does he like Undertale?'
		await reply(message, content)
	elif command == 'lui':
		content = 'i think /r/undertale is a pretty cool guy, eh deletes messages and doesnt afraid of lying'
		await reply(message, content)
	elif command == 'shiny':
		content = 'moar liek shittykitty amirite'
		await reply(message, content)
	elif command == 'tainy':
		content = random.choice([
			'moar liek stainy amirite',
			'moar like painy amirite',
		])
		await reply(message, content)
	elif command == 'kys':
		content = 'nah'
		await reply(message, content)
	elif command == 'botok':
		content = 'Bot is okay.'
		await reply(message, content)
	elif command == 'uptime':
		hostuptime = subprocess.Popen(['uptime'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
		content = (
			'**`Boot time:`**        `{}`\n'
			'**`Current time:`** `{}`\n'
			'**`Bot Uptime:`**      `{}`\n'
			'**`Host Uptime:`**   `{}`'
		).format(
			boottime,
			time.strftime(config.get_s('timeformat', message.server.id)),
			reltime(boottimeunix, True),
			hostuptime.decode('utf-8'),
		)
		await reply(message, content)
	elif command == '*formatting*':
		content = 'That’s italicized formatting.'
		await reply(message, content)
	elif command == '/r/undertale':
		content = 'They banned someone for posting an honest review of Undertale. Seriously, don’t go there if you don’t want to be censored.'
		await reply(message, content)
	elif command == 'invite':
		content = (
			'**`tOLP Discord`** – the server it’s built for. Join at __https://discord.gg/0r76El7PzkPMhSBF__.\n'
			'**`Aperture Science`** – the bot’s testing server. Join at __https://discord.gg/0skUn2HYSEHxw9Dg__.'
		)
		await reply(message, content)
	elif command == 'version':
		content = (
			'**`[\]`** – {}, last updated {}\n'
			'**`discord.py`** – {} {}'
		).format(
			botversion,
			modificationtimecache,
			discord.version_info.releaselevel, discord.__version__,
		)
		await reply(message, content)
	elif command == 'getrawmessagecontent':
		if not is_mod(message.author):
			logging.info('getrawmessagecontent attempted by {}#{} ({}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			content = t['mod_only']
			await reply(message, content)
			return
		try:
			argsplit = arguments.split(' ', 1)
			arg0 = argsplit[0]
			arg1 = argsplit[1]
			channelid = arg0[2:-1]
			getchannel = client.get_channel(channelid)
			getmessage = await client.get_message(getchannel, arg1)
			content = '``{}``'.format(mdspecialchars(getmessage.content[:1900]))
		except AttributeError:
			content = 'Invalid arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command)
		except IndexError:
			content = 'Invalid amount of arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command)
		except discord.errors.HTTPException:
			content = 'Invalid message ID given. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command)
		await reply(message, content)
	elif command == 'addcontrib' or command == 'removecontrib':
		if message.server.id != productionserver:
			content = t['production_only']
			await reply(message, content)
			return
		contribmodrole = discord.utils.get(message.server.roles, id='249695436812713984')
		contribrole = discord.utils.get(message.server.roles, id='241728185937559552')
		targetmember = get_member_input(message.server, arguments)
		if not contribmodrole in message.author.roles:
			content = 'Permission denied. This command can only be used by a tOLP Contributor Moderator.'
			await reply(message, content)
			return
		try:
			if command == 'addcontrib':
				await client.add_roles(targetmember, contribrole)
				content = 'Made <@{}> a tOLP Contributor.'.format(targetmember.id)
			if command == 'removecontrib':
				await client.remove_roles(targetmember, contribrole)
				content = 'Made <@{}> not a tOLP Contributor.'.format(targetmember.id)
		except(AttributeError,TypeError):
			content = t['specify_user']
		await reply(message, content)
	elif command == 'countpins':
		if arguments == None:
			getchannel = message.channel
		else:
			channelid = arguments[2:-1]
			getchannel = client.get_channel(channelid)
		try:
			pins = await client.pins_from(getchannel)
			content = '{} currently has {} pins, {} remaining.'.format(getchannel.mention, len(pins), 50-len(pins))
		except AttributeError:
			content = 'The channel doesn’t exist, has been deleted, or it’s not a channel at all. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command)
		await reply(message, content)
	else:
		if altinvokeractive:
			return # do not print error message if command is invalid
		else:
			content = 'Invalid command. Input `\help` for a list of valid commands.'
			await reply(message, content)

@client.event
async def on_message_delete(message): # when a message gets deleted
	if message.author == client.user: # is the deleted message originally sent by the bot
		logging.info('bot message {} by user {}#{} ({}) in channel {} ({}) at {} utc deleted, original content is \n{}'.format(message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.channel.name, message.timestamp, message.content))
		return
	if message.content == '' and message.attachments == []:
		return

	specialchannel = getspecialchannel_reply(message)

	msg_start = '**`>`**🚫`message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `at {} UTC ({}) deleted`\n'.format(message.id, mdspecialchars(message.author.name), message.author.discriminator, message.author.id, message.channel.id, message.timestamp, reltime(time.mktime(message.timestamp.timetuple())))
	content = '_`The original content is:`_\n' + message.content
	msg = msg_start + content
	if len(msg) >= 2000:
		content = '_`The original content is (part 1):`_\n' + message.content
		msg = msg_start + content
		msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		if len(msg_split [0]) >= 2000:
			msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		content1 = msg_split[0]
		content2 = '_`The original content is (part 2):`_\n' + msg_split[1]
		msg1 = content1
		msg2 = msg_start + content2
		await client.send_message(specialchannel, msg1)
		await client.send_message(specialchannel, msg2)
	else:
		await client.send_message(specialchannel, msg)
	if message.attachments != []:
		if os.path.isfile(attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename']):
			content = '_📎`The original attachment is attached.`_'
			msg = msg_start + content
			filetoattach = attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename']
			await client.send_file(destination=specialchannel, content=msg, fp=filetoattach, filename=message.attachments[0]['filename'])
		else:
			content = '_`The attachment is not in the message attachments cache.`_'
			msg = msg_start + content
			await client.send_message(specialchannel, msg)

@client.event
async def on_message_edit(before, after): # when a message gets edited
	specialchannel = getspecialchannel_reply(after)

	if before.pinned != after.pinned:
		if before.pinned == False and after.pinned == True: # if the message was pinned
			msg_start = '**`>`**`message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `at {} UTC ({}) pinned`'.format(before.id, mdspecialchars(before.author.name), before.author.discriminator, before.author.id, before.channel.id, before.timestamp, reltime(time.mktime(before.timestamp.timetuple())))
			await client.send_message(specialchannel, msg_start)
		if before.pinned == True and after.pinned == False: # if the message was unpinned
			msg_start = '**`>`**`message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `at {} UTC ({}) unpinned`'.format(after.id, mdspecialchars(after.author.name), after.author.discriminator, after.author.id, after.channel.id, after.timestamp, reltime(time.mktime(after.timestamp.timetuple())))
			await client.send_message(specialchannel, msg_start)
	# preliminary checkings
	if before.content == after.content:
		return # must be the message being pinned and/or embed(s) displaying
	if before.author == client.user or after.author == client.user: # the bot doesnt edits its own messages, so throw a warning
		logging.warn('this is the bots own message and the bot doesnt edit messages\nid of before: {}\nid of after: {}'.format(before.id, after.id))
		return
	# checks succeeded
	msg_start = '**`>`**📝`message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `at {} UTC ({}) edited`\n'.format(before.id, mdspecialchars(before.author.name), before.author.discriminator, before.author.id, before.channel.id, before.timestamp, reltime(time.mktime(before.timestamp.timetuple())))
	content = '_`The older content is:`_\n' + before.content
	msg = msg_start + content
	if len(msg) >= 2000:
		content = '_`The older content is (part 1):`_\n' + before.content
		msg = msg_start + content
		msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		if len(msg_split [0]) >= 2000:
			msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		content1 = msg_split[0]
		content2 = '_`The older content is (part 2):`_\n' + msg_split[1]
		msg1 = content1
		msg2 = msg_start + content2
		await client.send_message(specialchannel, msg1)
		await client.send_message(specialchannel, msg2)
	else:
		await client.send_message(specialchannel, msg)
	msg_start = '**`>`**`message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `at {} UTC ({}) edited`\n'.format(after.id, mdspecialchars(after.author.name), after.author.discriminator, after.author.id, after.channel.id, after.timestamp, reltime(time.mktime(after.timestamp.timetuple())))
	content = '_`The newer content is:`_\n' + after.content
	msg = msg_start + content
	if len(msg) >= 2000:
		content = '_`The newer content is (part 1):`_\n' + after.content
		msg = msg_start + content
		msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		if len(msg_split[0]) >= 2000:
			msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		content1 = msg_split [0]
		content2 = '_`The newer content is (part 2):`_\n' + msg_split[1]
		msg1 = content1
		msg2 = msg_start + content2
		await client.send_message(specialchannel, msg1)
		await client.send_message(specialchannel, msg2)
	else:
		await client.send_message(specialchannel, msg)

	# Delete a message if it has been edited more than 5 times in 30 seconds
	if not after.id in minutemessageedits:
		minutemessageedits[after.id] = [int(time.time())]
	else:
		edittime = int(time.time())
		while True:
			if edittime in minutemessageedits[after.id]:
				edittime += 0.1
			else:
				minutemessageedits[after.id].append(edittime)
				break
		if len(minutemessageedits[after.id]) >= 5:
			for i in minutemessageedits[after.id][:]: # [:] because we may be removing elements from here
				if i < (int(time.time())-30):
					minutemessageedits[after.id].remove(i)
			if len(minutemessageedits[after.id]) >= 5:
				# Ok, that's enough editing.
				await client.delete_message(after)
				msg = '**`>`**📝📝📝📝📝`Message {} was edited too many times.`'.format(after.id)
				await client.send_message(specialchannel, msg)
				# Also actually reply
				await client.send_message(after.channel, 'Were you going to stop editing that message?')
		# While we're at it, also clean up other messages.
		for k in minutemessageedits.copy(): # Copying because we may be removing elements from here [2]
			if k != after.id:
				for i in minutemessageedits[k][:]:
					if i < (int(time.time())-30):
						minutemessageedits[k].remove(i)
				if len(minutemessageedits[k]) == 0:
					del minutemessageedits[k]

@client.event
async def on_member_update(before, after):
	specialchannel = getspecialchannel(after.server)

	if before.nick != after.nick:
		msg_start = '**`>`**🇳📟`user` **``{}``**`#{}` `({}) changed nickname`\n'.format(mdspecialchars(before.name), before.discriminator, before.id)
		if before.nick == None:
			content = '_`The older nickname is:`_ `(none)`'
		else:
			content = '_`The older nickname is:`_\n``{}``'.format(mdspecialchars(before.nick))
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		msg_start = '**`>`**`user` **``{}``**`#{}` `({}) changed nickname`\n'.format(after.name, after.discriminator, after.id)
		if after.nick == None:
			content = '_`The newer nickname is:`_ `(none)`'
		else:
			content = '_`The newer nickname is:`_\n``{}``'.format(mdspecialchars(after.nick))
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
	if before.roles != after.roles:
		if len(before.roles) > len(after.roles): # if a role has been removed
			roleremoved = list(set(before.roles).symmetric_difference(set(after.roles)))[0]
			msg_start = '**`>`**`user` **``{}``**`#{}` `({}) has role` **``{}``** `({}) removed`'.format(mdspecialchars(before.name), before.discriminator, before.id, mdspecialchars(roleremoved.name), roleremoved.id)
			await client.send_message(specialchannel, msg_start)
		if len(before.roles) < len(after.roles): # if a role has been added
			roleadded = list(set(after.roles).symmetric_difference(set(before.roles)))[0]
			msg_start = '**`>`**`user` **``{}``**`#{}` `({}) has role` **``{}``** `({}) added`'.format(after.name, after.discriminator, after.id, mdspecialchars(roleadded.name), roleadded.id)
			await client.send_message(specialchannel, msg_start)

		if before.server.id == productionserver:
			updaterolecache(after)
			rolecachesave()
	if before.name != after.name:
		msg_start = '**`>`**🇺📟`user {} changed username`\n'.format(before.id)
		content = '_`The older username is:`_\n**``{}``**\n_`The older discriminator is:`_ `#{}`'.format(mdspecialchars(before.name), before.discriminator)
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		msg_start = '**`>`**`user {} changed username`\n'.format(after.id)
		content = '_`The newer username is:`_\n**``{}``**\n_`The newer discriminator is:`_ `#{}`'.format(mdspecialchars(after.name), after.discriminator)
		msg = msg_start + content
		if before.discriminator != after.discriminator:
			msg += '🔸'
		await client.send_message(specialchannel, msg)
	if before.avatar_url != after.avatar_url and before.id != '141769689406636032' and before.id != '88575421972516864' and before.id != '196574963673595904': # isn't 35, 42 or beta 42
		msg_start = '**`>`**👥`user` **``{}``**`#{}` `({}) changed avatar`\n'.format(mdspecialchars(before.name), before.discriminator, before.id)
		content = '_`The older avatar URL is:`_ ' + before.avatar_url
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		msg_start = '**`>`**`user` **``{}``**`#{}` `({}) changed avatar`\n'.format(mdspecialchars(after.name), after.discriminator, after.id)
		content = '_`The newer avatar URL is:`_ ' + after.avatar_url
		msg = msg_start + content
		await client.send_message(specialchannel, msg)

@client.event
async def on_member_join(member):
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**➡`user` **``{}``**`#{}` `({}) joined server {} ({})`'.format(mdspecialchars(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)
	if member.server.id == productionserver:
		if is_bot(member):
			await client.add_roles(member, discord.utils.get(member.server.roles, id='201129507967598592')) # bot role
			return
		# Are they in our database of members which had roles before?
		if str(member.id) in memberroles:
			# They're found in the database! Give them the groups they should have
			for rid in memberroles[str(member.id)]:
				await client.add_roles(member, discord.utils.get(member.server.roles, id=rid)) # TODO make this less iterative and add multiple roles at once
			msg = '**`>`**`user` **``{}``**`#{}` `({}) found in the role cache`'.format(mdspecialchars(member.name), member.discriminator, member.id)
			await client.send_message(specialchannel, msg)
		else:
			# Not found, so they're just a tOLPer.
			await client.add_roles(member, discord.utils.get(member.server.roles, id='231644869351833600')) # The tOLPer role

@client.event
async def on_member_remove(member):
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**🚪`user` **``{}``**`#{}` `({}) removed from server {} ({})`'.format(mdspecialchars(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_member_ban(member):
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(mdspecialchars(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_member_unban(server, user):
	specialchannel = getspecialchannel(server)
	msg = '**`>`**<:doormat:239361673532669953>`user` **``{}``**`#{}` `({}) unbanned from server {} ({})`'.format(mdspecialchars(user.name), user.discriminator, user.id, server.name, server.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_typing(channel, user, when):
	try:
		specialchannel = getspecialchannel(channel.server)
	except AttributeError: # this would happen if the typing event is in a private message
		return
	if specialchannel.id == channel.server.default_channel.id:
		specialchannel = channel
	if str(user.status) == 'offline':
		msg = '**`>`**👻`user` **``{}``**`#{}` `({}) was invisible while typing in channel` <#{}> `at {}`'.format(mdspecialchars(user.name), user.discriminator, user.id, channel.id, when)
		await client.send_message(specialchannel, msg)
	else:
		return # practically unnecessary, but this is for if we want to do things when members type later

@client.event
async def on_server_role_create(role):
	specialchannel = getspecialchannel(role.server)
	msg = '**`>`**`role` **``{}``** `({}) was created in server` **``{}``** `({}) at {}`'.format(mdspecialchars(role.name), role.id, mdspecialchars(role.server.name), role.server.id, role.created_at)
	await client.send_message(specialchannel, msg)

@client.event
async def on_server_role_delete(role):
	specialchannel = getspecialchannel(role.server)
	msg = '**`>`**`role` **``{}``** `({}) was deleted in server` **``{}``** `({}) originally created at {}`'.format(mdspecialchars(role.name), role.id, mdspecialchars(role.server.name), role.server.id, role.created_at)
	await client.send_message(specialchannel, msg)

@client.event
async def on_server_role_update(before, after):
	specialchannel = getspecialchannel(before.server)
	if before.name != after.name: # if the name changed
		msg_start = '**`>`**`role {} has name changed`\n'.format(before.id)
		content = '_`The older name is:`_\n**``{}``**'.format(mdspecialchars(before.name))
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		content = '_`The newer name is:`_\n**``{}``**'.format(mdspecialchars(after.name))
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
	if before.hoist != after.hoist: # if "display online members separately" changed
		if before.hoist == 0 and after.hoist == 1: # if the role has been hoisted
			msg = '**`>`**`role` **``{}``** `({}) has been hoisted`'.format(mdspecialchars(after.name), after.id)
			await client.send_message(specialchannel, msg)
		if before.hoist == 1 and after.hoist == 0: # if the role has been lowered
			msg = '**`>`**`role` **``{}``** `({}) has been lowered`'.format(mdspecialchars(after.name), after.id)
			await client.send_message(specialchannel, msg)
	if before.mentionable != after.mentionable: # if "allow everyone to mention this role" changed
		if before.mentionable == 0 and after.mentionable == 1: # if the role is now mentionable
			msg = '**`>`**`role` **``{}``** `({}) is now mentionable`'.format(mdspecialchars(after.name), after.id)
			await client.send_message(specialchannel, msg)
		if before.mentionable == 1 and after.mentionable == 0: # if the role is no longer mentionable
			msg = '**`>`**`role` **``{}``** `({}) is no longer mentionable`'.format(mdspecialchars(after.name), after.id)
			await client.send_message(specialchannel, msg)
	if before.position != after.position: # if the role has been moved up or down in the hierarchy
		if before.position > after.position: # the role has been moved down
			msg = '**`>`**`role` **``{}``** `({}) has been moved down by {} roles ({} to {})`'.format(mdspecialchars(after.name), after.id, before.position - after.position, before.position, after.position)
			await client.send_message(specialchannel, msg)
		if before.position < after.position: # the role has been moved up
			msg = '**`>`**`role` **``{}``** `({}) has been moved up by {} roles ({} to {})`'.format(mdspecialchars(after.name), after.id, after.position - before.position, before.position, after.position)
			await client.send_message(specialchannel, msg)
	if before.colour != after.colour:
		msg_start = '**`>`**`role` **``{}``** `({}) has changed color`\n'.format(mdspecialchars(after.name), after.id)
		content = '_`The older color is:`_ `{}`'.format('(default)' if str(before.colour) == '#000000' else str(before.colour).upper())
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		content = '_`The newer color is:`_ `{}`'.format('(default)' if str(after.colour) == '#000000' else str(after.colour).upper())
		msg = msg_start + content
		await client.send_message(specialchannel, msg)


@client.event
async def on_reaction_add(reaction, user):
	specialchannel = getspecialchannel(reaction.message.server)
	try:
		iscustomemote = True
		emotename = reaction.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = reaction.emoji
	msg = '**`>`**`user` **``{}``**`#{}` `({}) added reaction` {} `{} to message {}'.format(mdspecialchars(user.name), user.discriminator, user.id, emotename if not iscustomemote else '**`{}`**'.format(emotename), '({})'.format(reaction.emoji.id) if iscustomemote else '', reaction.message.id)
	if str(user.status) == 'offline':
		msg += ' and was invisible while doing so`'
	else:
		msg += '`'
	await client.send_message(specialchannel, msg)

@client.event
async def on_reaction_remove(reaction, user):
	specialchannel = getspecialchannel(reaction.message.server)
	try:
		iscustomemote = True
		emotename = reaction.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = reaction.emoji
	msg = '**`>`**`reaction` {} `{} by user` **``{}``**`#{}` `from message {} removed`'.format(emotename if not iscustomemote else '**`{}`**'.format(emotename), '({})'.format(reaction.emoji.id) if iscustomemote else '', mdspecialchars(user.name), user.discriminator, user.id, reaction.message.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_server_update(before, after):
	specialchannel = getspecialchannel(after)
	if before.icon != after.icon:
		msg_start = '**`>`**`server` **``{}``** `({}) changed icon`\n'.format(mdspecialchars(before.name), before.id)
		content = '_`The older icon URL is:`_ ' + before.icon_url
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		content = '_`The newer icon URL is:`_ ' + after.icon_url
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
	if before.name != after.name:
		msg_start = '**`>`**`server {} changed name`\n'.format(before.id)
		content = (
			'_`The older name is:`_\n'
			'**``{}``**'
		).format(mdspecialchars(before.name))
		msg = msg_start + content
		await client.send_message(specialchannel, msg)
		content = (
			'_`The newer name is:`_\n'
			'**``{}``**'
		).format(mdspecialchars(after.name))
		msg = msg_start + content
		await client.send_message(specialchannel, msg)

exec(compile(open("functions.py", "rb").read(), "functions.py", 'exec'))

client.run(token)
