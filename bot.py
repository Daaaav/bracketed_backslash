#!/usr/bin/python3.5
# encoding=utf-8

# Fun side effect: main.py has a reference to bot.customcommands
import customcommands  # pylint: disable=unused-import
import datetime
import importlib
import inspect
import json
import logging
import math
import os
import pathlib
import time

import discord

import checks
import config
import events
import utils
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

for dir_path in (cachelocation, attachcache, embedcache):
	pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)

hangmaninvoker = '-'

os.environ['TZ'] = 'UTC'
time.tzset()

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

def calculate_msg_start(message):
	# Removes the need for globalling msg_start every time
	indisp = (
		(
			'``{}``**`…`**'
		).format(
			utils.wrapbackticks(message.content[:100]).replace('discord.gg', 'discord\u200b.gg')
		)
	) if len(message.content) > 100 else (
		'``{}``'.format(utils.wrapbackticks(message.content))
		.replace('\n', '``**`\\n`**``​')
		.replace('discord.gg', 'discord\u200b.gg')
	)
	if indisp[-12:] == '``**`\\n`**``​':
		indisp += '``'

	if isinstance(message.channel, discord.abc.PrivateChannel):
		invokesymbol = '@'
	elif checks.is_mod(message.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'

	msg_start = (
		'**`>`**``{name}``**`{invsym}`**{indisp}\n'
	).format(
		name=utils.wrapbackticks(message.author.name),
		invsym=invokesymbol,
		indisp=indisp,
	)

	return msg_start

async def reply(messageobject, message=None, *, emb=None):
	# Removes the need for adding msg_start manually every time
	msg_start = calculate_msg_start(messageobject)
	if message is None:
		message = ''
	if len(msg_start + message) >= 2000:
		# We can at least try in a totally not failsafe and kinda ugly way
		content = msg_start + message
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
			await messageobject.channel.send(msg_start + message, embed=emb)
		else:
			await messageobject.channel.send(msg_start + message)
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

async def sync_invite_cache(client, cache):
	logging.info('%s: Syncing invite cache', datetime.datetime.now())

	for guild in client.guilds:
		if guild.id not in cache:
			cache[guild.id] = []

		try:
			guild_invites = await guild.invites()
		except discord.Forbidden:
			guild_invites = []

		audit_entries = guild.audit_logs(action=discord.AuditLogAction.invite_create)
		audit_invites = []
		try:
			async for entry in audit_entries:
				audit_invites.append(entry.target)
		except discord.Forbidden:
			pass

		all_invites = []
		all_invites.extend(guild_invites)
		# We filter() out any audit invites we already have, or it will mess up the number
		# of uses because audit invites aren't real invites
		all_invites.extend(
			filter(
				lambda i: i not in guild_invites,  # pylint: disable=cell-var-from-loop
				audit_invites,
			),
		)

		# Let's cache the invites
		# We can't simply use list.extend because it won't record the updated number of uses
		# Stupid piece of shit
		for invite in all_invites:
			cached_invite = discord.utils.find(
				lambda i: i.code == invite.code,  # pylint: disable=cell-var-from-loop
				cache[guild.id],
			)
			if cached_invite is not None:
				cached_invite.uses = invite.uses

		# Remove duplicates
		cache[guild.id] = list(set(cache[guild.id]))
