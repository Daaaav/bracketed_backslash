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

def rolecachesave():
	with open('memberroles.json', 'w') as outfile:
		json.dump(events.memberroles, outfile)

def rulesave():
	with open('rules.json', 'w') as outfile:
		json.dump(events.rules, outfile)

def rolexpiresave():
	with open('rolexpires.json', 'w') as outfile:
		json.dump(events.rolexpires, outfile)

def listroles(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '<@&{}>'.format(role.id)
	return returnage

def listroles_id(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '<@&{}>'.format(role)
	return returnage

def getspecialchannel(server):
	theconfig = config.get_s('specialchannel', server.id)
	if theconfig != '0':
		return client.get_channel(id=theconfig)
	else:
		return server.default_channel

def getspecialchannel_reply(message):
	if message.server == None:
		return message.channel
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

	return True

def parsereltime(inputstr, relative=False, now=None):
	# if relative is true then we only get the amount of seconds from now, if false we get a unix timestamp.
	if now == None:
		now = int(time.time())
	total = 0

	m = re.search("^((?P<d>[0-9]+)d)?((?P<h>[0-9]+)h)?((?P<m>[0-9]+)m)?((?P<s>[0-9]+)s)?$", inputstr)

	if m == None:
		return None

	ds = m.group('d')
	if ds != None:
		total += int(ds)*86400
	hs = m.group('h')
	if hs != None:
		total += int(hs)*3600
	ms = m.group('m')
	if ms != None:
		total += int(ms)*60
	ss = m.group('s')
	if ss != None:
		total += int(ss)

	if relative:
		return total
	else:
		return now+total

async def handleExpiryTimer():
	"""Sets the timer correctly to the first event
	If time is in the past, call autoExpiry immediately
	Can be called on startup, when changing something, or at the end of autoExpiry
	"""
	global exptimer

	# Cancel the existing timer, if it's running
	if exptimer != None:
		exptimer.cancel()
		exptimer = None  # Because there's no Timer.isCanceled()

	entriesleft = False

	for serverid in events.rolexpires:  # Merge with next for maybe
		if len(events.rolexpires[serverid]) > 0:
			entriesleft = True
			break

	if not entriesleft:
		# We're finished
		logging.info('Did not set expiry timer because there\'s no expiry entry left')
		return

	timelowscore = 9999999999

	for serverid in events.rolexpires:
		for userid in events.rolexpires[serverid]:
			if events.rolexpires[serverid][userid]['time'] < timelowscore:
				timelowscore = events.rolexpires[serverid][userid]['time']

	if timelowscore <= int(time.time()):
		logging.info('Immediately calling autoExpiry() because we’re overdue in resetting someone’s roles')
		await autoExpiry()
	else:
		timertime = (timelowscore - time.time()) + 2  # 2 seconds extra, just to make sure we're not getting problems due to being one second off
		exptimer = Timer(timertime, callAutoExpiry)
		exptimer.start()
		logging.info('Set expiry timer for {} seconds'.format(timertime))

def callAutoExpiry():
	asyncio.run_coroutine_threadsafe(autoExpiry(), client.loop)

async def autoExpiry():
	"""Called by timers
	Actually resets roles
	Calls back handleTimer to set the next timer
	"""
	now = int(time.time())

	# So apparently someone needs to be unbanned?
	for serverid in events.rolexpires:
		content = ''
		successfulresets = []

		cserver = discord.utils.get(client.servers, id=serverid)
		for userid in events.rolexpires[serverid]:
			if events.rolexpires[serverid][userid]['time'] <= now:
				try:
					await removeRestrictiveRoles(cserver.get_member(userid), cserver)
					content += '\nRoles for <@!{}> reset.'.format(userid)
				except (AttributeError, TypeError):
					# Look if they are in the role cache, and reset it there instead.
					if removerolecache(userid, serverid):
						content += '\n<@!{}> was supposed to have their roles reset now, they aren’t on the server, but they’ve successfully been removed from the role cache.'.format(userid)
						rolecachesave()
					else:
						content += '\n<@!{}> was supposed to have their roles reset now, but they can be found neither on the server nor in the role cache!'.format(userid)

				# Shorten the following thing so we don't have to keep typing it.
				thisexpiry = events.rolexpires[serverid][userid]
				if thisexpiry['msgedit_message'] != '0':
					await editexpirymessage(cserver, thisexpiry)
				if thisexpiry['msgpost_channel'] != '0':
					# We want to announce it with a new message!
					await client.send_message(
						discord.utils.get(cserver.channels,
							id=thisexpiry['msgpost_channel']
						),
						thisexpiry['msgpost_content']
					)

				successfulresets.append(userid)
		for userid in successfulresets:
			removeexpiryentry(serverid, userid)

		if len(successfulresets) > 0:
			if content == '':
				content = '\n(never mind, nobody has been found!)'

			content = '**Auto expiry:**' + content

			await client.send_message(getspecialchannel(cserver), content)

	rolexpiresave()

	await handleExpiryTimer()

async def removeRestrictiveRoles(member, server):
	try:
		await givetakeroles(
			member, server,
			config.get_s('defaultbotroles' if member.bot else 'defaultroles',server.id),
			config.get_s('restrictiveroles', server.id)
		)
	except (AttributeError,TypeError) as e:
		raise e

async def givetakeroles(member, server, giveids, takeids):
	badroles = [] # All the roles that are potentially deleted
	removingtheseroles = [] # Roles that the user has which will be deleted
	addingtheseroles = [] # Roles that the user doesn't have which will be added
	otherroles = [] # Other roles the user has

	for rid in takeids:
		badroles.append(
			discord.utils.get(server.roles, id=rid)
		)
	for rid in giveids:
		addingtheseroles.append(
			discord.utils.get(server.roles, id=rid)
		)
	for role in member.roles:
		if role in badroles:
			# This member has that bad role, we need to get rid of it!
			removingtheseroles.append(role)
			continue
		if role in addingtheseroles:
			# Oh, we already have that one
			addingtheseroles.remove(role)
		if not role.is_everyone:
			# If we're going to need to replace roles, keep these the same!
			otherroles.append(role)
	if len(addingtheseroles) == 0 and len(removingtheseroles) == 0:
		# Well what are we doing here?
		return
	if len(addingtheseroles) > 0 and len(removingtheseroles) > 0:
		# Replace - luckily the union of these is this simple!
		await client.replace_roles(member, *addingtheseroles, *otherroles)
	elif len(addingtheseroles) > 0:
		# Only adding
		await client.add_roles(member, *addingtheseroles)
	else:
		# Only removing
		await client.remove_roles(member, *removingtheseroles)

async def editexpirymessage(cserver, thisexpiry):
	# We want to edit a message to reflect the ban!
	getmessage = await client.get_message(
		discord.utils.get(cserver.channels,
			id=thisexpiry['msgedit_channel']
		),
		thisexpiry['msgedit_message']
	)
	if thisexpiry['msgedit_newcontent'] == '':
		await client.delete_message(getmessage)
	else:
		await client.edit_message(getmessage, new_content=thisexpiry['msgedit_newcontent'])

def addexpiryentry(serverid, memberid, expirytime,
                   e_channel='0', e_message='0', e_newcontent='',
                   p_channel='0', p_content=''):
	if not serverid in events.rolexpires:
		events.rolexpires[serverid] = {}

	events.rolexpires[serverid][memberid] = {
		'time': expirytime,
		'msgedit_channel': e_channel,
		'msgedit_message': e_message,
		'msgedit_newcontent': e_newcontent,
		'msgpost_channel': p_channel,
		'msgpost_content': p_content,
	}

def removeexpiryentry(serverid, memberid):
	if not serverid in events.rolexpires:
		return False

	if not memberid in events.rolexpires[serverid]:
		return False

	del events.rolexpires[serverid][memberid]
	return True

def getearliestexpiry(serverid):  # Returns: [userid, entry]
	if not serverid in events.rolexpires or len(events.rolexpires[serverid]) == 0:
		return None

	timelowscore = 9999999999
	earliestuserid = '0'
	earliestexpiry = None  # Entry

	for userid in events.rolexpires[serverid]:
		if events.rolexpires[serverid][userid]['time'] < timelowscore:
			timelowscore = events.rolexpires[serverid][userid]['time']
			earliestuserid = userid
			earliestexpiry = events.rolexpires[serverid][userid]

	return [earliestuserid, earliestexpiry]

async def fetch(url):
	async with ClientSession() as session:
		async with session.get(url) as response:
			return await response.read()

def logfailedcommand(command, arguments, message):
	if arguments == None:
		arguments = ''
	logging.info('{} {} attempted by {}#{} (uuid {}) at {} utc but failed'.format(command, arguments, message.author.name, message.author.discriminator, message.author.id, message.timestamp))

def logcommand(command, arguments, message):
	if arguments == None:
		arguments = ''
	logging.info('{} {} called by {}#{} (uuid {}) at {} utc'.format(command, arguments, message.author.name, message.author.discriminator, message.author.id, message.timestamp))

def infourl(query):
	return 'https://tolp2.nl/showdiscordinfo.php?' + query

def logdisabled(key, server):
	checks = [key, key.split('_')[0] + '_*', '*']

	if any(x in config.get_s('disabledlogs', server.id) for x in checks):
		return True
	if any(x in config.get_s('enabledlogs', server.id) for x in checks):
		return False
	return True

def respondtorule(rule):
	if int(rule) == 37:
		return 'Funny and original, nothing to see here.'
	return 'Wow, you’re the FIRST one to come up with that. I wish I could be as funny as you, I dunno how I’m ever gonna top "rule {}", though. That shit is genius.'.format(rule)

# Read as: dump code from file ... here
# So that we can have our existing functions without going across separate modules, and without
# making main.py far too long.
exec(compile(open("functions.py", "rb").read(), "functions.py", 'exec'))
exec(compile(open("commands.py", "rb").read(), "commands.py", 'exec'))

client.run(token)
