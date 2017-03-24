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
import utils
import op_ids

op_ids.load()
config.load()

# set bot version
botversion = '1.0'

# sets up logging
# level can be logging.DEBUG, logging.WARNING, et cetera
# see https://docs.python.org/3/library/logging.html for more info.
logging.basicConfig(level=logging.INFO)

client = discord.Client(max_messages=999999999) # defines all client.* commands

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

opserverid_config = open('opserverid.conf', 'r')
opserverid = opserverid_config.readline(18).split('\n')[0]
opserverid_config.close()

memberroles = {} # Now no longer userid -> roleids, but serverid -> userids -> roleids
minutemessageedits = {}

messages_deleted_by_bot = []
deleted_messages = []

owncache = [] # Holds IDs because that's the only thing that's needed here, saves a lot of memory
              # and has better performance, because the cache can get yuge

rules = {}
disabledrules = []

votemutes = {} # userid -> dict with `starttime`, `proponents`*, `opponents`*

rolexpires = {} # Now no longer userid -> unixtime, but serverid -> userids -> dict with 'time'
latestroled = None  # ID of the latest person that has been given a restrictive role
exptimer = None  # threading.Timer object

def loadstrings():
	stringsf = open('strings.json', 'r')
	stringsfr = stringsf.read()
	strings = json.loads(stringsfr)
	# TODO: noone better not put this on a cs grad thread
	global t
	global cmds
	global permissionlabels
	global funnynumbers
	global help_info_string
	t = strings['t']
	cmds = strings['cmds']
	permissionlabels = strings['permissionlabels']
	funnynumbers = strings['funnynumbers']
	help_info_string = strings['help_info_string']

loadstrings()

modificationtimes = [
	os.path.getmtime('main.py'),
	os.path.getmtime('functions.py'),
	os.path.getmtime('commands.py'),
	os.path.getmtime('config.py'),
	os.path.getmtime('emb.py'),
	os.path.getmtime('col.py'),
	os.path.getmtime('images.py'),
	os.path.getmtime('utils.py'),
]
modificationtimecache = time.strftime(config.get_s('timeformat'), time.gmtime(max(modificationtimes)))

maineventloop = asyncio.get_event_loop()

@client.event
async def on_ready():
	global memberroles, rules, disabledrules, server, specialchannel_prod, botschannel, voicetextchannel, botschannel_tntgb, joinchannel_tntgb, banlogchannel_tntgb, productionserver, tntgbserver, rolexpires, opserver, opserver_botservers
	productionserver = '153368829160849408'
	tntgbserver = '242099933665034240'
	server = discord.utils.get(client.servers, id=productionserver) # defines all server.* commands
	server_tntgb = discord.utils.get(client.servers, id=tntgbserver)
	specialchannel_prod = discord.utils.get(server.channels, id='234185735266238464')
	botschannel = discord.utils.get(server.channels, id='201130047736643584')
	voicetextchannel = discord.utils.get(server.channels, id='256924583737819146')
	botschannel_tntgb = discord.utils.get(server_tntgb.channels, id='266626198249930764')
	joinchannel_tntgb = discord.utils.get(server_tntgb.channels, id='266591127644143618')
	banlogchannel_tntgb = discord.utils.get(server_tntgb.channels, id='242253449922609152')
	opserver = discord.utils.find(lambda s: s.id == opserverid, client.servers)
	opserver_botservers = discord.utils.find(
		lambda c: c.id == '291764490578558977',
		opserver.channels,
	)
	logging.info('logged in as {} with id {}'.format(client.user.name, client.user.id))
	await client.change_presence(game=discord.Game(name=config.get_s('gamestatus')))
	embed = discord.Embed(title='🔌BOT CONNECTED', colour=server.me.colour)
	embed.add_field(name='Startup Time', value=reltime(boottimeunix))
	await client.send_message(specialchannel_prod, embed=embed)

	try:
		with open('memberroles.json', 'r') as infile:
			memberroles = json.load(infile)

		# Now look what I've woken up to.
		for ser in memberroles:
			if config.get_s('rolecachemode', ser) == 0:
				continue
			rcwarnings = ''
			for mem in client.get_server(ser).members:
				if not str(mem.id) in memberroles[ser]:
					if len(mem.roles) >= 2:
						rcwarnings += '\nUser {}#{} ({}) is not in the cache! (They’re suddenly in the server.) Adding their roles to the cache now.'.format(mem.name, mem.discriminator, mem.id)
						memberroles[ser][str(mem.id)] = list(rolelist(mem.roles)) # Possibly redundant list() tbh, just making sure since I can't test and I don't know python well enough to know whether it's redundant
					continue
				if set(memberroles[ser][str(mem.id)]) != set(rolelist(mem.roles)):
					rcwarnings += (
						'\n'
						'User {}#{} ({}) has different roles than in the cache! Maybe you want to correct things.\n'
						'    **`Cached:`** {}\n'
						'    **`Seen:`** {}'
					).format(
						mem.name, mem.discriminator, mem.id,
						listroles_id(memberroles[ser][str(mem.id)]),
						listroles(mem.roles),
					)
			if rcwarnings != '':
				logging.warn('Role cache warnings for server {}: {}'.format(
						ser, rcwarnings
					)
				)
				rcwarnings = (
					'**User role cache warning.**\n'
					'Full warning output has been sent to the terminal.\n'
					+ rcwarnings
				)
				await client.send_message(
					getspecialchannel(
						discord.utils.get(client.servers, id=ser)
					),
					rcwarnings[:1900]
				)

	except FileNotFoundError:
		# Maybe we do have an old members.json?
		try:
			with open('members.json', 'r') as infile:
				memberrolesold = json.load(infile)
			# Convert it to the new system where all servers can use it!
			logging.info('CONVERTING OLD members.json TO memberroles.json')
			memberroles = {productionserver: memberrolesold}

			with open('memberroles.json', 'w') as outfile:
				json.dump(memberroles, outfile)

			logging.info('Exiting (aka restarting) now to make the conversion go smoothly...')
			await client.logout()
			sys.exit(43)
		except FileNotFoundError:
			logging.info('memberroles file does not exist yet so creating it now')
			memberroles = {}

			with open('memberroles.json', 'w') as outfile:
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

	for chan in client.get_all_channels():
		if chan.type == discord.ChannelType.text:
			msgs = client.logs_from(chan)
			try:
				async for m in msgs:
					client.messages.append(m)
			except discord.errors.Forbidden:
				logging.info(
					(
						'Failed to retrieve message history for'
						' {serv.name} ({serv.id})#{chan.name} ({chan.id}).'
					).format(serv=chan.server, chan=chan)
				)

	# Now set up our own cache, that Discord.py won't remove messages from before telling us!
	for m in client.messages:
		owncache.append(m.id)

commands = {}

def shadow(auth=None, aliases=None, servonly=False):
	def living_shadow(func):
		name = func.__name__
		matchargs = [r'__[0-9a-f]{4}', name, re.IGNORECASE]
		if re.match(*matchargs):
			encodings = re.findall(*matchargs)
			symbols = list(encodings)
			for count, i in enumerate(symbols):
				symbols[count] = chr(int(i[2:], 16))
			for count, i in enumerate(encodings):
				name = name.replace(encodings[count], symbols[count])
		if name.startswith('_'):
			name = name[1:]
		commands[name] = [func, auth, aliases, servonly]
	return living_shadow

@client.event
async def on_message(m):
	owncache.append(m.id)

	if m.author == client.user or m.author.bot:
		return

	global msg_start, hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, \
	hangmanstarter, guessedletters, algeraden, memberroles, rules, disabledrules, latestroled
	schan = getspecialchannel_reply(m)
	indisp = (
		(
			'``{}``**`…`**'
		).format(
			wrapbackticks(m.content[:100]).replace('discord.gg', 'discord\u200b.gg')
		)
	) if len(m.content) > 100 else (
		'``{}``'.format(wrapbackticks(m.content))
		.replace('\n', '``**`\\n`**``​')
		.replace('discord.gg', 'discord\u200b.gg')
	)
	if indisp[-12:] == '``**`\\n`**``​':
		indisp += '``'
	priv = isprivatemessage(m.server)

	if type(m.author) != discord.User and m.author.status == discord.Status.offline and \
	not logdisabled('invisible_sentmessage', m.server):
		e = discord.Embed(
			title=(
				':ghost:INVISIBLE WHILE SENDING MESSAGE IN {chanmen}'
			).format(
				chanmen=m.channel.mention
			),
			description=m.content,
			colour=m.author.colour
		)
		e.set_author(
			name=m.author.display_name,
			icon_url=m.author.avatar_url,
			url=infourl(
				'userid={0.author.id}&messageid={0.id}'
			).format(m)
		)
		await client.send_message(schan, embed=e)

	if not priv and m.tts:
		e = discord.Embed(
			title=(
				':microphone2:Message {0.id} was sent with TTS'
				' in {0.channel.mention}'
			).format(m),
			description=m.content,
			colour=m.author.colour,
			timestamp=m.timestamp
		)
		e.set_author(
			name=m.author.display_name,
			icon_url=m.author.avatar_url
		)
		e.add_field(
			name='Message author',
			value='<@!{id}> ({id})'.format(id=m.author.id)
		)
		await client.send_message(schan, embed=e)

	if not priv and m.attachments != []:
		a = await fetch(m.attachments[0]['url'])
		fn = (
			'{atchcche}/{id}_{fn}'
		).format(
			atchcche=attachcache,
			id=m.attachments[0]['id'],
			fn=m.attachments[0]['filename'],
		)
		with open(fn, 'wb') as f:
			f.write(a)
			f.close()

	if not priv and m.embeds != []:
		for n, e in enumerate(m.embeds):
			if e['type'] == 'image':
				# get the filename from the url
				# i.e. the part after the last forward slash
				fn = e['url'].split('/')[-1]

				# fetch the embed preview discord fetches
				img = await fetch(e['thumbnail']['proxy_url'])

				# cache the image
				dfn = '{embedcache}/{m.id}_{n}_{fn}'.format(
					embedcache=embedcache,
					m=m,
					n=n,
					fn=fn,
				)
				with open(dfn, 'wb') as f:
					f.write(img)
					f.close()

	if not priv and m.author.id in config.get_s('blacklist', m.server.id):
		return

	if priv and m.author.id in config.get_s('blacklist'):
		return

	if m.content.startswith(invoker):
		altinvokeractive = False
		hangmaninvokeractive = False
		pass
	elif m.content.startswith(altinvoker):
		altinvokeractive = True
		hangmaninvokeractive = False
		pass
	elif m.content.startswith(hangmaninvoker):
		hangmaninvokeractive = True
		pass
	else:
		# Not of the bot's interest, but is this in the join channel for this server?
		if not priv and \
		config.get_s('rolecachemode', m.server.id) == 2 and \
		m.channel.id == config.get_s('joinchannel', m.server.id):
			await client.delete_message(m)
			messages_deleted_by_bot.append(m)
		return

	if priv:
		invokesymbol = '@'
	elif is_mod(m.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'
	if hangmaninvokeractive:
		if not hangmanactive:
			return
		if is_mod(m.author):
			msg_start = (
				'**`>`**``{name}``**`#`**{indisp}\n'
			).format(
				name=wrapbackticks(m.author.name),
				indisp=indisp,
			)
		else:
			msg_start = (
				'**`>`**``{name}``**`$`**{indisp}\n'
			).format(
				name=wrapbackticks(m.author.name),
				indisp=indisp,
			)
		if priv:
			e = emb.error('Guesses are not accepted via PM.')
			await client.send_message(m.channel, msg_start, embed=e)
		if m.channel.id != '201130047736643584':
			return
		hangmanguessed = m.content[1:]

		if len(hangmanguessed) == 1:
			# Have we already used that letter? And is it a valid letter?
			if alphabet.find(hangmanguessed.upper()) == -1:
				e = emb.error(
					'The character ``{}`` is invalid.'
					.format(wrapbackticks(hangmanguessed.upper()))
				)
				await client.send_message(m.channel, msg_start, embed=e)
				return
			if guessedletters[alphabet.find(hangmanguessed.upper())]:
				e = emb.error(
					'The letter **{}** has already been used.'
					.format(hangmanguessed.upper())
				)
				await client.send_message(m.channel, msg_start, embed=e)
				return
			# Ok, so does this letter occur in the word?
			if hangmanchosenword.upper().find(hangmanguessed.upper()) != -1:
				# Set the guessed letter correctly
				guessedletters[alphabet.find(hangmanguessed.upper())] = True

				con = '**{ltr}** is correct!\n{worddisp}'.format(
						ltr=hangmanguessed.upper(),
						worddisp=hangmanworddisp(hangmanchosenword)
					)
				msg = msg_start + con
				await client.send_message(m.channel, msg)

				if algeraden:
					hangmanactive = False
					con = (
						'You guessed the word correctly!'
						' You made {n} mistakes in total.'
						.format(n=hangmantotalattempts-hangmanattempts)
					)
					await client.send_message(m.channel, con)
					return
			else:
				# Set the guessed letter correctly, and it has to be a letter
				guessedletters[alphabet.find(hangmanguessed.upper())] = True
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					con = (
						'**{ltr}** is incorrect! Game over.'
						' The word was: **{word}**'
					).format(
						ltr=hangmanguessed.upper(),
						word=hangmanchosenword,
					)
					msg = msg_start + con
					await client.send_message(m.channel, msg)
					return
				else:
					if hangmanattempts != 1:
						plural = 's'
					else:
						plural = ''
					con = (
						'**{ltr}** is incorrect!'
						' {attempts} attempt{pl} left.\n'
						'{worddisp}'
					).format(
						ltr=hangmanguessed.upper(),
						attempts=hangmanattempts,
						pl=plural,
						worddisp=hangmanworddisp(hangmanchosenword),
					)
					msg = msg_start + con
					await client.send_message(m.channel, msg)
					return
		else:
			# We're guessing the entire word. Well, is it the word?
			if hangmanguessed.lower() == hangmanchosenword.lower():
				hangmanactive = False
				con = (
					'You guessed the word ({word}) correctly!'
					' You made {n} mistakes in total.'
				).format(
					word=hangmanchosenword,
					n=hangmantotalattempts-hangmanattempts,
				)
				msg = msg_start + con
				await client.send_message(m.channel, msg)
				return
			elif len(hangmanguessed) != len(hangmanchosenword):
				# We're not even trying. It's not the same length.

				# if before was "not even trying", this is -1 trying
				if len(hangmanguessed) == 0:
					e = emb.error('You should probably enter in a letter.')
					await client.send_message(m.channel, msg_start, embed=e)
					return
				e = emb.error(
					(
						'**``{guess}``** isn’t even the same length'
						' as the correct word. Please try again.'
					).format(
						guess=wrapbackticks(hangmanguessed)
					)
				)
				await client.send_message(m.channel, msg_start, embed=e)
				return
			else:
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					con = (
						'**{guess}** is not the word! Game over.'
						' The word was: **{word}**'
					).format(
						guess=hangmanguessed,
						word=hangmanchosenword,
					)
					msg = msg_start + con
					await client.send_message(m.channel, msg)
					return
				else:
					con = (
						'**{guess}** is not the word!'
						' {n} attempts left.\n{worddisp}'
					).format(
						guess=hangmanguessed,
						n=hangmanattempts,
						worddisp=hangmanworddisp(hangmanchosenword),
					)
					msg = msg_start + con
					await client.send_message(m.channel, msg)
					return

		return

	elif altinvokeractive:
		command = m.content.split(altinvoker, 1)[1]
		clean_command = m.clean_content.split(altinvoker, 1)[1]
	else:
		command = m.content.split(invoker, 1)[1]
		clean_command = m.clean_content.split(invoker, 1)[1]
	msg_start = (
		'**`>`**``{name}``**`{invsym}`**{indisp}\n'
	).format(
		name=wrapbackticks(m.author.name),
		invsym=invokesymbol,
		indisp=indisp,
	)
	try:
		arguments = command.split(' ', 1)[1]
		clean_arguments = clean_command.split(' ', 1)[1]
	except IndexError:
		arguments = None
		clean_arguments = None
	command = command.split(' ', 1)[0]
	clean_command = clean_command.split(' ', 1)[0]
	# Prevent access to those who aren't supposed to send messages
	if not priv and \
	config.get_s('rolecachemode', m.server.id) == 2 and \
	m.channel.id == config.get_s('joinchannel', m.server.id):
		# Join channel
		if command == 'join' and len(m.author.roles) <= 1:
			await newmemberroles(m.author, getspecialchannel(m.server), True)
		await client.delete_message(m)
		messages_deleted_by_bot.append(m)
		return
	# But react to the message as a hint to the message sender
	if not priv and \
	not is_mod(m.author) and \
	m.channel.id != '201130047736643584' and \
	m.server.id == productionserver and \
	not (is_dev(m.author) and m.channel.id == '238423391571279872') and \
	not command in ['rule', 'rules', 'rulefind', 'rulesfind'] and \
	not (m.channel.id == '256924583737819146' and command in ['votevoicemute', 'vy', 'vn']):
		if is_valid_command(command) and command != '':
			await client.add_reaction(
				m,
				discord.utils.get(
					m.server.emojis,
					id='262051482549878796',
				),
			)
		return
	if not priv and \
	m.server.id == tntgbserver and \
	m.channel != botschannel_tntgb and \
	not is_tntgb_mod(m.author) and \
	command != 'selfban':
		return
	if not priv and command in config.get_s('disabledcommands', m.server.id):
		e = emb.error('This command is currently disabled{onthisserv}.'.format(
			onthisserv=(
				' on this server'
				if config.is_detached('disabledcommands', m.server.id) else
				'')
			)
		)
		await reply(m, emb=e)
		return

	if priv and command in config.get_s('disabledcommands'):
		e = emb.error('This command is currently disabled.')
		await reply(m, emb=e)

	if command in commands:
		func = commands[command]
	else:
		# Check if it's an alias
		for c, p in commands.items():
			if p[2] != None and command in p[2]:
				func = commands[c]
				break
		else:
			if (not priv and config.get_s('notify_invalidcmd', m.server.id)) or \
			(priv and config.get_s('notify_invalidcmd')):
				e = emb.warning(
					(
						'Invalid command. Input `\help` for'
						' a list of valid commands.'
					)
				)
				await reply(m, emb=e)
			return

	if m.channel.is_private and func[3]:
		e = emb.error(t['noprivate'])
		await reply(m, emb=e)
		return
	if func[1] != None and not func[1](m.author):
		e = emb.error(t['you_no_permission'])
		logfailedcommand(command, arguments, m)
		await reply(m, emb=e)
		return
	kwargs = {
		'command': command,
		'arguments': arguments,
		'clean_arguments': clean_arguments,
		'invokesymbol': invokesymbol,
	}
	try:
		await func[0](client, m, **kwargs)
	except Exception:
		e = emb.error(t['generic_error'])
		await reply(m, emb=e)
		raise

@client.event
async def on_message_delete(msg):
	deleted_messages.append(msg)
	if isprivatemessage(msg.server):
		return
	if msg.author == client.user:
		logging.info(
			(
				'bot message {0.id} by user {1.name}#{1.discriminator} ({1.id})'
				' in channel {2.id} ({2.name}) at {0.timestamp} utc deleted,'
				' original content is \n{0.content}'
			).format(msg, msg.author, msg.channel)
		)
		return
	if (msg.content == '' and msg.attachments == []) \
	or logdisabled('message_delete', msg.server):
		return
	schan = getspecialchannel_reply(msg)
	em = discord.Embed(
		title=(
			'\N{NO ENTRY SIGN}MESSAGE {withatch}DELETED (SENT {reltime} IN #{chan})'
		).format(
			withatch='WITH ATTACHMENT ' if msg.attachments != [] else '',
			reltime=reltime(time.mktime(msg.timestamp.timetuple())),
			chan=utils.mdspecialchars(msg.channel.name),
		),
		description=msg.content,
		colour=msg.author.colour,
	)
	em.set_author(
		name=msg.author.display_name,
		icon_url=msg.author.avatar_url,
	)
	em.set_footer(text=utils.id_summary(uid=msg.author.id, mid=msg.id, cid=msg.channel.id))
	await client.send_message(schan, embed=em)
	if msg.attachments != []:
		fp = (
				'{atchcche}/{id}_{fn}'
		).format(
			atchcche=attachcache,
			id=msg.attachments[0]['id'],
			fn=msg.attachments[0]['filename'],
		)
		if os.path.isfile(fp):
			con = (
				'_\N{PAPERCLIP}The attachment for message {0.id} is attached._'
			).format(msg)
			try:
				await client.send_file(
					destination=schan,
					content=con,
					fp=fp,
					filename=msg.attachments[0]['filename'],
				)
			except discord.HTTPException:
				con = (
					'_Failed to upload the attachment for message {0.id}._'
				).format(msg)
				await client.send_message(schan, con)
		else:
			con = (
				'_The attachment for message {0.id} was not found'
				' in the message attachments cache._'
			).format(msg)
			await client.send_message(schan, con)
	if msg in messages_deleted_by_bot:
		messages_deleted_by_bot.remove(msg)
		return
	dthreshold = datetime.timedelta(
		seconds=config.get_s('deleted_message_resend_timer', msg.server.id),
	)
	if (datetime.datetime.now() - msg.timestamp) < dthreshold and \
	not msg.author.bot:
		if config.get_s('deleted_message_resend_content', msg.server.id):
			em = discord.Embed(
				title='UNDELETED MESSAGE',
				description=msg.content,
				colour=msg.author.colour,
			)
			em.set_footer(
				text='This message was resent as it was deleted too recently.',
			)
		else:
			em = discord.Embed(title='Message was deleted', colour=msg.author.colour)
			em.set_footer(
				text=(
					'This notification was sent because a message by this'
					' user was deleted too recently.'
				),
			)
		em.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
		await client.send_message(msg.channel, embed=em)

@client.event
async def on_message_edit(old, new):
	if isprivatemessage(old.server):
		return
	schan = getspecialchannel_reply(new)
	if not old.pinned and new.pinned and not logdisabled('message_pin', new.server):
		em = discord.Embed(
			title=(
				'\N{PUSHPIN}MESSAGE PINNED (SENT {reltime} IN #{chan})'
			).format(
				reltime=reltime(time.mktime(new.timestamp.timetuple())),
				chan=utils.mdspecialchars(new.channel.name),
			),
			description=new.content,
			colour=new.author.colour,
		)
		em.set_author(
			name=new.author.display_name,
			icon_url=new.author.avatar_url,
		)
		em.set_footer(
			text=utils.id_summary(uid=new.author.id, mid=new.id, cid=new.channel.id),
		)
		await client.send_message(schan, embed=em)
	if old.pinned and not new.pinned and not logdisabled('message_unpin', new.server):
		em = discord.Embed(
			title=(
				'\N{PUSHPIN}MESSAGE UNPINNED (SENT {reltime} IN #{chan})'
			).format(
				reltime=reltime(time.mktime(new.timestamp.timetuple())),
				chan=utils.mdspecialchars(new.channel.name),
			),
			description=new.content,
			colour=new.author.colour,
		)
		em.set_author(
			name=new.author.display_name,
			icon_url=new.author.avatar_url,
		)
		em.set_footer(
			text=utils.id_summary(uid=new.author.id, mid=new.id, cid=new.channel.id),
		)
		await client.send_message(schan, embed=em)

	# Preliminary checkings
	if old.content == new.content:
		# Must be the message being pinned and/or embed(s) displaying
		# Actually, TTS and rich embeds could also have changed,
		# but this is just a refactor
		return

	if not logdisabled('message_edit', new.server):
		if len(new.content) > 1024 or len(new.content) > 1024:
			em = discord.Embed(
				title=(
					'\N{MEMO}MESSAGE EDITED (SENT {reltime} IN #{chan}).'
					' The older content is:'
				).format(
					reltime=reltime(time.mktime(new.timestamp.timetuple())),
					chan=utils.mdspecialchars(new.channel.name),
				),
				description=old.content,
				colour=old.author.colour,
			)
			em.set_author(
				name=new.author.display_name,
				icon_url=new.author.avatar_url,
			)
			em.set_footer(
				text=utils.id_summary(
					uid=new.author.id, mid=new.id, cid=new.channel.id,
				),
			)
			await client.send_message(schan, embed=em)
			em = discord.Embed(
				title=(
					'MESSAGE EDITED (SENT {reltime} IN #{chan}).'
					' The newer content is:'
				).format(
					reltime=reltime(time.mktime(new.timestamp.timetuple())),
					chan=utils.mdspecialchars(new.channel.name),
				),
				description=new.content,
				colour=new.author.colour,
			)
			em.set_author(
				name=new.author.display_name,
				icon_url=new.author.avatar_url,
			)
			em.set_footer(
				text=utils.id_summary(
					uid=new.author.id, mid=new.id, cid=new.channel.id,
				),
			)
			await client.send_message(schan, embed=em)
		else:
			em = discord.Embed(
				title=(
					'\N{MEMO}MESSAGE EDITED (SENT {reltime} IN #{chan})'
				).format(
					reltime=reltime(time.mktime(new.timestamp.timetuple())),
					chan=utils.mdspecialchars(new.channel.name),
				),
				colour=new.author.colour,
			)
			em.set_author(
				name=new.author.display_name,
				icon_url=new.author.avatar_url,
			)
			em.add_field(name='Older Content', value=old.content, inline=False)
			em.add_field(name='Newer Content', value=new.content, inline=False)
			em.set_footer(
				text=utils.id_summary(
					uid=new.author.id, mid=new.id, cid=new.channel.id,
				),
			)
			await client.send_message(schan, embed=em)

	# Turning off this logging also turns off the feature
	if not logdisabled('message_overedit', new.server):
		# Delete a message if it has been edited more than 5 times in 30 seconds
		await utils.handle_minute_message_edits(new, schan)

@client.event
async def on_member_update(before, after):
	specialchannel = getspecialchannel(after.server)
	if before.nick != after.nick and not logdisabled('member_nickname', after.server):
		embed = discord.Embed(title='🇳📟CHANGED NICKNAME'.format(id=after.id), colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
		if before.nick == None:
			embed.add_field(name='No Older Nickname', value='_No Older Nickname_')
		else:
			embed.add_field(name='Older Nickname', value=utils.mdspecialchars(before.nick))
		if after.nick == None:
			embed.add_field(name='No Newer Nickname', value='_No Newer Nickname_')
		else:
			embed.add_field(name='Newer Nickname', value=utils.mdspecialchars(after.nick))
		await client.send_message(specialchannel, embed=embed)
	if before.roles != after.roles:
		# TODO: Make these better
		if len(before.roles) == len(after.roles) and not (
			logdisabled('member_roleadd', after.server) and \
			logdisabled('member_roleremove', after.server)
		):
			embed = discord.Embed(title='ROLES CHANGED FOR USER')
			embed.set_author(
				name=after.display_name,
				icon_url=after.avatar_url,
				url=infourl('userid={}'.format(after.id))
			)
			await client.send_message(specialchannel, embed=embed)
		if len(before.roles) > len(after.roles) and not logdisabled('member_roleremove', after.server): # if a role has been removed
			rolesremoved = list(set(before.roles).symmetric_difference(set(after.roles)))
			embed = discord.Embed(title='ROLE REMOVED FROM USER'.format(id=after.id), colour=rolesremoved[0].colour)
			embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
			for roleremoved in rolesremoved:
				embed.add_field(name='Removed Role', value=utils.mdspecialchars('{} ({})'.format(roleremoved.name, roleremoved.id)))
			await client.send_message(specialchannel, embed=embed)
		if len(before.roles) < len(after.roles) and not logdisabled('member_roleadd', after.server): # if a role has been added
			rolesadded = list(set(after.roles).symmetric_difference(set(before.roles)))
			embed = discord.Embed(title='ROLE ADDED TO USER'.format(id=after.id), colour=rolesadded[0].colour)
			# i am fucking TRIGGERED that i have to set these values twice
			embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
			for roleadded in rolesadded:
				embed.add_field(name='Added Role', value=utils.mdspecialchars('{} ({})'.format(roleadded.name, roleadded.id)))
			await client.send_message(specialchannel, embed=embed)
		if config.get_s('rolecachemode', after.server.id) != 0:
			updaterolecache(after)
			rolecachesave()
	if before.name != after.name and not logdisabled('member_username', after.server):
		description = '🇺📟CHANGED USERNAME'.format(id=after.id)
		if before.discriminator != after.discriminator:
			description += ' AND DISCRIMINATOR 🔸'
		embed = discord.Embed(title=description, colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=infourl('userid={}'.format(after.id)))
		embed.add_field(name='Older Username', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Username', value=utils.mdspecialchars(after.name))
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
	if not logdisabled('member_join', member.server):
		specialchannel = getspecialchannel(member.server)
		embed = discord.Embed(description='➡<@!{id}> ({id}) joined server'.format(id=member.id), colour=member.server.me.colour, timestamp=datetime.datetime.now())
		embed.add_field(
			name='This server now has',
			value=str(member.server.member_count) + ' members',
		)
		embed.set_author(name=member.display_name)
		embed.set_thumbnail(url=member.avatar_url)
		await client.send_message(specialchannel, embed=embed)
	await newmemberroles(member, specialchannel, False)

@client.event
async def on_member_remove(member):
	if not logdisabled('member_remove', member.server):
		specialchannel = getspecialchannel(member.server)
		embed = discord.Embed(description='🚪<@!{id}> ({id}) removed from server'.format(id=member.id), colour=member.colour, timestamp=datetime.datetime.now())
		embed.add_field(name='Originally joined server', value=reltime(time.mktime(member.joined_at.timetuple())))
		embed.add_field(
			name='This server now has',
			value=str(member.server.member_count) + ' members',
		)
		embed.set_author(name=member.display_name, icon_url=member.avatar_url)
		embed.set_thumbnail(url=member.avatar_url)
		await client.send_message(specialchannel, embed=embed)

@client.event
async def on_member_ban(member):
	if logdisabled('member_ban', member.server):
		return
	specialchannel = getspecialchannel(member.server)

	msg = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(wrapbackticks(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await client.send_message(specialchannel, msg)

@client.event
async def on_member_unban(server, user):
	if logdisabled('member_unban', server):
		return
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
async def on_server_role_create(r):
	if logdisabled('role_create', r.server):
		return
	schan = getspecialchannel(r.server)
	embed = discord.Embed(
		title='ROLE ADD AT {time}'.format(time=str(r.created_at)),
		description=utils.mdspecialchars(r.name),
		colour=r.colour,
	)
	await client.send_message(schan, embed=embed)

@client.event
async def on_server_role_delete(r):
	if logdisabled('role_delete', r.server):
		return
	schan = getspecialchannel(r.server)
	embed = discord.Embed(
		title='ROLE REMOVE',
		description=utils.mdspecialchars(r.name),
		colour=r.colour,
	)
	embed.add_field(name='Original Creation Time', value=str(r.created_at))
	await client.send_message(schan, embed=embed)

@client.event
async def on_server_role_update(before, after):
	specialchannel = getspecialchannel(before.server)
	# If the name changed
	if before.name != after.name and not logdisabled('role_rename', before.server):
		embed = discord.Embed(title='ROLE NAME CHANGE', description=utils.mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Name', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=utils.mdspecialchars(after.name))
		await client.send_message(specialchannel, embed=embed)
	# If "display online members separately" changed
	if before.hoist != after.hoist:
		# If the role has been hoisted
		if before.hoist == 0 and after.hoist == 1 and not logdisabled(
			'role_hoist', before.server
		):
			embed = discord.Embed(
				title='ROLE HOIST',
				description='{name}\nID: {id}'.format(
					name=utils.mdspecialchars(after.name),
					id=after.id,
				),
				colour=after.colour,
			)
			await client.send_message(specialchannel, embed=embed)
		# If the role has been lowered
		if before.hoist == 1 and after.hoist == 0 and not logdisabled(
			'role_unhoist', before.server
		):
			embed = discord.Embed(
				title='ROLE UNHOIST',
				description='{name}\nID: {id}'.format(
					name=utils.mdspecialchars(after.name),
					id=after.id,
				),
				colour=after.colour,
			)
			await client.send_message(specialchannel, embed=embed)
	# If "allow everyone to mention this role" changed
	if before.mentionable != after.mentionable:
		# If the role is now mentionable
		if before.mentionable == 0 and after.mentionable == 1 and not logdisabled(
			'role_mentionable', before.server
		):
			msg = '**`>`**`role` **``{}``** `({}) is now mentionable`'.format(wrapbackticks(after.name), after.id)
			await client.send_message(specialchannel, msg)
		# If the role is no longer mentionable
		if before.mentionable == 1 and after.mentionable == 0 and not logdisabled(
			'role_unmentionable', before.server
		):
			msg = '**`>`**`role` **``{}``** `({}) is no longer mentionable`'.format(wrapbackticks(after.name), after.id)
			await client.send_message(specialchannel, msg)
	# If the role has been moved up or down in the hierarchy
	if before.position != after.position and not logdisabled('role_hierarchy', before.server):
		# The role has been moved down
		if before.position > after.position:
			msg = '**`>`**`role` **``{}``** `({}) has been moved down by {} roles ({} to {})`'.format(wrapbackticks(after.name), after.id, before.position - after.position, before.position, after.position)
			await client.send_message(specialchannel, msg)
		# The role has been moved up
		if before.position < after.position:
			msg = '**`>`**`role` **``{}``** `({}) has been moved up by {} roles ({} to {})`'.format(wrapbackticks(after.name), after.id, after.position - before.position, before.position, after.position)
			await client.send_message(specialchannel, msg)
	# If the role color has changed
	if before.colour != after.colour and not logdisabled('role_color', before.server):
		embed = discord.Embed(title='ROLE COLOR CHANGE', description=utils.mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Color', value='(default)' if before.colour.value == 0 else str(before.colour).upper())
		embed.add_field(name='Newer Color', value='(default)' if after.colour.value == 0 else str(after.colour).upper())
		await client.send_message(specialchannel, embed=embed)
	# If any of the permissions has changed
	if before.permissions != after.permissions and not logdisabled(
		'role_permissions', before.server
	):
		diff = list(set(before.permissions).symmetric_difference(set(after.permissions)))
		e = discord.Embed(
			title='ROLE PERMISSIONS CHANGE',
			description='**{name}** ({0.id})'.format(
				after, name=utils.mdspecialchars(after.name)
			),
			colour=after.colour,
		)
		e.add_field(name='Permission Updated', value=diff[0][0])
		e.add_field(
			name='Older Permission',
			value=str(dict(before.permissions)[diff[0][0]]),
		)
		e.add_field(
			name='Newer Permission',
			value=str(dict(after.permissions)[diff[0][0]]),
		)
		await client.send_message(specialchannel, embed=e)


@client.event
async def on_reaction_add(r, u):
	if isprivatemessage(r.message.server) or logdisabled('reaction_add', r.message.server):
		return
	specialchannel = getspecialchannel(r.message.server)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION ADDED TO MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=reltime(time.mktime(r.message.timestamp.timetuple())),
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	embed.set_author(
		name=u.display_name,
		icon_url=u.avatar_url,
		url=infourl('userid={}&messageid={}'.format(u.id, r.message.id))
	)
	mdetails = u.mention
	if u.status == discord.Status.offline:
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
					name=str(r.emoji),
					id=r.emoji.id,
				)
			)
		),
	)
	await client.send_message(specialchannel, embed=embed)

@client.event
async def on_reaction_remove(r, u):
	if isprivatemessage(r.message.server) or logdisabled('reaction_remove', r.message.server):
		return
	specialchannel = getspecialchannel(r.message.server)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION REMOVED FROM MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=reltime(time.mktime(r.message.timestamp.timetuple())),
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	embed.set_author(
		name=u.display_name,
		icon_url=u.avatar_url,
		url=infourl('userid={}&messageid={}'.format(u.id, r.message.id))
	)
	mdetails = u.mention
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
					name=str(r.emoji),
					id=r.emoji.id,
				)
			)
		),
	)
	await client.send_message(specialchannel, embed=embed)

@client.event
async def on_reaction_clear(m, rs):
	if isprivatemessage(m.server) or logdisabled('reaction_clear', m.server):
		return
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
					name=str(r.emoji),
					id=r.emoji.id,
				)
		else:
			rlist += name + '\n'
	embed = discord.Embed(
		title='REACTIONS CLEARED FROM MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=reltime(time.mktime(m.timestamp.timetuple())),
			c=m.channel,
		),
		description=m.content,
		colour=m.author.colour,
	)
	embed.add_field(name='Message ID (temp)', value=m.id)
	embed.add_field(name='Reactions', value=rlist)
	await client.send_message(schan, embed=embed)

@client.event
async def on_server_update(before, after):
	specialchannel = getspecialchannel(after)
	if before.icon != after.icon and not logdisabled('server_icon', after):
		embed = discord.Embed(description='Server changed icon')
		embed.set_thumbnail(url=before.icon_url)
		embed.add_field(name='Older Icon URL: None' if before.icon_url == '' else 'Older Icon URL (Thumbnail)', value='No Older Icon URL' if before.icon_url == '' else before.icon_url)
		embed.add_field(name='Newer Icon URL: None' if after.icon_url == '' else 'Newer Icon URL (Inset Image)', value='No Newer Icon URL' if after.icon_url == '' else after.icon_url)
		embed.set_image(url=after.icon_url)
		await client.send_message(specialchannel, embed=embed)
	if before.name != after.name and not logdisabled('server_rename', after):
		embed = discord.Embed(description='Server changed name')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Name', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=utils.mdspecialchars(after.name))
		await client.send_message(specialchannel, embed=embed)
	if before.region != after.region and not logdisabled('server_region', after):
		embed = discord.Embed(description='VOICE REGION CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Region', value=str(before.region))
		embed.add_field(name='Newer Region', value=str(after.region))
		await client.send_message(specialchannel, embed=embed)
	if before.afk_timeout != after.afk_timeout and not logdisabled('server_afktimeout', after):
		b_m, b_s = divmod(before.afk_timeout, 60)
		b_h, b_m = divmod(b_m, 60)
		a_m, a_s = divmod(after.afk_timeout, 60)
		a_h, a_s = divmod(a_m, 60)
		embed = discord.Embed(description='AFK TIMEOUT CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(
			name='Older Timeout',
			value='{h}h {m}m {s}s'.format(h=b_h, m=b_m, s=b_s),
		)
		embed.add_field(
			name='Newer Timeout',
			value='{h}h {m}m {s}s'.format(h=a_h, m=a_m, s=a_s),
		)
		await client.send_message(specialchannel, embed=embed)
	if before.afk_channel != after.afk_channel and not logdisabled('server_afkchannel', after):
		embed = discord.Embed(description='AFK CHANNEL CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(
			name='Older Channel: None' if before.afk_channel == None else 'Older Channel',
			value='No Older Channel' if before.afk_channel == None else '{name} ({0.id})'.format(before.afk_channel, name=utils.mdspecialchars(before.afk_channel.name)),
		)
		embed.add_field(
			name='Newer Channel: None' if after.afk_channel == None else 'Newer Channel',
			value='No Newer Channel' if after.afk_channel == None else '{name} ({0.id})'.format(after.afk_channel, name=utils.mdspecialchars(after.afk_channel.name)),
		)
		await client.send_message(specialchannel, embed=embed)
	if before.verification_level != after.verification_level and not logdisabled(
		'server_verificationlevel', after
	):
		embed = discord.Embed(description='VERIFICATION LEVEL CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(
			name='Older Level',
			value=str(before.verification_level).title(),
		)
		embed.add_field(
			name='Newer Level',
			value=str(after.verification_level).title(),
		)
		await client.send_message(specialchannel, embed=embed)
	if before.mfa_level != after.mfa_level and not logdisabled('server_2fa', after):
		if before.mfa_level == 0 and after.mfa_level == 1:
			embed=discord.Embed(description='SERVER 2FA ENABLED')
		elif before.mfa_level == 1 and after.mfa_level == 0:
			embed=discord.Embed(description='SERVER 2FA DISABLED')
		await client.send_message(specialchannel, embed=embed)

@client.event
async def on_server_emojis_update(b, a):
	try:
		schan = getspecialchannel(a[0].server)
	except IndexError:
		schan = getspecialchannel(b[0].server)
	if logdisabled('server_emotes', schan.server):
		# We could split this into separate emotes_* log types
		return
	diff = list(set(b).symmetric_difference(set(a)))
	elist = ''
	for e in diff:
		elist += '{str} – {0.name} ({0.id})\n'.format(e, str=str(e))
	if len(b) > len(a):
		desc = 'EMOTE REMOVE'
	elif len(b) < len(a):
		desc = 'EMOTE ADD'
	else:
		# Emote name change, get the emote in question
		for befemo in b:
			for aftemo in a:
				if befemo.id == aftemo.id and befemo.name != aftemo.name:
					embef = befemo
					emaft = aftemo

		embed = discord.Embed(
			title='EMOTE NAME CHANGE',
			description=str(emaft),
		)
		embed.add_field(name='Older Name', value=embef.name)
		embed.add_field(name='Newer Name', value=emaft.name)
		await client.send_message(schan, embed=embed)
		return
	embed = discord.Embed(description=desc)
	embed.add_field(name='Emotes', value=elist)
	await client.send_message(schan, embed=embed)

@client.event
async def on_voice_state_update(before, after):
	voicetextchannel = after.server.get_channel(
		config.get_s('voicechat_channel_text', after.server.id),
	)
	voicevoicechannel = after.server.get_channel(
		config.get_s('voicechat_channel_voice', after.server.id),
	)
	if voicetextchannel == None or voicevoicechannel == None:
		return
	if after.voice.voice_channel != None \
	and after.voice.voice_channel == voicevoicechannel:
		# JOINED the voice channel.
		overwrite = discord.PermissionOverwrite()
		overwrite.read_messages = True
		await client.edit_channel_permissions(voicetextchannel, after, overwrite)

	if before.voice.voice_channel != None \
	and before.voice.voice_channel == voicevoicechannel:
		# LEFT the voice channel.
		await client.delete_channel_permissions(voicetextchannel, after)

@client.event
async def on_channel_create(c):
	if c.type == discord.ChannelType.private or logdisabled('channel_add', c.server):
		return
	schan = getspecialchannel(c.server)
	embed = discord.Embed(
		description='{type} CHANNEL ADD\n{0.name} ({0.id})'.format(
			c,
			type=str(c.type).upper(),
		),
	)
	await client.send_message(schan, embed=embed)

@client.event
async def on_channel_delete(c):
	if c.type == discord.ChannelType.private or logdisabled('channel_remove', c.server):
		return
	schan = getspecialchannel(c.server)
	embed = discord.Embed(
		description='{type} CHANNEL REMOVE\n{0.name} ({0.id})'.format(
			c,
			type=str(c.type).upper(),
		),
	)
	await client.send_message(schan, embed=embed)

@client.event
async def on_socket_raw_receive(payload):
	try:
		event = json.loads(payload)
	except TypeError:
		return

	# Events to check
	ckevnts = [
		'MESSAGE_DELETE',
		'MESSAGE_UPDATE',
		'MESSAGE_REACTION_ADD',
		'MESSAGE_REACTION_REMOVE',
		'MESSAGE_REACTION_REMOVE_ALL',
	]
	if event['t'] not in ckevnts:
		return

	# We must first know what server it is
	mchan = client.get_channel(event['d']['channel_id'])
	if mchan.type == discord.ChannelType.private:
		return

	if event['t'] == 'MESSAGE_DELETE':
		if logdisabled('message_deleteuncached', mchan.server):
			return
		# Check if on_message_delete() was already called by this message
		# If it was, then return
		if discord.utils.find(lambda m: m.id == event['d']['id'], client.messages) != None:
			# If the message lingers in deleted_messages, it doesn't really matter for now
			return
		if event['d']['id'] in owncache:
			# Already removed from the cache, but we still haven't run on_message_delete
			# This happens all the time.
			owncache.remove(event['d']['id'])
			return
		for m in deleted_messages:
			if m.id == event['d']['id']:
				# on_message_delete was faster
				deleted_messages.remove(m)
				return

		schan = getspecialchannel(
			mchan.server
		)
		e = discord.Embed(
			title='UNCACHED MESSAGE DELETED IN {0.mention}'.format(mchan),
			url=infourl('messageid=' + event['d']['id']),
			description=(
				'Since this message is uncached, I can’t give you'
				' any more information than its ID and its channel.'
			),
			colour=mchan.server.me.colour,
		)
		await client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_UPDATE':
		if logdisabled('message_updateuncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['id'], client.messages) != None:
			return

		schan = getspecialchannel(mchan.server)
		athr = mchan.server.get_member(event['d']['author']['id'])
		e = discord.Embed(
			title=(
				'UNCACHED MESSAGE UPDATED (SENT {rltm}'
				' IN {0.mention}).'
				' NEWER CONTENT AND PROPERTIES:'
			).format(
				mchan,
				rltm=reltime(
					time.mktime(
						discord.utils.parse_time(
							event['d']['timestamp']
						).timetuple()
					)
				),
			),
			description=event['d']['content'],
			colour=athr.colour,
		)
		e.set_author(
			name=athr.display_name,
			icon_url=athr.avatar_url,
			url=infourl(
				(
					'userid={uid}&messageid={mid}'
				).format(
					uid=athr.id,
					mid=event['d']['id'],
				),
			)
		)
		e.add_field(
			name='Pinned',
			value='Yes' if event['d']['pinned'] else 'No',
		)
		e.add_field(
			name='TTS',
			value='Yes' if event['d']['tts'] else 'No',
		)
		e.add_field(
			name='Rich Embed',
			value=(
				'``{}``'.format(wrapbackticks(str(event['d']['embeds']['rich'])))
				if 'rich' in event['d']['embeds']
				else '(none)'
			),
		)
		e.set_footer(
			text=(
				'Since this message is uncached,'
				' I can’t give you its older properties.'
			)
		)
		await client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_REACTION_ADD':
		if logdisabled('reaction_adduncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['message_id'], client.messages) \
		!= None:
			return

		schan = getspecialchannel(mchan.server)
		athr = mchan.server.get_member(event['d']['user_id'])
		mdetails = athr.mention
		if athr.status == discord.Status.offline:
			mdetails += ' (Invisible)'
		e = discord.Embed(
			title='REACTION ADDED TO UNCACHED MESSAGE IN {0.mention}'.format(mchan),
			description=(
				'Since this message is uncached, I can’t give you'
				' any more information than its ID, author, and channel.'
			),
			colour=mchan.server.me.colour,
		)
		e.set_author(
			name=athr.display_name,
			icon_url=athr.avatar_url,
			url=infourl(
				(
					'userid={uid}&messageid={mid}'
				).format(
					uid=athr.id,
					mid=event['d']['message_id'],
				),
			)
		)
		e.add_field(
			name='Member of Reaction',
			value=mdetails,
		)
		e.add_field(
			name='Reaction',
			value=(
				'<:{name}:{id}>'
			).format(
				name=event['d']['emoji']['name'],
				id=event['d']['emoji']['id'],
			) if event['d']['emoji']['id'] != None else event['d']['emoji']['name'],
		)
		await client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_REACTION_REMOVE':
		if logdisabled('reaction_removeuncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['message_id'], client.messages) \
		!= None:
			return

		schan = getspecialchannel(mchan.server)
		athr = mchan.server.get_member(event['d']['user_id'])
		mdetails = athr.mention
		e = discord.Embed(
			title='REACTION REMOVED FROM UNCACHED MESSAGE IN {0.mention}'.format(mchan),
			description=(
				'Since this message is uncached, I can’t give you'
				' any more information than its ID, author, and channel.'
			),
			colour=mchan.server.me.colour,
		)
		e.set_author(
			name=athr.display_name,
			icon_url=athr.avatar_url,
			url=infourl(
				(
					'userid={uid}&messageid={mid}'
				).format(
					uid=athr.id,
					mid=event['d']['message_id'],
				),
			)
		)
		e.add_field(
			name='Member of Reaction',
			value=mdetails,
		)
		e.add_field(
			name='Reaction',
			value=(
				'<:{name}:{id}>'
			).format(
				name=event['d']['emoji']['name'],
				id=event['d']['emoji']['id'],
			) if event['d']['emoji']['id'] != None else event['d']['emoji']['name'],
		)
		await client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_REACTION_REMOVE_ALL':
		if logdisabled('reaction_clearuncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['message_id'], client.messages) \
		!= None:
			return

		schan = getspecialchannel(mchan.server)
		e = discord.Embed(
			title=(
				'REACTIONS CLEARED FROM UNCACHED MESSAGE'
				' IN {0.mention}'
			).format(mchan),
			url=infourl('messageid=' + event['d']['message_id']),
			description=(
				'Since this message is uncached, I can’t give you'
				' any more information than its ID and its channel.'
			),
			colour=mchan.server.me.colour,
		)
		await client.send_message(schan, embed=e)

@client.event
async def on_channel_update(b, a):
	if a.type == discord.ChannelType.private or logdisabled('channel_rename', a.server):
		return
	schan = getspecialchannel(a.server)
	if b.name != a.name:
		e = discord.Embed(
			title='{type} CHANNEL UPDATE'.format(type=str(a.type).upper()),
			description=(
				'**{name}** ({id})'
			).format(
				name=utils.mdspecialchars(a.name),
				id=a.id,
			),
			colour=a.server.me.colour,
		)
		e.add_field(name='Older Name', value=utils.mdspecialchars(b.name))
		e.add_field(name='Newer Name', value=utils.mdspecialchars(a.name))
		await client.send_message(schan, embed=e)

@client.event
async def on_server_join(serv):
	em = discord.Embed(
		title='BOT ADDED TO SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(serv.name),
			id=serv.id,
		),
		colour=opserver.me.colour,
	)
	em.set_image(url=serv.icon_url)
	await client.send_message(opserver_botservers, embed=em)

@client.event
async def on_server_remove(serv):
	em = discord.Embed(
		title='BOT REMOVED FROM SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(serv.name),
			id=serv.id,
		),
		colour=opserver.me.colour,
	)
	em.set_image(url=serv.icon_url)
	await client.send_message(opserver_botservers, embed=em)

# Read as: dump code from file ... here
# So that we can have our existing functions without going across separate modules, and without
# making main.py far too long.
exec(compile(open("functions.py", "rb").read(), "functions.py", 'exec'))
exec(compile(open("commands.py", "rb").read(), "commands.py", 'exec'))

client.run(token)
