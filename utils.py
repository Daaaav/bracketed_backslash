#!/usr/bin/python3.5
# encoding=utf-8

import datetime
import time

import discord

import __main__
import op_ids

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
		summary += ' \N{BUST IN SILHOUETTE}' + uid
	if mid:
		summary += ' \N{SPEECH BALLOON}' + mid
	if cid:
		summary += ' \N{TELEVISION}' + cid
	if rid:
		summary += ' \N{KEY}' + rid
	if summary.startswith(' '):
		summary = summary[1:]
	return summary

async def handle_minute_message_edits(msg, schan):
	if not msg.id in __main__.minutemessageedits:
		__main__.minutemessageedits[msg.id] = [int(time.time())]
	else:
		edittime = int(time.time())
		while True:
			if edittime in __main__.minutemessageedits[msg.id]:
				edittime += .1
			else:
				__main__.minutemessageedits[msg.id].append(edittime)
				break
		if len(__main__.minutemessageedits[msg.id]) >= 5:
			await handle_delete_overedited_message(msg, schan)

		# While we're at it, also clean up other messages.

		# Copy because we may be removing elements from here
		for k in list(__main__.minutemessageedits):
			if k != msg.id:
				for i in list(__main__.minutemessageedits[k]):
					if i < (int(time.time())-30):
						__main__.minutemessageedits[k].remove(i)
				if len(__main__.minutemessageedits[k]) == 0:
					del __main__.minutemessageedits[k]

async def handle_delete_overedited_message(msg, schan):
	# Copy the list, we may be removing elements from here
	for i in list(__main__.minutemessageedits[msg.id]):
		if i < (int(time.time())-30):
			__main__.minutemessageedits[msg.id].remove(i)

	if len(__main__.minutemessageedits[msg.id]) >= 5:
		# Ok, that's enough editing.
		try:
			await __main__.client.delete_message(msg)
			__main__.messages_deleted_by_bot.append(msg)
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
		await __main__.client.send_message(schan, embed=em)

		# Also actually reply
		await __main__.client.send_message(
			msg.channel,
			(
				'{0.author.mention}. Were you going to stop editing that message?'
			).format(msg),
		)

def match_input(objtype, request, *, server=None, client=None):
	"""Return a member/server/channel/role/emoji object given an input which could be anything
	that identifies that object. If it can't be found, return None.

	objtype: A string that specifies the type of object to search for. Can be either 'member',
	'server', 'channel', 'role', or 'emoji'.

	request: A string that will be tried to be matched to.

	server (optional): A discord.Server object, which is the scope of where
	members/channels/roles/emojis will be searched. Defaults to None.

	client (optional): A discord.Client object, which is the scope of where servers will be
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
	acceptvals = ('member', 'server', 'channel', 'role', 'emoji')
	if objtype not in acceptvals:
		raise ValueError('objtype has to be one of ' + str(acceptvals))

	# Is there a Discord server in between us, did we get a client,
	# or is the request anything at all?
	if (not server and objtype != 'server') or \
	(not client and objtype == 'server') or \
	not request:
		return None

	# Is this a mention, or an emoji? If so, extract the ID from it
	if request.startswith('<') and request.endswith('>'):
		if (objtype == 'member' and request[1:3] == '@!') or \
		(objtype == 'role' and request[1:3] == '@&'):
			request = request[3:-1]
		elif (objtype == 'member' and request[1] == '@') or \
		(objtype == 'channel' and request[1] == '#'):
			request = request[2:-1]
		elif objtype == 'emoji' and request[1] == request[-20] == ':':
			request = request[-19:-1]

	# Now get the object from the ID
	tgt = server.get_member(request) if objtype == 'member' else \
	client.get_server(request) if objtype == 'server' else \
	server.get_channel(request) if objtype == 'channel' else \
	discord.utils.find(lambda r: r.id == request, server.roles) if objtype == 'role' else \
	discord.utils.find(lambda e: e.id == request, server.emojis) if objtype == 'emoji' else None

	if not tgt:
		# Not an ID

		if objtype == 'member':
			tgt = server.get_member_named(request) if objtype == 'member' else tgt

			if not tgt:
				# Not found by server.get_member_named()

				# Everything else fails? Then try searching.
				# Nicknames have priority, then usernames.
				# Maybe we're entering just a discriminator, match those as well.
				nickmatched = False
				usermatched = None
				nickfound = None
				userfound = None
				discmatched = None
				for mem in server.members:
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

			searchthru = client.servers if objtype == 'server' else \
			server.channels if objtype == 'channel' else \
			server.roles if objtype == 'role' else \
			server.emojis if objtype == 'emoji' else None
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
		else:
			return '_'

	return ''.join(safechar(c) for c in string).strip('_')

async def id_lookup(uid):
	"""Return a discord.Member/discord.User object with a given ID. If the ID is not a user ID
	and doesn't exist on Discord, return None.

	Note that it is inconsistent whether or not the object returned is a discord.Member or a
	discord.User.

	Note that if a discord.Member object is returned server-specific attributes will be
	inconsistent. The only attributes that should be used are:
	- name
	- id
	- discriminator
	- avatar/avatar_url
	- bot
	- default_avatar/default_avatar_url
	- mention
	- created_at
	"""
	member = None

	for x in __main__.client.get_all_members():
		# Look through all members the bot can see for any matching the ID
		if x.id == uid:
			member = x
			break

	if member is None:
		# Look up the ID by banning it
		opserver = __main__.client.get_server(op_ids.ids['opserver'])
		try:
			await __main__.client.http.ban(uid, opserver.id, 0)
		except discord.errors.HTTPException:
			pass
		else:
			bans = await __main__.client.get_bans(opserver)
			for x in bans:
				if x.id == uid:
					member = x
					break
			if member is not None:
				try:
					await __main__.client.unban(opserver, member)
				except discord.errors.HTTPException:
					pass

	return member
