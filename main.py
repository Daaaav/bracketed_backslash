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
import time
from threading import Timer
import traceback

import discord

import config
import col
import emb
import events
import images
import op_ids
import utils

op_ids.load()
config.load()

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
async def on_voice_state_update(old, new):
	if old.voice.voice_channel == new.voice.voice_channel:
		return

	vtcs = [
		new.server.get_channel(i) for i in config.get_s(
			'voicechat_channel_text', new.server.id,
		)
	]
	vvcs = [
		new.server.get_channel(i) for i in config.get_s(
			'voicechat_channel_voice', new.server.id,
		)
	]

	for vtc, vvc in zip(vtcs, vvcs):
		if new.voice.voice_channel and new.voice.voice_channel == vvc:
			# Joined the voice channel
			ow = discord.PermissionOverwrite(read_messages=True)
			await client.edit_channel_permissions(vtc, new, ow)
			break

		if old.voice.voice_channel and old.voice.voice_channel == vvc:
			# Left the voice channel
			await client.delete_channel_permissions(vtc, new)
			break

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
	except UnicodeDecodeError:
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
		colour=events.opserver.me.colour,
	)
	em.set_image(url=serv.icon_url)
	await client.send_message(events.opserver_botservers, embed=em)

@client.event
async def on_server_remove(serv):
	em = discord.Embed(
		title='BOT REMOVED FROM SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(serv.name),
			id=serv.id,
		),
		colour=events.opserver.me.colour,
	)
	em.set_image(url=serv.icon_url)
	await client.send_message(events.opserver_botservers, embed=em)

# Read as: dump code from file ... here
# So that we can have our existing functions without going across separate modules, and without
# making main.py far too long.
exec(compile(open("functions.py", "rb").read(), "functions.py", 'exec'))
exec(compile(open("commands.py", "rb").read(), "commands.py", 'exec'))

client.run(token)
