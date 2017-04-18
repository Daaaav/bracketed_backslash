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
