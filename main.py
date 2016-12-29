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
import datetime
import time
import json
import logging
import math
import traceback
import subprocess
import re
from threading import Timer

import config
import col
import emb
import images

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
embedcache = cachelocation + '/' + 'embed'

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

ownerid_config = open('ownerid.conf', 'r')
ownerid = ownerid_config.readline(18).split('\n')[0]
ownerid_config.close()


memberroles = {}
minutemessageedits = {}

rules = {}
disabledrules = []

votemutes = {} # userid -> dict with `starttime`, `proponents`*, `opponents`*

rolexpires = {} # userid -> unixtime
latestroled = None  # ID of the latest person that has been given a restrictive role
exptimer = None  # threading.Timer object

# rule numbers that we can, unsarcastically, totally all agree on are funny. Especially rule 34 and 69.
# I would be afraid a cool kid used one of them and totally outcooled everyone else using it.
# (note: 37 gives a different message - it's not as extremely funny if people use it)
funnynumbers = [34,37,69]

modificationtimes = [
	os.path.getmtime('main.py'),
	os.path.getmtime('functions.py'),
	os.path.getmtime('config.py'),
	os.path.getmtime('emb.py'),
	os.path.getmtime('col.py'),
	os.path.getmtime('images.py'),
]
modificationtimecache = time.strftime(config.get_s('timeformat'), time.gmtime(max(modificationtimes)))

client.max_messages = 999999999

maineventloop = asyncio.get_event_loop()

t = {
	'owner_only': 'Permission denied. This command can only be used by the owner.',
	'op_only': 'Permission denied. This command can only be used by an operator.',
	'mod_only': 'Permission denied. This command can only be used by a moderator or administrator.',
	'specify_user': 'Please specify a user ID, a username, a username and discriminator, or a nickname.',
	'you_no_permission': 'You don’t have permission to do this.',
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
			{
				'name': 'countallpins',
				'short': 'Count the amount of pins in all channels.',
				'extra': ''
			},
			{
				'name': 'math',
				'short': 'Does maths. What do you expect? Supports most maths operands that do not return a negative number.',
				'extra': 'Syntax: `\\math NUMBER OPERAND NUMBER`'
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
			{
				'name': 'gamestatus',
				'short': 'Sets the game status.',
				'extra': ''
			},
			{
				'name': 'eval',
				'short': 'Evaluates your arguments as code.',
				'extra': ''
			},
			{
				'name': 'evalawait',
				'short': 'Evaluates your arguments as code, but precedes them with `await`.',
				'extra': ''
			},
			{
				'name': 'evalfile',
				'short': 'Evaluates `eval.txt` as code.',
				'extra': ''
			},
			{
				'name': 'evalawaitfile',
				'short': 'Evaluates `eval.txt` as code, but precedes them with `await`.',
				'extra': ''
			},
			{
				'name': 'setvar',
				'short': 'Sets a global variable.',
				'extra': 'Syntax: `\setvar VARIABLE ASSIGNMENT`'
			}
		]
	},
	{
		'cat_name': 'Moderation Commands',
		'cat_slug': 'mod',
		'cat_desc': '',
		'cat_shown': True,
		'commands': [
			{
				'name': 'kick',
				'short': 'Kicks a user from the server.',
				'extra': t['accepts_user']
			},
			{
				'name': 'serverban',
				'short': 'Bans a user from the server.',
				'extra': t['accepts_user']
			},
			{
				'name': 'unserverban',
				'short': 'Unbans a user from the server.',
				'extra': t['accepts_user']
			},
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
				'name': 'votevoicemute',
				'short': 'Starts a vote on whether to mute a user in a voice channel.',
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
				'name': 'expires',
				'short': 'Sets an expiry time for someone’s ban or otherwise restrictive roles. It will carry out a role reset after the specified time has elapsed.',
				'extra': 'The first argument is always required, and takes a relative time in the format `[#d][#h][#m][#s]`, for example: `7d12h`, `1h`, `1d`, `1d2h3m4s`, `1d20s` or whatever combination you can think of. The units have to be in the correct order, though.\nThe second argument is optional, if given, it means the nickname/username/part of it/ID/discriminator of the member to set the expiry time for, if not given, the latest member to have been given a role will be chosen.'
			},
			{
				'name': 'expirylist',
				'short': 'Gives a list of all expiry timers that are currently running.',
				'extra': ''
			},
			{
				'name': 'rolecacheadd',
				'short': 'Gives someone a role after they have left the server.',
				'extra': 'Give a user ID, then a space, and then the role you want to add.'
			},
			{
				'name': 'rolesync',
				'short': 'Re-syncs the roles cache with the current roles everyone has, if the bot missed role additions/removals',
				'extra': 'Does not remove members from the cache who have left the server.'
			},
			{
				'name': 'rolecacheinfo',
				'short': 'Shows the roles that are stored in the role cache for a certain user.',
				'extra': 'Only accepts a user ID!',
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
		'cat_slug': config.get_s('meme_helplist_string'),
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
			{
				'name': 'fuckingdense',
				'short': 'Stop making fun of them! They have children at age 18, after all.',
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
	global memberroles, rules, disabledrules, server, specialchannel_prod, botschannel, voicetextchannel, productionserver, rolexpires
	productionserver = '153368829160849408'
	server = discord.utils.get(client.servers, id=productionserver) # defines all server.* commands
	specialchannel_prod = discord.utils.get(server.channels, id='234185735266238464')
	botschannel = discord.utils.get(server.channels, id='201130047736643584')
	voicetextchannel = discord.utils.get(server.channels, id='256924583737819146')
	logging.info('logged in as {} with id {}'.format(client.user.name, client.user.id))
	await client.change_presence(game=discord.Game(name=config.get_s('gamestatus')))
	embed = discord.Embed(title='🔌BOT CONNECTED', colour=server.me.colour)
	embed.add_field(name='Startup Time', value=reltime(boottimeunix))
	await client.send_message(specialchannel_prod, embed=embed)

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

	try:
		with open('rolexpires.json', 'r') as infile:
			rolexpires = json.load(infile)
	except FileNotFoundError:
		logging.info('rolexpires file does not exist yet so creating it now')
		rolexpires = {}

		with open('rolexpires.json', 'w') as outfile:
			json.dump(rolexpires, outfile)

		await client.send_message(specialchannel_prod, 'Rolexpires file didn’t exist yet, created a new one.')

	await handleExpiryTimer()

@client.event
async def on_message(message):
	global msg_start, hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, hangmanstarter, guessedletters, algeraden, memberroles, rules, disabledrules, latestroled

	if message.author == client.user: # is the message sent by the bot
		return # do nothing

	specialchannel = getspecialchannel_reply(message)
	displaymessagecontent = ('``{}``**`…`**'.format(wrapbackticks(message.content[:100]))) if len(message.content) > 100 else '``{}``'.format(wrapbackticks(message.content)).replace('\n', '``**`\\n`**``​')
	if displaymessagecontent[-12:] == '``**`\\n`**``​':
		displaymessagecontent += '``'
	isprivate = isprivatemessage(message.server) # cant use isprivatemessage = isprivatemessage(), otherwise python will think "holy fuck a variable was referenced before assignment"

	try:
		if not isprivate and str(message.author.status) == 'offline' and not logdisabled('invisible_sentmessage', message.server):
			embed = discord.Embed(title='👻INVISIBLE WHILE SENDING MESSAGE IN {}'.format(message.channel.mention), description=message.content, colour=message.author.colour)
			embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url, url=infourl('userid={}&messageid={}'.format(message.author.id, message.id)))
			await client.send_message(specialchannel, embed=embed)
	except AttributeError:
		return

	if not isprivate and message.tts:
		embed = discord.Embed(title='🎙Message {} was sent with TTS in {}'.format(message.id, message.channel.mention), description=message.content, colour=message.author.colour, timestamp=message.timestamp)
		embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
		embed.add_field(name='Message author', value='<@!{id}> ({id})'.format(id=message.author.id))
		await client.send_message(specialchannel, embed=embed)

	if message.attachments != []:
		actuallyretrieving = await fetch(message.attachments[0]['url'])
		with open(attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename'], 'wb') as f:
			f.write(actuallyretrieving)
			f.close()

	if message.embeds != []:
		for n, e in enumerate(message.embeds):
			if e['type'] == 'image':
				# get the filename from the url
				# i.e. the part after the last forward slash
				fn = e['url'].split('/')[-1]

				# fetch the embed preview discord fetches
				img = await fetch(e['thumbnail']['proxy_url'])

				# cache the image
				with open('{embedcache}/{m.id}_{n}_{fn}'.format(embedcache=embedcache, m=message, n=n, fn=fn), 'wb') as f:
					f.write(img)
					f.close()

	if not isprivate and message.author.id in config.get_s('blacklist', message.server.id):
		return

	if isprivate and message.author.id in config.get_s('blacklist'):
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
			msg_start = '**`>`**``{}``**`#`**{}\n'.format(wrapbackticks(message.author.name), displaymessagecontent)
		else:
			msg_start = '**`>`**``{}``**`$`**{}\n'.format(wrapbackticks(message.author.name), displaymessagecontent)
		if isprivate:
			embed = emb.error('Guesses are not accepted via PM.')
			await client.send_message(message.channel, msg_start, embed=embed)
		if message.channel.id != '201130047736643584':
			return
		hangmanguessed = message.content[1:]

		if len(hangmanguessed) == 1:
			# Have we already used that letter? And is it a valid letter?
			if alphabet.find(hangmanguessed.upper()) == -1:
				embed = emb.error('The character ``{}`` is invalid.'.format(wrapbackticks(hangmanguessed.upper())))
				await client.send_message(message.channel, msg_start, embed=embed)
				return
			if guessedletters[alphabet.find(hangmanguessed.upper())]:
				embed = emb.error('The letter **{}** has already been used.'.format(hangmanguessed.upper()))
				await client.send_message(message.channel, msg_start, embed=embed)
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
					embed = emb.error('You should probably enter in a letter.')
					await client.send_message(message.channel, msg_start, embed=embed)
					return
				embed = emb.error('**``{}``** isn’t even the same length as the correct word. Please try again.'.format(wrapbackticks(hangmanguessed)))
				await client.send_message(message.channel, msg_start, embed=embed)
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
		msg_start = '**`>`**``{}``**`{}`**{}\n'.format(wrapbackticks(message.author.name), invokesymbol, displaymessagecontent) # shows what the user put in, without main invoker
	else:
		command = message.content.split(invoker, 1)[1] # removes invoker from the message
		msg_start = '**`>`**``{}``**`{}`**{}\n'.format(wrapbackticks(message.author.name), invokesymbol, displaymessagecontent) # shows what the user put in

	try:
		arguments = command.split(' ', 1)[1]
	except IndexError:
		arguments = None
	command = command.split(' ', 1)[0]
	# Prevent access to those who aren't supposed to send messages
	if not isprivate and not is_mod(message.author) and message.channel.id != '201130047736643584' and message.server.id == productionserver and \
	not (is_dev(message.author) and message.channel.id == '238423391571279872') and \
	not command in ['rule','rules','rulefind','rulesfind'] and \
	not (message.channel.id == '256924583737819146' and command in ['votevoicemute', 'vy', 'vn']):
		if is_valid_command(command):
			await client.add_reaction(message, discord.utils.get(message.server.emojis, id='262051482549878796'))
		return
	if not isprivate and command in config.get_s('disabledcommands', message.server.id):
		embed = emb.error('This command is currently disabled{}.'.format(' on this server' if config.is_detached('disabledcommands', message.server.id) else ''))
		await reply(message, emb=embed)
		return

	if isprivate and command in config.get_s('disabledcommands'):
		embed = emb_error('This command is currently disabled.')
		await reply(message, emb=embed)

	if command == 'help':
		content = (
			'`[\]` is a bot written by Info Teddy and Dav999 in Python utilizing `discord.py`, for use on the tOLP Discord server.\n'
			'To get accepted into the developer team, you have to be accepted by eighty-percent of the current members of the team.\n'
			'Special thanks to Shiny for making the current icon for the bot.\n'
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
			embed = emb.error(t['op_only'])
			logfailedcommand(message, content)
			await reply(message, emb=embed)
			return
		embed = emb.success('Restarting.', True)
		embed.add_field(name='Uptime', value=reltime(boottimeunix, True))
		embed.add_field(name='Messages in Cache', value=str(len(client.messages)))
		logcommand(command, arguments, message)
		await reply(message, emb=embed)
		await os.execl(__file__, '')
	elif command == 'kill':
		if not is_operator(message.author):
			embed = emb.error(t['op_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		embed = emb.success('Killing.', True)
		embed.add_field(name='Uptime', value=reltime(boottimeunix, True))
		logcommand(command, arguments, message)
		await reply(message, emb=embed)
		await client.logout()
		sys.exit(1)
	elif command == 'config':
		if not is_operator(message.author):
			embed = emb.error(t['op_only'])
			logfailedcommand(message, content)
			await reply(message, emb=embed)
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
			logcommand(command, arguments, message)
			embed = emb.success('Reloaded config.')
			await reply(message, emb=embed)
			return
		elif arguments == 'list':
			content = '```css'
			for c in config.s:
				if not config.get_shown(c):
					continue
				try:
					content += '\n{} [{}] = {}'.format(c, config.get_type(c) + ('*' if config.is_array(c) else ''), config.get_s(c, message.server.id) if not config.is_array(c) else '[{}]'.format(len(config.get_s(c, message.server.id))))
					if config.is_detached(c, message.server.id):
						content += ' [local value]'
				except AttributeError:
					content += '\n{} [{}] = {}'.format(c, config.get_type(c) + ('*' if config.is_array(c) else ''), config.get_s(c) if not config.is_array(c) else '[{}]'.format(len(config.get_s(c))))
			content += '\n```'
			await reply(message, content)
			return

		splitargs = arguments.split(' ', 2)

		if splitargs[0] == 'set':
			if not config.exists(splitargs[1]):
				embed = emb.error('That setting does not exist')
				await reply(message, emb=embed)
				return
			if config.is_array(splitargs[1]):
				embed = emb.error('That doesn’t work for an array')
				await reply(message, emb=embed)
				return
			if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
				embed = emb.error('Integer expected')
				await reply(message, emb=embed)
				return
			try:
				config.set_s(splitargs[1], splitargs[2], message.server.id)
			except AttributeError:
				config.set_s(splitargs[1], splitargs[2])
			config.saveconfig()
			logcommand(command, arguments, message)
			embed = emb.success('Set `{}` to `{}`'.format(splitargs[1], wrapbackticks(splitargs[2])))
			await reply(message, emb=embed)
		elif splitargs[0] == 'get':
			if not config.exists(splitargs[1]):
				embed = emb.error('That setting does not exist')
				await reply(message, emb=embed)
				return
			try:
				content = 'Key: `{}`   Type: `{}`   Array: `{}`   Detachable: `{}`   Using: `{}`\n'.format(splitargs[1], config.get_type(splitargs[1]), config.is_array(splitargs[1]), config.is_detachable(splitargs[1]), ('Local value' if config.is_detached(splitargs[1], message.server.id) else 'Master value'))
			except AttributeError:
				content = 'Key: `{}`   Type: `{}`   Array: `{}`   Detachable: `{}`   Using: `{}`\n'.format(splitargs[1], config.get_type(splitargs[1]), config.is_array(splitargs[1]), config.is_detachable(splitargs[1]), 'Master value')
			if config.get_expl(splitargs[1]) != None:
				content += 'Explanation: {}\n'.format(config.get_expl(splitargs[1]))
			content += 'Value:'

			if config.is_array(splitargs[1]):
				try:
					for val in config.get_s(splitargs[1], message.server.id):
						content += ' `{}`,'.format(val)
				except AttributeError:
					for val in config.get_s(splitargs[1]):
						content += ' `{}`,'.format(val)
			else:
				try:
					content += ' `{}`\nDefault: `{}`'.format(config.get_s(splitargs[1], message.server.id), config.get_default(splitargs[1]))
				except AttributeError:
					content += ' `{}`\nDefault: `{}`'.format(config.get_s(splitargs[1]), config.get_default(splitargs[1]))
			await reply(message, content)
		elif splitargs[0] == 'insert' or splitargs[0] == 'remove':
			if not config.exists(splitargs[1]):
				embed = emb.error('That setting does not exist')
				await reply(message, emb=embed)
				return
			if not config.is_array(splitargs[1]):
				embed = emb.error('That doesn’t work for something that is not an array')
				await reply(message, emb=embed)
				return
			if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
				embed = emb.error('Integer expected')
				await reply(message, emb=embed)
				return
			if splitargs[0] == 'insert':
				try:
					config.insert_s(splitargs[1], splitargs[2], message.server.id)
				except AttributeError:
					config.insert_s(splitargs[1], splitargs[2])
				embed = emb.success('Inserted `{}` into array `{}`'.format(wrapbackticks(splitargs[2]), splitargs[1]))
			else:
				try:
					config.remove_s(splitargs[1], splitargs[2], message.server.id)
				except AttributeError:
					config.remove_s(splitargs[1], splitargs[2])
				embed = emb.success('Removed `{}` from array `{}`'.format(wrapbackticks(splitargs[2]), splitargs[1]))
			config.saveconfig()
			logcommand(command, arguments, message)
			await reply(message, emb=embed)
		elif splitargs[0] == 'detach' or splitargs[0] == 'reattach':
			if not config.exists(splitargs[1]):
				embed = emb.error('That setting does not exist')
				await reply(message, emb=embed)
				return
			if not config.is_detachable(splitargs[1]):
				embed = emb.error('That setting cannot have an independent local value.')
				await reply(message, emb=embed)
				return
			if splitargs[0] == 'detach':
				try:
					config.detach(splitargs[1], message.server.id)
					embed = emb.success('Setting `{}` now uses a local value for this server.'.format(splitargs[1]))
				except AttributeError:
					embed = emb.error('Can’t detach values for non-servers.')
			else:
				try:
					config.reattach(splitargs[1], message.server.id)
					embed = emb.success('Setting `{}` is now using the master value again on this server.'.format(splitargs[1]))
				except AttributeError:
					embed = emb.error('Can’t reattach values for non-servers.')
			config.saveconfig()
			logcommand(command, arguments, message)
			await reply(message, emb=embed)
		elif splitargs[0] == 'default':
			if not config.exists(splitargs[1]):
				embed = emb.error('That setting does not exist')
				await reply(message, emb=embed)
				return
			try:
				config.restore_default(splitargs[1], message.server.id)
			except AttributeError:
				config.restore_default(splitargs[1])
			config.saveconfig()
			logcommand(command, arguments, message)
			embed = emb.success('Set `{}` back to default value of `{}`'.format(splitargs[1], wrapbackticks(config.get_default(splitargs[1]))))
			await reply(message, emb=embed)
		else:
			embed = emb.error('`{}` was not recognized'.format(splitargs[0]))
			await reply(message, emb=embed)
	elif command == 'echo':
		if arguments == None:
			arguments = ''
		displayarguments = arguments.replace('@', '@​')[:2000-len(msg_start)]
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
			embed = emb.error('Hangman is already running. It can be aborted by the starter or by a mod with `\stophangman`.')
			await reply(message, emb=embed)
			return
		if not isprivatemessage(message.server):
			embed = emb.error('For now, this can only be run via DM.')
			await reply(message, emb=embed)
			return
		if arguments == None:
			embed = emb.error('Please specify a word.')
			await reply(message, emb=embed)
			return
		if not arguments.isalpha():
			embed = emb.error('Words can only consist of letters A-Z')
			await reply(message, emb=embed)
			return
		if len(arguments) > 50:
			embed = emb.error('Sorry, but your word is too long. It can be 50 characters max.')
			await reply(message, emb=embed)
			return

		hangmanchosenword = arguments
		hangmanattempts = 10
		hangmantotalattempts = 10
		hangmanactive = True
		hangmanstarter = message.author
		guessedletters = [False]*26
		msg_start = '**`>`**``{}``**`{}`**``\{} {}``\n'.format(wrapbackticks(message.author.name), invokesymbol, wrapbackticks(command.split(' ')[0]), '*'*len(hangmanchosenword)) # you will never have mod/admin perms in private messages (probably), where the hangman will be started from, so for now theres no mod/admin check to make the input display different
		content = 'New game of hangman initiated by <@{}> with a custom word. Guess letters by chatting "{}" followed by the letter (for example {}a) or the word. {} attempts left.\n{}'.format(hangmanstarter.id, hangmaninvoker, hangmaninvoker, hangmanattempts, hangmanworddisp(hangmanchosenword))
		msg = msg_start + content
		await client.send_message(botschannel, msg)

		content = 'https://discord.gg/gj6YmtV'
		await reply(message, content)
	elif command == 'stophangman':
		if not hangmanactive:
			embed = emb.error('Can’t abort hangman because it’s not running.')
			await reply(message, emb=embed)
			return
		elif not is_mod(message.author) and message.author.id != hangmanstarter.id:
			embed = emb.error('Can’t abort hangman because you haven’t started this game.')
			await reply(message, emb=embed)
			return

		hangmanactive = False
		content = 'Game of hangman aborted. The word was: **{}**'.format(hangmanchosenword)
		await client.send_message(botschannel, content)
	elif command == 'source':
		content = 'Source code to the bot: __https://gitgud.io/infoteddy/bracketed_backslash__'
		await reply(message, content)
	elif command == 'findu' or command == 'findup':
		if arguments == None:
			targetmember = message.author
		else:
			targetmember = get_member_input(message.server, arguments)
		if targetmember == None:
			embed = emb.error('Unable to find that member. ' + t['specify_user'])
			await reply(message, emb=embed)
			return
		if command == "findup":
			displaymatch = '<@{}>'.format(targetmember.id)
		else:
			displaymatch = '__@{}__'.format(mdspecialchars(targetmember.display_name))
		if targetmember.game == None:
			memberhasgame = False
			displaygamestatus = 'Not Playing'
			displaygamename = 'Not Playing'
			displaygameurlstatus = 'No Stream Link'
			displaygameurl = 'No Stream Link'
			pass
		else:
			memberhasgame = True
		if memberhasgame:
			if targetmember.game.type == 0 or targetmember.game.type == None:
				displaygamestatus = 'Playing'
				displaygamename = mdspecialchars(targetmember.game.name)
			if targetmember.game.type == 1:
				displaygamestatus = 'Streaming'
				displaygamename = mdspecialchars(targetmember.game.name)
			if targetmember.game.url == None:
				displaygameurlstatus = 'No Stream Link'
				displaygameurl = 'No Stream Link'
			else:
				displaygameurlstatus = 'Stream Link'
				displaygameurl = mdspecialchars(targetmember.game.url)
		embed = discord.Embed(colour=targetmember.colour)
		embed.set_image(url=targetmember.avatar_url)
		embed.add_field(name='Nickname' if targetmember.nick != None else 'No Nickname', value=mdspecialchars(targetmember.nick) if targetmember.nick != None else 'No Nickname')
		embed.add_field(name='Username', value=mdspecialchars(targetmember.name))
		embed.add_field(name='Discriminator', value='#{}'.format(targetmember.discriminator))
		embed.add_field(name='User ID', value=targetmember.id)
		embed.add_field(name='Bot', value='Yes' if is_bot(targetmember) else 'No')
		embed.add_field(name=displaygamestatus, value=displaygamename)
		embed.add_field(name=displaygameurlstatus, value=displaygameurl)
		embed.add_field(name='Status', value='Do Not Disturb' if str(targetmember.status) == 'dnd' else str(targetmember.status).title())
		embed.add_field(name='Default Avatar', value=str(targetmember.default_avatar).title())
		embed.add_field(name='Joined Server At', value=time.strftime(config.get_s('timeformat', message.server.id), targetmember.joined_at.timetuple()))
		embed.add_field(name='Joined Discord At', value=time.strftime(config.get_s('timeformat', message.server.id), targetmember.created_at.timetuple()))
		embed.add_field(name='Color', value='_(default)_' if str(targetmember.colour) == '#000000' else str(targetmember.colour).upper())
		# IMPORTANT: in `embed.add_field()`, `name` or `value` cannot be an empty string or you will get a 400 bad request when sending it
		# (i learned that the hard way)
		# (that was about twenty restarts smh)
		content = 'Matched ' + displaymatch
		await reply(message, content, embed)
	elif command == 'softban':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
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
			latestroled = targetmember.id
		except(AttributeError,TypeError):
			embed = emb.error(t['specify_user'])
			await reply(message, emb=embed)
			return

		content = targetmember.mention
		embed = emb.success(':no_entry: <@{}> has been softbanned.'.format(targetmember.id))
		await reply(message, content, emb=embed)
	elif command == 'nononly' or command == 'nogenmen' or command == 'nocedule' or command == 'notts' or command == 'noreact':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
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
			latestroled = targetmember.id
		except(AttributeError,TypeError):
			embed = emb.error(t['specify_user'])
			await reply(message, emb=embed)
			return
		content = targetmember.mention
		embed = emb.success('Gave <@{}> the {} role.'.format(targetmember.id, rolelabel[command]))
		await reply(message, content, emb=embed)
	elif command == 'nonick':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return
		try:
			targetmember = get_member_input(message.server, arguments)
			await client.add_roles(targetmember, discord.utils.get(message.server.roles, id='236925451216355338'))
			await client.remove_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
			latestroled = targetmember.id
		except(AttributeError,TypeError):
			embed = emb.error(t['specify_user'])
			await reply(message, emb=embed)
			return
		content = targetmember.mention
		embed = emb.success('Gave <@{}> the tOLPer who can’t change nickname role, and removed the tOLPer role from them.'.format(targetmember.id))
		await reply(message, content, emb=embed)
		return
	elif command == 'voicemute' or command == 'voiceunmute':
		targetmember = get_member_input(message.server, arguments)
		content = None
		try:
			if not is_mod(message.author):
				embed = emb.error(t['mod_only'])
				logfailedcommand(command, arguments, message)
			elif targetmember.voice.voice_channel == None:
				embed = emb.error('User is not in a voice channel.')
			elif command == 'voicemute':
				await client.server_voice_state(targetmember, mute=1)
				content = targetmember.mention
				embed = emb.success('Voice muted <@{}>.'.format(targetmember.id))
			elif command == 'voiceunmute':
				await client.server_voice_state(targetmember, mute=0)
				content = targetmember.mention
				embed = emb.success('Voice unmuted <@{}>.'.format(targetmember.id))
		except AttributeError:
			embed = emb.error(t['specify_user'])
		except discord.errors.Forbidden:
			embed = emb.error(t['no_permission'])
		await reply(message, content, emb=embed)
	elif command == 'votevoicemute':
		# TODO start supporting this. When voting, require (part of) name (or id/mention/disc/you know the drill) if more than one vote is running
		if len(votemutes) >= 1:
			embed = emb.error('Multiple votes running at the same time is not yet supported.')
			await reply(message, emb=embed)
			return

		targetmember = get_member_input(message.server, arguments)
		try:
			if message.author.voice.voice_channel == None:
				embed = emb.error('You have to be in a voice channel to be able to start a vote.')
			elif targetmember.voice.voice_channel == None:
				embed = emb.error('User is not in a voice channel.')
			elif targetmember.id in votemutes:
				embed = emb.warning('There is already a vote running for this user. Type **`\\vy`** to vote yes.')
			else:
				# Count the amount of people in all the voice channels
				voicechatters = 0
				for chan in message.server.channels:
					if str(chan.type) == 'voice':
						voicechatters += len(chan.voice_members)

				if voicechatters < config.get_s('votevmute_minmembers', message.server.id):
					embed = emb.warning('There are not enough members in voice channels to start a vote.')
					await reply(message, emb=embed)
					return

				votemutes[targetmember.id] = {
					'starttime': int(time.time()),
					'proponents': [message.author.id],
					'opponents': []
				}
				content = 'A vote has been started to voice mute <@{}>.\nTo vote in favor of muting, type **`\\vy`**.\nTo vote against muting, type **`\\vn`**.\nModerators can cancel the vote by typing **`\\vc`**.'.format(targetmember.id)
				await replyattach(message, images.votebar(1/voicechatters*100, 0, config.get_s('votevmute_threshold', message.server.id)), 'temp.png', content)
				return
		except AttributeError:
			embed = emb.error(t['specify_user'])
		await reply(message, emb=embed)
	elif command == 'vy' or command == 'vn':
		if len(votemutes) == 0:
			embed = emb.error('There are currently no votes running.')
		elif len(votemutes) > 1:
			embed = emb.error('Multiple votes running at the same time is not yet supported.')
		else:
			# First, who are we going to mute, again?
			for m in votemutes:
				mutee = m
				break

			if message.author.voice.voice_channel == None:
				embed = emb.error('You’re not in any voice channel.')
				await reply(message, emb=embed)
				return

			content = 'Voted {}.'
			if command == 'vy':
				side = 'proponents'
				oppositeside = 'opponents'
				resulttext = 'in favor of muting'
			else:
				side = 'opponents'
				oppositeside = 'proponents'
				resulttext = 'against muting'

			content = content.format(resulttext)

			if message.author.id in votemutes[mutee][side]:
				embed = emb.warning('You have already voted that.')
				await reply(message, emb=embed)
				return

			votemutes[mutee][side].append(message.author.id)

			if message.author.id in votemutes[mutee][oppositeside]:
				# Changing your mind, huh?
				content = 'Changed vote to be {}.'.format(resulttext)
				votemutes[mutee][oppositeside].remove(message.author.id)

			# For the amount of people who voted, only count those who are still inside the channel!
			voicechatters = 0
			numproponents = 0
			numopponents  = 0
			for chan in message.server.channels:
				if str(chan.type) == 'voice':
					voicechatters += len(chan.voice_members)

					for voicemember in chan.voice_members:
						if voicemember.id in votemutes[mutee]['proponents']:
							numproponents += 1
						if voicemember.id in votemutes[mutee]['opponents']:
							numopponents  += 1

			percpro = numproponents/voicechatters*100
			percopp = numopponents /voicechatters*100

			if percpro >= config.get_s('votevmute_threshold', message.server.id):
				targetmember = get_member_input(message.server, mutee)
				await client.server_voice_state(targetmember, mute=1)
				content += '\n{}% of the members have now voted in favor of muting, so <@{}> is now voice muted.'.format(round(percpro,1), mutee)
				del votemutes[mutee]
			elif percopp > 100-config.get_s('votevmute_threshold', message.server.id):
				content += '\n{}% of the members have now voted against muting, so <@{}> is not getting voice muted.'.format(round(percopp,1), mutee)
				del votemutes[mutee]

			await replyattach(message, images.votebar(percpro, percopp, config.get_s('votevmute_threshold', message.server.id)), 'temp.png', content)
			return
		await reply(message, emb=embed)
	elif command == 'vc':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		if len(votemutes) == 0:
			embed = emb.error('There are currently no votes running.')
		elif len(votemutes) > 1:
			embed = emb.error('Multiple votes running at the same time is not yet supported.')
		else:
			# We're going to cancel the vote on whom?
			for m in votemutes:
				mutee = m
				break

			del votemutes[mutee]
			embed = emb.success('The vote on <@{}> has been vetoed.'.format(mutee))
		await reply(message, emb=embed)
	elif command == 'rolerst':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return

		try:
			targetmember = get_member_input(message.server, arguments)
			if not is_bot(targetmember) and not discord.utils.get(message.server.roles, id='231644869351833600') in targetmember.roles:
				await client.add_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
				embed = emb.warning('<@{}> didn’t have the tOLPer role, so I’ve added that back. To remove any restrictive roles, re-run this command.'.format(targetmember.id))
				await reply(message, emb=embed)
				return

			await removeRestrictiveRoles(targetmember, message.server)
		except(AttributeError,TypeError):
			embed = emb.error(t['specify_user'])
			await reply(message, emb=embed)
			return
		content = targetmember.mention
		embed = emb.success('Reset roles for <@{}> back to normal.'.format(targetmember.id))
		await reply(message, content, emb=embed)
	elif command == 'expires':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return
		elif arguments == None:
			embed = emb.error('Please input at least a relative time.')
			await reply(message, emb=embed)
			return

		splitargs = arguments.split(' ', 1)

		expirytime = parsereltime(splitargs[0])
		if expirytime == None:
			embed = emb.error('Invalid expiry time. Please input a relative time in the format `[#d][#h][#m][#s]`, for example: `7d12h`, `1h`, `1d`, `1d2h3m4s`, `1d20s` or whatever combination you can think of. The units have to be in the correct order, though.')
			await reply(message, emb=embed)
			return

		if len(splitargs) < 2:
			if latestroled == None:
				embed = emb.error('Nobody has gotten a restrictive role this session. Please provide any member identification instead.')
				await reply(message, emb=embed)
				return
			targetmemberid = latestroled
		else:
			targetmember = get_member_input(message.server, splitargs[1])
			targetmemberid = targetmember.id

		rolexpires[targetmemberid] = expirytime
		rolexpiresave()
		await handleExpiryTimer()

		embed = emb.success('Roles for <@{}> will be reset {}'.format(targetmemberid, reltime(expirytime)))
		await reply(message, emb=embed)
	elif command == 'expirylist':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return

		content = ''

		for memberid in rolexpires:
			content += '<@{}>: {}\n'.format(memberid, reltime(rolexpires[memberid]))

		if content == '':
			content = 'No expiry timers are currently running.'

		embed = emb.info(content)
		await reply(message, emb=embed)
	elif command == 'rolecacherst':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return
		elif arguments == None:
			embed = emb.error('Please give an ID')
			await reply(message, emb=embed)
			return
		elif get_member_input(message.server, arguments) != None:
			embed = emb.error('That member is apparently still on this server! Not removing from the cache.')
			await reply(message, emb=embed)
			return

		if removerolecache(arguments):
			embed = emb.success('Member {} successfully removed from role cache.'.format(arguments))
			await reply(message, emb=embed)
			rolecachesave()
		else:
			embed = emb.error('Member {} cannot be found in the role cache. Please note you have to enter an ID, not any form of name!'.format(arguments))
			await reply(message, emb=embed)
	elif command == 'rolecacheadd':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return
		elif arguments == None:
			embed = emb.error('Please give two IDs.')
			await reply(message, emb=embed)
			return

		splitargs = arguments.split(' ')
		if get_member_input(message.server, splitargs[0]) != None:
			embed = emb.error('That member is apparently still on this server! Not doing anything.')
			await reply(message, emb=embed)
			return

		if splitargs[1] == None:
			embed = emb.error('Please give two IDs.')
			await reply(message, emb=embed)
			return

		if splitargs[0] not in memberroles:
			embed = emb.error('Member {} cannot be found in the role cache. Please note you have to enter an ID, not any form of name!'.format(arguments))
			await reply(message, emb=embed)
			return

		memberroles[splitargs[0]].append(splitargs[1])
		rolecachesave()

		embed = emb.success('Successfully added role {} to member {} in the role cache.'.format(splitargs[1], splitargs[0]))
		await reply(message, emb=embed)
	elif command == 'rolesync':
		perms = discord.Channel.permissions_for(message.channel, message.author)
		if not perms.manage_roles:
			embed = emb.error(t['you_no_permission'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		elif message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return

		for mem in message.server.members:
			updaterolecache(mem)

		rolecachesave()

		embed = emb.success('Synced roles.')
		await reply(message, emb=embed)
	elif command == 'rolecacheinfo':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)
			await reply(message, emb=embed)
			return
		if message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return
		if not arguments in memberroles:
			embed = emb.error('That member is not in the role cache.')
			await reply(message, emb=embed)
			return

		content = 'According to the role cache, this member has the following roles: ' + listroles_id(memberroles[arguments])

		await reply(message, content)
	elif command == 'rules' or command == 'rule':
		if isprivatemessage(message.server):
			content = 'Rules:\n**1.** I am always right.\n**2.** If I am not right, rule 1 applies.'
			await reply(message, content)
			return
		if message.server.id in disabledrules and not is_mod(message.author):
			embed = emb.error('The rules system is currently disabled for this server.')
			await reply(message, emb=embed)
			return
		if not message.server.id in rules:
			embed = emb.warning('Rules are not (yet) set for this server.')
			await reply(message, emb=embed)
			return
		if arguments != None and arguments.isdigit():
			try:
				rules[message.server.id][int(arguments)-1]

				# Oh, we survived this? That means the given specific rule exists!
				content = 'Rule **{}** for server `{}`:\n{}'.format(int(arguments), wrapbackticks(message.server.name), rules[message.server.id][int(arguments)-1])
				await reply(message, content)
				return
			except IndexError:
				# But only if the rules actually don't exist
				if int(arguments) in funnynumbers:
					content = respondtorule(arguments)
					await reply(message, content)
					return
				pass
		n = 1
		content = 'Rules for server `{}`:{}'.format(wrapbackticks(message.server.name), ' (Disabled)' if message.server.id in disabledrules else '')
		for rule in rules[message.server.id]:
			content += '\n**{}.** {}'.format(n, rule)
			n += 1
		await reply(message, content)
	elif command == 'rulefind' or command == 'rulesfind':
		if isprivatemessage(message.server):
			embed = emb.error('Alright, this isn’t a server, this is our private conversation. I run on multiple servers with different rules, you know.')
			await reply(message, emb=embed)
			return
		if message.server.id in disabledrules and not is_mod(message.author):
			embed = emb.error('The rules system is currently disabled for this server.')
			await reply(message, emb=embed)
			return
		if not message.server.id in rules:
			embed = emb.warning('Rules are not (yet) set for this server.')
			await reply(message, emb=embed)
			return
		if arguments == None:
			embed = emb.error('Please enter a search term.')
			await reply(message, emb=embed)
			return
		matched = False
		n = 1
		content = 'Rules for server **``{}``** matching **``{}``**:'.format(wrapbackticks(message.server.name), wrapbackticks(arguments))
		for rule in rules[message.server.id]:
			if rule.lower().find(arguments.lower()) != -1:
				content += '\n**{}.** {}'.format(n, rule)
				matched = True
			n += 1
		if not matched:
			embed = emb.warning('No rules on server `{}` matching `{}`.'.format(wrapbackticks(message.server.name), wrapbackticks(arguments)))
			await reply(message, emb=embed)
			return
		await reply(message, content)
	elif command == 'ruleadd' or command == 'addrule':
		if not is_mod(message.author):
			# Okay, so they're not allowed to mess with the rules - but we want to respond to some particular things as well.
			splitargs = arguments.split(' ', 1)
			if splitargs[0].isdigit() and int(splitargs[0]) in funnynumbers:
				content = respondtorule(splitargs[0])
				await reply(message, content)
				return
			elif splitargs[0].isdigit() and int(splitargs[0]) > len(rules[message.server.id]):
				embed = emb.warning('Why are you mentioning the number if you want to add this as the last rule?')
				await reply(message, emb=embed)
				return

			# Ok good, they're not doing something weird or trying to be funny.
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)

			await reply(message, emb=embed)
			return
		if arguments == None:
			embed = emb.error('I’m not going to think up any rules by myself.')
			await reply(message, emb=embed)
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
		embed = emb.success(content)
		rulesave()
		await reply(message, emb=embed)
	elif command == 'ruleedit' or command == 'editrule':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)

			await reply(message, emb=embed)
			return
		if arguments == None:
			embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
			await reply(message, emb=embed)
			return
		if not message.server.id in rules:
			embed = emb.error('No rules to edit.')
			await reply(message, emb=embed)
			return

		splitargs = arguments.split(' ', 1)
		if splitargs[0].isdigit():
			try:
				rules[message.server.id][int(splitargs[0])-1]
			except IndexError:
				embed = emb.error('Rule {} does not appear to exist.'.format(int(splitargs[0])))
				await reply(message, emb=embed)
				return

			embed = emb.success('Rule {} successfully edited from:\n{}\nTo:\n{}'.format(int(splitargs[0]), rules[message.server.id][int(splitargs[0])-1], splitargs[1]))

			rules[message.server.id][int(splitargs[0])-1] = splitargs[1]
			rulesave()
		else:
			embed = emb.error('Invalid rule number given, just check the help entry.')
		await reply(message, emb=embed)
	elif command == 'rulemove' or command == 'moverule':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)

			await reply(message, emb=embed)
			return
		if arguments == None:
			embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
			await reply(message, emb=embed)
			return
		if not message.server.id in rules:
			embed = emb.error('No rules to move.')
			await reply(message, emb=embed)
			return

		splitargs = arguments.split(' ', 1)
		if splitargs[0].isdigit() and splitargs[1].isdigit():
			try:
				rules[message.server.id][int(splitargs[0])-1]
				rules[message.server.id][int(splitargs[1])-1]
			except IndexError:
				embed = emb.error('Either rule {} does not exist or {} is not a slot it can be moved to.'.format(int(splitargs[0]), int(splitargs[1])))
				await reply(message, emb=embed)
				return

			rulecontent = rules[message.server.id][int(splitargs[0])-1]
			rules[message.server.id].remove(rules[message.server.id][int(splitargs[0])-1])
			rules[message.server.id].insert(int(splitargs[1])-1, rulecontent)
			rulesave()

			embed = emb.success('Rule {} successfully moved to number {}.'.format(int(splitargs[0]), int(splitargs[1])))
		else:
			embed = emb.error('Invalid rule number(s) given, just check the help entry.')
		await reply(message, emb=embed)
	elif command == 'ruleremove' or command == 'removerule':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)

			await reply(message, emb=embed)
			return
		if arguments == None:
			embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
			await reply(message, emb=embed)
			return
		if not message.server.id in rules:
			embed = emb.error('No rules to delete.')
			await reply(message, emb=embed)
			return

		if arguments.isdigit():
			try:
				rules[message.server.id][int(arguments)-1]
			except IndexError:
				embed = emb.error('Rule {} does not appear to exist.'.format(int(arguments)))
				await reply(message, emb=embed)
				return

			embed = emb.success('Rule {} successfully removed:\n{}'.format(int(arguments), rules[message.server.id][int(arguments)-1]))

			rules[message.server.id].remove(rules[message.server.id][int(arguments)-1])
			rulesave()
		else:
			embed = emb.error('Invalid rule number given, just check the help entry.')
		await reply(message, emb=embed)
	elif command == 'rulemaint':
		if not is_mod(message.author):
			embed = emb.error(t['mod_only'])
			logfailedcommand(command, arguments, message)

			await reply(message, emb=embed)
			return
		if message.server.id in disabledrules:
			disabledrules.remove(message.server.id)
			embed = emb.success('Rules system enabled for this server.')
		else:
			disabledrules.append(message.server.id)
			embed = emb.success('Rules system disabled for this server.')
		with open('disabledrules.json', 'w') as outfile:
			json.dump(disabledrules, outfile)
		await reply(message, emb=embed)
	elif command == 'info':
		persontocheck = get_member_input(message.server, arguments)
		yesperm = '☑'
		noperm = '❎'
		try:
			perms = discord.Channel.permissions_for(message.channel, persontocheck)
		except AttributeError:
			embed = emb.error(t['specify_user'])
			await reply(message, emb=embed)
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
	elif command == 'fuckingdense':
		content = random.choice([
			'I cant believe you destroyed my recreation of something better than the original Back to VVVVVV. I wish it was never against the rules in the 1st place. It took me forever to make it, and as a consequence for releasing it, I get this. Hate. Hate! HATE! You never did that when Dimension Anomaly came out! Next time, you better not send hate stuff',
			'Stop! I have children!',
			'Well. Well well well. Welly well well well. Well well well welly well well welly. Dimension anomaly still had effort, just with 3 dimensions. VVVVVV, Open, and ZYX. You dont want me to spam again, do you? If so, then dont give hatred for a simple remodified level. FIQ made the original, I recieved permission, and I got to make it slightly better and more challenging! Why, Vultarix...? :verdigris: Why? :vitellary: WHY? :victoria: We were on our way to REAL victory... :vermillion: On our way to making up for LAST time! :vermillion: Whyd you have to SCREW IT UP? :violet: Ahahahahaha... :viridian: Is this REVENGE? :vermillion: Making me watch you act so pure and happy, while I...? :victoria: ... :victoria: No. :verdigris: NO. :vermillion: I KNOW what youre doing. :vermillion: You just wanna see what its all like. :vermillion: Before we TEAR IT AWAY from them. :vermillion: Ahahahahaha... :vermillion: Genius, Vultarix. :vermillion: Well, Ill let you mess around. :viridian: I KNOW youll come back eventually. :vermillion: And when that time comes... :vermillion: Vultarix. :viridian: Ill be waiting for you. :viridian:',
			'Well. I guess the hate I received is critical. I never wanted hatred from everyone. Every time I do this thing, THIS. I get THIS. Hatred, hatred, everywhere! And to think Dimension Anomaly wasnt good enough! Look. Look! LOOK! Its a nightmare, I tell ya!',
			'Well. Well well well. Welly well well well. Well well well welly well well welly. You never accepted the fact it took me a bunch of days to deal with this. I had to copy the ROOMS, not remove the SCRIPTS. ... And now Im done with your hatred for what I do and how I do it. Im telling FIQ about what you said about Back to VVVVVV II... Through PM.',
			'THATS IT. I KNOW WHAT I MUST DO.',
		])
		await reply(message, content)
	elif command == 'kys':
		content = 'nah'
		await reply(message, content)
	elif command == 'botok':
		embed = emb.success('Bot is okay.')
		await reply(message, emb=embed)
	elif command == 'uptime':
		hostuptime = subprocess.Popen(['uptime', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
		embed = discord.Embed(colour=col.r_success, timestamp=message.timestamp)
		embed.set_author(name='Uptime Statistics', icon_url=client.user.avatar_url)
		embed.set_thumbnail(url=client.user.avatar_url)
		embed.set_footer(text='Uptime Statistics', icon_url=client.user.avatar_url)
		embed.add_field(name='Boot Time', value=boottime)
		try:
			now = config.get_s('timeformat', message.server.id)
		except AttributeError:
			now = config.get_s('timeformat')
		embed.add_field(name='Current Time', value=time.strftime(now))
		embed.add_field(name='Bot Uptime', value=reltime(boottimeunix, True))
		embed.add_field(name='Host Uptime', value=hostuptime.decode('utf-8'))
		await reply(message, emb=embed)
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
		embed = discord.Embed(colour=col.r_success, timestamp=message.timestamp)
		embed.set_author(name='Version Information', icon_url=client.user.avatar_url)
		embed.set_thumbnail(url=client.user.avatar_url)
		embed.set_footer(text='Version Information', icon_url=client.user.avatar_url)
		embed.set_thumbnail(url=client.user.avatar_url)
		embed.add_field(name='\\[\\\\\\]', value='{}, last updated {}'.format(botversion, modificationtimecache))
		embed.add_field(name='discord.py', value='{} {}'.format(discord.version_info.releaselevel, discord.__version__))
		embed.add_field(name='Python', value=sys.version)
		embed.add_field(name='PIL', value=__import__("PIL").VERSION)
		await reply(message, emb=embed)
	elif command == 'getrawmessagecontent':
		if not is_mod(message.author):
			logfailedcommand(command, arguments, message)
			embed = emb.error(t['mod_only'])
			await reply(message, emb=embed)
			return
		try:
			argsplit = arguments.split(' ', 1)
			arg0 = argsplit[0]
			arg1 = argsplit[1]
			channelid = arg0[2:-1]
			getchannel = client.get_channel(channelid)
			getmessage = await client.get_message(getchannel, arg1)
			content = '``{}``'.format(wrapbackticks(getmessage.content[:1900]))
			await reply(message, content)
			if getmessage.embeds != []:
				content = '``{}``'.format(wrapbackticks(getmessage.embeds[:1900]))
				await reply(message, content)
			return
		except AttributeError:
			embed = emb.error('Invalid arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
		except IndexError:
			embed = emb.error('Invalid amount of arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
		except discord.errors.HTTPException:
			embed = emb.error('Invalid channel or message ID given. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
		await reply(message, emb=embed)
	elif command == 'addcontrib' or command == 'removecontrib':
		if isprivate:
			embed = emb.error(t['noprivate'])
			await reply(message, emb=embed)
			return
		if message.server.id != productionserver:
			embed = emb.error(t['production_only'])
			await reply(message, emb=embed)
			return
		contribmodrole = discord.utils.get(message.server.roles, id='249695436812713984')
		contribrole = discord.utils.get(message.server.roles, id='241728185937559552')
		targetmember = get_member_input(message.server, arguments)
		if not contribmodrole in message.author.roles:
			embed = emb.error('Permission denied. This command can only be used by a tOLP Contributor Moderator.')
			await reply(message, emb=embed)
			return
		try:
			if command == 'addcontrib':
				if contribrole in targetmember.roles:
					embed = emb.warning('The user is already a tOLP Contributor.')
					await reply(message, emb=embed)
					return
				await client.add_roles(targetmember, contribrole)
				content = targetmember.mention
				embed = emb.success('Made <@{}> a tOLP Contributor.'.format(targetmember.id))
			if command == 'removecontrib':
				if contribrole not in targetmember.roles:
					embed = emb.warning('The user is already not a tOLP Contributor.')
					await reply(message, emb=embed)
					return
				await client.remove_roles(targetmember, contribrole)
				content = targetmember.mention
				embed = emb.success('Made <@{}> not a tOLP Contributor.'.format(targetmember.id))
		except AttributeError:
			content = None
			embed = emb.error(t['specify_user'])
		await reply(message, content, emb=embed)
	elif command == 'countpins':
		if arguments == None:
			getchannel = message.channel
		else:
			channelid = arguments[2:-1]
			getchannel = client.get_channel(channelid)
		try:
			pins = await client.pins_from(getchannel)
			content = '{} currently has {} pins, {} remaining.'.format(getchannel.mention, len(pins), 50-len(pins))
			await replyattach(message, images.progressbar(len(pins)*2), 'temp.png', content)
		except AttributeError:
			embed = emb.error('The channel doesn’t exist, has been deleted, or it’s not a channel at all. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
			await reply(message, emb=embed)
	elif command == 'countallpins':
		if isprivate:
			embed = emb.error('No channels to iterate through, try `\countpins` instead')
			await reply(message, emb=embed)
			return
		content = ''
		for chan in message.server.channels:
			if str(chan.type) == 'text':
				pins = await client.pins_from(chan)
				content += '{} – {} pins, {} remaining\n'.format(chan.mention, len(pins), 50-len(pins))
		await reply(message, content)
	elif command == 'math':
		# what kind of stupid language uses elif instead of elseif or else if?
		try:
			cmdbits = arguments.split() # should split it so [0] is number, [1] is operand, [2] is second number
		except AttributeError:
			embed = emb.error('Invalid arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
			await reply(message, emb=embed)
			return
		try:
			if len(cmdbits) != 3: # the arguments should be [number], [operand], [number]
				embed = emb.error('Invalid amount of arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
				await reply(message, emb=embed)
				return
			numbers = ['', '']
			numbers[0] = float(cmdbits[0]) # number 1
			numbers[1] = float(cmdbits[2]) # number 2
			out = '' # setting extra crashes
			if cmdbits[1] == '+':
				out = numbers[0] + numbers[1]
			elif cmdbits[1] == '-':
				out = numbers[0] - numbers[1]
			elif cmdbits[1] == 'x' or cmdbits[1] == '*':
				out = numbers[0] * numbers[1]
			elif cmdbits[1] == '÷' or cmdbits[1] == '/':
				try:
					out = numbers[0] / numbers[1]
				except ZeroDivisionError:
					out = 'Undefined.'
			elif cmdbits[1] == '^':
				out = numbers[0] ** numbers[1] # decimal powers are allowed
			elif cmdbits[1] == '↑↑' or cmdbits[1] == '^^': # this one's for you, Info
				oper = numbers[0] # this one's the stored operand, and has to be an int otherwise it won't work properly
				out = numbers[0] # Why is this still here? Dunno, changed it
				for i in range(int(numbers[1])): # decimal range isn't
					out = out ** oper # iterate until tetration is finished
			else: #invalid operand, we don't care what the inputs are
				embed = emb.error('Invalid operands passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=command))
				await reply(message, emb=embed)
				return
		except OverflowError:
			embed = emb.error('Overflow error.')
			await reply(message, emb=embed)
			return
		# end
		content = '{number1} {operand} {number2} = {out}'.format(number1=cmdbits[0], operand=cmdbits[1], number2=cmdbits[2], out=out)
		embed = discord.Embed(title='Math Output', description=content, colour=col.r_success)
		await reply(message, emb=embed)
	elif command == 'gamestatus':
		if not is_operator(message.author):
			logfailedcommand(command, arguments, message)
			embed = emb.error(t['op_only'])
		else:
			await client.change_presence(game=discord.Game(name=arguments))
			embed = emb.success('Set game status to: ``{}``'.format(wrapbackticks(arguments)))
		await reply(message, emb=embed)
	elif command == 'eval' or command == 'evalawait' or command == 'evalfile' or command == 'evalawaitfile' or command == 'setvar':
		if message.author.id != ownerid:
			logfailedcommand(command, arguments, message)
			embed = emb.error(t['owner_only'])
			await reply(message, emb=embed)
			return
		else:
			try:
				if command == 'eval':
					evaluate = eval(arguments)
				elif command == 'evalawait':
					evaluate = await eval(arguments)
				elif command == 'evalfile':
					evalfile = open('eval.txt', 'r')
					evalstring = evalfile.read()
					evaluate = eval(evalstring)
					evalfile.close()
				elif command == 'evalawaitfile':
					evalfile = open('eval.txt', 'r')
					evalstring = evalfile.read()
					evaluate = await eval(evalstring)
					evalfile.close()
				elif command == 'setvar':
					splitargs = arguments.split(' ', 1)
					evaluate = setglobal(splitargs[0], splitargs[1])
				content = '```py\n{}```'.format(wrapbackticks(evaluate))
			except:
				content = '```py\n{}```'.format(wrapbackticks(traceback.format_exc()))
		try:
			await reply(message, content)
		except discord.errors.HTTPException:
			print((
				'The result of your latest evaluation command is:\n'
				'{}\n'
				'End of results.'
			).format(content))
			embed = emb.warning('Content too large to print. Printing to terminal instead.')
			await reply(message, emb=embed)
	elif command == 'kick' or command == 'serverban' or command == 'unserverban':
		targetmember = get_member_input(message.server, arguments)
		try:
			if command == 'kick':
				if not message.author.server_permissions.kick_members:
					logfailedcommand(command, arguments, message)
					embed = emb.error(t['you_no_permission'])
					await reply(message, emb=embed)
					return
				await client.kick(targetmember)
			elif command == 'serverban':
				if not message.author.server_permissions.ban_members:
					logfailedcommand(command, arguments, message)
					embed = emb.error(t['you_no_permission'])
					await reply(message, emb=embed)
					return
				await client.ban(targetmember, 0)
			elif command == 'serverunban':
				if not message.author.server_permissions.ban_members:
					logfailedcommand(command, arguments, message)
					embed = emb.error(t['you_no_permission'])
					await reply(message, emb=embed)
					return
				await client.unban(message.server, targetmember)
			content = targetmember.mention
			embed = emb.success('{}ed <@{}>.'.format(command.title() if command == 'kick' else command.title() + 'n', targetmember.id))
		except AttributeError:
			content = ''
			embed = emb.error(t['specify_user'])
		except discord.errors.Forbidden:
			content = ''
			embed = emb.error(t['no_permission'])
		await reply(message, content, emb=embed)
	else:
		if altinvokeractive:
			return # do not print error message if command is invalid
		else:
			embed = emb.warning('Invalid command. Input `\help` for a list of valid commands.')
			await reply(message, emb=embed)

@client.event
async def on_message_delete(message): # when a message gets deleted
	if isprivatemessage(message.server):
		return
	if message.author == client.user: # is the deleted message originally sent by the bot
		logging.info('bot message {} by user {}#{} ({}) in channel {} ({}) at {} utc deleted, original content is \n{}'.format(message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.channel.name, message.timestamp, message.content))
		return
	if message.content == '' and message.attachments == []:
		return
	if logdisabled('message_delete', message.server):
		return
	specialchannel = getspecialchannel_reply(message)
	embed = discord.Embed(title='🚫MESSAGE DELETED (SENT {} IN {})'.format(reltime(time.mktime(message.timestamp.timetuple())), message.channel.mention), description=message.content, colour=message.author.colour)
	embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url, url=infourl('userid={}&messageid={}'.format(message.author.id, message.id)))
	await client.send_message(specialchannel, embed=embed)
	if message.attachments != []:
		if os.path.isfile(attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename']):
			filetoattach = attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename']
			content = '_📎The attachment for message {} is attached._'.format(message.id)
			await client.send_file(destination=specialchannel, content=content, fp=filetoattach, filename=message.attachments[0]['filename'])
		else:
			content = '_The attachment for message {} was not found in the message attachments cache._'.format(message.id)
			await client.send_message(specialchannel, content)

@client.event
async def on_message_edit(before, after): # when a message gets edited
	if isprivatemessage(after.server):
		return
	specialchannel = getspecialchannel_reply(after)
	if before.pinned != after.pinned:
		if not before.pinned and after.pinned and not logdisabled('message_pin', after.server): # if the message was pinned
			embed = discord.Embed(title='📌MESSAGE PINNED (SENT {} IN {})'.format(reltime(time.mktime(after.timestamp.timetuple())), after.channel.mention), description=after.content, color=after.author.colour)
			embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url, url=infourl('userid={}&messageid={}'.format(after.author.id, after.id)))
			await client.send_message(specialchannel, embed=embed)
		if before.pinned and not after.pinned and not logdisabled('message_unpin', after.server): # if the message was unpinned
			embed = discord.Embed(title='📌MESSAGE UNPINNED (SENT {} IN {})'.format(reltime(time.mktime(after.timestamp.timetuple())), after.channel.mention), description=after.content, color=after.author.colour)
			embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url, url=infourl('userid={}&messageid={}'.format(after.author.id, after.id)))
			await client.send_message(specialchannel, embed=embed)
	# preliminary checkings
	if before.content == after.content:
		return # must be the message being pinned and/or embed(s) displaying
	if before.author == client.user or after.author == client.user: # the bot doesnt edits its own messages, so throw a warning
		logging.warn('this is the bots own message and the bot doesnt edit messages\nid of before: {}\nid of after: {}'.format(before.id, after.id))
		return
	# checks succeeded
	if not logdisabled('message_edit', after.server):
		if len(before.content) > 1024 or len(after.content) > 1024:
			embed = discord.Embed(title='📝MESSAGE EDITED (SENT {} IN {}). The older content is:'.format(reltime(time.mktime(after.timestamp.timetuple())), after.channel.mention), description=before.content, colour=after.author.colour)
			embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url, url=infourl('userid={}&messageid={}'.format(after.author.id, after.id)))
			await client.send_message(specialchannel, embed=embed)
			embed = discord.Embed(title='MESSAGE EDITED (SENT {} IN {}). The newer content is:'.format(reltime(time.mktime(after.timestamp.timetuple())), after.channel.mention), description=after.content, colour=after.author.colour)
			embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url, url=infourl('userid={}&messageid={}'.format(after.author.id, after.id)))
			await client.send_message(specialchannel, embed=embed)
		else:
			embed = discord.Embed(title='📝MESSAGE EDITED (SENT {} IN {})'.format(reltime(time.mktime(after.timestamp.timetuple())), after.channel.mention), colour=after.author.colour)
			embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url, url=infourl('userid={}&messageid={}'.format(after.author.id, after.id)))
			embed.add_field(name='Older Content', value=before.content, inline=False)
			embed.add_field(name='Newer Content', value=after.content, inline=False)
			await client.send_message(specialchannel, embed=embed)
	if not logdisabled('message_overedit', after.server): # Turning off this logging also turns off the feature
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
					try:
						await client.delete_message(after)
						embed = discord.Embed(title='📝📝📝📝📝Message {} was edited too many times in {} and has been deleted by me'.format(after.id, after.channel.mention), description=after.content, colour=after.author.colour, timestamp=datetime.datetime.now())
						embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url)
						embed.add_field(name='Message author', value='<@!{id}> ({id})'.format(id=after.author.id))
					except discord.errors.NotFound:
						embed = discord.Embed(title='📝📝📝📝📝Message {} was edited too many times in {} but they deleted it before I could'.format(after.id, after.channel.mention), description=after.content, colour=after.author.colour, timestamp=datetime.datetime.now())
						embed.set_author(name=after.author.display_name, icon_url=after.author.avatar_url)
						embed.add_field(name='Message author', value='<@!{id}> ({id})'.format(id=after.author.id))
					await client.send_message(specialchannel, embed=embed)
					# Also actually reply
					await client.send_message(after.channel, '<@!{}>. Were you going to stop editing that message?'.format(after.author.id))
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
	if before.nick != after.nick and not logdisabled('member_nickname', after.server):
		embed = discord.Embed(title='🇳📟CHANGED NICKNAME'.format(id=after.id), colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
		if before.nick == None:
			embed.add_field(name='No Older Nickname', value='_No Older Nickname_')
		else:
			embed.add_field(name='Older Nickname', value=mdspecialchars(before.nick))
		if after.nick == None:
			embed.add_field(name='No Newer Nickname', value='_No Newer Nickname_')
		else:
			embed.add_field(name='Newer Nickname', value=mdspecialchars(after.nick))
		await client.send_message(specialchannel, embed=embed)
	if before.roles != after.roles:
		# TODO: Handle it well when roles are both added and deleted!
		if len(before.roles) > len(after.roles) and not logdisabled('member_roleremove', after.server): # if a role has been removed
			rolesremoved = list(set(before.roles).symmetric_difference(set(after.roles)))
			embed = discord.Embed(title='ROLE REMOVED FROM USER'.format(id=after.id), colour=rolesremoved[0].colour)
			embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
			for roleremoved in rolesremoved:
				embed.add_field(name='Removed Role', value=mdspecialchars('{} ({})'.format(roleremoved.name, roleremoved.id)))
			await client.send_message(specialchannel, embed=embed)
		if len(before.roles) < len(after.roles) and not logdisabled('member_roleadd', after.server): # if a role has been added
			rolesadded = list(set(after.roles).symmetric_difference(set(before.roles)))
			embed = discord.Embed(title='ROLE ADDED TO USER'.format(id=after.id), colour=rolesadded[0].colour)
			# i am fucking TRIGGERED that i have to set these values twice
			embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
			for roleadded in rolesadded:
				embed.add_field(name='Added Role', value=mdspecialchars('{} ({})'.format(roleadded.name, roleadded.id)))
			await client.send_message(specialchannel, embed=embed)
		if after.server.id == productionserver:
			updaterolecache(after)
			rolecachesave()
	if before.name != after.name and not logdisabled('member_username', after.server):
		description = '🇺📟CHANGED USERNAME'.format(id=after.id)
		if before.discriminator != after.discriminator:
			description += ' AND DISCRIMINATOR 🔸'
		embed = discord.Embed(title=description, colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
		embed.add_field(name='Older Username', value=mdspecialchars(before.name))
		embed.add_field(name='Newer Username', value=mdspecialchars(after.name))
		if before.discriminator != after.discriminator:
			embed.add_field(name='Older Discriminator', value=before.discriminator, inline=False)
			embed.add_field(name='Newer Discriminator', value=after.discriminator)
		await client.send_message(specialchannel, embed=embed)
	if before.avatar_url != after.avatar_url and ((not logdisabled('member_botavatar', after.server)) if is_bot(after) else (not logdisabled('member_avatar', after.server))):
		embed = discord.Embed(description='👥<@!{id}> ({id}) changed avatar'.format(id=after.id), colour=after.colour, timestamp=datetime.datetime.now())
		embed.set_author(name=after.display_name, icon_url=after.avatar_url)
		embed.set_thumbnail(url=before.avatar_url)
		embed.set_image(url=after.avatar_url)
		embed.add_field(name='Older Avatar URL: None' if before.avatar_url == '' else 'Older Avatar URL (Thumbnail)', value='No Older Avatar URL' if before.avatar_url == '' else before.avatar_url)
		embed.add_field(name='Newer Avatar URL: None' if after.avatar_url == '' else 'Newer Avatar URL (Inset Image)', value='No Newer Avatar URL' if after.avatar_url == '' else after.avatar_url, inline=False)
		await client.send_message(specialchannel, embed=embed)

@client.event
async def on_member_join(member):
	specialchannel = getspecialchannel(member.server)
	embed = discord.Embed(description='➡<@!{id}> ({id}) joined server'.format(id=member.id), colour=member.server.me.colour, timestamp=datetime.datetime.now())
	embed.set_author(name=member.display_name)
	embed.set_thumbnail(url=member.avatar_url)
	await client.send_message(specialchannel, embed=embed)
	if member.server.id == productionserver:
		if is_bot(member):
			await client.add_roles(member, discord.utils.get(member.server.roles, id='201129507967598592')) # bot role
			return
		# Are they in our database of members which had roles before?
		if member.id in memberroles:
			addingtheseroles = []
			# They're found in the database! Give them the groups they should have
			for rid in memberroles[member.id]:
				addingrole = discord.utils.get(member.server.roles, id=rid)
				if addingrole.is_everyone:
					continue
				addingtheseroles.append(addingrole)
			await client.add_roles(member, *addingtheseroles)
			content = '<@!{id}> ({id}) found in the role cache\n'.format(id=member.id)
			value = '_{} role'.format(str(len(addingtheseroles)))
			value += 's:' if len(addingtheseroles) != 1 else ':'
			value += listroles(addingtheseroles) + '_'
			content += 'Given them back their roles:\n' + value
			await client.send_message(specialchannel, content)
		else:
			# Not found, so they're just a tOLPer.
			await client.add_roles(member, discord.utils.get(member.server.roles, id='231644869351833600')) # The tOLPer role

@client.event
async def on_member_remove(member):
	specialchannel = getspecialchannel(member.server)
	embed = discord.Embed(description='🚪<@!{id}> ({id}) removed from server'.format(id=member.id), colour=member.colour, timestamp=datetime.datetime.now())
	embed.set_author(name=member.display_name, icon_url=member.avatar_url)
	embed.set_thumbnail(url=member.avatar_url)
	await client.send_message(specialchannel, embed=embed)

@client.event
async def on_member_ban(member):
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(wrapbackticks(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_member_unban(server, user):
	specialchannel = getspecialchannel(server)
	msg = '**`>`**<:doormat:239361673532669953>`user` **``{}``**`#{}` `({}) unbanned from server {} ({})`'.format(wrapbackticks(user.name), user.discriminator, user.id, server.name, server.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_typing(channel, user, when):
	try:
		specialchannel = getspecialchannel(channel.server)
	except AttributeError: # this would happen if the typing event is in a private message
		return
	if specialchannel.id == channel.server.default_channel.id:
		specialchannel = channel
	if str(user.status) == 'offline' and not logdisabled('invisible_typing', channel.server):
		embed = discord.Embed(title='👻INVISIBLE WHILE TYPING IN {}'.format(channel.mention), colour=user.colour)
		embed.set_author(name=user.display_name, icon_url=user.avatar_url, url=infourl('userid={}'.format(user.id)))
		await client.send_message(specialchannel, embed=embed)
	else:
		return # practically unnecessary, but this is for if we want to do things when members type later

@client.event
async def on_server_role_create(role):
	specialchannel = getspecialchannel(role.server)
	msg = '**`>`**`role` **``{}``** `({}) was created in server` **``{}``** `({}) at {}`'.format(wrapbackticks(role.name), role.id, wrapbackticks(role.server.name), role.server.id, role.created_at)
	await client.send_message(specialchannel, msg)

@client.event
async def on_server_role_delete(role):
	specialchannel = getspecialchannel(role.server)
	msg = '**`>`**`role` **``{}``** `({}) was deleted in server` **``{}``** `({}) originally created at {}`'.format(wrapbackticks(role.name), role.id, wrapbackticks(role.server.name), role.server.id, role.created_at)
	await client.send_message(specialchannel, msg)

@client.event
async def on_server_role_update(before, after):
	specialchannel = getspecialchannel(before.server)
	if before.name != after.name: # if the name changed
		embed = discord.Embed(title='ROLE NAME CHANGE', description=mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Name', value=mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=mdspecialchars(after.name))
		await client.send_message(specialchannel, embed=embed)
	if before.hoist != after.hoist: # if "display online members separately" changed
		if before.hoist == 0 and after.hoist == 1: # if the role has been hoisted
			msg = '**`>`**`role` **``{}``** `({}) has been hoisted`'.format(wrapbackticks(after.name), after.id)
			await client.send_message(specialchannel, msg)
		if before.hoist == 1 and after.hoist == 0: # if the role has been lowered
			msg = '**`>`**`role` **``{}``** `({}) has been lowered`'.format(wrapbackticks(after.name), after.id)
			await client.send_message(specialchannel, msg)
	if before.mentionable != after.mentionable: # if "allow everyone to mention this role" changed
		if before.mentionable == 0 and after.mentionable == 1: # if the role is now mentionable
			msg = '**`>`**`role` **``{}``** `({}) is now mentionable`'.format(wrapbackticks(after.name), after.id)
			await client.send_message(specialchannel, msg)
		if before.mentionable == 1 and after.mentionable == 0: # if the role is no longer mentionable
			msg = '**`>`**`role` **``{}``** `({}) is no longer mentionable`'.format(wrapbackticks(after.name), after.id)
			await client.send_message(specialchannel, msg)
	if before.position != after.position: # if the role has been moved up or down in the hierarchy
		if before.position > after.position: # the role has been moved down
			msg = '**`>`**`role` **``{}``** `({}) has been moved down by {} roles ({} to {})`'.format(wrapbackticks(after.name), after.id, before.position - after.position, before.position, after.position)
			await client.send_message(specialchannel, msg)
		if before.position < after.position: # the role has been moved up
			msg = '**`>`**`role` **``{}``** `({}) has been moved up by {} roles ({} to {})`'.format(wrapbackticks(after.name), after.id, after.position - before.position, before.position, after.position)
			await client.send_message(specialchannel, msg)
	if before.colour != after.colour:
		embed = discord.Embed(title='ROLE COLOR CHANGE', description=mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Color', value='(default)' if before.colour.value == 0 else str(before.colour).upper())
		embed.add_field(name='Newer Color', value='(default)' if after.colour.value == 0 else str(after.colour).upper())
		await client.send_message(specialchannel, embed=embed)


@client.event
async def on_reaction_add(r, u):
	if isprivatemessage(r.message.server):
		return
	specialchannel = getspecialchannel(r.message.server)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION ADD TO MESSAGE {m.id} IN {c.mention}'.format(
			m=r.message,
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	mdetails = '**{name}**#{discrim}'.format(
		name=mdspecialchars(u.display_name),
		discrim=u.discriminator,
	)
	if user.status == discord.Status.offline:
		mdetails += ' (Invisible)'
	embed.add_field(
		name='Member of Reaction',
		value=mdetails,
	)
	embed.add_field(
		name='Reaction',
		value=(
			(emotename)
			if
			(not iscustomemote)
			else
			(
				'{name} ({id})'.format(
					name=emotename,
					id=r.id,
				)
			)
		),
	)
	await client.send_message(specialchannel, embed=embed)

@client.event
async def on_reaction_remove(r, u):
	if isprivatemessage(r.message.server):
		return
	specialchannel = getspecialchannel(r.message.server)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION REMOVE FROM MESSAGE {m.id} IN {c.mention}'.format(
			m=r.message,
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	mdetails = '**{name}**#{discrim}'.format(
		name=mdspecialchars(u.display_name),
		discrim=u.discriminator,
	)
	if user.status == discord.Status.offline:
		mdetails += ' (Invisible)'
	embed.add_field(
		name='Member of Reaction',
		value=mdetails,
	)
	embed.add_field(
		name='Reaction',
		value=(
			(emotename)
			if
			(not iscustomemote)
			else
			(
				'{name} ({id})'.format(
					name=emotename,
					id=r.id,
				)
			)
		),
	)
	await client.send_message(specialchannel, embed=embed)

@client.event
async def on_reaction_clear(m, rs):
	schan = getspecialchannel(m.server)
	rlist = ''
	for r in rs:
		try:
			name = r.emoji.name
			cemt = True
		except AttributeError:
			name = r.emoji
			cemt = False
		rlist += str(r.count) + ' '
		if cemt:
			rlist += '{name} ({id})\n'.format(
					name=emotename,
					id=r.id,
				)
		else:
			rlist += name + '\n'
	embed = discord.Embed(
		title='REACTIONS CLEAR FROM MESSAGE {m.id} IN {c.mention}'.format(
			m=m,
			c=m.channel,
		),
		description=m.content,
		colour=m.author.colour,
	)
	embed.add_field(name='Reactions', value=rlist)

@client.event
async def on_server_update(before, after):
	specialchannel = getspecialchannel(after)
	if before.icon != after.icon:
		embed = discord.Embed(description='Server changed icon')
		embed.set_thumbnail(url=before.icon_url)
		embed.add_field(name='Older Icon URL: None' if before.icon_url == '' else 'Older Icon URL (Thumbnail)', value='No Older Icon URL' if before.icon_url == '' else before.icon_url)
		embed.add_field(name='Newer Icon URL: None' if after.icon_url == '' else 'Newer Icon URL (Inset Image)', value='No Newer Icon URL' if after.icon_url == '' else after.icon_url)
		embed.set_image(url=after.icon_url)
		await client.send_message(specialchannel, embed=embed)
	if before.name != after.name:
		embed = discord.Embed(description='Server changed name')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Name', value=mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=mdspecialchars(after.name))
		await client.send_message(specialchannel, embed=embed)

@client.event
async def on_voice_state_update(before, after):
	global productionserver, voicetextchannel

	if after.server.id != productionserver:
		return

	# notcounting = [None, '160641024811728896']
	notcounting = [None]

	# Count the amount of users in voice channels... But don't count modchat. It'd make no sense to open the public voicechat text channel once two mods are talking privately.
	voicechatters = 0
	for chan in after.server.channels:
		if str(chan.type) == 'voice' and (not chan.id in notcounting):
			voicechatters += len(chan.voice_members)

	if before.voice.voice_channel in notcounting and (not after.voice.voice_channel in notcounting):
		# JOINED a voice channel. If this is the second person, open the #voicechat channel!
		if voicechatters == 2:
			overwrite = discord.PermissionOverwrite()
			overwrite.read_messages = True
			overwrite.read_message_history = False
			await client.edit_channel_permissions(voicetextchannel, after.server.default_role, overwrite)

			logembed = emb.info('Opening <#256924583737819146> because there are now 2 people in voice chat.\nThis channel accompanies the voice chat; read the channel description for more info.')
			await client.send_message(voicetextchannel, embed=logembed)

	elif (not before.voice.voice_channel in notcounting) and after.voice.voice_channel in notcounting:
		# LEFT a voice channel. If they're now alone, close the #voicechat channel again.
		if voicechatters == 1:
			overwrite = discord.PermissionOverwrite()
			overwrite.read_messages = False
			overwrite.read_message_history = False
			await client.edit_channel_permissions(voicetextchannel, after.server.default_role, overwrite)

			logembed = emb.info('Closing <#256924583737819146> because there is now only one person left in voice chat')
			await client.send_message(voicetextchannel, embed=logembed)

exec(compile(open("functions.py", "rb").read(), "functions.py", 'exec'))

client.run(token)
