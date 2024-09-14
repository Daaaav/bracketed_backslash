# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
import contextlib
import datetime
import io
import inspect
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from typing import Optional

import discord

import bot
import checks
import col
import config
import customcommands
import dispatch
import emb
import events
import images
import op_ids
import reaction_roles
import starboard
import utils
import wrapper

op_ids.load()

# This file contains all the bot commands as functions.

commands = {}

def shadow(auth=None, aliases=None, guildonly=False, tntgbguildonly=False, joinchannelonly=False):
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
		commands[name] = [func, auth, aliases, guildonly, tntgbguildonly, joinchannelonly]
		return func
	return living_shadow

@shadow()
async def _help(client, message, **kwargs):
	content = (bot.help_info_string + utils.helplist(bot.cmds, message.guild))

	# General
	if kwargs['arguments'] is None:
		pass
	else:
		matched = False
		for cat in (bot.cmds):
			if kwargs['arguments'] == cat['cat_slug']:
				content = utils.helplist(
					bot.cmds,
					message.guild,
					kwargs['arguments'],
				)
				matched = True
				break

			# Maybe have a nested try-except KeyError
			# instead of looping through every command
			for cmd in cat['commands']:
				if kwargs['arguments'] == cmd['name']:
					try:
						content = '`\{}` – {}'.format(
							cmd['name'], cmd['extrafull']
						)
					except KeyError:
						content = '`\{}` – {}\n{}'.format(
							cmd['name'], cmd['short'], cmd['extra']
						)
					matched = True
					break
			for cmd in customcommands.list_commands(message.guild):
				if kwargs['arguments'] == cmd:
					content = '[Custom command, more info NYI]'
					matched = True
					break
			if matched:
				break

		if not matched:
			content = (
				'Invalid arguments passed, or the command is not in the help list. '
				'Input `\help` for a list of valid commands to pass as arguments.'
			)
	embed = discord.Embed(description=content, colour=col.r_success)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_host)
async def restart(client, message, **kwargs):
	embed = emb.success('Restarting.', True)
	embed.add_field(name='Uptime', value=utils.reltime(wrapper.boottimeunix, True))
	embed.add_field(name='Messages in Cache', value=str(len(client.cached_messages)))
	utils.logcommand(kwargs['command'], kwargs['arguments'], message)
	await bot.reply(message, emb=embed)
	await client.close()
	__main__ = __import__('__main__')
	__main__.exit_code = 8

@shadow(auth=checks.is_host)
async def kill(client, message, **kwargs):
	embed = emb.success('Killing.', True)
	embed.add_field(name='Uptime', value=utils.reltime(wrapper.boottimeunix, True))
	utils.logcommand(kwargs['command'], kwargs['arguments'], message)
	await bot.reply(message, emb=embed)
	await client.close()
	__main__ = __import__('__main__')
	__main__.exit_code = 4

@shadow(auth=checks.is_operator)
async def errors(client, message, **kwargs):
	n = 10
	if kwargs['arguments'] is not None:
		try:
			n = int(kwargs['arguments'])
		except ValueError:
			embed = emb.error('Please specify a valid number.')
			await bot.reply(message, emb=embed)
			return

	# wrapper.runtime_exceptions is list of (datetime, event_name, (exc_type, exception, traceback))
	n_in_24h = 0
	for i in range(len(wrapper.runtime_exceptions)-1, -1, -1):
		if wrapper.runtime_exceptions[i][0] < (
			discord.utils.utcnow() - datetime.timedelta(hours=24)
		):
			break
		n_in_24h += 1

	content = '{} exception(s) in the past 24 hours. Last exceptions, max {}, going down: ```\n'.format(
		n_in_24h, n
	)

	for exc in wrapper.runtime_exceptions[-n:]:
		# Time, event and exception type
		content += '[{}] {}: {}.{}\n'.format(
			exc[0], exc[1], exc[2][0].__module__, exc[2][0].__qualname__
		)

	content += '\n```'
	await bot.reply(message, content)

@shadow(auth=checks.is_operator)
async def _config(client, message, **kwargs):
	if message.guild and \
	message.guild.id == op_ids.ids['opguild'] and \
	not checks.is_host(message.author):
		embed = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
		return
	if kwargs['arguments'] is None:
		content = (
			'You can use the following options:\n'
			'`\config list [CAT]`\n'
			'`\config reload`\n'
			'`\config get <key>`\n'
			'`\config set <key> <value>` (not for arrays or dics)\n'
			'`\config insert <key> [indice] <value>` (only for arrays and dics)\n'
			'`\config remove <key> <value/indice>` (only for arrays and dics)\n'
			'`\config detach <key>`\n'
			'`\config reattach <key>`\n'
			'`\config default <key>`\n'
		)
		await bot.reply(message, content)
		return
	elif kwargs['arguments'] == 'reload':
		config.load()
		utils.logcommand(kwargs['command'], kwargs['arguments'], message)
		embed = emb.success('Reloaded config.')
		await bot.reply(message, emb=embed)
		return
	elif kwargs['arguments'] == 'list':
		content = 'All option categories:\n'
		for cat in config.configcats:
			content += '    `{}`: {}\n'.format(cat, config.configcats[cat]['name'])
		content += 'Use `\config list <CAT>` to list all settings under a given category.'
		await bot.reply(message, content)
		return


	splitargs = kwargs['arguments'].split(' ', 2)

	editingmaster = True

	if len(splitargs) == 1:
		embed = emb.error('Too few arguments.')
		await bot.reply(message, emb=embed)
		return

	if splitargs[0] == 'list':
		if splitargs[1] not in config.configcats:
			embed = emb.error(
				(
					'That category does not exist. '
					'Try `\\config list` for a list of categories.'
				)
			)
			await bot.reply(message, emb=embed)
			return

		content = '**{}** options:```css'.format(config.configcats[splitargs[1]]['name'])
		for c in config.s:
			if not config.exists(c):
				continue
			if config.get_cat(c) != splitargs[1]:
				continue
			try:
				content += '\n{} [{}] = {}'.format(
					c,
					config.get_type(c) + (
						'*' if config.is_array(c) else
						'&' if config.is_dic(c) else
						''),
					config.get_s(c, message.guild.id)
					if not (config.is_array(c) or config.is_dic(c))
					else '[{}]'.format(len(config.get_s(c, message.guild.id))),
				)
				if config.is_detached(c, message.guild.id):
					content += ' [local value]'
			except AttributeError:
				content += '\n{} [{}] = {}'.format(
					c,
					config.get_type(c) + (
						'*' if config.is_array(c) else
						'&' if config.is_dic(c) else
						''),
					(config.get_s(c)
					if not (config.is_array(c) or config.is_dic(c))
					else '[{}]'.format(len(config.get_s(c)))),
				)
		content += '\n```'
		await bot.reply(message, content)
		return

	elif splitargs[0] == 'set':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await bot.reply(message, emb=embed)
			return
		if config.is_array(splitargs[1]):
			embed = emb.error('That doesn’t work for an array')
			await bot.reply(message, emb=embed)
			return
		if config.is_dic(splitargs[1]):
			embed = emb.error('That doesn’t work for a dic.')
			await bot.reply(message, emb=embed)
			return
		if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
			embed = emb.error('Integer expected')
			await bot.reply(message, emb=embed)
			return
		try:
			try:
				config.set_s(splitargs[1], splitargs[2], message.guild.id)
				editingmaster = not config.is_detached(
					splitargs[1], message.guild.id
				)
			except AttributeError:
				config.set_s(splitargs[1], splitargs[2])
		except ValueError:
			embed = emb.error('Invalid value specified')
			await bot.reply(message, emb=embed)
			return
		config.saveconfig()
		utils.logcommand(kwargs['command'], kwargs['arguments'], message)
		embed = emb.success('Set `{}` to `{}`{}'.format(
				splitargs[1], utils.wrapbackticks(
					config.input_to_type_key(splitargs[2], splitargs[1])
				),
				bot.t['editingmasterval'] if editingmaster else ''
			)
		)
		await bot.reply(message, emb=embed)
	elif splitargs[0] == 'get':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await bot.reply(message, emb=embed)
			return
		try:
			content = (
				'Key: `{}`   Type: `{}`   Array: `{}`'
				'   Detachable: `{}`   Using: `{}`\n'
			).format(
				splitargs[1],
				config.get_type(splitargs[1]),
				config.is_array(splitargs[1]),
				config.is_detachable(splitargs[1]),
				(
					'Local value' if
					config.is_detached(splitargs[1], message.guild.id) else
					'Master value'
				),
			)
		except AttributeError:
			content = 'Key: `{}`   Type: `{}`   Array: `{}`   Detachable: `{}`   Using: `{}`\n'.format(splitargs[1], config.get_type(splitargs[1]), config.is_array(splitargs[1]), config.is_detachable(splitargs[1]), 'Master value')
		if config.get_expl(splitargs[1]) is not None:
			content += 'Explanation: {}\n'.format(config.get_expl(splitargs[1]))
		content += 'Value:'

		if config.is_array(splitargs[1]):
			try:
				for val in config.get_s(splitargs[1], message.guild.id):
					content += ' `{}`,'.format(val)
			except AttributeError:
				for val in config.get_s(splitargs[1]):
					content += ' `{}`,'.format(val)
		else:
			try:
				content += ' `{}`\nDefault: `{}`'.format(
					str(config.get_s(splitargs[1], message.guild.id)),
					str(config.get_default(splitargs[1])),
				)
			except AttributeError:
				content += ' `{}`\nDefault: `{}`'.format(
					str(config.get_s(splitargs[1])),
					str(config.get_default(splitargs[1])),
				)
		await bot.reply(message, content)
	elif splitargs[0] == 'insert' or splitargs[0] == 'remove':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await bot.reply(message, emb=embed)
			return
		if not (config.is_array(splitargs[1]) or config.is_dic(splitargs[1])):
			embed = emb.error(
				'That doesn’t work for something that is not an array or dic',
			)
			await bot.reply(message, emb=embed)
			return
		if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
			embed = emb.error('Integer expected')
			await bot.reply(message, emb=embed)
			return
		if splitargs[0] == 'insert':
			try:
				try:
					if config.is_dic(splitargs[1]):
						config.insert_dic_s(
							splitargs[1],
							splitargs[2],
							splitargs[3],
							message.guild.id,
						)
					elif config.is_array(splitargs[1]):
						config.insert_s(
							splitargs[1],
							splitargs[2],
							message.guild.id,
						)
						editingmaster = not config.is_detached(
							splitargs[1],
							message.guild.id,
						)
				except AttributeError:
					if config.is_dic(splitargs[1]):
						config.insert_dic_s(
							splitargs[1],
							splitargs[2],
							splitargs[3],
						)
					elif config.is_array(splitargs[1]):
						config.insert_s(splitargs[1], splitargs[2])
			except ValueError:
				embed = emb.error('Invalid value specified')
				await bot.reply(message, emb=embed)
				return
			embed = emb.success('Inserted `{0}` into {type} `{1}`{2}'.format(
					utils.wrapbackticks(
						config.input_to_type_key(splitargs[2], splitargs[1])
					), splitargs[1],
					bot.t['editingmasterval'] if editingmaster else '',
					type=config.get_type(splitargs[1]),
				)
			)
		else:
			try:
				try:
					if config.is_dic(splitargs[1]):
						config.remove_dic_s(
							splitargs[1],
							splitargs[2],
							message.guild.id,
						)
					elif config.is_array(splitargs[1]):
						config.remove_s(
							splitargs[1],
							splitargs[2],
							message.guild.id,
						)
					editingmaster = not config.is_detached(
						splitargs[1],
						message.guild.id,
					)
				except AttributeError:
					if config.is_dic(splitargs[1]):
						config.remove_dic_s(splitargs[1], splitargs[2])
					elif config.is_array(splitargs[1]):
						config.remove_s(splitargs[1], splitargs[2])
			except ValueError:
				embed = emb.error('Invalid value specified')
				await bot.reply(message, emb=embed)
				return
			embed = emb.success('Removed `{}` from {type} `{}`{}'.format(
					utils.wrapbackticks(
						config.input_to_type_key(splitargs[2], splitargs[1])
					), splitargs[1],
					bot.t['editingmasterval'] if editingmaster else '',
					type=config.get_type(splitargs[1]),
				)
			)
		config.saveconfig()
		utils.logcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
	elif splitargs[0] == 'detach' or splitargs[0] == 'reattach':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await bot.reply(message, emb=embed)
			return
		if not config.is_detachable(splitargs[1]):
			embed = emb.error('That setting cannot have an independent local value.')
			await bot.reply(message, emb=embed)
			return
		if splitargs[0] == 'detach':
			try:
				config.detach(splitargs[1], message.guild.id)
				embed = emb.success('Setting `{}` now uses a local value for this server.'.format(splitargs[1]))
			except AttributeError:
				embed = emb.error('Can’t detach values for non-servers.')
		else:
			try:
				config.reattach(splitargs[1], message.guild.id)
				embed = emb.success('Setting `{}` is now using the master value again on this server.'.format(splitargs[1]))
			except AttributeError:
				embed = emb.error('Can’t reattach values for non-servers.')
		config.saveconfig()
		utils.logcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
	elif splitargs[0] == 'default':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await bot.reply(message, emb=embed)
			return
		try:
			config.restore_default(splitargs[1], message.guild.id)
		except AttributeError:
			config.restore_default(splitargs[1])
		config.saveconfig()
		utils.logcommand(kwargs['command'], kwargs['arguments'], message)
		embed = emb.success('Set `{}` back to default value of `{}`'.format(splitargs[1], utils.wrapbackticks(config.get_default(splitargs[1]))))
		await bot.reply(message, emb=embed)
	else:
		embed = emb.error('`{}` was not recognized'.format(splitargs[0]))
		await bot.reply(message, emb=embed)

@shadow()
async def echo(client, message, **kwargs):
	if kwargs['arguments'] is None:
		arguments = ''
	else:
		arguments = kwargs['clean_arguments']

	msg_start = bot.calculate_msg_start(message)

	if (isinstance(message.channel, discord.abc.GuildChannel) and \
	message.channel.permissions_for(message.guild.me).embed_links) \
	or isinstance(message.channel, discord.abc.PrivateChannel):
		displayarguments = arguments[:2048-len(msg_start)]
		try:
			echocolor = message.guild.me.colour
		except AttributeError:
			# No message.guild apparently! (.me and .colour always exist)
			echocolor = None
		em = discord.Embed(description=displayarguments, colour=echocolor)
		replyargs = {'emb': em}
	else:
		displayarguments = arguments[:2000-len(msg_start)]
		replyargs = {'message': displayarguments}
	await bot.reply(message, **replyargs)

@shadow()
async def source(client, message, **kwargs):
	content = 'Source code to the bot: https://gitgud.io/infoteddy/bracketed_backslash'
	await bot.reply(message, content)

@shadow(aliases=['findup'])
async def findu(client, message, **kwargs):
	if kwargs['arguments'] is None:
		targetmember = message.author
	else:
		targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	if targetmember is None:
		embed = emb.error('Unable to find that member. ' + bot.t['specify_user'])
		await bot.reply(message, emb=embed)
		return
	displaymatch = '<@{}>'.format(targetmember.id)
	if targetmember.activity is None:
		memberhasgame = False
		displaygamestatus = 'Not Playing'
		displaygamename = 'Not Playing'
		displaygameurlstatus = 'No Stream Link'
		displaygameurl = 'No Stream Link'
	else:
		memberhasgame = True

	if memberhasgame:
		displaygamename = utils.mdspecialchars(targetmember.activity.name)

		displaygamestatus = 'Activity'

		if targetmember.activity.type == discord.ActivityType.playing:
			displaygamestatus = 'Playing'
		if targetmember.activity.type == discord.ActivityType.streaming:
			displaygamestatus = 'Streaming'
		if targetmember.activity.type == discord.ActivityType.listening:
			displaygamestatus = 'Listening'
		if targetmember.activity.type == discord.ActivityType.watching:
			displaygamestatus = 'Watching'

		if not hasattr(targetmember.activity, 'url') or targetmember.activity.url is None:
			displaygameurlstatus = 'No Stream Link'
			displaygameurl = 'No Stream Link'
		else:
			displaygameurlstatus = 'Stream Link'
			displaygameurl = utils.mdspecialchars(targetmember.activity.url)
	embed = discord.Embed(description='Matched ' + displaymatch, colour=targetmember.colour)
	embed.set_image(url=targetmember.display_avatar.url)
	embed.add_field(name='Nickname' if targetmember.nick is not None else 'No Nickname', value=utils.mdspecialchars(targetmember.nick) if targetmember.nick is not None else 'No Nickname')
	embed.add_field(name='Username', value=utils.mdspecialchars(targetmember.name))
	embed.add_field(name='Discriminator', value='#{}'.format(targetmember.discriminator))
	embed.add_field(name='User ID', value=targetmember.id)
	embed.add_field(name='Bot', value='Yes' if checks.is_bot(targetmember) else 'No')
	embed.add_field(name=displaygamestatus, value=displaygamename)
	embed.add_field(name=displaygameurlstatus, value=displaygameurl)
	embed.add_field(name='Status', value='Do Not Disturb' if str(targetmember.status) == 'dnd' else str(targetmember.status).title())
	embed.add_field(
		name='Joined Server At',
		value=time.strftime(
			config.get_s('timeformat', message.guild.id),
			targetmember.joined_at.timetuple(),
		),
	)
	embed.add_field(
		name='Joined Discord At',
		value=time.strftime(
			config.get_s('timeformat', message.guild.id),
			targetmember.created_at.timetuple(),
		),
	)
	embed.add_field(name='Color', value='_(default)_' if str(targetmember.colour) == '#000000' else str(targetmember.colour).upper())
	# IMPORTANT: in `embed.add_field()`, `name` or `value` cannot be an empty string or you will get a 400 bad request when sending it
	# (i learned that the hard way)
	# (that was about twenty restarts smh)
	await bot.reply(message, emb=embed)

@shadow(guildonly=True)
async def findc(client, message, **kwargs):
	if not kwargs['arguments']:
		# No channel for me to get? Have a list of the guild's channels, then.

		# Lists
		tchans = ''
		vchans = ''

		# Numbers
		tchanc = 0
		vchanc = 0

		# Generation of the lists
		for c in sorted(message.guild.channels, key=lambda c: c.position):
			apnd = utils.obj_info(c)
			if isinstance(c, discord.TextChannel):
				tchans += apnd
				tchanc += 1
			elif isinstance(c, discord.VoiceChannel):
				vchans += apnd
				vchanc += 1

		# Some guilds can have no voice channels. You can't have no text channels, though.
		# Well, after a Discord update you now can, although then I'm not sure how we're receiving this command in the first place... whatever
		tchans = '_(none)_' if not tchans else tchans
		vchans = '_(none)_' if not vchans else vchans

		em = discord.Embed(colour=message.guild.me.colour)
		if message.guild.icon is not None:
			em.set_thumbnail(url=message.guild.icon.url)

		utils.paginate_field(em, max_length=1024,
			name='Text Channels ({0})'.format(tchanc),
			value=tchans,
			inline=False,
		)
		utils.paginate_field(em, max_length=1024,
			name='Voice Channels ({0})'.format(vchanc),
			value=vchans,
			inline=False,
		)
		await bot.reply(message, emb=em)
		return

	tgt = utils.match_input(message.guild.channels, discord.abc.GuildChannel, kwargs['arguments'])
	if not tgt:
		em = emb.error('Unable to find that channel. ' + bot.t['specify_channel'])
		await bot.reply(message, emb=em)
		return

	readbleby = 0
	for i in message.guild.members:
		readbleby += 1 if tgt.permissions_for(i).read_messages else 0

	em = discord.Embed(description='Matched ' + tgt.mention, colour=message.guild.me.colour)
	if message.guild.icon is not None:
		em.set_thumbnail(url=message.guild.icon.url)
	em.add_field(name='Name', value=utils.mdspecialchars(tgt.name))
	em.add_field(name='ID', value=tgt.id)
	em.add_field(name='Type', value=type(tgt).__name__)
	em.add_field(name='Default', value='No')
	em.add_field(
		name='Position',
		value='{0} from the top of {1} list'.format(
			str(tgt.position), type(tgt).__name__,
		),
	)
	em.add_field(
		name='Topic' if hasattr(tgt, 'topic') and tgt.topic else 'No Topic',
		value=tgt.topic if hasattr(tgt, 'topic') and tgt.topic else 'No Topic',
	)
	em.add_field(
		name='Created At',
		value=time.strftime(
			config.get_s('timeformat', message.guild.id),
			tgt.created_at.timetuple(),
		),
	)
	em.add_field(
		name='User Limit',
		value='N/A' if not isinstance(tgt, discord.VoiceChannel) else str(tgt.user_limit),
	)
	em.add_field(
		name='Voice Members',
		value=(
			'N/A' if not isinstance(tgt, discord.VoiceChannel) else
			str(len(tgt.members))
		),
	)
	em.add_field(
		name='Bitrate',
		value=(
			'N/A' if not isinstance(tgt, discord.VoiceChannel) else
			str(int(tgt.bitrate / 1000)) + ' kbps'
		),
	)
	em.add_field(name='Overwrites', value=str(len(tgt.overwrites)))
	em.add_field(
		name='Readable By',
		value=(
			'N/A' if not isinstance(tgt, discord.TextChannel) else
			str(readbleby) + ' members'
		),
	)
	await bot.reply(message, emb=em)

@shadow(auth=checks.is_mod, aliases=['voiceunmute'])
async def voicemute(client, message, **kwargs):
	targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	content = None
	try:
		if targetmember.voice.voice_channel is None:
			embed = emb.error('User is not in a voice channel.')
		elif kwargs['command'] == 'voicemute':
			await targetmember.edit(mute=True)
			content = targetmember.mention
			embed = emb.success('Voice muted <@{}>.'.format(targetmember.id))
		elif kwargs['command'] == 'voiceunmute':
			await targetmember.edit(mute=False)
			content = targetmember.mention
			embed = emb.success('Voice unmuted <@{}>.'.format(targetmember.id))
	except AttributeError:
		embed = emb.error(bot.t['specify_user'])
	except discord.errors.Forbidden:
		embed = emb.error(bot.t['no_permission'])
	await bot.reply(message, content, emb=embed)

@shadow(auth=checks.is_mod, guildonly=True)
async def rolerst(client, message, **kwargs):
	targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	if targetmember is None:
		embed = emb.error(bot.t['specify_user'])
		await bot.reply(message, emb=embed)
		return
	await utils.removeRestrictiveRoles(targetmember, message.guild)
	embed = emb.success('Reset roles for <@{}> back to normal.'.format(targetmember.id))
	await bot.reply(message, emb=embed)

@shadow(guildonly=True, aliases=['role_add_all', 'remove_role_all', 'role_remove_all'])
async def add_role_all(client, message, **kwargs):
	perms = message.channel.permissions_for(message.author)
	if not perms.manage_roles and not kwargs['sudo']:
		embed = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
		return

	role = utils.match_input(message.guild.roles, discord.Role, kwargs['arguments'])

	if role is None:
		embed = emb.error(bot.t['specify_role'])
		await bot.reply(message, emb=embed)
		return

	remove = kwargs['command'] in ('remove_role_all', 'role_remove_all')

	# Do this in a separate task so it doesn't block the role adding
	async def first_respond():
		embed = emb.info(
			'{doing} {role} {with_} every member on the server. This can take a while...'
			'{addendum}'
			.format(
				doing='Removing' if remove else 'Adding',
				role=utils.obj_info(role),
				with_='from' if remove else 'to',
				addendum='' if remove else
				'\nIf you added the wrong role, you can use `\\remove_role_all`.',
			),
		)
		await bot.reply(message, emb=embed)
	dispatch.run(wrapper.client, first_respond())

	# Lists of member IDs
	failures = []
	successes = []

	action_func = 'remove_roles' if remove else 'add_roles'

	for member in message.guild.members:
		try:
			await getattr(member, action_func)(
				role,
				reason='Mass role {act} called by {mod}'.format(
					act='removal' if remove else 'addition',
					mod=utils.obj_info(message.author, markdown=False),
				),
			)
		except discord.errors.Forbidden:
			# Well, why continue?
			embed = emb.error(bot.t['no_permission'])
			await bot.reply(message, emb=embed)
			return
		except discord.errors.HTTPException:
			failures.append(member.id)
		else:
			successes.append(member.id)

	if failures:
		embed = emb.warning(
			# I assume if a non-bot called this command, that there is more than
			# 1 member in the server. Thus there is no plural-checking code.
			'I have successfully {done} {role} {with_} {n1} members, '
			'but have failed to do it for {n2} members.'
			.format(
				done='removed' if remove else 'added',
				role=utils.obj_info(role),
				with_='from' if remove else 'to',
				n1=len(successes),
				n2=len(failures),
			)
		)
		await bot.reply(message, emb=embed)
		return

	if successes:
		embed = emb.success(
			# Again, no plural-checking code here, too.
			'Successfully {did} {role} {with_} {n} members.'.format(
				did='removed' if remove else 'added',
				role=utils.obj_info(role),
				with_='from' if remove else 'to',
				n=len(successes),
			)
		)
		await bot.reply(message, emb=embed)
		return

	# Why are we here? We shouldn't be here.
	assert False

@shadow(auth=checks.is_mod)
async def expires(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Please input at least a relative time.')
		await bot.reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ', 1)

	expirytime = utils.parsereltime(splitargs[0])
	if expirytime is None:
		embed = emb.error((
				'Invalid expiry time. Please input a relative time '
				'in the format `[#d][#h][#m][#s]`, for example: '
				'`7d12h`, `1h`, `1d`, `1d2h3m4s`, `1d20s` or '
				'whatever combination you can think of. The units '
				'have to be in the correct order, though.'
			)
		)
		await bot.reply(message, emb=embed)
		return

	if len(splitargs) < 2:
		if not events.latestroled:
			embed = emb.error((
					'Nobody has gotten a restrictive role this session. '
					'Please provide any member identification instead.'
				)
			)
			await bot.reply(message, emb=embed)
			return
		targetmemberid = events.latestroled
	else:
		try:
			targetmember = utils.match_input(message.guild.members, discord.Member, splitargs[1])
			targetmemberid = targetmember.id
		except AttributeError:
			embed = emb.error(bot.t['specify_user'])
			await bot.reply(message, emb=embed)
			return

	utils.addexpiryentry(message.guild.id, targetmemberid, expirytime)

	utils.rolexpiresave()
	await utils.handleExpiryTimer()

	embed = emb.success('Roles for <@{}> will be reset {}'.format(
			targetmemberid, utils.reltime(expirytime)
		)
	)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def expiryremove(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Please enter something.')
		await bot.reply(message, emb=embed)
		return

	try:
		targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
		if bot.removeexpiryentry(message.guild.id, targetmember.id):
			embed = emb.success(
				'Roles for <@{}> will no longer automatically expire.'.format(
					targetmember.id
				)
			)
			bot.rolexpiresave()
		else:
			embed = emb.error(
				'Could not find <@!{}> in the expiry list.'.format(
					targetmember.id
				)
			)
		await bot.reply(message, emb=embed)
	except AttributeError:
		embed = emb.error(bot.t['specify_user'])
		await bot.reply(message, emb=embed)
		return

@shadow()
async def expirylist(client, message, **kwargs):
	if isinstance(message.channel, discord.abc.PrivateChannel):
		if not kwargs['arguments']:
			embed = emb.error('You should probably specify a server.')
			await bot.reply(message, emb=embed)
			return
		guild = utils.match_input(client.guilds, discord.Guild, kwargs['arguments'])
		if not guild or (message.author not in guild.members and not kwargs['sudo']):
			embed = emb.error(
				(
					'Either the bot isn’t in that server,'
					' you aren’t in that server,'
					' or that server doesn’t exist.'
				),
			)
			await bot.reply(message, emb=embed)
			return
		content = 'Expiry list for {0}:\n'.format(utils.obj_info(guild))
	else:
		guild = message.guild
		content = ''

	if guild.id in wrapper.rolexpires:
		for k, v in sorted(wrapper.rolexpires[guild.id].items(), key=lambda i: i[1]['time']):
			content += '<@{}>: {}\n'.format(k, utils.reltime(v['time']))

	if content == '':
		content = 'No expiry timers are currently running.'

	embed = emb.info(content)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def rolecacherst(client, message, **kwargs):
	if config.get_s('rolecachemode', message.guild.id) == 0:
		embed = emb.error(bot.t['rolecachedisabled'])
		await bot.reply(message, emb=embed)
		return
	elif kwargs['arguments'] is None:
		embed = emb.error('Please give an ID.')
		await bot.reply(message, emb=embed)
		return
	elif utils.match_input(message.guild.members, discord.Member, kwargs['arguments']) is not None:
		embed = emb.error('That member is apparently still on this server! Not removing from the cache.')
		await bot.reply(message, emb=embed)
		return

	if utils.removerolecache(int(kwargs['arguments']), message.guild.id):
		embed = emb.success('Member {} successfully removed from role cache.'.format(kwargs['arguments']))
		await bot.reply(message, emb=embed)
		utils.rolecachesave()
	else:
		embed = emb.error('Member {} cannot be found in the role cache. Please note you have to enter an ID, not any form of name!'.format(kwargs['arguments']))
		await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def rolecacheadd(client, message, **kwargs):
	if config.get_s('rolecachemode', message.guild.id) == 0:
		embed = emb.error(bot.t['rolecachedisabled'])
		await bot.reply(message, emb=embed)
		return
	elif kwargs['arguments'] is None:
		embed = emb.error('Please give two IDs.')
		await bot.reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split()
	if utils.match_input(message.guild.members, discord.Member, splitargs[0]) is not None:
		embed = emb.error('That member is apparently still on this server! Not doing anything.')
		await bot.reply(message, emb=embed)
		return

	if splitargs[1] is None:
		embed = emb.error('Please give two IDs.')
		await bot.reply(message, emb=embed)
		return

	if int(splitargs[0]) not in wrapper.memberroles[message.guild.id]:
		wrapper.memberroles[message.guild.id][int(splitargs[0])] = []

	wrapper.memberroles[message.guild.id][int(splitargs[0])].append(int(splitargs[1]))
	utils.rolecachesave()

	embed = emb.success('Successfully added role {} to member {} in the role cache.'.format(splitargs[1], splitargs[0]))
	await bot.reply(message, emb=embed)

@shadow(aliases=['syncroles'])
async def rolesync(client, message, **kwargs):
	perms = message.channel.permissions_for(message.author)
	if not perms.manage_roles and not kwargs['sudo']:
		embed = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
		return
	elif config.get_s('rolecachemode', message.guild.id) == 0:
		embed = emb.error(bot.t['rolecachedisabled'])
		await bot.reply(message, emb=embed)
		return

	for mem in message.guild.members:
		utils.updaterolecache(mem, message.guild.id)

	utils.rolecachesave()

	embed = emb.success('Synced roles.')
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def rolecacheinfo(client, message, **kwargs):
	if config.get_s('rolecachemode', message.guild.id) == 0:
		embed = emb.error(bot.t['rolecachedisabled'])
		await bot.reply(message, emb=embed)
		return
	if not kwargs['arguments'].isdigit():
		embed = emb.error('Invalid arguments. An ID can only be passed.')
		await bot.reply(message, emb=embed)
		return

	member_id = int(kwargs['arguments'])
	if member_id not in wrapper.memberroles[message.guild.id]:
		embed = emb.error('That member is not in the role cache.')
		await bot.reply(message, emb=embed)
		return

	content = (
		'According to the role cache, this member has the following roles: '
		+ utils.listroles_id(wrapper.memberroles[message.guild.id][member_id])
	)

	await bot.reply(message, content)

@shadow()
async def rolecache(client, message, **kwargs):
	perms = message.channel.permissions_for(message.author)
	if not perms.manage_guild and not kwargs['sudo']:
		embed = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
		return

	if not config.is_detached('rolecachemode', message.guild.id):
		config.detach('rolecachemode', message.guild.id)

	if kwargs['arguments'] == 'enable':
		config.set_s('rolecachemode', 2, message.guild.id)
		em = emb.success('Role cache has been enabled. Make sure to run `\\rolesync` to sync everyone’s roles.')
	elif kwargs['arguments'] == 'enable_with_default':
		config.set_s('rolecachemode', 1, message.guild.id)
		em = emb.success('Role cache has been enabled, and new members will be given default roles. Make sure to run `\\rolesync` to sync everyone’s roles.')
	elif kwargs['arguments'] == 'disable':
		config.set_s('rolecachemode', 0, message.guild.id)
		em = emb.success('Role cache has been disabled.')
	else:
		em = emb.error('Invalid argument. Use either `enable`, `enable_with_default`, or `disable`.')

	config.saveconfig()
	await bot.reply(message, emb=em)

@shadow(aliases=['rule'], guildonly=True)
async def rules(client, message, **kwargs):
	if message.guild.id in wrapper.disabledrules and not checks.is_mod(message.author):
		embed = emb.error('The rules system is currently disabled for this server.')
		await bot.reply(message, emb=embed)
		return
	if not message.guild.id in wrapper.rules:
		embed = emb.warning('Rules are not (yet) set for this server.')
		await bot.reply(message, emb=embed)
		return
	if kwargs['arguments'] is not None and kwargs['arguments'].isdigit():
		if int(kwargs['arguments']) - 1 in wrapper.rules[message.guild.id]:
			content = 'Rule **{}** for server `{}`:\n{}'.format(
				int(kwargs['arguments']),
				utils.wrapbackticks(message.guild.name),
				wrapper.rules[message.guild.id][int(kwargs['arguments'])-1],
			)
			await bot.reply(message, content)
			return
	n = 1
	content = 'Rules for server `{}`:{}'.format(
		utils.wrapbackticks(message.guild.name),
		' (Disabled)' if message.guild.id in wrapper.disabledrules else '',
	)
	for rule in wrapper.rules[message.guild.id]:
		content += '\n**{}.** {}'.format(n, rule)
		n += 1
	await bot.reply(message, content)

@shadow(guildonly=True)
async def rulefind(client, message, **kwargs):
	if message.guild.id in wrapper.disabledrules and not checks.is_mod(message.author):
		embed = emb.error('The rules system is currently disabled for this server.')
		await bot.reply(message, emb=embed)
		return
	if not message.guild.id in wrapper.rules:
		embed = emb.warning('Rules are not (yet) set for this server.')
		await bot.reply(message, emb=embed)
		return
	if kwargs['arguments'] is None:
		embed = emb.error('Please enter a search term.')
		await bot.reply(message, emb=embed)
		return
	matched = False
	n = 1
	content = 'Rules for server **``{}``** matching **``{}``**:'.format(
		utils.wrapbackticks(message.guild.name),
		utils.wrapbackticks(kwargs['arguments']),
	)
	for rule in wrapper.rules[message.guild.id]:
		if rule.lower().find(kwargs['arguments'].lower()) != -1:
			content += '\n**{}.** {}'.format(n, rule)
			matched = True
		n += 1
	if not matched:
		embed = emb.warning('No rules on server `{}` matching `{}`.'.format(
				utils.wrapbackticks(message.guild.name),
				utils.wrapbackticks(kwargs['arguments']),
			),
		)
		await bot.reply(message, emb=embed)
		return
	await bot.reply(message, content)

@shadow(aliases=['addrule'])
async def ruleadd(client, message, **kwargs):
	if not checks.is_mod(message.author):
		# Okay, so they're not allowed to mess with the rules - but we want to respond to some particular things as well.
		splitargs = kwargs['arguments'].split(' ', 1)
		if splitargs[0].isdigit() and \
		int(splitargs[0]) > len(wrapper.rules[message.guild.id]):
			embed = emb.warning('Why are you mentioning the number if you want to add this as the last rule?')
			await bot.reply(message, emb=embed)
			return

		# Ok good, they're not doing something weird or trying to be funny.
		embed = emb.error(bot.t['mod_only'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)

		await bot.reply(message, emb=embed)
		return
	if kwargs['arguments'] is None:
		embed = emb.error('I’m not going to think up any rules by myself.')
		await bot.reply(message, emb=embed)
		return
	if not message.guild.id in wrapper.rules:
		wrapper.rules[message.guild.id] = []

	splitargs = kwargs['arguments'].split(' ', 1)
	if splitargs[0].isdigit():
		if int(splitargs[0]) > len(wrapper.rules[message.guild.id]):
			content = '**Why are you mentioning the number if you’re adding this at the end?**\n'
		else:
			content = ''
		wrapper.rules[message.guild.id].insert(int(splitargs[0])-1, splitargs[1])
		content += 'New rule {} inserted:\n{}'.format(int(splitargs[0]), splitargs[1])      # Yes, this one is "inserted"...
	else:
		wrapper.rules[message.guild.id].append(kwargs['arguments'])

		# ...and this one is "added". That is on purpose, not an inconsistency.
		content = 'New rule {} added:\n{}'.format(
			len(wrapper.rules[message.guild.id]),
			kwargs['arguments'],
		)

	embed = emb.success(content)
	utils.rulesave()
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod, aliases=['editrule'])
async def ruleedit(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
		await bot.reply(message, emb=embed)
		return
	if not message.guild.id in wrapper.rules:
		embed = emb.error('No rules to edit.')
		await bot.reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ', 1)
	if splitargs[0].isdigit():
		try:
			wrapper.rules[message.guild.id][int(splitargs[0])-1]
		except IndexError:
			embed = emb.error('Rule {} does not appear to exist.'.format(int(splitargs[0])))
			await bot.reply(message, emb=embed)
			return

		embed = emb.success('Rule {} successfully edited from:\n{}\nTo:\n{}'.format(
				int(splitargs[0]),
				wrapper.rules[message.guild.id][int(splitargs[0])-1], splitargs[1],
			),
		)

		wrapper.rules[message.guild.id][int(splitargs[0])-1] = splitargs[1]
		utils.rulesave()
	else:
		embed = emb.error('Invalid rule number given, just check the help entry.')
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod, aliases=['moverule'])
async def rulemove(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
		await bot.reply(message, emb=embed)
		return
	if not message.guild.id in wrapper.rules:
		embed = emb.error('No rules to move.')
		await bot.reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ', 1)
	if splitargs[0].isdigit() and splitargs[1].isdigit():
		if any(
			x not in wrapper.rules[message.guild.id]
			for x in (int(splitargs[0]) - 1, int(splitargs[1]) - 1)
		):
			embed = emb.error('Either rule {} does not exist or {} is not a slot it can be moved to.'.format(int(splitargs[0]), int(splitargs[1])))
			await bot.reply(message, emb=embed)
			return

		rulecontent = wrapper.rules[message.guild.id][int(splitargs[0])-1]
		wrapper.rules[message.guild.id].remove(
			wrapper.rules[message.guild.id][int(splitargs[0])-1],
		)
		wrapper.rules[message.guild.id].insert(int(splitargs[1])-1, rulecontent)
		utils.rulesave()

		embed = emb.success('Rule {} successfully moved to number {}.'.format(int(splitargs[0]), int(splitargs[1])))
	else:
		embed = emb.error('Invalid rule number(s) given, just check the help entry.')
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod, aliases=['removerule'])
async def ruleremove(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
		await bot.reply(message, emb=embed)
		return
	if not message.guild.id in wrapper.rules:
		embed = emb.error('No rules to delete.')
		await bot.reply(message, emb=embed)
		return

	if kwargs['arguments'].isdigit():
		try:
			wrapper.rules[message.guild.id][int(kwargs['arguments'])-1]
		except IndexError:
			embed = emb.error('Rule {} does not appear to exist.'.format(int(kwargs['arguments'])))
			await bot.reply(message, emb=embed)
			return

		embed = emb.success('Rule {} successfully removed:\n{}'.format(
				int(kwargs['arguments']),
				wrapper.rules[message.guild.id][int(kwargs['arguments'])-1],
			),
		)

		wrapper.rules[message.guild.id].remove(
			wrapper.rules[message.guild.id][int(kwargs['arguments'])-1],
		)
		utils.rulesave()
	else:
		embed = emb.error('Invalid rule number given, just check the help entry.')
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def rulemaint(client, message, **kwargs):
	if message.guild.id in wrapper.disabledrules:
		wrapper.disabledrules.remove(message.guild.id)
		embed = emb.success('Rules system enabled for this server.')
	else:
		wrapper.disabledrules.append(message.guild.id)
		embed = emb.success('Rules system disabled for this server.')
	with open('disabledrules.json', 'w') as outfile:
		json.dump(wrapper.disabledrules, outfile)
	await bot.reply(message, emb=embed)

@shadow()
async def info(client, message, **kwargs):
	persontocheck = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	if persontocheck is None:
		embed = emb.error(bot.t['specify_user'])
		await bot.reply(message, emb=embed)
		return
	yesperm = '✅'
	noperm = '⛔'
	perms = message.channel.permissions_for(persontocheck)

	leftover = []
	for detected_p in iter(perms):
		leftover.append(detected_p[0])

	content = 'Permissions for **``{}``**`#{}` in <#{}>:\n**`Server Owner:`** {}'.format(
		persontocheck.name,
		persontocheck.discriminator,
		message.channel.id,
		yesperm if persontocheck == persontocheck.guild.owner else noperm,
	)

	for stored_p in bot.permissionlabels:
		if not stored_p[0] in leftover:
			content += '\n**`{}:`** NOT USED'.format(stored_p[1])
		else:
			content += '\n**`{}:`** {}'.format(stored_p[1], yesperm if getattr(perms, stored_p[0]) else noperm)
			leftover.remove(stored_p[0])
		if perms.administrator:
			await bot.reply(message, content)
			return

	for left_p in leftover:
		# Apparently these permissions are new
		content += '\n`{}:` {}'.format(left_p, yesperm if getattr(perms, left_p) else noperm)

	await bot.reply(message, content)

@shadow(auth=checks.is_role_manager)
async def channelperms(client, message, **kwargs):
	if kwargs['arguments'] is not None:
		person = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
		if person is None:
			embed = emb.error(
				'You specified a member, but no matching member has been found.'
			)
			await bot.reply(message, emb=embed)
			return
	else:
		person = None

	chans = {} # channel -> permissions
	times_targeted = {} # role/member -> amount of occurrences
	for c in sorted(message.guild.channels, key=lambda c: c.position):
		if person is None:
			chans[c] = c.overwrites
			for o in chans[c]:
				if o in times_targeted:
					times_targeted[o] += 1
				else:
					times_targeted[o] = 1
		else:
			chans[c] = {person: c.permissions_for(person)}

	if person is not None:
		times_targeted[person] = 1

	ordered_overwrites = []
	for o in times_targeted:
		ordered_overwrites.append((o, times_targeted[o]))
	ordered_overwrites.sort(key=lambda o: o[1], reverse=True)

	# Occurrences are no longer necessary
	for i in range(len(ordered_overwrites)):
		ordered_overwrites[i] = ordered_overwrites[i][0]

	import html
	html_table = (
		'\t<table border="1">\n'
		'\t\t<tr>\n'
		'\t\t\t<td></td>\n'
	)
	for o in ordered_overwrites:
		name = o.name
		if isinstance(o, discord.Member) or isinstance(o, discord.User):
			name += '#{}'.format(o.discriminator)
		html_table += '\t\t\t<td style="color: rgb({},{},{});">{}</td>\n'.format(
			o.color.r, o.color.g, o.color.b, html.escape(name)
		)

	html_table += '\t\t</tr>\n'

	for c in sorted(chans, key=lambda c: c.position):
		if not isinstance(c, discord.TextChannel):
			# Only show text channels for now
			continue

		html_table += '\t\t<tr>\n'

		if isinstance(c, discord.TextChannel):
			html_table += '\t\t\t<td>#{}</td>\n'.format(html.escape(c.name))
		elif isinstance(c, discord.CategoryChannel):
			html_table += '\t\t\t<td><strong>{}</strong></td>\n'.format(
				html.escape(c.name)
			)
		else:
			html_table += '\t\t\t<td>{}</td>\n'.format(html.escape(c.name))

		for o in ordered_overwrites:
			if o not in chans[c]:
				html_table += '\t\t\t<td></td>\n'
			else:
				perm_info = ''
				if isinstance(chans[c][o], discord.PermissionOverwrite):
					# Permissions can also be None, for neutral
					if chans[c][o].read_messages:
						perm_info = '<span class="allow">+R</span> '
					elif chans[c][o].read_messages == False:
						perm_info = '<span class="deny">-R</span> '
					if chans[c][o].send_messages:
						perm_info += '<span class="allow">+W</span> '
					elif chans[c][o].send_messages == False:
						perm_info += '<span class="deny">-W</span> '
				else:
					# discord.Permissions: Only True and False
					if chans[c][o].read_messages and chans[c][o].send_messages:
						perm_info = '<span class="allow">Read/Write</span>';
					elif chans[c][o].read_messages:
						perm_info = '<span class="halfallow">Read-only</span>';
					else:
						perm_info = '<span class="deny">No access</span>';

				html_table += '\t\t\t<td>{}</td>\n'.format(perm_info)
		html_table += '\t\t</tr>\n'
	html_table += '\t</table>\n'

	if person is None:
		title = 'Channel permissions in {}'.format(html.escape(message.guild.name))
		result_info = (
			'Just open this file in your browser '
			'to see an overview of channel permissions:'
		)
	else:
		title = 'Evaluated channel permissions for {}#{} in {}'.format(
			html.escape(person.name), person.discriminator,
			html.escape(message.guild.name)
		)
		result_info = (
			'Just open this file in your browser '
			'to see an overview of channel permissions '
			'for this member: '
		)

	html_main = (
		'<!DOCTYPE html>\n'
		'<html>\n'
		'<head>\n'
		'\t<title>{title}</title>\n'
		'\t<style>\n'
		'\t\tbody {{ font-family: sans-serif; }}\n'
		'\t\t.allow {{ color: green; }}\n'
		'\t\t.deny {{ color: red; }}\n'
		'\t\t.halfallow {{ color: orange; }}\n'
		'\t</style>\n'
		'</head>\n'
		'<body>\n'
		'\t<h1>{title}</h1>\n'
		'{table}'
		'\t<p>Generated at {time}</p>'
		'</body>'
	).format(
		title=title, table=html_table, time=time.strftime(
			config.get_s('timeformat', message.guild.id)
		)
	)

	with tempfile.NamedTemporaryFile() as temp:
		temp.write(html_main.encode())
		temp.flush()
		await message.channel.send(
			bot.calculate_msg_start(message) + result_info,
			file=discord.File(temp.name, 'channels.html')
		)

@shadow()
async def botok(client, message, **kwargs):
	embed = emb.success('Bot is okay.')
	await bot.reply(message, emb=embed)

@shadow()
async def uptime(client, message, **kwargs):
	hostuptime = subprocess.Popen(['uptime', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
	embed = discord.Embed(colour=col.r_success, timestamp=message.created_at)
	embed.set_author(name='Uptime Statistics', icon_url=client.user.display_avatar.url)
	embed.set_thumbnail(url=client.user.display_avatar.url)
	embed.set_footer(text='Uptime Statistics', icon_url=client.user.display_avatar.url)
	embed.add_field(name='Boot Time', value=wrapper.boottime)
	try:
		now = config.get_s('timeformat', message.guild.id)
	except AttributeError:
		now = config.get_s('timeformat')
	embed.add_field(name='Current Time', value=time.strftime(now))
	embed.add_field(name='Bot Uptime', value=utils.reltime(wrapper.boottimeunix, True))
	embed.add_field(name='Host Uptime', value=hostuptime.decode('utf-8'))
	await bot.reply(message, emb=embed)

@shadow()
async def invite(client, message, **kwargs):
	oauth_url = discord.utils.oauth_url(client.user.id)
	content = (
		'Invite link for this bot:\n'
		f'<{oauth_url}>\n\n'
		'Join the **[\\\\]** server at <https://discord.gg/nc7HUZ4>'
	)
	await bot.reply(message, content)

@shadow()
async def version(client, message, **kwargs):
	embed = discord.Embed(colour=col.r_success, timestamp=message.created_at)
	embed.set_author(name='Version Information', icon_url=client.user.display_avatar.url)
	embed.set_thumbnail(url=client.user.display_avatar.url)
	embed.set_footer(text='Version Information', icon_url=client.user.display_avatar.url)
	embed.set_thumbnail(url=client.user.display_avatar.url)
	embed.add_field(name='\\[\\\\\\]', value='{}, commit {}{}'.format(
		bot.version,
		wrapper.current_commit,
		'\n(uncommitted changes)' if wrapper.current_dir_dirty else ''
	), inline=False)
	embed.add_field(name='Python', value=sys.version, inline=False)
	embed.add_field(name='discord.py', value='{} {}'.format(discord.version_info.releaselevel, discord.__version__))
	embed.add_field(name='Pillow', value=__import__("PIL").__version__)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def getrawmessagecontent(client, message, **kwargs):
	try:
		argsplit = kwargs['arguments'].split(' ', 1)
		if len(argsplit) == 1:
			# Just the message ID, try finding it in all the channels
			getmessage = None
			for channel in message.guild.text_channels:
				try:
					getmessage = await channel.fetch_message(argsplit[0])
					break
				except discord.errors.HTTPException:
					# If I can/may not view this message, or it's
					# not in this channel, then forget about it
					pass
			if getmessage is None:
				raise KeyError("Not found")
		else:
			arg0 = argsplit[0]
			arg1 = argsplit[1]
			channelid = int(arg0[2:-1])
			getchannel = client.get_channel(channelid)
			getmessage = await getchannel.fetch_message(arg1)
		content = '``{}``'.format(utils.wrapbackticks(getmessage.content[:1900]))
		await bot.reply(message, content)
		if getmessage.embeds != []:
			content = '``{}``'.format(utils.wrapbackticks(getmessage.embeds[:1900]))
			await bot.reply(message, content)
		return
	except AttributeError:
		embed = emb.error('Invalid arguments passed.')
	except IndexError:
		embed = emb.error('Invalid amount of arguments passed.')
	except (discord.errors.HTTPException, KeyError):
		embed = emb.error('Invalid channel or message ID given.')
	await bot.reply(message, emb=embed)

@shadow()
async def countpins(client, message, **kwargs):
	channel = message.channel
	guild = message.guild

	if kwargs['arguments'] is None:
		getchannel = channel
	else:
		getchannel = utils.match_input(
			guild.text_channels, discord.abc.GuildChannel, kwargs['arguments'],
		)

	if getchannel is None:
		embed = emb.error(
			'The channel doesn’t exist, has been deleted,'
			' or it’s not a channel at all.',
		)
		await bot.reply(message, emb=embed)
		return

	try:
		pins = await getchannel.pins()
	except discord.Forbidden:
		embed = emb.error(
			'I don’t have permission to look in {channel.mention}.'.format(
				channel=getchannel,
			),
		)
		await bot.reply(message, emb=embed)
		return

	content = '{} currently has {} pin{s}, {} remaining.'.format(
		getchannel.mention, len(pins), 50 - len(pins), s='s' if len(pins) != 1 else '',
	)
	await bot.replyattach(message, images.progressbar(len(pins)*2), 'temp.png', content)

@shadow(guildonly=True)
async def countallpins(client, message, **kwargs):
	async with message.channel.typing():
		content = ''
		for chan in message.guild.text_channels:
			try:
				pins = await chan.pins()
				content += '{} – {} pin{s}, {} remaining\n'.format(
					chan.mention,
					len(pins),
					50 - len(pins),
					s='s' if len(pins) != 1 else '',
				)
			except discord.errors.Forbidden:
				content += chan.mention + ' - Unable to get data\n'
	await bot.reply(message, content)

@shadow(auth=checks.is_operator)
async def gamestatus(client, message, **kwargs):
	if kwargs['arguments'] is None:
		status = None
	else:
		status = discord.Game(name=kwargs['arguments'])
	await client.change_presence(activity=status)
	embed = emb.success('Set game status to: ``{}``'.format(utils.wrapbackticks(kwargs['arguments'])))
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_host, aliases=['evalfile', 'setvar'])
async def _eval(client, message, **kwargs):
	if kwargs['command'] == 'eval':
		evaluate = kwargs['arguments']
	elif kwargs['command'] == 'evalfile':
		with open('eval.txt', 'r') as f:
			evaluate = f.read()
	elif kwargs['command'] == 'setvar':
		splitargs = kwargs['arguments'].split(' ', 1)
		evalvar = splitargs[0]
		evaluate = splitargs[1]
	env = {
		'message': message,
		'guild': message.guild,
		'channel': message.channel,
		'author': message.author,
	}
	env.update(globals())
	stdout = io.StringIO()
	to_compile = 'async def func():\n' + textwrap.indent(evaluate, '\t')
	try:
		exec(to_compile, env)
		with contextlib.redirect_stdout(stdout):
			evaluate = await env['func']()
	except Exception:
		value = stdout.getvalue()
		evaluate = value + traceback.format_exc()
	else:
		value = stdout.getvalue()
		if kwargs['command'] == 'setvar':
			globals()[evalvar] = evaluate
		if evaluate is None:
			if value:
				evaluate = value
		else:
			evaluate = value + repr(evaluate)
	content = '```py\n{0}```'.format(utils.wrapbackticks(str(evaluate)))
	if len(content) > 2000:
		print((
			'The result of your latest evaluation command is:\n'
			'{}\n'
			'End of results.'
		).format(evaluate))
		embed = emb.warning('Content too large to print. Printing to terminal instead.')
		await bot.reply(message, emb=embed)
		return
	await bot.reply(message, content)

@shadow(aliases=['serverban', 'unserverban', 'ban', 'unban'])
async def kick(client, message, **kwargs):
	targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	try:
		if kwargs['command'] == 'kick':
			if not message.author.guild_permissions.kick_members and not kwargs['sudo']:
				bot.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(bot.t['you_no_permission'])
				await bot.reply(message, emb=embed)
				return
			await targetmember.kick()
		elif kwargs['command'] in ('serverban', 'ban'):
			if not message.author.guild_permissions.ban_members and not kwargs['sudo']:
				bot.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(bot.t['you_no_permission'])
				await bot.reply(message, emb=embed)
				return
			await targetmember.ban(delete_message_days=0)
		elif kwargs['command'] in ('unserverban', 'unban'):
			if not message.author.guild_permissions.ban_members and not kwargs['sudo']:
				bot.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(bot.t['you_no_permission'])
				await bot.reply(message, emb=embed)
				return
			await message.guild.unban(targetmember)
		content = targetmember.mention
		embed = emb.success('{}ed <@{}>.'.format(kwargs['command'].title() if kwargs['command'] == 'kick' else kwargs['command'].title() + 'n', targetmember.id))
	except AttributeError:
		content = ''
		embed = emb.error(bot.t['specify_user'])
	except discord.errors.Forbidden:
		content = ''
		embed = emb.error(bot.t['no_permission'])
	await bot.reply(message, content, emb=embed)

@shadow()
async def bans(client, message, **kwargs):
	try:
		bans = await message.guild.bans()
	except discord.errors.Forbidden:
		embed = emb.error(bot.t['no_permission'])
		await bot.reply(message, emb=embed)
		return
	ulist = ''
	for ban_entry in bans:
		ulist += '{user}{reason}\n'.format(
			user=utils.obj_info(ban_entry.user),
			reason=' - ' + ban_entry.reason if ban_entry.reason is not None else '',
		)

	if not ulist:
		# Apparently there are no bans, so don't just display a server avatar
		ulist = '_(No server bans are currently active)_'

	embed = discord.Embed(
		name='Bans',
		description=ulist,
		colour=col.r_success,
	)
	if message.guild.icon is not None:
		embed.set_thumbnail(url=message.guild.icon.url)

	utils.paginate_description(embed=embed, max_length=2048)

	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_operator)
async def reloadstrings(client, message, **kwargs):
	bot.loadstrings()
	embed = emb.success('Reloaded strings.')
	await bot.reply(message, emb=embed)

@shadow(guildonly=True, joinchannelonly=True)
async def join(client, message, **kwargs):
	if len(message.author.roles) <= 1:
		await utils.newmemberroles(
			message.author,
			utils.getspecialchannel(message.guild),
			True,
		)

@shadow(auth=checks.is_tntgb_mod, aliases=['b_mod'], tntgbguildonly=True)
async def b(client, message, **kwargs):
	try:
		await message.delete()
	except discord.NotFound:
		pass
	else:
		wrapper.messages_deleted_by_bot.append(message)

	ban_log_channel = config.get_s('tntgb', message.guild.id)['ban_log_channel']
	ban_log_channel = message.guild.get_channel(ban_log_channel)

	# Who are we banning, and for what reason?
	if kwargs['arguments'].find('\n') != -1:
		splitargs = kwargs['arguments'].split('\n', 1)
	elif kwargs['arguments'].find(' ') != -1:
		splitargs = kwargs['arguments'].split(' ', 1)
	else:
		splitargs = [kwargs['arguments'], '(no given reason)']

	banningnonmod = True
	announcemsg = ''
	specialchannel = utils.getspecialchannel(message.channel.guild)
	targetmember = utils.match_input(message.guild.members, discord.Member, splitargs[0])
	if targetmember is None:
		embed = emb.error(bot.t['specify_user'])
		await specialchannel.send(embed=embed)
		banningnonmod = False
		return
	if checks.is_tntgb_banned(targetmember):
		embed = emb.warning('{} is already banned!'.format(targetmember.mention))
		await specialchannel.send(embed=embed)
		banningnonmod = False  # See this as "don't set expiry timer"
	elif checks.is_tntgb_mod(targetmember):
		mod_mistake_lifts = config.get_s('tntgb', message.guild.id)['mod_mistake_lifts']
		if kwargs['command'] != 'b_mod':
			embed = emb.warning(
				'{} is a mod, please use `\\b_mod` instead '
				'to cause {bans} ban{s} to be lifted!'
				.format(
					targetmember.mention,
					bans=(
						str(mod_mistake_lifts)
						if mod_mistake_lifts == 0
						else 'the oldest' + (
							''
							if mod_mistake_lifts == 1
							else ' ' + str(mod_mistake_lifts)
						)
					),
					s='' if mod_mistake_lifts == 1 else 's',
				)
			)
			await specialchannel.send(embed=embed)
			return

		# Get oldest two bans here and expire them
		expiredmentions = []

		# Technical messages:
		content = 'Lifted bans:'

		for _ in range(0, mod_mistake_lifts):
			currentexpiry = utils.getearliestexpiry(message.guild.id)

			if currentexpiry is None:
				continue

			getmember = message.guild.get_member(currentexpiry[0])
			if getmember is not None:
				await utils.removeRestrictiveRoles(
					message.guild.get_member(currentexpiry[0]),
					message.guild
				)
				content +='\n<@!{}> lifted normally'.format(
					currentexpiry[0]
				)
			else:
				# Look in the role cache
				if utils.removerolecache(currentexpiry[0], message.guild.id):
					utils.rolecachesave()
					content += '\n<@!{}> lifted via role cache'.format(
						currentexpiry[0]
					)
				else:
					content += (
						'\n<@!{}> cannot be found '
						'in the role cache!'
					).format(currentexpiry[0])
			# Shorten this again
			thisexpiry = currentexpiry[1]
			if thisexpiry['msgedit_message'] != '0':
				await utils.editexpirymessage(message.guild, thisexpiry)
			if not utils.removeexpiryentry(message.guild.id, currentexpiry[0]):
				em = emb.warning((
					'Could not remove expiry entry for '
					'<@!{}>! Debug: S:{} M:{} SI:{} MI:{}'
				).format(
					currentexpiry[0],
					message.guild.id,
					currentexpiry[0],
					message.guild.id in wrapper.rolexpires,
					currentexpiry[0] in wrapper.rolexpires
				))
				await specialchannel.send(embed=em)
			expiredmentions.append('<@!{}>'.format(currentexpiry[0]))

		utils.rolexpiresave()

		# Send administration info
		embed = emb.info(content)
		await specialchannel.send(embed=embed)

		# Now annouce it to the world
		if len(expiredmentions) > 2:
			whose = 'The bans on {mention_list}{last_joiner}{last_mention} have'.format(
				mention_list=', '.join(expiredmentions[:-1]),
				last_joiner=', and ',
				last_mention=expiredmentions[-1],
			)
		elif len(expiredmentions) == 2:
			whose = 'The bans on {} and {} have'.format(
				expiredmentions[0], expiredmentions[1]
			)
		elif len(expiredmentions) == 1:
			whose = 'The ban on {} has'.format(
				expiredmentions[0]
			)
		elif not expiredmentions:
			whose = 'All remaining bans (0) have'
		else:
			whose = 'An inexplicable number of bans ({}) has'.format(
				len(expiredmentions)
			)
		announcemsg = (
			'{} been lifted by {}, '
			'after {} has been {} in {}.'
		).format(
			whose,
			message.author.display_name,
			targetmember.mention,
			splitargs[1],
			message.channel.mention
		)
		await ban_log_channel.send(announcemsg)
		banningnonmod = False
	else:
		await targetmember.edit(
			roles=[
				discord.utils.find(lambda r: r.id == role_id, message.guild.roles)
				for role_id in config.get_s('restrictiveroles', message.guild.id)
			],
		)
		ban_days = str(config.get_s('tntgb', message.guild.id)['ban_days'])
		announcemsg = '{} has been banned for {ban_days} days by {} in {} for {}.'.format(
			targetmember.mention,
			message.author.display_name,
			message.channel.mention,
			splitargs[1],
			ban_days=ban_days,
		)
		content = '⛔ ' + announcemsg
		sentmessage = await ban_log_channel.send(content)

	if banningnonmod:
		# Also set an expiry timer
		expirytime = utils.parsereltime(ban_days + 'd')

		utils.addexpiryentry(message.guild.id, targetmember.id, expirytime,
			e_channel=sentmessage.channel.id, e_message=sentmessage.id,
			e_newcontent='[LIFTED] ' + announcemsg,
			p_channel=ban_log_channel.id,
			p_content='The ban on {} has expired.'.format(targetmember.mention)
		)

		utils.rolexpiresave()
		await utils.handleExpiryTimer()

@shadow(tntgbguildonly=True)
async def selfban(client, message, **kwargs):
	await message.delete()
	wrapper.messages_deleted_by_bot.append(message)

	if checks.is_tntgb_banned(message.author):
		# Wait, what?
		embed = emb.warning('How, then? You are already banned!')
		await bot.reply(message, emb=embed)
		return
	if checks.is_tntgb_mod(message.author):
		specialchannel = utils.getspecialchannel(message.channel.guild)
		embed = emb.warning('Sorry, moderators cannot use `\selfban`!')
		await specialchannel.send(embed=embed)


		return

	if kwargs['arguments'] is None or kwargs['arguments'] == '':
		kwargs['arguments'] = '(no given reason)'

	roles = []

	for role_id in config.get_s('restrictiveroles', message.guild.id):
		role = discord.utils.find(lambda r: r.id == role_id, message.guild.roles)

		if role is not None:
			roles.append(role)

	await message.author.edit(roles=roles)
	ban_days = config.get_s('tntgb', message.guild.id)['ban_days']
	announcemsg = '{} has carried out a self-ban for {ban_days} days in {} for {}.'.format(
		message.author.mention,
		message.channel.mention,
		kwargs['arguments'],
		ban_days=ban_days,
	)
	content = '⛔ ' + announcemsg
	ban_log_channel = config.get_s('tntgb', message.guild.id)['ban_log_channel']
	ban_log_channel = message.guild.get_channel(ban_log_channel)
	sentmessage = await ban_log_channel.send(content)

	# Also set an expiry timer
	expirytime = utils.parsereltime(str(ban_days) + 'd')

	utils.addexpiryentry(
		message.guild.id,
		message.author.id,
		expirytime,
		e_channel=sentmessage.channel.id, e_message=sentmessage.id,
		e_newcontent='[LIFTED] ' + announcemsg,
		p_channel=ban_log_channel.id,
		p_content='The ban on {} has expired.'.format(message.author.mention),
	)

	utils.rolexpiresave()
	await utils.handleExpiryTimer()

@shadow(auth=checks.is_tntgb_mod, aliases=['b_left', 'b_offserver'], tntgbguildonly=True)
async def b_id(client, message, **kwargs):
	await message.delete()
	wrapper.messages_deleted_by_bot.append(message)

	# Who are we banning, and for what reason?
	if kwargs['arguments'].find('\n') != -1:
		splitargs = kwargs['arguments'].split('\n', 1)
	elif kwargs['arguments'].find(' ') != -1:
		splitargs = kwargs['arguments'].split(' ', 1)
	else:
		splitargs = [kwargs['arguments'], '(no given reason)']

	# Now look if we can actually find the member. We're only looking for IDs, though!
	request = splitargs[0]
	if request.startswith('<@!') and request.endswith('>'):
		request = request[3:-1] # Extract the ID from it
	elif request.startswith('<@') and request.endswith('>'):
		request = request[2:-1] # Same

	request = int(request)

	targetmember = message.guild.get_member(request)

	if targetmember is None:
		# Just as I thought, they left
		if not utils.removerolecache(request, message.guild.id):
			embed = emb.error((
				'Member {} cannot be found in the role cache. '
				'Please note you have to enter an ID, not any form of name!'
			).format(request))
			await bot.reply(message, emb=embed)
			return

		# Okay, removing their entry altogether was a bit drastic
		wrapper.memberroles[message.guild.id][request] = []
		for role_id in config.get_s('restrictiveroles', message.guild.id):
			wrapper.memberroles[message.guild.id][request].append(role_id)

		# Alright, just send a message about it now!
		# The extra space is intentional, it's a 'hidden' indicator to
		# see whether the ban was made after the person left the guild
		ban_days = config.get_s('tntgb', message.guild.id)['ban_days']
		announcemsg = (
			'<@!{}>  has been banned for {ban_days} days by {} in {} for {}.'
		).format(
			request,
			message.author.display_name,
			message.channel.mention,
			splitargs[1],
			ban_days=ban_days,
		)
		content = '⛔ ' + announcemsg
		ban_log_channel = config.get_s('tntgb', message.guild.id)['ban_log_channel']
		ban_log_channel = message.guild.get_channel(ban_log_channel)
		sentmessage = await ban_log_channel.send(content)

		# Also set an expiry timer
		expirytime = utils.parsereltime(str(ban_days) + 'd')

		utils.addexpiryentry(
			message.guild.id,
			request,
			expirytime,
			e_channel=sentmessage.channel.id, e_message=sentmessage.id,
			e_newcontent='[LIFTED] ' + announcemsg,
			p_channel=ban_log_channel.id,
			p_content='The ban on <@!{}> has expired.'.format(request),
		)

		utils.rolexpiresave()
		await utils.handleExpiryTimer()
	else:
		# Okay, they are on the guild, so why not use \b?
		await b(client, message, **kwargs)

@shadow(auth=checks.is_tntgb_mod, aliases=['banrevert'], tntgbguildonly=True)
async def revertban(client, message, **kwargs):
	specialchannel = utils.getspecialchannel(message.guild)

	targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])

	if targetmember is None:
		embed = emb.error(bot.t['specify_user'])
		await specialchannel.send(embed=embed)
		return

	await utils.removeRestrictiveRoles(targetmember, message.guild)

	embed = emb.info('Ban on {} was reverted by {}.'.format(
			targetmember.mention, message.author.mention
		)
	)
	await specialchannel.send(embed=embed)

	# That member is also in the role cache. Right?
	if message.guild.id not in wrapper.rolexpires or \
	targetmember.id not in wrapper.rolexpires[message.guild.id]:
		embed = emb.warning('Could not find {} in the role cache!'.format(
				targetmember.mention
			)
		)
		await specialchannel.send(embed=embed)
		return

	# It's even longer this time
	thisexpiry = wrapper.rolexpires[message.guild.id][targetmember.id]
	if thisexpiry['msgedit_message'] != '0':
		thisexpiry['msgedit_newcontent'] = ''
		await utils.editexpirymessage(message.guild, thisexpiry)

	utils.removeexpiryentry(message.guild.id, targetmember.id)
	utils.rolexpiresave()

@shadow(auth=checks.is_admin, aliases=['tntgb_maint_p'], tntgbguildonly=True)
async def tntgb_maint(client, message, **kwargs):
	splitargs = kwargs['arguments'].split(' ')

	if kwargs['command'] == 'tntgb_maint_p':
		embed = emb.info('Opening prompt for `{}`'.format(splitargs[0]))
		await bot.reply(message, emb=embed)

	ban_log_channel = config.get_s('tntgb', message.guild.id)['ban_log_channel']
	ban_log_channel = message.guild.get_channel(ban_log_channel)

	while True:
		if kwargs['command'] == 'tntgb_maint_p':
			message2 = await client.wait_for(
				'message',
				check=lambda x: x.author == message.author and \
				x.channel == message.channel,
				timeout=120,
			)
			if message2 is None:
				embed = emb.info('Timed out, closing prompt')
				await bot.reply(message, emb=embed)
				break
			if message2.content == 'exit':
				embed = emb.info('Ok, closing prompt')
				await bot.reply(message, emb=embed)
				break
			splitargs[1] = message2.content
		output = ''
		if splitargs[0] == 'liftmsg':
			getmessage = await ban_log_channel.fetch_message(splitargs[1])
			content = getmessage.content
			if content.find('⛔') == -1:
				embed = emb.error('Cannot find the ⛔!')
				await bot.reply(message, emb=embed)
				return
			content = content.replace('⛔', '[LIFTED]', 1)
			await getmessage.edit(content=content)
			output = 'Edited successfully.'
		elif splitargs[0] == 'addtimer':
			getmessage = await ban_log_channel.fetch_message(splitargs[1])
			content = getmessage.content
			m = re.search('<@!?([0-9]+)>', content)
			if m is None:
				embed = emb.error('m is None! Maybe I couldn’t find the mention.')
				await bot.reply(message, emb=embed)
				return
			userid = m.group(1)
			ban_days = config.get_s('tntgb', message.guild.id)['ban_days']
			newexpires = utils.parsereltime(
				str(ban_days) + 'd',
				now=time.mktime(getmessage.created_at.timetuple()),
			)

			sentbybot = False
			if getmessage.author == client.user:
				sentbybot = True

				if content.find('⛔') == -1:
					embed = emb.error('Cannot find the ⛔!')
					await bot.reply(message, emb=embed)
					return
				content = content.replace('⛔', '[LIFTED]', 1)

				utils.addexpiryentry(
					message.guild.id,
					userid,
					newexpires,
					e_channel=getmessage.channel.id,
					e_message=getmessage.id,
					e_newcontent=content,
					p_channel=ban_log_channel.id,
					p_content='The ban on <@!{}> has expired.'.format(userid),
				)
			else:
				utils.addexpiryentry(
					message.guild.id,
					userid,
					newexpires,
					e_channel='0',
					e_message='0',
					e_newcontent='',
					p_channel=ban_log_channel.id,
					p_content='The ban on <@!{}> has expired.'.format(userid),
				)

			output = 'I found the member <@!{}>, and it expires {}. Also, the message was {} sent by me. Did I do it right?'.format(
				userid, utils.reltime(newexpires),
				"" if sentbybot else "not"
			)

			utils.rolexpiresave()
			await utils.handleExpiryTimer()

		embed = emb.success('Nothing appears to have gone wrong. Output:\n'+output)
		await bot.reply(message, emb=embed)

		if kwargs['command'] != 'tntgb_maint_p':
			break

@shadow(auth=checks.is_operator)
async def uploadfile(client, message, **kwargs):
	if kwargs['arguments'] is None:
		e = emb.error('You should probably enter in something.')
		await bot.reply(message, emb=e)
		return

	disalwfiles = ['bot_token.conf']

	if not os.path.abspath(kwargs['arguments']).startswith(os.getcwd()):
		e = emb.error('Cannot access paths above working directory.')
		await bot.reply(message, emb=e)
		return

	elif kwargs['arguments'] in disalwfiles:
		e = emb.error('``{file}`` contains sensitive info and cannot be uploaded.'.format(
			file=kwargs['arguments'],
			)
		)
		await bot.reply(message, emb=e)
		return

	try:
		await message.channel.send(
			bot.calculate_msg_start(message), file=discord.File(kwargs['arguments']),
		)
	except FileNotFoundError:
		e = emb.error('That file does not exist.')
		await bot.reply(message, emb=e)
	except IsADirectoryError:
		e = emb.error('That file is a directory.')
		await bot.reply(message, emb=e)


@shadow(auth=checks.is_mod, aliases=['blackunlist'], guildonly=True)
async def blacklist(client, message, **kwargs):
	tgtmem = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	if tgtmem is None:
		embed = emb.error('Unable to find that member. ' + bot.t['specify_user'])
		await bot.reply(message, emb=embed)
		return
	if not config.is_detached('blacklist', message.guild.id):
		config.detach('blacklist', message.guild.id)
	if kwargs['command'] == 'blacklist':
		if tgtmem.id in config.get_s('blacklist', message.guild.id):
			embed = emb.error('{0.mention} is already blacklisted.'.format(tgtmem))
			await bot.reply(message, emb=embed)
			return
		config.insert_s('blacklist', tgtmem.id, message.guild.id)
		config.saveconfig()
		embed = emb.success('Blacklisted {0.mention} from this server.'.format(tgtmem))
		await bot.reply(message, emb=embed)
		return
	elif kwargs['command'] == 'blackunlist':
		if tgtmem.id not in config.get_s('blacklist', message.guild.id):
			embed = emb.error('{0.mention} is not blacklisted.'.format(tgtmem))
			await bot.reply(message, emb=embed)
			return
		config.remove_s('blacklist', tgtmem.id, message.guild.id)
		config.saveconfig()
		embed = emb.success('Blackunlisted {0.mention} from this server.'.format(tgtmem))
		await bot.reply(message, emb=embed)
		return

@shadow(auth=checks.is_operator)
async def sudo(client, message, **kwargs):
	try:
		command = kwargs['arguments'].split(' ', 1)[0]
	except AttributeError:
		e = emb.error('You should probably put something in.')
		await bot.reply(message, emb=e)
		return

	# TODO: This is the command-parsing code copied from main.py, but with some changes.
	# Put the command-parsing code in a function instead.
	if command in commands:
		func = commands[command]
	else:
		# Check if it's an alias
		for c, p in commands.items():
			if p[2] is not None and command in p[2]:
				func = commands[c]
				break
		else:
			e = emb.warning(
				(
					'Invalid command. Input `\help` for'
					' a list of valid commands.'
				)
			)
			await bot.reply(message, emb=e)
			return
	if func[1] == checks.is_host and not func[1](message.author):
		e = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=e)
		return
	utils.logcommand(kwargs['command'], kwargs['arguments'], message)
	kwargs['command'] = command
	try:
		kwargs['arguments'] = kwargs['arguments'].split(' ', 1)[1]
		kwargs['clean_arguments'] = kwargs['clean_command_with_args'].split(' ', 2)[2]
	except IndexError:
		kwargs['arguments'] = None
		kwargs['clean_arguments'] = None
	kwargs['sudo'] = True
	await func[0](client, message, **kwargs)

@shadow(auth=checks.is_channel_manager, guildonly=True)
async def joinchannel(client, message, **kwargs):
	splitargs = kwargs['arguments'].split(' ')
	if len(splitargs) != 2:
		em = emb.error('Invalid amount of arguments passed.')
	if splitargs[0] == 'set':
		try:
			chan = client.get_channel(int(splitargs[1][2:-1]))
		except IndexError:
			em = emb.error('You should probably enter in a channel.')
			await bot.reply(message, emb=em)
			return
		if not chan:
			em = emb.error(
				(
					'Invalid channel. The channel must be a'
					' channel mention, i.e. in `<#ID>` form.'
				)
			)
			await bot.reply(message, emb=em)
			return
		if not config.is_detached('joinchannel', message.guild.id):
			config.detach('joinchannel', message.guild.id)
		config.set_s('joinchannel', chan.id, message.guild.id)
		config.saveconfig()
		em = emb.success(
			'Set {0.mention} to be the join channel for this server.'.format(chan)
		)
		await bot.reply(message, emb=em)
		return
	elif splitargs[0] == 'unset':
		if not config.is_detached('joinchannel', message.guild.id):
			config.detach('joinchannel', message.guild.id)
		config.restore_default('joinchannel', message.guild.id)
		config.saveconfig()
		em = emb.success('Unset the join channel for this server.')
		await bot.reply(message, emb=em)
		return
	elif splitargs[0] == 'get':
		chanid = config.get_s('joinchannel', message.guild.id)
		if chanid == '0':
			em = emb.info('There is no join channel set for this server.')
		else:
			chan = message.guild.get_channel(chanid)
			if chan:
				em = emb.info(
					(
						'The join channel is set to {0.mention}'
						' for this server.'
					).format(chan)
				)
			else:
				em = emb.info(
					(
						'The join channel is set to an invalid channel ID'
						' of **{0}**.'
					).format(chanid)
				)
		await bot.reply(message, emb=em)
	else:
		em = emb.error('Invalid arguments.')
		await bot.reply(message, emb=em)
		return

@shadow(guildonly=True)
async def testroleconditional(client, message, **kwargs):
	try:
		splitargs = kwargs['arguments'].split(' ')

		tgtmem = utils.match_input(message.guild.members, discord.Member, splitargs[0])
		if tgtmem is None:
			tgtmem = message.author
		embed = emb.success('Result: {}'.format(
				customcommands.parseroleconditional(
					splitargs[1], message.author, tgtmem
				)
			)
		)
	except (AttributeError, IndexError):
		embed = emb.error('Not enough arguments. See the `\help`')
	except customcommands.InvalidExpression as e:
		embed = emb.error('Invalid expression:\n{}'.format(str(e)))
	except customcommands.UnexpectedExprParserState as e:
		embed = emb.error('Unexpected parser state!\n{}'.format(str(e)))
		await bot.reply(message, emb=embed)
		raise

	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_admin, guildonly=True)
async def addcustomrolecommand(client, message, **kwargs):
	if kwargs['arguments'] is None:
		kwargs['arguments'] = ''
	splitargs = kwargs['arguments'].split(' ')
	if len(splitargs) < 6:
		embed = emb.error('Invalid amount of arguments specified, please see the `\help`')
		await bot.reply(message, emb=embed)
		return

	if splitargs[1] not in ('self', 'input'):
		embed = emb.error('`{}` is an invalid target, please see the `\help`'.format(
				utils.mdspecialchars(splitargs[1])
			)
		)
		await bot.reply(message, emb=embed)
		return
	if splitargs[2] not in ('no', 'input', 'input_strict', 'command') and \
	utils.parsereltime(splitargs[2]) is None:
		embed = emb.error('The expiry `{}` is invalid, please see the `\help`'.format(
				utils.mdspecialchars(splitargs[2])
			)
		)
		await bot.reply(message, emb=embed)
		return

	setlatestroled = True
	if splitargs[2] == 'no':
		setlatestroled = False
	elif splitargs[2] == 'command':
		splitargs[2] = 'no'

	ma = re.match('^\[([0-9]+(\,[0-9]+)*)?\]$', splitargs[4])
	mb = re.match('^\[([0-9]+(\,[0-9]+)*)?\]$', splitargs[5])
	if ma is None or mb is None:
		embed = emb.error((
				'The lists of roles must be surrounded with square '
				'brackets, and entries must be separated with commas.'
			)
		)
		await bot.reply(message, emb=embed)
		return
	if splitargs[4] == '[]':
		giveroles = []
	else:
		giveroles = list(
			map(int, splitargs[4][1:-1].split(','))
		)

	if splitargs[5] == '[]':
		takeroles = []
	else:
		takeroles = list(
			map(int, splitargs[5][1:-1].split(','))
		)

	if customcommands.exists(message.guild, splitargs[0]):
		embed = emb.error(
			(
				'The custom command `{}` already exists! '
				'You can remove it using `\\removecustomcommand`.'
			).format(
				utils.mdspecialchars(splitargs[0])
			)
		)
		await bot.reply(message, emb=embed)
		return

	builtin_alias_exists = False

	for _, p in commands.items():
		if p[2] is not None and splitargs[0] in p[2]:
			builtin_alias_exists = True
			break

	if builtin_alias_exists or splitargs[0] in commands:
		embed = emb.error('`{}` is already a built-in {} command!'.format(
				utils.mdspecialchars(splitargs[0]),
				utils.mdspecialchars('[\]')
			)
		)
		await bot.reply(message, emb=embed)
		return

	customcommands.add_custom_command(message.guild, splitargs[0],
		{
			'type': 'role',
			'precondition': splitargs[3],
			'target': splitargs[1],
			'expiry': splitargs[2],
			'setlatestroled': setlatestroled,
			'giverole': giveroles,
			'takerole': takeroles
		}
	)
	customcommands.save()

	embed = emb.success('Successfully added command `\{}`'.format(
			utils.mdspecialchars(splitargs[0])
		)
	)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_admin, guildonly=True)
async def addcustomaliascommand(client, message, **kwargs):
	if kwargs['arguments'] is None:
		kwargs['arguments'] = ''
	splitargs = kwargs['arguments'].split(' ')
	if len(splitargs) < 2:
		embed = emb.error('Invalid amount of arguments specified, please see the `\help`')
		await bot.reply(message, emb=embed)
		return

	if customcommands.exists(message.guild, splitargs[0]):
		embed = emb.error(
			(
				'The custom command `{}` already exists! '
				'You can remove it using `\\removecustomcommand`.'
			).format(
				utils.mdspecialchars(splitargs[0])
			)
		)
		await bot.reply(message, emb=embed)
		return

	builtin_alias_exists = 0  # 0 for false, 1 for command exists, 2 for aliased exists

	for _, p in commands.items():
		if p[2] is not None:
			if splitargs[0] in p[2]:
				builtin_alias_exists = 1
				break
			if splitargs[1] in p[2]:
				builtin_alias_exists = 2
				break

	if builtin_alias_exists == 1 or splitargs[0] in commands:
		embed = emb.error('`{}` is already a built-in {} command!'.format(
				utils.mdspecialchars(splitargs[0]),
				utils.mdspecialchars('[\]')
			)
		)
		await bot.reply(message, emb=embed)
		return
	if builtin_alias_exists == 2 or splitargs[1] in commands:
		embed = emb.error((
				'Sorry, you can only make aliases for custom '
				'commands, `{}` is a built-in {} command.'
			).format(
				utils.mdspecialchars(splitargs[1]),
				utils.mdspecialchars('[\]')
			)
		)
		await bot.reply(message, emb=embed)
		return

	if splitargs[0] == splitargs[1]:
		embed = emb.error((
				'Aliases do recursively call the run function... '
				'Maybe you can come up with something more creative?'
			)
		)
		await bot.reply(message, emb=embed)
		return

	customcommands.add_custom_command(message.guild, splitargs[0],
		{
			'type': 'alias',
			'to': splitargs[1]
		}
	)
	customcommands.save()

	if customcommands.exists(message.guild, splitargs[1]):
		embed = emb.success('Successfully added command `\{}`'.format(
				utils.mdspecialchars(splitargs[0])
			)
		)
	else:
		embed = emb.warning((
				'Successfully added command `\{}`, but note that '
				'`\{}` does not exist!'
			).format(
				utils.mdspecialchars(splitargs[0]),
				utils.mdspecialchars(splitargs[1])
			)
		)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_admin, guildonly=True)
async def removecustomcommand(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Please supply the name of the command to remove.')
		await bot.reply(message, emb=embed)
		return

	if not customcommands.exists(message.guild, kwargs['arguments']):
		embed = emb.error('The custom command to remove doesn’t exist.')
		await bot.reply(message, emb=embed)
		return

	customcommands.remove_custom_command(message.guild, kwargs['arguments'])
	customcommands.save()

	embed = emb.success('Command `\{}` has been removed.'.format(
			utils.mdspecialchars(kwargs['arguments'])
		)
	)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_admin, guildonly=True)
async def archive(client, message, **kwargs):
	# Note that this command currently only allows admins to run it, particularly so that we can
	# think about read and history permissions later. If opening it up to everyone, there should
	# be a detachable config option for the maximum limit for non-staff.

	if kwargs['arguments'] is None:
		em = emb.error('Please supply at least a channel mention.')
		await bot.reply(message, emb=em)
		return

	splitargs = kwargs['arguments'].split(' ')

	tgt = utils.match_input(message.guild.channels, discord.abc.GuildChannel, splitargs[0])
	if tgt is None:
		em = emb.error('Unable to find that channel. ' + bot.t['specify_channel'])
		await bot.reply(message, emb=em)
		return

	if not isinstance(tgt, discord.abc.Messageable):
		em = emb.error('Did not match a text channel - text-to-speech is not implemented.')
		await bot.reply(message, emb=em)
		return

	lim = 100
	if len(splitargs) >= 2:
		try:
			lim = int(splitargs[1])
		except ValueError:
			em = emb.error('Invalid limit specified.')
			await bot.reply(message, emb=em)
			return
		else:
			if lim < 1:
				lim = 1

	if lim > config.get_s('maxarchive'):
		# If we open this up to anyone, might also want to hide the limit.
		em = emb.error('The limit may not be higher than {}.'.format(
				config.get_s('maxarchive')
			)
		)
		await bot.reply(message, emb=em)
		return

	log = []

	msgs = tgt.history(limit=lim)
	try:
		async for m in msgs:
			log.append('[{}] {}#{}: {}'.format(
					time.strftime(
						config.get_s('timeformat', message.guild.id),
						m.created_at.timetuple()
					),
					m.author.name,
					m.author.discriminator,
					m.content
				)
			)
	except discord.errors.Forbidden:
		em = emb.error('Unable to get messages from that channel.')
		await bot.reply(message, emb=em)
		return

	log.reverse()
	textlog = '\n'.join(log)

	with tempfile.NamedTemporaryFile() as temp:
		temp.write(textlog.encode())
		temp.flush()
		try:
			await message.channel.send(
				'{} latest messages from {}'.format(
					lim, tgt.mention
				),
				file=discord.File(
					temp.name,
					'{}.{}.{}.log'.format(
						utils.safefilename(message.guild.name),

						# Better be futureproof
						utils.safefilename(tgt.name),

						int(time.time()),
					),
				),
			)
		except discord.HTTPException:
			em = emb.error('An error occurred while uploading the file.')
			await bot.reply(message, emb=em)

@shadow(auth=checks.is_host)
async def reload(client, message, **kwargs):
	embed = emb.success('Reloading.')
	utils.logcommand(kwargs['command'], kwargs['arguments'], message)
	await bot.reply(message, emb=embed)
	__main__ = __import__('__main__')
	if hasattr(__main__.recursive_reload, 'reloaded_modules'):
		__main__.recursive_reload.reloaded_modules = []
	__main__.reload_bot()

@shadow(auth=checks.is_admin, guildonly=True)
async def tntgb(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('You should probably type some arguments in.')
		await bot.reply(message, emb=embed)
		return

	guild_id = message.guild.id
	action = kwargs['arguments']

	if action == 'init':
		if config.is_detached('tntgb', guild_id) and \
		'active' in config.get_s('tntgb', guild_id) and \
		config.get_s('tntgb', guild_id)['active']:
			embed = emb.error(
				'TNTGB is already running in this server.'
				' You can stop it by doing `\\tntgb stop`.'
			)
			await bot.reply(message, emb=embed)
			return
		elif config.is_detached('tntgb', guild_id) and \
		'active' in config.get_s('tntgb', guild_id) and \
		not config.get_s('tntgb', guild_id)['active']:
			config.insert_dic_s('tntgb', 'active', True, guild_id)
			config.saveconfig()
			embed = emb.success('TNTGB has been initialized.')
			await bot.reply(message, emb=embed)
			return

		config.detach('tntgb', guild_id)
		if any(
			indice not in config.get_s('tntgb', guild_id) for indice in
			('ban_days', 'mod_mistake_lifts', 'mod_role', 'ban_log_channel')
			# Also required: unbanned_role, banned_role, internal_log_channel
		) or not (
			config.get_s('defaultroles', guild_id) and
			config.get_s('restrictiveroles', guild_id) and
			config.get_s('specialchannel', guild_id) != '0'
		):
			embed = emb.info(
				'Opening a prompt to set up TNTGB. Timeout length: 2 min.\n'
				'Type `exit` to exit.\n'
				'(If you’ve already set it up before, the settings were'
				' corrupted or broken in some way.)',
			)
			await bot.reply(message, emb=embed)

			questions = [
				'How many days would you like someone to be rolebanned?',

				'How many of the oldest bans should be lifted when a moderator'
				' makes a mistake?',

				'Please specify the moderator role, using anything from mentions'
				' and IDs to partial matches.',

				'Please specify the role that unbanned people will possess, using'
				' anything from mentions and IDs to partial matches.',

				'Please specify the banned role, using—you know what to use.',

				'Please specify the public channel where bans and lifts will be'
				' logged.',

				'Please specify the private channel where messages only the'
				' moderators should be able to see will be sent.',
			]
			responses = []
			question = 0
			while True:
				embed = emb.info(questions[question])
				await bot.reply(message, emb=embed)
				try:
					response = await client.wait_for(
						'message',
						check=lambda m: m.author == message.author and \
						m.channel == message.channel,
						timeout=120,
					)
				except asyncio.TimeoutError:
					embed = emb.info('Timed out, closing prompt.')
					await bot.reply(message, emb=embed)
					return

				if response.content == 'exit':
					embed = emb.info('Closing prompt.')
					await bot.reply(message, emb=embed)
					return

				responses.append(response.content)
				question += 1

				if question >= len(questions):
					break

			embed = emb.info('You’re all done, no more questions.')
			await bot.reply(message, emb=embed)

			def parse_answers(answers):
				parsed = []

				for number, value in enumerate(answers):
					if number in (0, 1):
						try:
							parsed.append(int(value))
						except TypeError:
							return False
					elif number in range(2, 5):
						value = utils.match_input(message.guild.roles, discord.Role, value)

						if value is None:
							return False
						else:
							parsed.append(value)
					elif number in range(5, 7):
						value = utils.match_input(message.guild.channels, discord.abc.GuildChannel, value)

						if value is None:
							return False
						else:
							parsed.append(value)

				return parsed

			values = parse_answers(responses)

			if not values:
				embed = emb.error(
					'One of the responses you entered is either'
					' not an integer, or not a role or channel,'
					' please try again.'
				)
				await bot.reply(message, emb=embed)
				return

			tntgb_specific_setup = {
				'ban_days': values[0],
				'mod_mistake_lifts': values[1],
				'mod_role': values[2].id,
				'ban_log_channel': values[5].id,
			}

			for key, indice in tntgb_specific_setup.items():
				config.insert_dic_s('tntgb', key, indice, guild_id)

			common_roles_setup = {
				'defaultroles': values[3].id,
				'restrictiveroles': values[4].id,
			}

			for key, indice in common_roles_setup.items():
				if not config.is_detached(key, guild_id):
					config.detach(key, guild_id)

				if indice in config.get_s(key, guild_id):
					continue

				config.insert_s(key, indice, guild_id)

			internal_log_channel = values[6].id

			if not config.is_detached('specialchannel', guild_id):
				config.detach('specialchannel', guild_id)

			config.set_s('specialchannel', internal_log_channel, guild_id)
			config.saveconfig()

			embed = emb.info('TNTGB has been set up and initialized.')
			await bot.reply(message, emb=embed)
			return
	elif action == 'stop':
		if config.is_detached('tntgb', guild_id) and \
		config.get_s('tntgb', guild_id)['active']:
			config.insert_dic_s('tntgb', 'active', False, guild_id)
			config.saveconfig()
			embed = emb.success('TNTGB has been stopped.')
			await bot.reply(message, emb=embed)
			return
		embed = emb.error('TNTGB is not running in this server.')
		await bot.reply(message, emb=embed)
		return

	try:
		action, value = kwargs['arguments'].split(' ', 1)
	except ValueError:
		embed = emb.error('Not enough arguments.')
		await bot.reply(message, emb=embed)
		return

	if action == 'set':
		try:
			setting, indice = value.split(' ', 1)
		except ValueError:
			embed = emb.error('Not enough arguments.')
			await bot.reply(message, emb=embed)
			return

		setting_types = {
			'ban_days': int,
			'mod_mistake_lifts': int,
			'mod_role': discord.Role,
			'banned_role': discord.Role,
			'unbanned_role': discord.Role,
			'ban_log_channel': discord.TextChannel,
			'internal_log_channel': discord.TextChannel,
		}

		if setting not in setting_types:
			embed = emb.error(
				'``{setting}`` is not a valid setting.'
				.format(setting=utils.wrapbackticks(setting)),
			)
			await bot.reply(message, emb=embed)
			return

		# Input checking

		errors = ''
		category = setting_types[setting]

		if category is int:
			try:
				indice = int(indice)
			except ValueError:
				errors += 'That is not a valid number.\n'
		elif category is discord.Role:
			indice = utils.match_input(message.guild.roles, discord.Role, indice)

			if indice is None:
				errors += 'That role doesn’t appear to exist.\n'

		elif category is discord.TextChannel:
			indice = utils.match_input(message.guild.channels, discord.abc.GuildChannel, indice)

			if indice is None:
				errors += 'That channel doesn’t appear to exist.\n'

		if errors:
			embed = emb.error(errors)
			await bot.reply(message, emb=embed)
			return

		if not config.is_detached('tntgb', guild_id):
			config.detach('tntgb', guild_id)

		if category in (discord.Role, discord.TextChannel):
			indice = indice.id
			if setting == 'banned_role' and \
			indice not in config.get_s('restrictiveroles', guild_id):
				config.restore_default('restrictiveroles', guild_id)
				config.insert_s('restrictiveroles', indice, guild_id)
			elif setting == 'unbanned_role' and \
			indice not in config.get_s('defaultroles', guild_id):
				config.restore_default('defaultroles', guild_id)
				config.insert_s('defaultroles', indice, guild_id)
			elif setting == 'mod_role':
				config.insert_dic_s('tntgb', setting, indice, guild_id)
			elif setting == 'ban_log_channel':
				config.insert_dic_s('tntgb', setting, indice, guild_id)
			elif setting == 'internal_log_channel':
				config.set_s('specialchannel', indice, guild_id)
		elif category is int:
			config.insert_dic_s('tntgb', setting, indice, guild_id)
		config.saveconfig()

		embed = emb.success(
			'Successfully set `{setting}` to that value.'
			.format(setting=setting),
		)
		await bot.reply(message, emb=embed)
		return
	embed = emb.error('Invalid action given.')
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def move(client, message, **kwargs):
	if kwargs['arguments'] is None:
		em = emb.error('Please supply at least a channel mention.')
		await bot.reply(message, emb=em)
		return

	splitargs = kwargs['arguments'].split(' ', 1)

	tgt = utils.match_input(message.guild.channels, discord.abc.GuildChannel, splitargs[0])
	if tgt is None:
		em = emb.error('Unable to find that channel. ' + bot.t['specify_channel'])
		await bot.reply(message, emb=em)
		return

	if not isinstance(tgt, discord.abc.Messageable):
		em = emb.error('You can only move discussions to messageable channels.')
		await bot.reply(message, emb=em)
		return

	# So was the conversation about anything?
	if len(splitargs) <= 1:
		convo_desc = 'current conversation'
	else:
		convo_desc = 'conversation about _{}_'.format(utils.mdspecialchars(splitargs[1]))

	emote_source = '👆'
	emote_target = '👇'
	emote_samech = '👍'

	# People can fill in the same channel, of course.
	if tgt == message.channel:
		em = discord.Embed(
			title=(
				emote_samech + ' '
				'Conversation kept in this channel'
			),
			description=(
				'Apparently {} _is_ the right channel for the {}. '
				'Keep it up, I guess!'
			).format(tgt.mention, convo_desc)
		)
		await bot.reply(message, emb=em)
		return

	msg_start = bot.calculate_msg_start(message)

	em_source = discord.Embed(
		title=(
			emote_source + ' '
			'Conversation moving to #{}'
		).format(utils.mdspecialchars(tgt.name)),
		description='Please continue the {} in {}.'.format(
			convo_desc, tgt.mention
		),
		colour=0x0000FF
	)
	sentmessage_source = await message.channel.send(msg_start, embed=em_source)

	url_source = sentmessage_source.jump_url

	em_target = discord.Embed(
		title=(
			emote_target + ' '
			'Conversation from #{} moving here'
		).format(utils.mdspecialchars(message.channel.name)),
		description=(
			'Please continue the {} from {} in this channel.\n\n'
			'**Link to previous part**: {}'
		).format(
			convo_desc, message.channel.mention, url_source
		),
		colour=0x0000FF
	)
	try:
		sentmessage_target = await tgt.send(msg_start, embed=em_target)

		url_target = sentmessage_target.jump_url

		# Now edit the source message
		em_source.description = (
			em_source.description + '\n\n'
			'**Link to next part**: ' + url_target
		)
	except discord.errors.Forbidden:
		# Turns out we can't send a message in the target channel!
		em_source.description = (
			em_source.description + '\n\n'
			'I don’t have permission to send a message in that channel myself, though.'
		)
	await sentmessage_source.edit(embed=em_source)

@shadow(aliases=['star'], guildonly=True)
async def _starboard(client, message, **kwargs):
	if kwargs['arguments'] is None:
		em = emb.error('Try `\help starboard` to know what arguments can be used.\nTo see the current starboard configuration, try `\starboard summarize_config`.')
		await bot.reply(message, emb=em)
		return

	splitargs = kwargs['arguments'].split(' ')
	action = splitargs[0]

	# We should have a starboard if you're doing anything other than making one.
	if config.get_s('starboard_channel', message.guild.id) == 0 and action != 'init':
		em = emb.error(
			(
				'There is currently no starboard channel set on this server. '
				'Please use `\{} init #channel` to set one.'
			).format(kwargs['command'])
		)
		await bot.reply(message, emb=em)
		return

	# First we have the commands that everyone can do (not many)
	if action == 'summarize_config':
		sa = config.get_s('starboard_active', message.guild.id)
		sc = config.get_s('starboard_channel', message.guild.id)
		sth = config.get_s('starboard_threshold', message.guild.id)
		snb = config.get_s('starboard_nostar_barrier', message.guild.id)
		stl = config.get_s('starboard_timelimit', message.guild.id)
		sic = config.get_s('starboard_ignoredchannels', message.guild.id)
		sanm = config.get_s('starboard_author_nostar_mode', message.guild.id)

		text = '' if sa else 'NOTE: The starboard is currently not active.\n'

		text += 'The starboard channel is <#{}>.'.format(sc)

		if snb == -1:
			text += ' The star emote is {}.'.format(
				starboard.guild_starboard_emote(True, message.guild.id)
			)
		else:
			text += ' The star emote is {}, the nostar emote is {}.'.format(
				starboard.guild_starboard_emote(True, message.guild.id),
				starboard.guild_starboard_emote(False, message.guild.id)
			)

		text += ' After {} star reaction{}, a message will be posted on the starboard.'.format(
			sth, 's' if sth != 1 else ''
		)

		if snb == 0:
			text += (
				' But, nostars will be subtracted from the number of stars.'
				' (so, {} star{} and 1 nostar will total to {} star{}).'
			).format(
				sth, 's' if sth != 1 else '',
				(sth-1), 's' if sth != 2 else ''
			)
		elif snb != -1:
			text += (
				' But, after a buffer of {} nostar{}, nostars will be subtracted'
				' from the number of stars.'
				' (so, {} star{} and {} nostars will total to {} star{}).'
			).format(
				snb, 's' if snb != 1 else '',
				sth, 's' if sth != 1 else '',
				(snb+1), # <- cannot be 1 logically
				(sth-1), 's' if sth != 2 else ''
			)

		text += ' Messages older than {} will be ignored.'.format(
			utils.reltime(stl, True, True, True)
		)

		#if sic:
		#	text += ' Note that messages cannot be starboarded in certain channels.'

		if sanm == 1 or snb == -1:
			text += ' Users cannot star their own messages.'
		elif sanm == 0:
			text += (
				' Users cannot star their own messages. When a user nostars their'
				' own message, it is counted as a veto and the message can no'
				' longer appear on the starboard.'
			)
		elif sanm == 2:
			text += ' Users cannot star or nostar their own messages.'

		if len(splitargs) > 1 and splitargs[1] == 'raw':
			await bot.reply(message, '```\n{}```'.format(text))
		else:
			await bot.reply(message, text)

		return

	# Now we check if the caller is at least a moderator, before we do the mod-only commands.
	if not checks.is_mod(message.author) and not kwargs['sudo']:
		em = emb.error(
			(
				'The action `{}` was not recognized or forbidden. '
				'Try `\help starboard` to know what arguments can be used.'
			).format(
				utils.mdspecialchars(action)
			)
		)
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=em)
		return

	if action in ('ban', 'unban'):
		if len(splitargs) == 1:
			em = emb.error('Too few arguments.')
			await bot.reply(message, emb=em)
			return

		tgtmem = utils.match_input(
			message.guild.members, discord.Member, splitargs[1]
		)
		if tgtmem is None:
			em = emb.error('Unable to find that member. ' + bot.t['specify_user'])
			await bot.reply(message, emb=em)
			return

		config.detach('starboard_bans', message.guild.id)

		if action == 'ban':
			if tgtmem.id in config.get_s('starboard_bans', message.guild.id):
				em = emb.warning(
					(
						'{} is already banned from '
						'interacting with the starboard.'
					).format(tgtmem.mention)
				)
				await bot.reply(message, emb=em)
				return

			config.insert_s('starboard_bans', tgtmem.id, message.guild.id)

			em = emb.success(
				(
					'{} has been banned from '
					'interacting with the starboard.'
				).format(tgtmem.mention)
			)
		elif action == 'unban':
			if tgtmem.id not in config.get_s('starboard_bans', message.guild.id):
				em = emb.warning(
					(
						'{} is already not banned from '
						'interacting with the starboard.'
					).format(tgtmem.mention)
				)
				await bot.reply(message, emb=em)
				return

			config.remove_s('starboard_bans', tgtmem.id, message.guild.id)

			em = emb.success(
				(
					'{} has been unbanned from '
					'interacting with the starboard.'
				).format(tgtmem.mention)
			)

		config.saveconfig()

		await bot.reply(message, emb=em)
		return

	# Now come the admin-only commands. If you can manage channels, you can add and delete
	# entire channels, so you're trusted enough to configure a starboard as well.
	if not checks.is_channel_manager(message.author) and not kwargs['sudo']:
		em = emb.error(
			(
				'The action `{}` was not recognized or forbidden.'
				'Try `\help starboard` to know what arguments can be used.'
			).format(
				utils.mdspecialchars(action)
			)
		)
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=em)
		return

	if action == 'init':
		# Set up a starboard
		if len(splitargs) == 1:
			em = emb.error('Too few arguments.')
			await bot.reply(message, emb=em)
			return

		new_starboard = utils.match_input(
			message.guild.channels, discord.abc.GuildChannel, splitargs[1]
		)
		if new_starboard is None:
			em = emb.error(
				'Unable to find that channel - it must already exist. '
				+ bot.t['specify_channel']
			)
			await bot.reply(message, emb=em)
			return

		# Okay, so this is happening. But did we already have a starboard here?
		existing_starboard_id = config.get_s('starboard_channel', message.guild.id)
		if existing_starboard_id != 0 \
		and config.get_s('starboard_active', message.guild.id):
			# Not if they haven't suspended it first! Just in case.
			em = emb.warning(
				(
					'You already have a starboard at <#{}>. '
					'If you want to switch to a different channel, '
					'you must suspend the starboard first.'
				).format(existing_starboard_id)
			)
			await bot.reply(message, emb=em)
			return

		# Remove references to any existing starboard messages which might be left
		starboard.detach_all_starboard_messages(message.guild.id)

		# Detach all configuration, if already detached this won't have effect
		config.detach('starboard_active', message.guild.id)
		config.detach('starboard_channel', message.guild.id)
		config.detach('starboard_threshold', message.guild.id)
		config.detach('starboard_star', message.guild.id)
		config.detach('starboard_nostar', message.guild.id)
		config.detach('starboard_nostar_barrier', message.guild.id)
		config.detach('starboard_timelimit', message.guild.id)
		config.detach('starboard_ignoredchannels', message.guild.id)
		config.detach('starboard_author_nostar_mode', message.guild.id)
		config.detach('starboard_bans', message.guild.id)
		config.detach('starboard_permalink', message.guild.id)

		# Suspend it at first
		config.set_s('starboard_active', False, message.guild.id)
		config.set_s('starboard_channel', new_starboard.id, message.guild.id)

		# Also I guess by default we should add NSFW channels to the ignored channels list
		nsfw_added = False
		nsfw_text = ''
		if existing_starboard_id == 0 \
		and not config.get_s('starboard_ignoredchannels', message.guild.id):
			for chan in message.guild.channels:
				try:
					if chan.is_nsfw():
						config.insert_s(
							'starboard_ignoredchannels',
							chan.id, message.guild.id
						)
						nsfw_added = True
				except AttributeError:
					# VoiceChannel or CategoryChannel
					pass

			if nsfw_added:
				nsfw_text = (
					' All NSFW channels have been ignored by default, but can '
					'be unignored. (New NSFW channels will not be ignored '
					'automatically upon their creation.)'
				)

		config.saveconfig()

		em = emb.success(
			(
				'Starboard channel set to {}.\n'
				'To see the configuration, use `\\{starcmd} summarize_config`.\n'
				'To change the threshold, use `\\{starcmd} set threshold 5`.\n'
				'To change the star/nostar emotes, use `\\{starcmd} set star` '
				'or `\\{starcmd} set nostar`.\n'
				'To change the nostar barrier, use `\\{starcmd} set '
				'nostar_barrier 2`, or `\\{starcmd} set nostar_barrier -1` to '
				'disable nostars.\n'
				'Other settings can be changed as well, see '
				'https://gitgud.io/infoteddy/bracketed_backslash/wikis/Starboard '
				'for all details. That page also contains advice for a smooth '
				'transition from another bot’s starboard.\n'
				'To ignore a channel for the starboard, use `\\{starcmd} ignore '
				'#channel`.{nsfw_text}\n'
				'**The starboard is suspended by default.** Once you’re ready, use `\\{starcmd} unsuspend` to activate it.'
			).format(
				new_starboard.mention,
				starcmd=kwargs['command'],
				nsfw_text=nsfw_text
			)
		)
		await bot.reply(message, emb=em)
	elif action == 'set':
		if len(splitargs) == 1 \
		or splitargs[1] not in ('star', 'nostar') and len(splitargs) == 2:
			em = emb.error('Too few arguments.')
			await bot.reply(message, emb=em)
			return
		setting = splitargs[1]

		if setting in ('star', 'nostar'):
			if setting == 'star':
				em = emb.info(
					(
						'**Please specify the star emote to use, by adding '
						'it as a reaction to this message.** This can be '
						'an emoji, or a custom emote from this server. ⭐ '
						'is recommended. If you choose an emoji that can be '
						'affected by skin tone modifiers, then choose the '
						'yellow variant in order to support all skin tones.'
					)
				)
				success = 'Star set to {}'
			else:
				em = emb.info(
					(
						'**Please specify the nostar emote to use, by '
						'adding it as a reaction to this message.** If you '
						'don’t want to use the nostar feature, then react '
						'with anything you like (but not a custom emote '
						'from a different server), you can disable the '
						'nostar feature.'
					)
				)
				success = 'Nostar set to {}'
			question_message = await message.channel.send(
				bot.calculate_msg_start(message), embed=em
			)
			try:
				reaction, user = await client.wait_for(
					'reaction_add',
					check=lambda r, u: u == message.author \
					and r.message.id == question_message.id, # <- try w/o id?!!?
					timeout=120
				)
			except asyncio.TimeoutError:
				em = emb.error('Timed out.')
				await bot.reply(message, emb=em)
				return
			# Now, is it some kind of homebrew emote, or a Unicode emoji?
			if isinstance(reaction.emoji, discord.PartialEmoji):
				# Okay, we can't see it, must be from somewhere else.
				em = emb.error(
					'You can not use custom emotes from other servers.'
				)
				await bot.reply(message, emb=em)
				return
			elif isinstance(reaction.emoji, discord.emoji.Emoji):
				# Some kind of homebrew emote then. But it must be from here.
				if reaction.emoji.guild != message.guild:
					em = emb.error(
						'You can not use custom emotes from other servers.'
					)
					await bot.reply(message, emb=em)
					return
				# Don't allow animated emotes, that's unfair plus requires an "a"
				if reaction.emoji.animated:
					em = emb.error(
						'You can not use animated emotes.'
					)
					await bot.reply(message, emb=em)
					return
				value = str(reaction.emoji.id)
			else:
				# Look kids, THIS is an emoji.
				value = reaction.emoji

			config.detach('starboard_' + setting, message.guild.id)
			config.set_s('starboard_' + setting, value, message.guild.id)
			config.saveconfig()

			em = emb.success(success.format(reaction.emoji))
			await bot.reply(message, emb=em)

			return
		if setting == 'timelimit':
			# Also kind of a special case
			config.detach('starboard_timelimit', message.guild.id)
			try:
				config.set_s('starboard_timelimit', splitargs[2], message.guild.id)
			except ValueError:
				em = emb.error(
					(
						'Invalid relative time. Please input a relative time '
						'in the format `[#d][#h][#m][#s]`, for example: '
						'`3d12h`, `1h`, `3d`, `48h`, `1d2h3m4s`, `1d20s` or '
						'whatever combination you can think of. The units '
						'have to be in the correct order, though.'
					)
				)
				await bot.reply(message, emb=em)
				return
			if config.get_s('starboard_timelimit', message.guild.id) > 863999999:
				# Do a maximum of 9999d23h59m59s
				config.set_s(
					'starboard_timelimit', '9999d23h59m59s', message.guild.id
				)

			em = emb.success('Time limit set to {}.'.format(
					utils.reltime(
						config.get_s('starboard_timelimit', message.guild.id),
						True, True, True
					)
				)
			)
			await bot.reply(message, emb=em)
			return

		if setting in ('threshold', 'nostar_barrier'):
			# Simple integers, let's do this the pythonic way
			try:
				value = int(splitargs[2])
			except ValueError:
				em = emb.error('`{}` is not a valid integer.'.format(
						utils.mdspecialchars(splitargs[2])
					)
				)
				await bot.reply(message, emb=em)
				return
			if setting == 'threshold':
				value = max(1, min(99999, value))
				success = (
					'Messages will now go on the starboard after {} star{s}.'
				).format(
					value, s='s' if value != 1 else ''
				)
			elif setting == 'nostar_barrier' and value == -1:
				success = 'Nostars disabled.'
			elif setting == 'nostar_barrier':
				value = max(0, min(99998, value))
				success = 'Nostar barrier set to {} nostar{s}.'.format(
					value, s='s' if value != 1 else ''
				)
		elif setting in ('author_nostar_mode', 'permalink'):
			if splitargs[2] not in ('0', '1', '2'):
				em = emb.error('Please enter a value of 0, 1 or 2.')
				await bot.reply(message, emb=em)
				return
			value = int(splitargs[2])
			if setting == 'author_nostar_mode':
				if value == 0:
					success = 'Author nostar mode set to 0 (veto)'
				elif value == 1:
					success = 'Author nostar mode set to 1 (like other people)'
				elif value == 2:
					success = 'Author nostar mode set to 2 (forbidden)'
			elif setting == 'permalink':
				if value == 0:
					success = 'Permalinks set to hidden.'
				elif value == 1:
					success = 'Permalinks set to in message content.'
				elif value == 2:
					success = 'Permalinks set to in embed.'
		else:
			em = emb.error('`{}` is not a recognized config option.'.format(
					utils.mdspecialchars(setting)
				)
			)
			await bot.reply(message, emb=em)
			return

		# Ensure this option is detached, just to make sure.
		config.detach('starboard_' + setting, message.guild.id)
		config.set_s('starboard_' + setting, value, message.guild.id)
		config.saveconfig()

		em = emb.success(success)
		await bot.reply(message, emb=em)
	elif action == 'suspend':
		config.detach('starboard_active', message.guild.id)
		config.set_s('starboard_active', False, message.guild.id)
		config.saveconfig()

		em = emb.success('The starboard on this server has been suspended.')
		await bot.reply(message, emb=em)
	elif action == 'unsuspend':
		config.detach('starboard_active', message.guild.id)
		config.set_s('starboard_active', True, message.guild.id)
		config.saveconfig()

		em = emb.success('The starboard on this server has been unsuspended.')
		await bot.reply(message, emb=em)
	elif action in ('ignore', 'unignore'):
		if len(splitargs) == 1:
			em = emb.error('Too few arguments.')
			await bot.reply(message, emb=em)
			return

		tgtchan = utils.match_input(
			message.guild.channels, discord.abc.GuildChannel, splitargs[1]
		)
		if tgtchan is None:
			em = emb.error('Unable to find that channel. ' + bot.t['specify_channel'])
			await bot.reply(message, emb=em)
			return

		config.detach('starboard_ignoredchannels', message.guild.id)

		if action == 'ignore':
			if tgtchan.id in config.get_s(
				'starboard_ignoredchannels', message.guild.id
			):
				em = emb.warning(
					(
						'{} is already ignored '
						'for the starboard.'
					).format(tgtchan.mention)
				)
				await bot.reply(message, emb=em)
				return

			config.insert_s('starboard_ignoredchannels', tgtchan.id, message.guild.id)

			em = emb.success(
				(
					'Messages in {} can now no longer '
					'appear on the starboard.'
				).format(tgtchan.mention)
			)
		elif action == 'unignore':
			if tgtchan.id not in config.get_s(
				'starboard_ignoredchannels', message.guild.id
			):
				em = emb.warning(
					(
						'{} is already not ignored '
						'for the starboard.'
					).format(tgtchan.mention)
				)
				await bot.reply(message, emb=em)
				return

			config.remove_s('starboard_ignoredchannels', tgtchan.id, message.guild.id)

			em = emb.success(
				(
					'Messages in {} can now appear '
					'on the starboard again.'
				).format(tgtchan.mention)
			)

		config.saveconfig()

		await bot.reply(message, emb=em)
	elif action == 'scan_danny':
		# Scan a channel for messages by R. Danny to aid with a smooth transition
		# First argument is channel to scan, second is the ID of R. Danny
		if len(splitargs) < 3:
			em = emb.error('Too few arguments.')
			await bot.reply(message, emb=em)
			return

		scan_channel = utils.match_input(
			message.guild.channels, discord.abc.GuildChannel, splitargs[1]
		)
		if scan_channel is None:
			em = emb.error(
				'Unable to find that channel - it must already exist. '
				+ bot.t['specify_channel']
			)
			await bot.reply(message, emb=em)
			return

		# Just so we don't accidentally pollute the database with nonsense,
		# only do this if the starboard is suspended.
		if config.get_s('starboard_active', message.guild.id):
			em = emb.warning('Please suspend the starboard first to take this action.')
			await bot.reply(message, emb=em)
			return

		try:
			count = starboard.ignore_danny_stars(
				[m async for m in scan_channel.history(limit=200)], int(splitargs[2])
			)
		except ValueError:
			em = emb.error('Please enter a valid user ID.')
			await bot.reply(message, emb=em)
			return

		em = emb.success('{} messages matched.'.format(count))
		await bot.reply(message, emb=em)
	else:
		em = emb.error(
			(
				'The action `{}` was not recognized. '
				'Try `\help starboard` to know what arguments can be used.'
			).format(action)
		)
		await bot.reply(message, emb=em)

@shadow(aliases=['rr'], guildonly=True)
async def reactroles(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Try `\\help reactroles` to know what arguments can be used.')
		await bot.reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ')
	action = splitargs[0]

	async def interactive_make_message() -> (list[discord.Role], list[discord.Emoji]):
		embed = emb.info(
			'React to this message with the emojis you want to use. Only '
			'reactions made by you will be processed. (This is just to check that '
			'those are valid emojis and for Discord’s reaction limit. You’ll specify '
			'the roles later.)\n'
			'\n'
			'Type `done` when you’re done, `cancel` to cancel. This prompt times out '
			'in 5 minutes.'
		)
		prompt = await bot.reply(message, emb=embed)

		try:
			response = await client.wait_for(
				'message',
				check=lambda m: (m.author == message.author
				and m.channel == message.channel),
				timeout=300,
			)
		except asyncio.TimeoutError:
			embed = emb.info('Timed out, closing prompt.')
			await bot.reply(message, emb=embed)
			return

		# Actually anything other than 'done' will close the prompt
		if response.content.lower() != 'done':
			embed = emb.info('Closing prompt.')
			await bot.reply(message, emb=embed)
			return

		# Let's take a look at what they reacted with. We DO need to re-fetch the message
		try:
			prompt = await message.channel.fetch_message(prompt.id)
		except discord.errors.NotFound:
			embed = emb.error('My message got deleted!')
			await bot.reply(message, emb=embed)
			return
		except discord.errors.Forbidden:
			embed = emb.error('I no longer have permission to view message history!')
			await bot.reply(message, emb=embed)
			return

		emojis = []
		for idx, reaction in enumerate(prompt.reactions):
			# No one else can interfere with this prompt
			# But, ugh, a network request for every reaction? C'mon Discord
			# TODO: Rework this whole thing to be based on waiting for 'reaction_add'
			# events to circumvent having to do this network request. But we'll have to
			# be waiting for both a message and a reaction at the same time, and we'll
			# quickly be plunged into async hell, bleh
			users = [user async for user in reaction.users()]
			user_ids = (user.id for user in users)

			# After a million years waiting for the network request, we'll finally know
			# if someone has been adding reactions as a prank
			if message.author.id not in user_ids:
				continue

			# And now process it finally
			if isinstance(reaction.emoji, discord.PartialEmoji):
				# Custom emote, but we can't see it, and if we can't see it, it
				# must not be from here. So I can't use it
				embed = emb.error(
					(
						'Error with reaction #{}: '
						'You can not use custom emotes from other servers.'
					).format(idx + 1)
				)
				await bot.reply(message, emb=embed)
				return

			if isinstance(reaction.emoji, discord.emoji.Emoji):
				# Custom emote
				if reaction.emoji.guild != message.guild:
					# But not from here. You expect me to be able to react with
					# an emote I can't use?
					embed = emb.error(
						(
							'Error with reaction #{}: '
							'You can not use custom emotes from other servers.'
						).format(idx + 1)
					)
					await bot.reply(message, emb=embed)
					return
				# Unlike starboard, animated emotes are allowed because bots
				# basically have Nitro and can react with them
			else:
				# Unicode emoji
				pass

			emoji = reaction.emoji
			emojis.append(emoji)

		embed = emb.info(
			'Type in the names of each role for each emoji, on each line, in one '
			'message. IDs will work too. Example:\n'
			'```\n'
			'Role 1\n'
			'Role 2\n'
			'Role 3\n'
			'```\n'
			'\n'
			'This prompt times out in 5 minutes.'
		)
		await bot.reply(message, emb=embed)

		try:
			response = await client.wait_for(
				'message',
				check=lambda m: (m.author == message.author
				and m.channel == message.channel),
				timeout=300,
			)
		except asyncio.TimeoutError:
			embed = emb.info('Timed out, closing prompt.')
			await bot.reply(message, emb=embed)
			return

		lines = response.content.split('\n')
		if len(lines) != len(emojis):
			embed = emb.error('You don’t have the same amount of lines as emojis!')
			await bot.reply(message, emb=embed)
			return

		roles = []
		for idx, line in enumerate(lines):
			role = utils.match_input(message.guild.roles, discord.Role, line)
			if role is None:
				embed = emb.error(
					'Unable to find role #{}!'.format(
						idx + 1,
					),
				)
				await bot.reply(message, emb=embed)
				return

			roles.append(role)

		return roles, emojis

	async def post_message(
		roles: list[discord.Role], emojis: list[discord.Emoji],
	) -> Optional[discord.Message]:
		reaction_roles_list = []
		for role, emoji in zip(roles, emojis):
			reaction_roles_list.append(f'{emoji} {role.name}')

		embed = discord.Embed(
			description='\n'.join(reaction_roles_list),
		)
		try:
			reaction_roles_message = await channel.send(embed=embed)
		except discord.errors.Forbidden:
			embed = emb.error(f'I don’t have permission to post in {channel.mention}!')
			await bot.reply(message, emb=embed)
			return

		for emoji in emojis:
			try:
				await reaction_roles_message.add_reaction(emoji)
			except discord.errors.Forbidden:
				embed = emb.error(f'I don’t have permission to react in {channel.mention}!')
				await bot.reply(message, emb=embed)
				return
			except discord.errors.NotFound:
				embed = emb.error(f':{emoji.name}: got deleted!')
				await bot.reply(message, emb=embed)
				return
			except discord.errors.HTTPException:
				embed = emb.error('Somehow there are too many reactions on my reaction roles message?')
				await bot.reply(message, emb=embed)
				return

		return reaction_roles_message

	if action == 'create':
		if (not checks.is_channel_manager(message.author)
		or not checks.is_role_manager(message.author)) and not kwargs['sudo']:
			embed = emb.error(bot.t['you_no_permission'])
			utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
			await bot.reply(message, emb=embed)
			return

		entries = []

		while True:
			result = await interactive_make_message()

			if result is None:
				return

			entries.append(result)

			embed = emb.info(
				'Do you need another message of reaction roles? (Use this if you’ve hit the limit on the amount of reactions a single Discord message can have.) Type `yes` if so.\n'
				'\n'
				'This prompt times out in 5 minutes.'
			)
			await bot.reply(message, emb=embed)

			try:
				response = await client.wait_for(
					'message',
					check = lambda m: (m.author == message.author
					and m.channel == message.channel),
					timeout=300,
				)
			except asyncio.TimeoutError:
				embed = emb.info('Timed out, closing prompt.')
				await bot.reply(message, emb=embed)
				return

			if response.content.lower() == 'yes':
				continue

			break

		embed = emb.info(
			'Tell me the maximum amount of roles from this group that users can have at a time. Type `0` for no limit.\n'
			'\n'
			'This prompt times out in 5 minutes.'
		)
		await bot.reply(message, emb=embed)

		try:
			response = await client.wait_for(
				'message',
				check = lambda m: (m.author == message.author
				and m.channel == message.channel),
				timeout=300,
			)
		except asyncio.TimeoutError:
			embed = emb.info('Timed out, closing prompt.')
			await bot.reply(message, emb=embed)
			return

		try:
			max_count = int(response.content)
		except ValueError:
			embed = emb.error(
				'``{}`` is not a valid integer!'.format(
					utils.wrapbackticks(response.content[:100])
				)
			)
			await bot.reply(message, emb=embed)
			return

		embed = emb.info(
			'Please reply with the channel you want the reaction roles message in.\n'
			'\n'
			'This prompt times out in 5 minutes.'
		)
		await bot.reply(message, emb=embed)

		try:
			response = await client.wait_for(
				'message',
				check=lambda m: (m.author == message.author
				and m.channel == message.channel),
				timeout=300,
			)
		except asyncio.TimeoutError:
			embed = emb.info('Timed out, closing prompt.')
			await bot.reply(message, emb=embed)
			return

		channel = utils.match_input(
			message.guild.text_channels,
			discord.abc.GuildChannel,
			response.content,
		)
		if channel is None:
			embed = emb.error('Unable to find that channel!')
			await bot.reply(message, emb=embed)
			return

		batch = []

		for roles, emojis in entries:
			reaction_roles_message = await post_message(roles, emojis)

			if reaction_roles_message is None:
				return

			for role, emoji in zip(roles, emojis):
				if hasattr(emoji, 'id'):
					# Custom
					emoji = emoji.id

				batch.append(
					(
						reaction_roles_message.id,
						role.id,
						emoji,
					)
				)

		reaction_roles.add_reaction_group(
			batch,
			channel_id=channel.id,
			max_count=max_count
		)

		reaction_roles.db_commit()

		# Also enable the 'reaction_roles' config for this guild, otherwise it won't work
		config.detach('reaction_roles', message.guild.id)
		config.set_s('reaction_roles', True, message.guild.id)
		config.saveconfig()

		embed = emb.success(f'Successfully added reaction roles to {channel.mention}.')
		await bot.reply(message, emb=embed)
	else:
		embed = emb.error(
			f'The action `{action}` was not recognized. '
			'Try `\\help reactroles` to know what arguments can be used.'
		)
		await bot.reply(message, emb=embed)

@shadow(aliases=['emojis'], guildonly=True)
async def emotes(client, message, **kwargs):
	emoji_list = []

	for emoji in message.guild.emojis:
		emoji_list.append(str(emoji))

	emojis = '\n'.join(emoji_list)

	embed = discord.Embed(
		title='Server emotes',
		description=emojis,
		colour=message.guild.me.colour,
	)

	utils.paginate_description(embed, max_length=2048)

	await bot.reply(message, emb=embed)

@shadow(aliases=['rw'])
async def randwiki(client, message, **kwargs):
	try:
		import wikipedia
	except ModuleNotFoundError:
		embed = emb.error(
			'The bot host doesn’t have the `wikipedia` library installed. '
			'Please contact them to install it!'
		)
		return await bot.reply(message, emb=embed)

	# Originally from github.com/TRottinger/discord-randomify
	# Originally licensed under MIT
	page = wikipedia.random(1)

	try:
		info = wikipedia.page(page)
	except wikipedia.DisambiguationError as e:
		info = wikipedia.page(random.choice(e.options))

	embed = discord.Embed(title='Random Wikipedia Article', colour=discord.Colour.orange())
	embed.add_field(name=info.original_title, value=info.url, inline=False)
	embed.add_field(name='Summary', value=info.summary[:1024], inline=False)

	await bot.reply(message, emb=embed)

@shadow(aliases=['temp'])
async def temperature(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('A temperature needs to be specified.')
		await bot.reply(message, emb=embed)
		return

	negative = kwargs['arguments'][0] == '-'
	if negative:
		arguments = kwargs['arguments'][1:]
	else:
		arguments = kwargs['arguments']

	numbers = []

	for character in arguments:
		if character.isdigit():
			numbers.append(character)
		else:
			break

	if not numbers:
		embed = emb.error('The argument does not contain numbers.')
		await bot.reply(message, emb=embed)
		return

	original = int(''.join(numbers))
	if negative:
		original = -original
	unit = arguments[-1].upper()

	if unit == 'F':
		# Fahrenheit to Celsius
		converted = (original - 32) / 1.8
		converted = round(converted, 5)
		embed = emb.info(f'{original}\xB0F is {converted}\xB0C.')
	elif unit == 'C':
		# Celsius to Fahrenheit
		converted = original * 1.8 + 32
		converted = round(converted, 5)
		embed = emb.info(f'{original}\xB0C is {converted}\xB0F.')
	else:
		embed = emb.error('Invalid unit of temperature.')

	await bot.reply(message, emb=embed)
