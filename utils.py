#!/usr/bin/python3.5
# encoding=utf-8

import aiohttp
import asyncio
import datetime
import json
import logging
import math
import re
import time
import threading

import discord

import bot
import checks
import config
import customcommands
import events
import op_ids
import wrapper

def mdspecialchars(string, character='\\'):
	"""Return a Markdown-escaped version of a given string, for use in message output."""
	notspecialchars = ' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
	try:
		newstring = ''
		for i in string:
			newstring += character + i if i not in notspecialchars else i
		return newstring
	except AttributeError:
		return string

def id_summary(uid=None, mid=None, cid=None, rid=None):
	"""Return a oneline summary of IDs."""
	summary = ''
	if uid:
		summary += ' \N{BUST IN SILHOUETTE}' + str(uid)
	if mid:
		summary += ' \N{SPEECH BALLOON}' + str(mid)
	if cid:
		summary += ' \N{TELEVISION}' + str(cid)
	if rid:
		summary += ' \N{KEY}' + str(rid)
	if summary.startswith(' '):
		summary = summary[1:]
	return summary

async def handle_minute_message_edits(msg, schan):
	if msg.id not in bot.minutemessageedits:
		bot.minutemessageedits[msg.id] = [int(time.time())]
	else:
		edittime = int(time.time())
		while True:
			if edittime in bot.minutemessageedits[msg.id]:
				edittime += .1
			else:
				bot.minutemessageedits[msg.id].append(edittime)
				break
		if len(bot.minutemessageedits[msg.id]) >= 5:
			await handle_delete_overedited_message(msg, schan)

		# While we're at it, also clean up other messages.

		# Copy because we may be removing elements from here
		for k in list(bot.minutemessageedits):
			if k != msg.id:
				for i in list(bot.minutemessageedits[k]):
					if i < (int(time.time())-30):
						bot.minutemessageedits[k].remove(i)
				if not bot.minutemessageedits[k]:
					del bot.minutemessageedits[k]

async def handle_delete_overedited_message(msg, schan):
	# Copy the list, we may be removing elements from here
	for i in list(bot.minutemessageedits[msg.id]):
		if i < (int(time.time())-30):
			bot.minutemessageedits[msg.id].remove(i)

	if len(bot.minutemessageedits[msg.id]) >= 5:
		# Ok, that's enough editing.
		try:
			await msg.delete()
			bot.messages_deleted_by_bot.append(msg)
			em = discord.Embed(
				title=('\N{MEMO}' * 5) + (
					'Message {0.id} was edited too many times in'
					' {0.channel.mention} and has been deleted by me'
				).format(msg),
				description=msg.content,
				colour=msg.author.colour,
				timestamp=datetime.datetime.now(),
			)
			em.set_author(
				name=msg.author.display_name,
				icon_url=msg.author.avatar_url,
			)
			em.add_field(
				name='Message author',
				value='<@!{0}> ({0})'.format(msg.author.id),
			)
		except discord.errors.NotFound:
			em = discord.Embed(
				title=(
					'\N{MEMO}' * 5
				) + (
					'Message {0.id} was edited too many times in'
					' {0.channel.mention} but they deleted it before I could'
				).format(msg),
				description=msg.content,
				colour=msg.author.colour,
				timestamp=datetime.datetime.now(),
			)
			em.set_author(
				name=msg.author.display_name,
				icon_url=msg.author.avatar_url,
			)
			em.add_field(
				name='Message author',
				value='<@!{id}> ({id})'.format(id=msg.author.id),
			)
		await schan.send(embed=em)

		# Also actually reply
		await msg.channel.send(
			'{0.author.mention}. Were you going to stop editing that message?'
			.format(msg),
		)

def match_input(objtype, request, *, guild=None, client=None):
	"""Return a member/guild/channel/role/emoji object given an input which could be anything
	that identifies that object. If it can't be found, return None.

	objtype: A string that specifies the type of object to search for. Can be either 'member',
	'guild', 'channel', 'role', or 'emoji'.

	request: A string that will be tried to be matched to.

	guild (optional): A discord.Guild object, which is the scope of where
	members/channels/roles/emojis will be searched. Defaults to None.

	client (optional): A discord.Client object, which is the scope of where guilds will be
	searched. Defaults to None.

	The following priority is used:
	1) (Members only) Mention: <@146814960574398464> or <@!146814960574398464>
	2) (Channels only) Mention: <#153368829160849408>
	3) (Roles only) Mention: <@&153369506813706240>
	4) (Emojis only) Emoji: <:unjoy:263889385492185088>
	5) ID: 146814960574398464
	6) (Members only) Username/Username+Discriminator (Discord tag)/Nickname, whatever
	discord.Server.get_member_named() accepts: Info Teddy, Info Teddy#3737, info teddy
	7) Name: tOLP, general, Owner, unjoy
	8) (Members only) Case-insensitive nickname complete match: info teddy
	9) Case-insensitive name complete match: Info Teddy, tolp, owner
	10) (Members only) Case-insensitive nickname partial match: info
	11) Case-insensitive name partial match: Info, tOL, own
	12) (Members only) Discriminator only (either with or without #): 3737
	"""
	acceptvals = ('member', 'guild', 'channel', 'role', 'emoji')
	if objtype not in acceptvals:
		raise ValueError('objtype has to be one of ' + str(acceptvals))

	# Is there a Discord guild in between us, did we get a client,
	# or is the request anything at all?
	if (not guild and objtype != 'guild') or \
	(not client and objtype == 'guild') or \
	not request:
		return None

	# Is this a mention, or an emoji? If so, extract the ID from it
	if request.startswith('<') and request.endswith('>'):
		if (objtype == 'member' and request[1:3] == '@!') or \
		(objtype == 'role' and request[1:3] == '@&'):
			request = int(request[3:-1])
		elif (objtype == 'member' and request[1] == '@') or \
		(objtype == 'channel' and request[1] == '#'):
			request = int(request[2:-1])
		elif objtype == 'emoji' and request[1] == request[-20] == ':':
			request = int(request[-19:-1])
	elif request.isdigit():
		request = int(request)

	if isinstance(request, int):
		# Now get the object from the ID
		tgt = guild.get_member(request) if objtype == 'member' else \
		client.get_guild(request) if objtype == 'guild' else \
		guild.get_channel(request) if objtype == 'channel' else \
		discord.utils.find(
			lambda r: r.id == request,
			guild.roles,
		) if objtype == 'role' else \
		discord.utils.find(
			lambda e: e.id == request,
			guild.emojis,
		) if objtype == 'emoji' else None
	else:
		tgt = None

	if not tgt:
		# Not an ID

		if objtype == 'member':
			tgt = guild.get_member_named(request) if objtype == 'member' else tgt

			if not tgt:
				# Not found by guild.get_member_named()

				# Everything else fails? Then try searching.
				# Nicknames have priority, then usernames.
				# Maybe we're entering just a discriminator, match those as well.
				nickmatched = False
				usermatched = None
				nickfound = None
				userfound = None
				discmatched = None
				for mem in guild.members:
					if mem.nick and mem.nick.lower() == request.lower():
						tgt = mem
						nickmatched = True
						break
					if mem.name.lower() == request.lower():
						usermatched = mem
						break
					if mem.nick and \
					mem.nick.lower().find(request.lower()) != -1:
						nickfound = mem
						break
					if mem.name.lower().find(request.lower()) != -1:
						userfound = mem
						break
					if mem.discriminator == request or \
					(request.startswith('#') and \
					mem.discriminator == request[1:]):
						discmatched = mem
						break
				tgt = nickmatched if nickmatched else \
				usermatched if usermatched else \
				nickfound if nickfound else \
				userfound if userfound else \
				discmatched

		else:
			namematched = None
			namefound = None

			searchthru = client.guilds if objtype == 'guild' else \
			guild.channels if objtype == 'channel' else \
			guild.roles if objtype == 'role' else \
			guild.emojis if objtype == 'emoji' else None
			for i in searchthru:
				if i.name is None:
					continue
				if i.name.lower() == request.lower():
					namematched = i
					break
				if i.name.lower().find(request.lower()) != -1:
					namefound = i
					break
			tgt = namematched if namematched else namefound

	return tgt

def bracketlevels(condstring):
	"""Changes input string so that brackets have an indication of what level they are on.

	Changes (a(bc)) to (<0>a(<1>bc)<1>)<0>

	Also returns what the innermost level is, to be used later to determine where to start.
	"""
	bracketslevel = 0
	bracketshighscore = -1
	output = ''

	for c in condstring:
		if c == '(':
			output += '(<{}>'.format(bracketslevel)
			if bracketslevel > bracketshighscore:
				bracketshighscore = bracketslevel
			bracketslevel += 1
		elif c == ')':
			bracketslevel -= 1
			output += ')<{}>'.format(bracketslevel)
		else:
			output += c

	if bracketslevel != 0:
		raise ValueError('Invalid conditional string; mismatched brackets')

	return output, bracketshighscore

def wrapbackticks(string, character=u'​'):
	"""escapes backticks for use in message output to discord
	its a fucking glorified string.replace() command with some error handling
	any string this is used on should be placed in either one of the following:
	double backticks (like ``this``)
	or code blocks (like ```this```)
	"""
	try:
		return string.replace('`', u'{character}`{character}'.format(character=character))
	except AttributeError:
		return string

def safefilename(string):
	"""Makes a string safe and convenient for use in filenames.

	This converts the input string to alphanumeric with hyphens and underscores.
	"""
	def safechar(c):
		if c.isalnum() or c == '-':
			return c
		return '_'

	return ''.join(safechar(c) for c in string).strip('_')

async def id_lookup(uid):
	"""Return a discord.Member/discord.User object with a given ID. If the ID is not a user ID
	and doesn't exist on Discord, return None.

	Note that it is inconsistent whether or not the object returned is a discord.Member or a
	discord.User.

	Note that if a discord.Member object is returned guild-specific attributes will be
	inconsistent. The only attributes that should be used are:
	- name
	- id
	- discriminator
	- avatar/avatar_url/avatar_url_as
	- bot
	- default_avatar/default_avatar_url
	- mention/mentioned_in
	- created_at
	"""

	# Look through all members the bot can see for any matching the ID
	member = wrapper.client.get_user(uid)

	if member is None:
		# Look up the ID by banning it
		opguild = wrapper.client.get_guild(op_ids.ids['opguild'])
		try:
			await opguild.ban(uid, delete_message_days=0)
		except discord.errors.HTTPException:
			pass
		else:
			bans = await opguild.bans()
			for x in bans:
				if x.id == uid:
					member = x
					break
			if member is not None:
				try:
					await opguild.unban(member)
				except discord.errors.HTTPException:
					pass

	return member

def isprivatemessage(guild):
	# this is a function because so in the future more checks for if its a private message can
	# ezily be added
	return not bool(guild)

def helplist(cats, guild, onlycat=None):
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
			if cat['cat_slug'] == 'guild':
				helpcommands = customcommands.list_commands_help(guild)
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
	for cat in bot.cmds:
		for cmd in cat['commands']:
			if cmd['name'] == com:
				return True
	return False


def rolelist(roles):
	rlist = []
	for role in roles:
		rlist.append(role.id)

	return rlist

def updaterolecache(member, guildid=None):
	if guildid is None:
		guildid = member.guild.id
	if guildid not in events.memberroles:
		events.memberroles[guildid] = {}
	events.memberroles[guildid][member.id] = rolelist(member.roles)

def removerolecache(memberid, guildid):
	try:
		del events.memberroles[guildid][memberid]
	except KeyError:
		return False
	return True

def rolecachesave():
	with open('memberroles.json', 'w') as outfile:
		json.dump(events.memberroles, outfile)

	return True

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

def getspecialchannel(guild):
	theconfig = config.get_s('specialchannel', guild.id)
	if theconfig != '0':
		return wrapper.client.get_channel(id=theconfig)
	return guild.default_channel

def getspecialchannel_reply(message):
	if message.guild is None:
		return message.channel
	specialchannel = getspecialchannel(message.guild)
	if specialchannel == message.guild.default_channel:
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

def parsereltime(inputstr, relative=False, now=None):
	# if relative is true then we only get the amount of seconds from now, if false we get a unix timestamp.
	if now is None:
		now = int(time.time())
	total = 0

	m = re.search("^((?P<d>[0-9]+)d)?((?P<h>[0-9]+)h)?((?P<m>[0-9]+)m)?((?P<s>[0-9]+)s)?$", inputstr)

	if m is None:
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
	return now+total

async def handleExpiryTimer():
	"""Sets the timer correctly to the first event
	If time is in the past, call autoExpiry immediately
	Can be called on startup, when changing something, or at the end of autoExpiry
	"""
	# Cancel the existing timer, if it's running
	if bot.exptimer != None:
		bot.exptimer.cancel()
		bot.exptimer = None  # Because there's no Timer.isCanceled()

	entriesleft = False

	for guildid in events.rolexpires:  # Merge with next for maybe
		if events.rolexpires[guildid]:
			entriesleft = True
			break

	if not entriesleft:
		# We're finished
		logging.info('Did not set expiry timer because there\'s no expiry entry left')
		return

	timelowscore = 9999999999

	for guildid in events.rolexpires:
		for userid in events.rolexpires[guildid]:
			if events.rolexpires[guildid][userid]['time'] < timelowscore:
				timelowscore = events.rolexpires[guildid][userid]['time']

	if timelowscore <= int(time.time()):
		logging.info('Immediately calling autoExpiry() because we’re overdue in resetting someone’s roles')
		await autoExpiry()
	else:
		timertime = (timelowscore - time.time()) + 2  # 2 seconds extra, just to make sure we're not getting problems due to being one second off
		exptimer = threading.Timer(timertime, callAutoExpiry)
		exptimer.start()
		logging.info('Set expiry timer for %s seconds', timertime)

def callAutoExpiry():
	asyncio.run_coroutine_threadsafe(autoExpiry(), wrapper.client.loop)

async def autoExpiry():
	"""Called by timers
	Actually resets roles
	Calls back handleTimer to set the next timer
	"""
	now = int(time.time())

	# So apparently someone needs to be unbanned?
	for guildid in events.rolexpires:
		content = ''
		successfulresets = []

		cguild = discord.utils.get(wrapper.client.guilds, id=guildid)
		for userid in events.rolexpires[guildid]:
			if events.rolexpires[guildid][userid]['time'] <= now:
				try:
					await removeRestrictiveRoles(
						cguild.get_member(userid),
						cguild,
					)
					content += '\nRoles for <@!{}> reset.'.format(userid)
				except (AttributeError, TypeError):
					# Look if they are in the role cache, and reset it there instead.
					if removerolecache(userid, guildid):
						content += '\n<@!{}> was supposed to have their roles reset now, they aren’t on the server, but they’ve successfully been removed from the role cache.'.format(userid)
						rolecachesave()
					else:
						content += '\n<@!{}> was supposed to have their roles reset now, but they can be found neither on the server nor in the role cache!'.format(userid)

				# Shorten the following thing so we don't have to keep typing it.
				thisexpiry = events.rolexpires[guildid][userid]
				if thisexpiry['msgedit_message'] != '0':
					await editexpirymessage(cguild, thisexpiry)
				if thisexpiry['msgpost_channel'] != '0':
					# We want to announce it with a new message!
					await discord.utils.get(
						cguild.channels,
						id=thisexpiry['msgpost_channel'],
					).send(thisexpiry['msgpost_content'])

				successfulresets.append(userid)
		for userid in successfulresets:
			removeexpiryentry(guildid, userid)

		if successfulresets:
			if not content:
				content = '\n(never mind, nobody has been found!)'

			content = '**Auto expiry:**' + content

			await getspecialchannel(cguild).send(content)

	rolexpiresave()

	await handleExpiryTimer()

async def removeRestrictiveRoles(member, guild):
	await givetakeroles(
		member,
		guild,
		config.get_s(
			'defaultbotroles'
			if member.bot
			else 'defaultroles',
			guild.id,
		),
		config.get_s('restrictiveroles', guild.id),
	)

async def givetakeroles(member, guild, giveids, takeids):
	badroles = [] # All the roles that are potentially deleted
	removingtheseroles = [] # Roles that the user has which will be deleted
	addingtheseroles = [] # Roles that the user doesn't have which will be added
	otherroles = [] # Other roles the user has

	for rid in takeids:
		badroles.append(discord.utils.get(guild.roles, id=rid))
	for rid in giveids:
		addingtheseroles.append(discord.utils.get(guild.roles, id=rid))
	for role in member.roles:
		if role in badroles:
			# This member has that bad role, we need to get rid of it!
			removingtheseroles.append(role)
			continue
		if role in addingtheseroles:
			# Oh, we already have that one
			addingtheseroles.remove(role)
		if not role.is_default():
			# If we're going to need to replace roles, keep these the same!
			otherroles.append(role)
	if not addingtheseroles and not removingtheseroles:
		# Well what are we doing here?
		return
	if addingtheseroles and removingtheseroles:
		# Replace - luckily the union of these is this simple!
		await member.edit(roles=addingtheseroles + otherroles)
	elif addingtheseroles:
		# Only adding
		await member.add_roles(*addingtheseroles)
	else:
		# Only removing
		await member.remove_roles(*removingtheseroles)

async def editexpirymessage(cguild, thisexpiry):
	# We want to edit a message to reflect the ban!
	getmessage = await discord.utils.get(
		cguild.channels,
		id=thisexpiry['msgedit_channel']
	).get_message(thisexpiry['msgedit_message'])
	if thisexpiry['msgedit_newcontent'] == '':
		await getmessage.delete()
	else:
		await getmessage.edit(content=thisexpiry['msgedit_newcontent'])

def addexpiryentry(guildid, memberid, expirytime,
e_channel='0', e_message='0', e_newcontent='',
p_channel='0', p_content=''):
	if guildid not in events.rolexpires:
		events.rolexpires[guildid] = {}

	events.rolexpires[guildid][memberid] = {
		'time': expirytime,
		'msgedit_channel': e_channel,
		'msgedit_message': e_message,
		'msgedit_newcontent': e_newcontent,
		'msgpost_channel': p_channel,
		'msgpost_content': p_content,
	}

def removeexpiryentry(guildid, memberid):
	if guildid not in events.rolexpires:
		return False

	if memberid not in events.rolexpires[guildid]:
		return False

	del events.rolexpires[guildid][memberid]
	return True

def getearliestexpiry(guildid):  # Returns: [userid, entry]
	if guildid not in events.rolexpires or not events.rolexpires[guildid]:
		return None

	timelowscore = 9999999999
	earliestuserid = '0'
	earliestexpiry = None  # Entry

	for userid in events.rolexpires[guildid]:
		if events.rolexpires[guildid][userid]['time'] < timelowscore:
			timelowscore = events.rolexpires[guildid][userid]['time']
			earliestuserid = userid
			earliestexpiry = events.rolexpires[guildid][userid]

	return [earliestuserid, earliestexpiry]

async def fetch(url):
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			return await response.read()

def logfailedcommand(command, arguments, message):
	if arguments is None:
		arguments = ''
	logging.info(
		'%s %s attempted by %s#%s (uuid %s) at %s utc but failed',
		command, arguments,
		message.author.name, message.author.discriminator, message.author.id,
		message.created_at,
	)

def logcommand(command, arguments, message):
	if arguments is None:
		arguments = ''
	logging.info(
		'%s %s called by %s#%s (uuid %s) at %s utc',
		command, arguments,
		message.author.name, message.author.discriminator, message.author.id,
		message.created_at,
	)

def infourl(query):
	return 'https://tolp2.nl/showdiscordinfo.php?' + query

def logdisabled(key, guild):
	checks = [key, key.split('_')[0] + '_*', '*']

	if any(x in config.get_s('disabledlogs', guild.id) for x in checks):
		return True
	if any(x in config.get_s('enabledlogs', guild.id) for x in checks):
		return False
	return True

def respondtorule(rule):
	if int(rule) == 37:
		return 'Funny and original, nothing to see here.'
	return 'Wow, you’re the FIRST one to come up with that. I wish I could be as funny as you, I dunno how I’m ever gonna top "rule {}", though. That shit is genius.'.format(rule)

async def newmemberroles(member, specialchannel, bypassjoinchannel):
	if config.get_s('rolecachemode', member.guild.id) == 1 and checks.is_bot(member):
		# Give them the bot roles!
		addingtheseroles = []
		for rid in config.get_s('defaultbotroles', member.guild.id):
			addingtheseroles.append(
				discord.utils.get(member.guild.roles, id=rid)
			)
		await member.add_roles(*addingtheseroles) # bot role
		return

	if not bypassjoinchannel and \
	config.get_s('rolecachemode', member.guild.id) != 0 and \
	member.guild.id in events.memberroles:
		# Are they in our database of members which had roles before?
		if member.id in events.memberroles[member.guild.id]:
			addingtheseroles = []
			# They're found in the database! Give them the groups they should have
			for rid in events.memberroles[member.guild.id][member.id]:
				addingrole = discord.utils.get(member.guild.roles, id=rid)
				if addingrole.is_default():
					continue
				addingtheseroles.append(addingrole)
			await member.add_roles(*addingtheseroles)
			content = '<@!{id}> ({id}) found in the role cache\n'.format(id=member.id)
			value = '_{} role'.format(str(len(addingtheseroles)))
			value += 's:' if len(addingtheseroles) != 1 else ':'
			value += listroles(addingtheseroles) + '_'
			content += 'Given them back their roles:\n' + value
			await specialchannel.send(content)
	elif config.get_s('rolecachemode', member.guild.id) == 1 or bypassjoinchannel:
		# Not found, so just give them the default roles
		addingtheseroles = []
		for rid in config.get_s('defaultroles', member.guild.id):
			addingtheseroles.append(
				discord.utils.get(member.guild.roles, id=rid)
			)
		await member.add_roles(*addingtheseroles)

def convert_id_keys_to_int(dictionary):
	result = {}

	for key, value in dictionary.items():
		if isinstance(key, str) and key.isdigit():
			key = int(key)
		if isinstance(value, dict):
			value = convert_id_keys_to_int(value)
		result.update({key: value})

	return result
