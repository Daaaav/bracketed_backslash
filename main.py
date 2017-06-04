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

import asyncio
from aiohttp import ClientSession
import inspect
import importlib
import json
import logging
import math
import os
import os.path
import random
import re
import subprocess
import sys
import tempfile
import time
from threading import Timer
import traceback

import discord

import config
import col
import customcommands
import emb
import events
import images
import op_ids
import utils

op_ids.load()
config.load()
customcommands.load()

# set bot version
botversion = '1.0'

# sets up logging
# level can be logging.DEBUG, logging.WARNING, et cetera
# see https://docs.python.org/3/library/logging.html for more info.
logging.basicConfig(level=logging.INFO)

client = discord.Client(max_messages=999999999) # defines all client.* commands

def load_events():
	global events
	events = importlib.reload(events)
	for i in inspect.getmembers(events, inspect.isfunction):
		client.event(i[1])

load_events()

cachelocation = './.cache'
attachcache = cachelocation + '/' + 'attach' # define attachment caching location
embedcache = cachelocation + '/' + 'embed'

invoker = '\\' # command invoker
altinvoker = 'ok glass, ' # alt command invoker
hangmaninvoker = '-'

# Hangman stuff
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

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

minutemessageedits = {}

messages_deleted_by_bot = []
deleted_messages = []

owncache = [] # Holds IDs because that's the only thing that's needed here, saves a lot of memory
              # and has better performance, because the cache can get yuge

votemutes = {} # userid -> dict with `starttime`, `proponents`*, `opponents`*

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

modificationtimes = [os.path.getmtime(x) for x in os.listdir() if x.endswith('.py')]
modificationtimecache = time.strftime(config.get_s('timeformat'), time.gmtime(max(modificationtimes)))

maineventloop = asyncio.get_event_loop()

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

def is_channel_manager(member):
	try:
		return member.server_permissions.manage_channels
	except AttributeError:
		return False

def is_role_manager(member):
	try:
		return member.server_permissions.manage_roles
	except AttributeError:
		return False

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

def is_operator(member):
	return member.id in op_ids.ids['operators'] or member.id == op_ids.ids['host']

def is_tntgb_mod(member):
	for role in member.roles:
		if role.id == '266590337269497856': # TNTGB moderator role
			return True
	return False

def is_tntgb_banned(member):
	for role in member.roles:
		if role.id == '243076976565288960': # TNTGB banned role
			return True
	return False

def is_host(member):
	return member.id == op_ids.ids['host']

async def reply(messageobject, message=None, emb=None):
	# Removes the need for adding msg_start manually every time
	if message == None:
		message = ''
	if len(events.msg_start + message) >= 2000:
		# We can at least try in a totally not failsafe and kinda ugly way
		content = events.msg_start + message
		contentlines = content.split('\n')
		cut = math.floor(len(contentlines)/2)
		await client.send_message(messageobject.channel, '\n'.join(contentlines[:cut]))
		if emb != None:
			await client.send_message(messageobject.channel, '\n'.join(contentlines[cut:]), embed=emb)
		else:
			await client.send_message(messageobject.channel, '\n'.join(contentlines[cut:]))
		return
	try:
		if emb != None:
			await client.send_message(
				messageobject.channel,
				events.msg_start + message,
				embed=emb,
			)
		else:
			await client.send_message(messageobject.channel, events.msg_start + message)
	except(discord.errors.HTTPException, discord.errors.Forbidden) as e:
		if messageobject.channel.type == discord.ChannelType.private:
			servinfo = '\t(direct message)\n'
		else:
			servinfo = (
				'\tName: {0.name}\n'
				'\tID: {0.id}\n'
			).format(messageobject.server)
		if emb == None:
			dispemb = '\t(none)\n'
		else:
			dispemb = str(emb.to_dict())
		logging.info(
			(
				'A message reply() was rejected, with exception {excpt}\n'
				'The server it was attemped to be sent to is:\n'
				'{servinfo}\n'
				'The channel it was attempted to be sent to is:\n'
				'\tType: {chantype}\n'
				'\tName: {chan.name}\n'
				'\tID: {chan.id}\n'
				'\n'
				'The content of the rejected message is:\n'
				'\t{con}\n'
				'The rich embed of the rejected message is:\n'
				'\t{emb}\n'
			).format(
				excpt=type(e).__name__,
				servinfo=servinfo,
				chantype=str(messageobject.channel.type).title(),
				chan=messageobject.channel,
				con=events.msg_start + message,
				emb=dispemb,
			)
		)
		raise

async def replyattach(messageobject, filetoattach, fname, message=''):
	# Don't bother with handling >2000 character messages just yet
	await client.send_file(destination=messageobject.channel, content = events.msg_start + message, fp=filetoattach, filename=fname)

def isprivatemessage(server): # this is a function because so in the future more checks for if its a private message can ezily be added
	if server == None:
		return True
	else:
		return False

def helplist(cats, server, onlycat=None):
	returnage = ''
	for cat in cats:
		if (onlycat is None and cat['cat_shown']) or onlycat == cat['cat_slug']:
			if onlycat is None:
				returnage += (
					'\n\n__`{}:`__ — For command descriptions: **`\help {}`**'
				).format(cat['cat_name'], cat['cat_slug'])
			else:
				if cat['cat_desc'] != '':
					returnage += cat['cat_desc']
				returnage += '\n__`{}:`__'.format(cat['cat_name'])

			first = True
			if cat['cat_slug'] == 'server':
				helpcommands = customcommands.list_commands_help(server)
			else:
				helpcommands = cat['commands']
			for cmd in helpcommands:
				if onlycat is None:
					if first:
						returnage += '\n`\{}`'.format(cmd['name'])
						first = False
					else:
						returnage += '   `\{}`'.format(cmd['name'])
				else:
					returnage += '\n`\{}` – {}'.format(
						cmd['name'], cmd['short']
					)
	return returnage

def is_valid_command(com):
	global cmds
	for cat in cmds:
		for cmd in cat['commands']:
			if cmd['name'] == com:
				return True
	return False

def hangmanworddisp(theword):
	theoutput = ''
	events.algeraden = True

	for i in range(0, len(theword)):
		if events.guessedletters[alphabet.find(theword[i].upper())]:
			theoutput += '__**`{}`**__ '.format(theword[i])
		else:
			theoutput += '`_` '
			events.algeraden = False

	# Now display already guessed letters.
	theoutput += '    (used: '

	notnone = False

	for i in range(0, 26):
		if events.guessedletters[i]:
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

def updaterolecache(member, serverid=None):
	if serverid == None:
		serverid = member.server.id
	if not serverid in events.memberroles:
		events.memberroles[serverid] = {}
	events.memberroles[serverid][str(member.id)] = list(rolelist(member.roles))

def removerolecache(memberid, serverid):
	try:
		del events.memberroles[serverid][memberid]
	except KeyError:
		return False

	return True

# Read as: dump code from file ... here
# So that we can have our existing functions without going across separate modules, and without
# making main.py far too long.
exec(compile(open("functions.py", "rb").read(), "functions.py", 'exec'))
exec(compile(open("commands.py", "rb").read(), "commands.py", 'exec'))

client.run(token)
