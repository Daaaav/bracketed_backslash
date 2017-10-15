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
import contextlib
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

import discord

import bot
import checks
import col
import config
import customcommands
import emb
import events
import hangman
import images
import op_ids
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
	embed.add_field(name='Messages in Cache', value=str(len(client._connection._messages)))
	utils.logcommand(kwargs['command'], kwargs['arguments'], message)
	await bot.reply(message, emb=embed)
	os.execv(sys.executable, ['python'] + sys.argv)

@shadow(auth=checks.is_host)
async def kill(client, message, **kwargs):
	embed = emb.success('Killing.', True)
	embed.add_field(name='Uptime', value=utils.reltime(wrapper.boottimeunix, True))
	utils.logcommand(kwargs['command'], kwargs['arguments'], message)
	await bot.reply(message, emb=embed)
	await client.logout()
	sys.exit(42)

@shadow(auth=checks.is_operator)
async def _config(client, message, **kwargs):
	if message.guild and \
	message.guild.id == op_ids.ids['opguild'] and \
	not checks.is_host(message.author):
		embed = emb.error(bot.t['no_permission'])
		utils.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await bot.reply(message, emb=embed)
		return
	if kwargs['arguments'] is None:
		content = (
			'You can use the following options:\n'
			'`\config list`\n'
			'`\config listhidden`\n'
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
	elif kwargs['arguments'] == 'list' or kwargs['arguments'] == 'listhidden':
		content = '```css'
		for c in config.s:
			if (kwargs['arguments'] == 'list' and not config.get_shown(c)) or \
			(kwargs['arguments'] == 'listhidden' and config.get_shown(c)):
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

	splitargs = kwargs['arguments'].split(' ', 2)

	editingmaster = True

	if len(splitargs) == 1:
		embed = emb.error('Too few arguments.')
		await bot.reply(message, emb=embed)
		return

	if splitargs[0] == 'set':
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
			config.set_s(splitargs[1], splitargs[2], message.guild.id)
			editingmaster = not config.is_detached(splitargs[1], message.guild.id)
		except AttributeError:
			config.set_s(splitargs[1], splitargs[2])
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
			echocolor = discord.Embed.Empty
		em = discord.Embed(description=displayarguments, colour=echocolor)
		replyargs = {'emb': em}
	else:
		displayarguments = arguments[:2000-len(msg_start)]
		replyargs = {'message': displayarguments}
	await bot.reply(message, **replyargs)

@shadow()
async def _hangman(client, message, **kwargs):
	if message.channel.id in wrapper.hangman_games and \
	wrapper.hangman_games[message.channel.id].active:
		embed = emb.error((
				'Hangman is already running in this channel. It can be '
				'aborted by the starter or by a mod with `\stophangman`.'
			)
		)
		await bot.reply(message, emb=embed)
		return
	if kwargs['arguments'] is None:
		embed = emb.error('Please specify a word. (Yeah, for a bit, you need to send the word in public, we’ll change that Soon™)')
		await bot.reply(message, emb=embed)
		return
	if not kwargs['arguments'].isalpha():
		embed = emb.error('Words can only consist of letters A-Z')
		await bot.reply(message, emb=embed)
		return
	if len(kwargs['arguments']) > 50:
		embed = emb.error('Sorry, but your word is too long. It can be 50 characters max.')
		await bot.reply(message, emb=embed)
		return

	hm_inst = hangman.HangmanGame(kwargs['arguments'], message.author)
	wrapper.hangman_games[message.channel.id] = hm_inst

	content = (
		'New game of hangman initiated by {starter} with a custom word. Guess letters '
		'by chatting "{inv}" followed by the letter (for example {inv}a) or the word. '
		'{attempts} attempts left.\n{worddisp}'
	).format(
		starter=hm_inst.starter.mention,
		inv=bot.hangmaninvoker,
		attempts=hm_inst.maxmistakes,
		worddisp=hm_inst.worddisp()
	)
	await bot.reply(message, content)

@shadow()
async def stophangman(client, message, **kwargs):
	if message.channel.id not in wrapper.hangman_games or \
	not wrapper.hangman_games[message.channel.id].active:
		embed = emb.error('Can’t abort hangman because it’s not running.')
		await bot.reply(message, emb=embed)
		return
	hm_inst = wrapper.hangman_games[message.channel.id]
	if not checks.is_mod(message.author) and not hm_inst.isstarter(message.author):
		embed = emb.error('Can’t abort hangman because you haven’t started this game.')
		await bot.reply(message, emb=embed)
		return

	hm_inst.stop()
	content = 'Game of hangman aborted. The word was: **{}**'.format(hm_inst.word)
	await bot.reply(message, content)
	del wrapper.hangman_games[message.channel.id]

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
	if targetmember.game is None:
		memberhasgame = False
		displaygamestatus = 'Not Playing'
		displaygamename = 'Not Playing'
		displaygameurlstatus = 'No Stream Link'
		displaygameurl = 'No Stream Link'
	else:
		memberhasgame = True
	if memberhasgame:
		if targetmember.game.type == 0 or targetmember.game.type is None:
			displaygamestatus = 'Playing'
			displaygamename = utils.mdspecialchars(targetmember.game.name)
		if targetmember.game.type == 1:
			displaygamestatus = 'Streaming'
			displaygamename = utils.mdspecialchars(targetmember.game.name)
		if targetmember.game.url is None:
			displaygameurlstatus = 'No Stream Link'
			displaygameurl = 'No Stream Link'
		else:
			displaygameurlstatus = 'Stream Link'
			displaygameurl = utils.mdspecialchars(targetmember.game.url)
	embed = discord.Embed(description='Matched ' + displaymatch, colour=targetmember.colour)
	embed.set_image(url=targetmember.avatar_url)
	embed.add_field(name='Nickname' if targetmember.nick is not None else 'No Nickname', value=utils.mdspecialchars(targetmember.nick) if targetmember.nick is not None else 'No Nickname')
	embed.add_field(name='Username', value=utils.mdspecialchars(targetmember.name))
	embed.add_field(name='Discriminator', value='#{}'.format(targetmember.discriminator))
	embed.add_field(name='User ID', value=targetmember.id)
	embed.add_field(name='Bot', value='Yes' if checks.is_bot(targetmember) else 'No')
	embed.add_field(name=displaygamestatus, value=displaygamename)
	embed.add_field(name=displaygameurlstatus, value=displaygameurl)
	embed.add_field(name='Status', value='Do Not Disturb' if str(targetmember.status) == 'dnd' else str(targetmember.status).title())
	embed.add_field(name='Default Avatar', value=str(targetmember.default_avatar).title())
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
			apnd = '**{name}** ({id})\n'.format(
				name=utils.mdspecialchars(c.name),
				id=c.id,
			)
			if isinstance(c, discord.TextChannel):
				tchans += apnd
				tchanc += 1
			elif isinstance(c, discord.VoiceChannel):
				vchans += apnd
				vchanc += 1

		# Some guilds can have no voice channels. You can't have no text channels, though.
		vchans = '_(none)_' if not vchans else vchans

		em = discord.Embed(colour=message.guild.me.colour)
		em.set_thumbnail(url=message.guild.icon_url)

		# Some guilds have a lot of channels that can't be fit in one embed field.
		# So, go ahead and paginate that.
		# TODO: Maybe abstract pagination to a function or something.
		if len(tchans) > 1024:
			tchanl = tchans.split('\n')
			tpages = []
			result = ''
			count = 0
			for i in tchanl:
				count += len(i + '\n')

				if count > 1024:
					# We've overstepped the boundary

					count = len(i + '\n')
					tpages += [result]
					result = ''
				result += i + '\n'
			tpages += [result]
			for c, i in enumerate(tpages):
				em.add_field(
					name='Text Channels ({0})'.format(tchanc) \
					if not c else '\u200b',
					value=i,
					inline=False,
				)
		else:
			em.add_field(
				name='Text Channels ({0})'.format(tchanc),
				value=tchans,
				inline=False,
			)
		if len(vchans) > 1024:
			vchanl = vchans.split('\n')
			vpages = []
			result = ''
			count = 0
			for i in vchanl:
				count += len(i + '\n')

				if count > 1024:
					# We've overstepped the boundary

					count = len(i + '\n')
					vpages += [result]
					result = ''
				result += i + '\n'
			vpages += [result]
			for c, i in enumerate(vpages):
				em.add_field(
					name='Voice Channels ({0})'.format(vchanc) \
					if not c else '\u200b',
					value=i,
					inline=False,
				)
		else:
			em.add_field(
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
	em.set_thumbnail(url=message.guild.icon_url)
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

@shadow()
async def votevoicemute(client, message, **kwargs):
	# TODO start supporting this. When voting, require (part of) name (or id/mention/disc/you know the drill) if more than one vote is running
	if len(wrapper.votemutes) >= 1:
		embed = emb.error('Multiple votes running at the same time is not yet supported.')
		await bot.reply(message, emb=embed)
		return

	targetmember = utils.match_input(message.guild.members, discord.Member, kwargs['arguments'])
	try:
		if message.author.voice.voice_channel is None:
			embed = emb.error('You have to be in a voice channel to be able to start a vote.')
		elif targetmember.voice.voice_channel is None:
			embed = emb.error('User is not in a voice channel.')
		elif targetmember.id in bot.votemutes:
			embed = emb.warning('There is already a vote running for this user. Type **`\\vy`** to vote yes.')
		else:
			# Count the amount of people in all the voice channels
			voicechatters = 0
			for chan in message.guild.voice_channels:
				voicechatters += len(chan.members)

			if voicechatters < config.get_s('votevmute_minmembers', message.guild.id):
				embed = emb.warning('There are not enough members in voice channels to start a vote.')
				await bot.reply(message, emb=embed)
				return

			bot.votemutes[targetmember.id] = {
				'starttime': int(time.time()),
				'proponents': [message.author.id],
				'opponents': []
			}
			content = 'A vote has been started to voice mute <@{}>.\nTo vote in favor of muting, type **`\\vy`**.\nTo vote against muting, type **`\\vn`**.\nModerators can cancel the vote by typing **`\\vc`**.'.format(targetmember.id)
			await bot.replyattach(
				message,
				images.votebar(
					(1 / voicechatters) * 100,
					0,
					config.get_s('votevmute_threshold', message.guild.id),
				),
				'temp.png',
				content,
			)
			return
	except AttributeError:
		embed = emb.error(bot.t['specify_user'])
	await bot.reply(message, emb=embed)

@shadow(aliases=['vn'])
async def vy(client, message, **kwargs):
	if not wrapper.votemutes:
		embed = emb.error('There are currently no votes running.')
	elif len(wrapper.votemutes) > 1:
		embed = emb.error('Multiple votes running at the same time is not yet supported.')
	else:
		# First, who are we going to mute, again?
		for m in wrapper.votemutes:
			mutee = m
			break

		if message.author.voice.voice_channel is None:
			embed = emb.error('You’re not in any voice channel.')
			await bot.reply(message, emb=embed)
			return

		content = 'Voted {}.'
		if kwargs['command'] == 'vy':
			side = 'proponents'
			oppositeside = 'opponents'
			resulttext = 'in favor of muting'
		else:
			side = 'opponents'
			oppositeside = 'proponents'
			resulttext = 'against muting'

		content = content.format(resulttext)

		if message.author.id in wrapper.votemutes[mutee][side]:
			embed = emb.warning('You have already voted that.')
			await bot.reply(message, emb=embed)
			return

		wrapper.votemutes[mutee][side].append(message.author.id)

		if message.author.id in wrapper.votemutes[mutee][oppositeside]:
			# Changing your mind, huh?
			content = 'Changed vote to be {}.'.format(resulttext)
			wrapper.votemutes[mutee][oppositeside].remove(message.author.id)

		# For the amount of people who voted, only count those who are still inside the channel!
		voicechatters = 0
		numproponents = 0
		numopponents  = 0
		for chan in message.guild.voice_channels:
			voicechatters += len(chan.members)

			for voicemember in chan.members:
				if voicemember.id in wrapper.votemutes[mutee]['proponents']:
					numproponents += 1
				if voicemember.id in wrapper.votemutes[mutee]['opponents']:
					numopponents  += 1

		percpro = numproponents/voicechatters*100
		percopp = numopponents /voicechatters*100

		if percpro >= config.get_s('votevmute_threshold', message.guild.id):
			targetmember = utils.match_input(message.guild.members, discord.Member, mutee)
			await targetmember.edit(mute=True)
			content += '\n{}% of the members have now voted in favor of muting, so <@{}> is now voice muted.'.format(round(percpro,1), mutee)
			del wrapper.votemutes[mutee]
		elif percopp > 100-config.get_s('votevmute_threshold', message.guild.id):
			content += '\n{}% of the members have now voted against muting, so <@{}> is not getting voice muted.'.format(round(percopp,1), mutee)
			del wrapper.votemutes[mutee]

		await bot.replyattach(
			message,
			images.votebar(
				percpro,
				percopp,
				config.get_s('votevmute_threshold', message.guild.id),
			),
			'temp.png',
			content,
		)
		return
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_mod)
async def vc(client, message, **kwargs):
	if not wrapper.votemutes:
		embed = emb.error('There are currently no votes running.')
	elif len(wrapper.votemutes) > 1:
		embed = emb.error('Multiple votes running at the same time is not yet supported.')
	else:
		# We're going to cancel the vote on whom?
		for m in wrapper.votemutes:
			mutee = m
			break

		del wrapper.votemutes[mutee]
		embed = emb.success('The vote on <@{}> has been vetoed.'.format(mutee))
	await bot.reply(message, emb=embed)

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
		content = 'Expiry list for server **{0.name}** ({0.id}):\n'.format(guild)
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

	if utils.removerolecache(kwargs['arguments'], message.guild.id):
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

	if splitargs[0] not in wrapper.memberroles[message.guild.id]:
		wrapper.memberroles[message.guild.id][splitargs[0]] = []

	wrapper.memberroles[message.guild.id][splitargs[0]].append(splitargs[1])
	utils.rolecachesave()

	embed = emb.success('Successfully added role {} to member {} in the role cache.'.format(splitargs[1], splitargs[0]))
	await bot.reply(message, emb=embed)

@shadow()
async def rolesync(client, message, **kwargs):
	perms = message.channel.permissions_for(message.author)
	if not perms.manage_roles:
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
		elif int(kwargs['arguments']) in bot.funnynumbers:
			content = utils.respondtorule(kwargs['arguments'])
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
		if splitargs[0].isdigit() and int(splitargs[0]) in bot.funnynumbers:
			content = utils.respondtorule(splitargs[0])
			await bot.reply(message, content)
			return
		elif splitargs[0].isdigit() and \
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
	yesperm = '☑'
	noperm = '❎'
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

@shadow()
async def botok(client, message, **kwargs):
	embed = emb.success('Bot is okay.')
	await bot.reply(message, emb=embed)

@shadow()
async def uptime(client, message, **kwargs):
	hostuptime = subprocess.Popen(['uptime', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
	embed = discord.Embed(colour=col.r_success, timestamp=message.created_at)
	embed.set_author(name='Uptime Statistics', icon_url=client.user.avatar_url)
	embed.set_thumbnail(url=client.user.avatar_url)
	embed.set_footer(text='Uptime Statistics', icon_url=client.user.avatar_url)
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
	content = (
		'**`tOLP Discord`** – the server it’s built for. Join at __https://discord.gg/0r76El7PzkPMhSBF__.\n'
		'**`Aperture Science`** – the bot’s testing server. Join at __https://discord.gg/0skUn2HYSEHxw9Dg__.'
	)
	await bot.reply(message, content)

@shadow()
async def version(client, message, **kwargs):
	embed = discord.Embed(colour=col.r_success, timestamp=message.created_at)
	embed.set_author(name='Version Information', icon_url=client.user.avatar_url)
	embed.set_thumbnail(url=client.user.avatar_url)
	embed.set_footer(text='Version Information', icon_url=client.user.avatar_url)
	embed.set_thumbnail(url=client.user.avatar_url)
	embed.add_field(name='\\[\\\\\\]', value='{}, last updated {}'.format(bot.version, wrapper.modificationtimecache))
	embed.add_field(name='discord.py', value='{} {}'.format(discord.version_info.releaselevel, discord.__version__))
	embed.add_field(name='Python', value=sys.version)
	embed.add_field(name='PIL', value=__import__("PIL").VERSION)
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
					getmessage = await channel.get_message(argsplit[0])
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
			getmessage = await getchannel.get_message(arg1)
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
	if kwargs['arguments'] is None:
		getchannel = message.channel
	else:
		channelid = int(kwargs['arguments'][2:-1])
		getchannel = client.get_channel(channelid)
	try:
		pins = await getchannel.pins()
		content = '{} currently has {} pins, {} remaining.'.format(getchannel.mention, len(pins), 50-len(pins))
		await bot.replyattach(message, images.progressbar(len(pins)*2), 'temp.png', content)
	except AttributeError:
		embed = emb.error(
			'The channel doesn’t exist, has been deleted,'
			' or it’s not a channel at all.',
		)
		await bot.reply(message, emb=embed)

@shadow(guildonly=True)
async def countallpins(client, message, **kwargs):
	async with message.channel.typing():
		content = ''
		for chan in message.guild.text_channels:
			try:
				pins = await chan.pins()
				content += '{} – {} pins, {} remaining\n'.format(
					chan.mention,
					len(pins),
					50 - len(pins),
				)
			except discord.errors.Forbidden:
				content += chan.mention + '{} - Unable to get data\n'
		await bot.reply(message, content)

@shadow()
async def _math(client, message, **kwargs):
	# what kind of stupid language uses elif instead of elseif or else if?
	try:
		cmdbits = kwargs['arguments'].split() # should split it so [0] is number, [1] is operand, [2] is second number
	except AttributeError:
		embed = emb.error('Invalid arguments passed.')
		await bot.reply(message, emb=embed)
		return
	try:
		if len(cmdbits) != 3: # the arguments should be [number], [operand], [number]
			embed = emb.error('Invalid amount of arguments passed.')
			await bot.reply(message, emb=embed)
			return
		numbers = ['', '']
		numbers[0] = float(cmdbits[0]) # number 1
		numbers[1] = float(cmdbits[2]) # number 2
		out = '' # setting extra crashes
		if cmdbits[1] == '+':
			out = numbers[0] + numbers[1]
		elif cmdbits[1] == '-':
			out = numbers[0] - numbers[1]
		elif cmdbits[1] == 'x' or cmdbits[1] == '*':
			out = numbers[0] * numbers[1]
		elif cmdbits[1] == '÷' or cmdbits[1] == '/':
			try:
				out = numbers[0] / numbers[1]
			except ZeroDivisionError:
				out = 'Undefined.'
		elif cmdbits[1] == '^':
			out = numbers[0] ** numbers[1] # decimal powers are allowed
		elif cmdbits[1] == '↑↑' or cmdbits[1] == '^^': # this one's for you, Info
			oper = numbers[0] # this one's the stored operand, and has to be an int otherwise it won't work properly
			out = numbers[0] # Why is this still here? Dunno, changed it
			for _ in range(int(numbers[1])): # decimal range isn't
				out = out ** oper # iterate until tetration is finished
		else: #invalid operand, we don't care what the inputs are
			embed = emb.error('Invalid operands passed.')
			await bot.reply(message, emb=embed)
			return
	except OverflowError:
		embed = emb.error('Overflow error.')
		await bot.reply(message, emb=embed)
		return
	except ValueError:
		embed = emb.error('You should probably enter in numbers.')
		await bot.reply(message, emb=embed)
		return
	# end
	content = '{number1} {operand} {number2} = {out}'.format(number1=cmdbits[0], operand=cmdbits[1], number2=cmdbits[2], out=out)
	embed = discord.Embed(title='Math Output', description=content, colour=col.r_success)
	await bot.reply(message, emb=embed)

@shadow(auth=checks.is_operator)
async def gamestatus(client, message, **kwargs):
	await client.change_presence(game=discord.Game(name=kwargs['arguments']))
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

@shadow(aliases=['serverban', 'unserverban'])
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
		elif kwargs['command'] == 'serverban':
			if not message.author.guild_permissions.ban_members and not kwargs['sudo']:
				bot.logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(bot.t['you_no_permission'])
				await bot.reply(message, emb=embed)
				return
			await targetmember.ban(delete_message_days=0)
		elif kwargs['command'] == 'serverunban':
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
	for u in bans:
		ulist += (
			'**{0.name}**#{0.discriminator} ({0.id})\n'
			.format(u)
		)
	if len(ulist) > 2048:
		# TODO: actually split this into multiple strings
		pass
	embed = discord.Embed(
		name='Bans',
		description=ulist,
		colour=col.r_success,
	)
	embed.set_thumbnail(url=message.guild.icon_url)
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
			getmessage = await ban_log_channel.get_message(splitargs[1])
			content = getmessage.content
			if content.find('⛔') == -1:
				embed = emb.error('Cannot find the ⛔!')
				await bot.reply(message, emb=embed)
				return
			content = content.replace('⛔', '[LIFTED]', 1)
			await getmessage.edit(content=content)
			output = 'Edited successfully.'
		elif splitargs[0] == 'addtimer':
			getmessage = await ban_log_channel.get_message(splitargs[1])
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
		kwargs['clean_arguments'] = kwargs['clean_command'].split(' ', 2)[2]
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
		embed = emb.error('The custom command `{}` already exists!'.format(
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
		embed = emb.error('The custom command `{}` already exists!'.format(
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

	if not isinstance(tgt, discord.VoiceChannel):
		em = emb.error('Matched a voice channel - text-to-speech is not implemented.')
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
					response = await wrapper.client.wait_for(
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
