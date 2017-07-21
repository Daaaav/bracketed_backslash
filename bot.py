#!/usr/bin/python3.5
# encoding=utf-8

import asyncio
import importlib
import inspect
import json
import logging
import math
import os
import time

import discord

import config
import emb
import events
import wrapper

config.load()

version = '1.0'

def load_events():
	global events
	events = importlib.reload(events)
	for i in inspect.getmembers(events, inspect.isfunction):
		wrapper.client.event(i[1])

load_events()



cachelocation = './.cache'
attachcache = cachelocation + '/' + 'attach' # define attachment caching location
embedcache = cachelocation + '/' + 'embed'

invoker = '\\' # command invoker
altinvoker = 'ok glass, ' # alt command invoker
hangmaninvoker = '-'

os.environ['TZ'] = 'UTC'
time.tzset()

boottime = time.strftime(config.get_s('timeformat'))
boottimeunix = time.time()

with open('opguildid.conf', 'r') as f:
	opguildid = int(f.readline(18).split('\n')[0])

minutemessageedits = {}

messages_deleted_by_bot = []
deleted_messages = []

# Holds IDs because that's the only thing that's needed here, saves a lot of memory
# and has better performance, because the cache can get yuge
owncache = []

votemutes = {} # userid -> dict with `starttime`, `proponents`*, `opponents`*

exptimer = None  # threading.Timer object

t = {}
cmds = []
permissionlabels = []
funnynumbers = []
help_info_string = ''

def loadstrings():
	stringsf = open('strings.json', 'r')
	stringsfr = stringsf.read()
	strings = json.loads(stringsfr)
	# TODO: noone better not put this on a cs grad thread
	global t, cmds, permissionlabels, funnynumbers, help_info_string
	t = strings['t']
	cmds = strings['cmds']
	permissionlabels = strings['permissionlabels']
	funnynumbers = strings['funnynumbers']
	help_info_string = strings['help_info_string']

loadstrings()

modificationtimes = [os.path.getmtime(x) for x in os.listdir() if x.endswith('.py')]
modificationtimecache = time.strftime(config.get_s('timeformat'), time.gmtime(max(modificationtimes)))

maineventloop = asyncio.get_event_loop()

async def reply(messageobject, message=None, emb=None):
	# Removes the need for adding msg_start manually every time
	if message is None:
		message = ''
	if len(events.msg_start + message) >= 2000:
		# We can at least try in a totally not failsafe and kinda ugly way
		content = events.msg_start + message
		contentlines = content.split('\n')
		cut = math.floor(len(contentlines)/2)
		await messageobject.channel.send('\n'.join(contentlines[:cut]))
		if emb != None:
			await messageobject.channel.send('\n'.join(contentlines[cut:]), embed=emb)
		else:
			await messageobject.channel.send('\n'.join(contentlines[cut:]))
		return
	try:
		if emb != None:
			await messageobject.channel.send(events.msg_start + message, embed=emb)
		else:
			await messageobject.channel.send(events.msg_start + message)
	except(discord.errors.HTTPException, discord.errors.Forbidden) as e:
		if isinstance(messageobject.channel, discord.abc.PrivateChannel):
			guildinfo = '\t(direct message)\n'
		else:
			guildinfo = (
				'\tName: {0.name}\n'
				'\tID: {0.id}\n'
			).format(messageobject.guild)
		if emb is None:
			dispemb = '\t(none)\n'
		else:
			dispemb = str(emb.to_dict())
		logging.info(
			'A message reply() was rejected, with exception %s\n'
			'The server it was attemped to be sent to is:\n'
			'%s\n'
			'The channel it was attempted to be sent to is:\n'
			'\tType: %s\n'
			'\tName: %s\n'
			'\tID: %s\n'
			'\n'
			'The content of the rejected message is:\n'
			'\t%s\n'
			'The rich embed of the rejected message is:\n'
			'\t%s\n',
			type(e).__name__,
			guildinfo,
			(
				'Text'
				if isinstance(messageobject.channel, discord.TextChannel)
				else 'Voice'
				if isinstance(messageobject.channel, discord.VoiceChannel)
				else 'Unknown'
			),
			messageobject.channel,
			messageobject.id,
			events.msg_start + message,
			dispemb,
		)
		raise

async def replyattach(messageobject, filetoattach, fname, message=''):
	# Don't bother with handling >2000 character messages just yet
	await messageobject.channel.send(
		events.msg_start + message,
		file=discord.File(filetoattach, fname),
	)
