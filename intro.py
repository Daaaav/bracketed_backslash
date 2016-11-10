#!/usr/bin/python3.5
# encoding=utf-8

#	[\] bot, will be used for tolp server
#	Copyright (C) 2016  Info Teddy
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

import discord
import asyncio
import os
import os.path
import sys
import urllib.request
import warnings
import random
import re
import time
import json
import logging
import math
import subprocess

# sets up logging
# level can be logging.DEBUG, logging.WARNING, et cetera
# see https://docs.python.org/3/library/logging.html for more info
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

timeformat = '%Y-%m-%d %H:%M:%S (%Z)'
boottime = time.strftime(timeformat)
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

client.max_messages = None

t = {
	'op_only': 'Permission denied. This command can only be used by Info Teddy or Dav999.',
	'mod_only': 'Permission denied. This command can only be used by a moderator or administrator.',
	'specify_user': 'Please specify a user ID, a username, a username and discriminator, or a nickname.',
	'accepts_user': 'Accepts as an argument a user ID, nickname, username, discriminator, or username and discriminator.',
	'production_only': 'Production server only!',
	'noprivate': 'This command cannot be run inside a private conversation! You can probably guess why.',
	'its_meme': 'It’s a meme command.',
}

cmds = [
	{
		'cat_name': 'General Commands',
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
		]
	},
	{
		'cat_name': 'Bot Commands',
		'commands': [
			{
				'name': 'botok',
				'short': 'Pings the bot.',
				'extra': 'If the bot is okay, the bot will respond with “Bot is okay”.'
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
		]
	},
	{
		'cat_name': 'Moderation Commands',
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
				'short': 'Gives a user the `Voice Muted` role.',
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
		]
	},
]

meme_cmds = [
	{
		'cat_name': 'Meme Commands',
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
	}
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

@client.async_event
async def on_ready():
	global memberroles

	logging.info('logged in as {} with id {}'.format(client.user.name, client.user.id))
	await client.change_presence(game=discord.Game(name='​')) # the game name is u+200b

	await client.send_message(specialchannel_prod, '**`>`**🔌`Bot connected. (startup time is {})`'.format(reltime(boottimeunix)))

	try:
		with open('members.json', 'r') as infile:
			memberroles = json.load(infile)

		# Now look what I've woken up to.
		warnings = ''

		for mem in client.get_server(productionserver).members:
			if not str(mem.id) in memberroles:
				warnings += '\nUser {}#{} ({}) is not in the cache! Adding their roles to the cache now.'.format(mem.name, mem.discriminator, mem.id)
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

@client.async_event
async def on_message(message):
	global msg_start, hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, hangmanstarter, guessedletters, algeraden, memberroles

	if message.author == client.user: # is the message sent by the bot
		return # do nothing

	specialchannel = getspecialchannel_reply(message)
	displaymessagecontent = ('``{}``**`…`**'.format(mdspecialchars(message.content[:100]))) if len(message.content) > 100 else '``{}``'.format(mdspecialchars(message.content))
	isprivate = isprivatemessage(message.server) # cant use isprivatemessage = isprivatemessage(), otherwise python will think "holy fuck a variable was referenced before assignment"

	if not isprivate and str(message.author.status) == 'offline':
		msg_start = '**`>`**👻`user` **``{}``**`#{}` `({}) was invisible when sending message {} in channel` <#{}> `at {} UTC`'.format(mdspecialchars(message.author.name), message.author.discriminator, message.author.id, message.id, message.channel.id, message.timestamp)
		await client.send_message(specialchannel, msg_start)

	if not isprivate and message.tts:
		msg_start = '**`>`**`🎙message {} by user` **``{}``**`#{}` `({}) in channel` <#{}> `was sent with TTS.`\n{}'.format(message.id, mdspecialchars(message.author.name), message.author.discriminator, message.author.id, message.channel.id, message.content)
		await client.send_message(specialchannel, msg_start[0:1998]) # Just be very certain that the message isn't too long

	if message.attachments != []:
		attachtoretrieve = urllib.request.Request(
				message.attachments[0]['url'],
				data = None,
				headers = {
					'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
				}
			)
		actuallyretrieving = urllib.request.urlopen(attachtoretrieve)
		with open(attachcache + '/' + message.attachments[0]['id'] + '_' + message.attachments[0]['filename'], 'wb') as f:
			f.write(actuallyretrieving.read())
			f.close()
		actuallyretrieving.close()

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
	if command == 'help':
		content = (
			'`[\]` is a bot written by Info Teddy and Dav999 in Python utilizing `discord.py`, for use on the tOLP Discord server.\n'
			'To get accepted into the developer team, you have to be accepted by every one of the current members of the team.'
			+ helplist(cmds)
			)

		# General
		if arguments == 'useless':
			content = '`useless` – You found a secret, congratulations. The command to get this help message will change sometimes.' + helplist(meme_cmds)
		elif arguments == None:
			pass
		else:
			matched = False
			for i in range(0,2):
				for cat in (cmds if i == 0 else meme_cmds): # Good enough replacement to union
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
				content = 'Invalid arguments passed. Input `\help` for a list of valid commands to pass as arguments.'
		await reply(message, content)
	elif command == 'restart':
		if message.author.id != '146814960574398464' and message.author.id != '159793749604433921':
			content = t['op_only']
			logging.info('bot restart tried to be called by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		content = 'Restarting. Uptime was {}.'.format(reltime(boottimeunix, True))
		logging.info('bot restart called by {}#{} (uuid {}) at {} utc'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		await reply(message, content)
		await os.execl(__file__, '')
	elif command == 'kill':
		if message.author.id != '146814960574398464' and message.author.id != '159793749604433921':
			content = t['op_only']
			logging.info('bot kill tried to be called by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			await reply(message, content)
			return
		content = 'Killing.'
		logging.info('bot kill called by {}#{} (uuid {}) at {} utc'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		await reply(message, content)
		await sys.exit()
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
			'Luigi: 10/10 would watch again```\n'
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
		if targetmember.game == None:
			memberhasgame = False
			displaygame = '**`Not Playing`**'
			displaygameurl = '**`No Stream Link`**'
			pass
		else:
			memberhasgame = True
		if memberhasgame:
			if targetmember.game.type == 0 or targetmember.game.type == None:
				displaygame = '**`Playing:`** ``{}``'.format(mdspecialchars(targetmember.game.name))
			if targetmember.game.type == 1:
				displaygame = '**`Streaming:`** ``{}``'.format(mdspecialchars(targetmember.game.name))
			if targetmember.game.url == None:
				displaygameurl = '**`No Stream Link`**'
			else:
				displaygameurl = '**`Stream Link:`** ``{}``'.format(mdspecialchars(targetmember.game.url))

		if command == "findup":
			displaymatch = '<@{}>'.format(targetmember.id)
		else:
			displaymatch = '__@{}__'.format(targetmember.display_name)
		if str(targetmember.status) == 'online':
			statuss = 'online:232230526331650058'
		elif str(targetmember.status) == 'offline' or str(targetmember.status) == 'invisible':
			statuss = 'invisible:232230525711024129'
		elif str(targetmember.status) == 'idle':
			statuss = 'idle:232230526067408896'
		elif str(targetmember.status) == 'dnd' or str(targetmember.status) == 'do_not_disturb':
			statuss = 'dnd:232230526109351938'

		content = (
			'Matched {} <:{}>\n'
			'**`User ID:`** `{}`\n'
			'{}\n'
			'**`Username:`** ``{}``\n'
			'**`Discriminator:`** `#{}`\n'
			'{}\n'
			'{}\n'
			'**`Default Avatar:`** `{}`\n'
			'**`Avatar URL:`** {}\n'
		).format(
			displaymatch, statuss,
			targetmember.id,
			displaynick,
			mdspecialchars(targetmember.name),
			targetmember.discriminator,
			displaygame,
			displaygameurl,
			targetmember.default_avatar,
			targetmember.avatar_url,
		)
		await reply(message, content)
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
				discord.utils.get(message.server.roles, id='241612664143347712'), # voice mute
			)
			await client.add_roles(targetmember, discord.utils.get(message.server.roles, id='220643748508467220')) # The banned role
		except(AttributeError,TypeError):
			content = t['specify_user']
			await reply(message, content)
			return

		content = ':no_entry: <@{}> has been softbanned.'.format(targetmember.id)
		await reply(message, content)
	elif command == 'nononly' or command == 'nogenmen' or command == 'nocedule' or command == 'notts' or command == 'noreact' or command == 'voicemute':
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
			'voicemute': '241612664143347712',
		}
		rolelabel = {
			'nononly': 'Nonsense-Only',
			'nogenmen': 'No General Mentions',
			'nocedule': 'No Custom Emotes/Direct Uploads/Link Embeds',
			'notts': 'No TTS',
			'noreact': 'No Reactions',
			'voicemute': 'Voice Muted',
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
				discord.utils.get(message.server.roles, id='241612664143347712'), # voice muted
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
			time.strftime(timeformat),
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
	else:
		if altinvokeractive:
			return # do not print error message if command is invalid
		else:
			content = 'Invalid command. Input `\help` for a list of valid commands.'
			await reply(message, content)

@client.async_event
async def on_message_delete(message): # when a message gets deleted
	if message.author == client.user: # is the deleted message originally sent by the bot
		print('bot message {} by user {}#{} ({}) in channel {} ({}) at {} utc deleted, original content is \n{}'.format(message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.channel.name, message.timestamp, message.content))
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

@client.async_event
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

@client.async_event
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
			msg_start = '**`>`**`user` **``{}``**`#{}` `({}) has role {} ({}) removed`'.format(mdspecialchars(before.name), before.discriminator, before.id, roleremoved.name, roleremoved.id)
			await client.send_message(specialchannel, msg_start)
		if len(before.roles) < len(after.roles): # if a role has been added
			roleadded = list(set(after.roles).symmetric_difference(set(before.roles)))[0]
			msg_start = '**`>`**`user` **``{}``**`#{}` `({}) has role {} ({}) added`'.format(after.name, after.discriminator, after.id, roleadded.name, roleadded.id)
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

@client.async_event
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
			await client.send_message(specialchannel, '{}#{} ({}) is in the roles database! Given them back the roles they had.'.format(member.name, member.discriminator, member.id)) # TODO make it show the roles that were added
		else:
			# Not found, so they're just a tOLPer.
			await client.add_roles(member, discord.utils.get(member.server.roles, id='231644869351833600')) # The tOLPer role
	else:
		print('{} joined a server that is NOT the production server!'.format(member.name))

@client.async_event
async def on_member_remove(member):
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**🚪`user` **``{}``**`#{}` `({}) removed from server {} ({})`'.format(mdspecialchars(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)

@client.async_event
async def on_member_ban(member):
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(mdspecialchars(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)

@client.async_event
async def on_member_unban(server, user):
	specialchannel = getspecialchannel(server)
	msg = '**`>`**<:doormat:239361673532669953>`user` **``{}``**`#{}` `({}) unbanned from server {} ({})`'.format(mdspecialchars(user.name), user.discriminator, user.id, server.name, server.id)
	await client.send_message(specialchannel, msg)

@client.async_event
async def on_typing(channel, user, when):
	specialchannel = getspecialchannel(channel.server)
	if specialchannel.id == channel.server.default_channel.id:
		specialchannel = channel
	if str(user.status) == 'offline':
		msg = '**`>`**👻`user` **``{}``**`#{}` `({}) was invisible while typing in channel` <#{}> `at {}`'.format(mdspecialchars(user.name), user.discriminator, user.id, channel.id, when)
		await client.send_message(specialchannel, msg)
	else:
		return # practically unnecessary, but this is for if we want to do things when members type later

@client.async_event
async def on_server_role_create(role):
	specialchannel = getspecialchannel(role.server)
	msg = '**`>`**`role` **``{}``** `({}) was created in server` **``{}``** `({}) at {}`'.format(mdspecialchars(role.name), role.id, mdspecialchars(role.server.name), role.server.id, role.created_at)
	await client.send_message(specialchannel, msg)

@client.async_event
async def on_server_role_delete(role):
	specialchannel = getspecialchannel(role.server)
	msg = '**`>`**`role` **``{}``** `({}) was deleted in server` **``{}``** `({}) originally created at {}`'.format(mdspecialchars(role.name), role.id, mdspecialchars(role.server.name), role.server.id, role.created_at)
	await client.send_message(specialchannel, msg)

@client.async_event
async def on_reaction_add(reaction, user):
	specialchannel = getspecialchannel(reaction.message.server)
	try:
		iscustomemote = True
		emotename = reaction.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = reaction.emoji
	msg = '**`>`**`user` **``{}``**`#{}` `({}) added reaction` {} `{} to message {}`'.format(mdspecialchars(user.name), user.discriminator, user.id, emotename if not iscustomemote else '**`{}`**'.format(emotename), '({})'.format(reaction.emoji.id) if iscustomemote else '', reaction.message.id)
	await client.send_message(specialchannel, msg)

@client.async_event
async def on_reaction_remove(reaction, user):
	specialchannel = getspecialchannel(reaction.message.server)
	try:
		iscustomemote = True
		emotename = reaction.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = reaction.emoji
	msg = '**`>`**`user` **``{}``**`#{}` `({}) removed reaction` {} `{} from message {}`'.format(mdspecialchars(user.name), user.discriminator, user.id, emotename if not iscustomemote else '**`{}`**'.format(emotename), '({})'.format(reaction.emoji.id) if iscustomemote else '', reaction.message.id)
	await client.send_message(specialchannel, msg)

def is_admin(member):
	try:
		perms = member.server_permissions
	except AttributeError:
		return False
	if perms.administrator:
		return True
	return False

def is_mod(member):
	# Same here. No need to use is_admin and is_mod in the same conditional.
	try:
		perms = member.server_permissions
	except AttributeError:
		return False
	if perms.manage_messages:
		return True
	return is_admin(member) # Admins have moderator powers, too

def is_bot(member):
	# Alright then.
	if member.bot:
		return True
	return False

def is_dev(member):
	# Alright then. [2]
	for role in member.roles:
		if role.id == '238424544379928576': # [\] dev role
			return True
	return False

def get_member_input(server, input):
	"""Tries to return a member object given a user input which could be anything that identifies that member.

	The following priority is used:
	1) Mention: <@1234567890> or <@!1234567890>
	2) ID: 1234567890
	3) Username/Userame+discriminator/Nickname, whatever server.get_member_named() accepts
	4) Case-insensitive nickname 100% match
	5) Case-insensitive username 100% match
	6) Case-insensitive nickname partial match
	7) Case-insensitive username partial match
	8) Discriminator only (either with or without #)

	"""
	# Is there a Discord server in between us?
	if isprivatemessage(server):
		return None

	# Is this anything at all?
	if input == None:
		return None  # right back at ya

	# Is this a mention?
	if input.startswith('<@!') and input.endswith('>'):
		input = input[3:-1] # Extract the ID from it
	elif input.startswith('<@') and input.endswith('>'):
		input = input[2:-1] # Same

	targetmember = server.get_member(input)

	if targetmember == None:  # Not an ID
		targetmember = server.get_member_named(input)
		if targetmember == None:  # Not found by server.get_member_named()
			# Everything else fails? Then try searching. Nicknames have priority, then usernames.
			# Maybe we're entering just a discriminator, match those as well.
			nickmatched = False
			usermatched = None
			nickfound = None
			userfound = None
			discmatched = None
			for mem in server.members:
				if mem.nick != None and mem.nick.lower() == input.lower():
					targetmember = mem
					nickmatched = True
					break
				if mem.name.lower() == input.lower():
					usermatched = mem
				if mem.nick != None and mem.nick.lower().find(input.lower()) != -1:
					nickfound = mem
				if mem.name.lower().find(input.lower()) != -1:
					userfound = mem
				if mem.discriminator == input:
					discmatched = mem
				if input.startswith('#') and mem.discriminator == input[1:]:
					discmatched = mem

			if not nickmatched:  # No 100% nickname match
				targetmember = usermatched
				if targetmember == None:  # No 100% username match
					targetmember = nickfound
					if targetmember == None:  # No partial nickname match
						targetmember = userfound
						if targetmember == None:  # No partial username match
							targetmember = discmatched  # Last chance - just the discriminator

	return targetmember

@client.async_event
async def reply(messageobject, message):
	# Removes the need for adding msg_start manually every time
	await client.send_message(messageobject.channel, msg_start + message)

def mdspecialchars(string):
	return string.replace('`', u'​`​')

def isprivatemessage(server): # this is a function because so in the future more checks for if its a private message can ezily be added
	if server == None:
		return True
	else:
		return False

def helplist(cats):
	returnage = ''
	for cat in cats:
		returnage += '\n__`{}:`__'.format(cat['cat_name'])
		for cmd in cat['commands']:
			returnage += '\n`\{}` – {}'.format(cmd['name'], cmd['short'])
	return returnage

def hangmanworddisp(theword):
	global hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, hangmanstarter, guessedletters, algeraden

	theoutput = ''
	algeraden = True

	for i in range(0, len(theword)):
		if guessedletters[alphabet.find(theword[i].upper())]:
			theoutput += '__**`{}`**__ '.format(theword[i])
		else:
			theoutput += '`_` '
			algeraden = False

	# Now display already guessed letters.
	theoutput += '    (used: '

	notnone = False

	for i in range(0, 26):
		if guessedletters[i]:
			notnone = True
			theoutput += alphabet[i]

	if not notnone:
		theoutput += 'none'

	theoutput += ')'

	return theoutput

def rolelist(roles):
	rlist = []
	for role in roles:
		rlist.append(role.id)

	return rlist

def updaterolecache(member):
	global memberroles
	memberroles[str(member.id)] = list(rolelist(member.roles))

def removerolecache(memberid):
	global memberroles
	try:
		del memberroles[memberid]
	except KeyError:
		return False

	return True

def rolecachesave():
	global memberroles

	with open('members.json', 'w') as outfile:
		json.dump(memberroles, outfile)

def listroles(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '{} ({})'.format(role.name, role.id)
	return returnage

def listroles_id(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '{} ({})'.format(discord.utils.get(client.get_server('158091122747506688').roles, id=role), role)
	return returnage

def getspecialchannel(server):
	if server.id == '153368829160849408':
		return specialchannel_prod
	elif server.id == '158091122747506688':
		return specialchannel_aperture
	else:
		return server.default_channel

def getspecialchannel_reply(message):
	specialchannel = getspecialchannel(message.server)
	if specialchannel == message.server.default_channel:
		return message.channel
	return specialchannel

def reltime(timestamp, noago=False):
	timestamp = int(timestamp)
	now = int(time.time())
	sdt = now - timestamp
	dt = math.fabs(sdt)

	if dt == 0:
		return 'now'
	elif dt < 60:
		solong = '{}s'.format(int(dt))
	elif dt < 60*60:
		dm = math.floor(dt/60)
		ds = dt-dm*60
		solong = '{}m{}s'.format(dm, int(ds))
	elif dt < 24*60*60:
		dh = math.floor(dt/3600)
		dm = math.floor((dt-dh*3600)/60)
		#ds = dt-dh*3600-dm*60
		solong = '{}h{}m'.format(dh, dm)
	else:
		dd = math.floor(dt/86400)
		dh = math.floor((dt-dd*86400)/3600)
		solong = '{}d{}h'.format(dd, dh)

	if sdt >= 0:
		if noago:
			return solong
		return '{} ago'.format(solong)
	return '{} in the future'.format(solong)

client.run(token)
