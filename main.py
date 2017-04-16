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
import datetime
import inspect
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
		embed.add_field(name='\u200b', value='\u200b')
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
