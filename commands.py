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

# This file contains all the bot commands as functions.

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

@shadow()
async def _help(client, message, **kwargs):
	content = (help_info_string + helplist(cmds, message.server))

	# General
	if kwargs['arguments'] is None:
		pass
	else:
		matched = False
		for cat in (cmds):
			if kwargs['arguments'] == cat['cat_slug']:
				content = helplist(cmds, message.server, kwargs['arguments'])
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
			for cmd in customcommands.list_commands(message.server):
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
	await reply(message, emb=embed)

@shadow(auth=is_host)
async def restart(client, message, **kwargs):
	embed = emb.success('Restarting.', True)
	embed.add_field(name='Uptime', value=reltime(boottimeunix, True))
	embed.add_field(name='Messages in Cache', value=str(len(client.messages)))
	logcommand(kwargs['command'], kwargs['arguments'], message)
	await reply(message, emb=embed)
	os.execv(sys.executable, ['python'] + sys.argv)

@shadow(auth=is_host)
async def kill(client, message, **kwargs):
	embed = emb.success('Killing.', True)
	embed.add_field(name='Uptime', value=reltime(boottimeunix, True))
	logcommand(kwargs['command'], kwargs['arguments'], message)
	await reply(message, emb=embed)
	await client.logout()
	sys.exit(42)

@shadow(auth=is_operator)
async def _config(client, message, **kwargs):
	if message.server and \
	message.server.id == op_ids.ids['opserver'] and \
	not is_host(message.author):
		embed = emb.error(t['no_permission'])
		logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await reply(message, emb=embed)
		return
	if kwargs['arguments'] == None:
		content = (
			'You can use the following options:\n'
			'`\config list`\n'
			'`\config listhidden`\n'
			'`\config reload`\n'
			'`\config get <key>`\n'
			'`\config set <key> <value>` (not for arrays)\n'
			'`\config insert <key> <value>` (only for arrays)\n'
			'`\config remove <key> <value>` (only for arrays)\n'
			'`\config detach <key>`\n'
			'`\config reattach <key>`\n'
			'`\config default <key>`\n'
		)
		await reply(message, content)
		return
	elif kwargs['arguments'] == 'reload':
		config.load()
		logcommand(kwargs['command'], kwargs['arguments'], message)
		embed = emb.success('Reloaded config.')
		await reply(message, emb=embed)
		return
	elif kwargs['arguments'] == 'list' or kwargs['arguments'] == 'listhidden':
		content = '```css'
		for c in config.s:
			if (kwargs['arguments'] == 'list' and not config.get_shown(c)) or \
			(kwargs['arguments'] == 'listhidden' and config.get_shown(c)):
				continue
			try:
				content += '\n{} [{}] = {}'.format(c, config.get_type(c) + ('*' if config.is_array(c) else ''), config.get_s(c, message.server.id) if not config.is_array(c) else '[{}]'.format(len(config.get_s(c, message.server.id))))
				if config.is_detached(c, message.server.id):
					content += ' [local value]'
			except AttributeError:
				content += '\n{} [{}] = {}'.format(c, config.get_type(c) + ('*' if config.is_array(c) else ''), config.get_s(c) if not config.is_array(c) else '[{}]'.format(len(config.get_s(c))))
		content += '\n```'
		await reply(message, content)
		return

	splitargs = kwargs['arguments'].split(' ', 2)

	editingmaster = True

	if len(splitargs) == 1:
		embed = emb.error('Too few arguments.')
		await reply(message, emb=embed)
		return

	if splitargs[0] == 'set':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await reply(message, emb=embed)
			return
		if config.is_array(splitargs[1]):
			embed = emb.error('That doesn’t work for an array')
			await reply(message, emb=embed)
			return
		if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
			embed = emb.error('Integer expected')
			await reply(message, emb=embed)
			return
		try:
			config.set_s(splitargs[1], splitargs[2], message.server.id)
			editingmaster = not config.is_detached(splitargs[1], message.server.id)
		except AttributeError:
			config.set_s(splitargs[1], splitargs[2])
		config.saveconfig()
		logcommand(kwargs['command'], kwargs['arguments'], message)
		embed = emb.success('Set `{}` to `{}`{}'.format(
				splitargs[1], wrapbackticks(
					config.input_to_type_key(splitargs[2], splitargs[1])
				),
				t['editingmasterval'] if editingmaster else ''
			)
		)
		await reply(message, emb=embed)
	elif splitargs[0] == 'get':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await reply(message, emb=embed)
			return
		try:
			content = 'Key: `{}`   Type: `{}`   Array: `{}`   Detachable: `{}`   Using: `{}`\n'.format(splitargs[1], config.get_type(splitargs[1]), config.is_array(splitargs[1]), config.is_detachable(splitargs[1]), ('Local value' if config.is_detached(splitargs[1], message.server.id) else 'Master value'))
		except AttributeError:
			content = 'Key: `{}`   Type: `{}`   Array: `{}`   Detachable: `{}`   Using: `{}`\n'.format(splitargs[1], config.get_type(splitargs[1]), config.is_array(splitargs[1]), config.is_detachable(splitargs[1]), 'Master value')
		if config.get_expl(splitargs[1]) != None:
			content += 'Explanation: {}\n'.format(config.get_expl(splitargs[1]))
		content += 'Value:'

		if config.is_array(splitargs[1]):
			try:
				for val in config.get_s(splitargs[1], message.server.id):
					content += ' `{}`,'.format(val)
			except AttributeError:
				for val in config.get_s(splitargs[1]):
					content += ' `{}`,'.format(val)
		else:
			try:
				content += ' `{}`\nDefault: `{}`'.format(config.get_s(splitargs[1], message.server.id), config.get_default(splitargs[1]))
			except AttributeError:
				content += ' `{}`\nDefault: `{}`'.format(config.get_s(splitargs[1]), config.get_default(splitargs[1]))
		await reply(message, content)
	elif splitargs[0] == 'insert' or splitargs[0] == 'remove':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await reply(message, emb=embed)
			return
		if not config.is_array(splitargs[1]):
			embed = emb.error('That doesn’t work for something that is not an array')
			await reply(message, emb=embed)
			return
		if config.get_type(splitargs[1]) == 'int' and not splitargs[2].isdigit():
			embed = emb.error('Integer expected')
			await reply(message, emb=embed)
			return
		if splitargs[0] == 'insert':
			try:
				config.insert_s(splitargs[1], splitargs[2], message.server.id)
				editingmaster = not config.is_detached(splitargs[1], message.server.id)
			except AttributeError:
				config.insert_s(splitargs[1], splitargs[2])
			embed = emb.success('Inserted `{}` into array `{}`'.format(
					wrapbackticks(
						config.input_to_type_key(splitargs[2], splitargs[1])
					), splitargs[1],
					t['editingmasterval'] if editingmaster else ''
				)
			)
		else:
			try:
				config.remove_s(splitargs[1], splitargs[2], message.server.id)
				editingmaster = not config.is_detached(splitargs[1], message.server.id)
			except AttributeError:
				config.remove_s(splitargs[1], splitargs[2])
			embed = emb.success('Removed `{}` from array `{}`'.format(
					wrapbackticks(
						config.input_to_type_key(splitargs[2], splitargs[1])
					), splitargs[1],
					t['editingmasterval'] if editingmaster else ''
				)
			)
		config.saveconfig()
		logcommand(kwargs['command'], kwargs['arguments'], message)
		await reply(message, emb=embed)
	elif splitargs[0] == 'detach' or splitargs[0] == 'reattach':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await reply(message, emb=embed)
			return
		if not config.is_detachable(splitargs[1]):
			embed = emb.error('That setting cannot have an independent local value.')
			await reply(message, emb=embed)
			return
		if splitargs[0] == 'detach':
			try:
				config.detach(splitargs[1], message.server.id)
				embed = emb.success('Setting `{}` now uses a local value for this server.'.format(splitargs[1]))
			except AttributeError:
				embed = emb.error('Can’t detach values for non-servers.')
		else:
			try:
				config.reattach(splitargs[1], message.server.id)
				embed = emb.success('Setting `{}` is now using the master value again on this server.'.format(splitargs[1]))
			except AttributeError:
				embed = emb.error('Can’t reattach values for non-servers.')
		config.saveconfig()
		logcommand(kwargs['command'], kwargs['arguments'], message)
		await reply(message, emb=embed)
	elif splitargs[0] == 'default':
		if not config.exists(splitargs[1]):
			embed = emb.error('That setting does not exist')
			await reply(message, emb=embed)
			return
		try:
			config.restore_default(splitargs[1], message.server.id)
		except AttributeError:
			config.restore_default(splitargs[1])
		config.saveconfig()
		logcommand(kwargs['command'], kwargs['arguments'], message)
		embed = emb.success('Set `{}` back to default value of `{}`'.format(splitargs[1], wrapbackticks(config.get_default(splitargs[1]))))
		await reply(message, emb=embed)
	else:
		embed = emb.error('`{}` was not recognized'.format(splitargs[0]))
		await reply(message, emb=embed)

@shadow()
async def echo(client, message, **kwargs):
	if kwargs['arguments'] == None:
		arguments = ''
	else:
		arguments = kwargs['clean_arguments']
	if (not message.channel.is_private and \
	message.channel.permissions_for(message.server.me).embed_links) \
	or message.channel.is_private:
		displayarguments = arguments[:2048-len(events.msg_start)]
		try:
			echocolor = message.server.me.colour
		except AttributeError:
			echocolor = discord.Embed.Empty
		em = discord.Embed(description=displayarguments, colour=echocolor)
		replyargs = {'emb': em}
	else:
		displayarguments = arguments[:2000-len(events.msg_start)]
		replyargs = {'message': displayarguments}
	await reply(message, **replyargs)

@shadow()
async def hangman(client, message, **kwargs):
	global guessedletters
	if events.hangmanactive:
		embed = emb.error('Hangman is already running. It can be aborted by the starter or by a mod with `\stophangman`.')
		await reply(message, emb=embed)
		return
	if not isprivatemessage(message.server):
		embed = emb.error('For now, this can only be run via DM.')
		await reply(message, emb=embed)
		return
	if kwargs['arguments'] == None:
		embed = emb.error('Please specify a word.')
		await reply(message, emb=embed)
		return
	if not kwargs['arguments'].isalpha():
		embed = emb.error('Words can only consist of letters A-Z')
		await reply(message, emb=embed)
		return
	if len(kwargs['arguments']) > 50:
		embed = emb.error('Sorry, but your word is too long. It can be 50 characters max.')
		await reply(message, emb=embed)
		return

	events.hangmanchosenword = kwargs['arguments']
	events.hangmanattempts = 10
	events.hangmantotalattempts = 10
	events.hangmanactive = True
	events.hangmanstarter = message.author
	events.guessedletters = [False]*26
	msg_start = '**`>`**``{}``**`{}`**``\{} {}``\n'.format(wrapbackticks(message.author.name), kwargs['invokesymbol'], wrapbackticks(kwargs['command'].split(' ')[0]), '*'*len(events.hangmanchosenword)) # you will never have mod/admin perms in private messages (probably), where the hangman will be started from, so for now theres no mod/admin check to make the input display different
	content = 'New game of hangman initiated by <@{}> with a custom word. Guess letters by chatting "{}" followed by the letter (for example {}a) or the word. {} attempts left.\n{}'.format(events.hangmanstarter.id, hangmaninvoker, hangmaninvoker, events.hangmanattempts, hangmanworddisp(events.hangmanchosenword))
	msg = msg_start + content
	await client.send_message(events.botschannel, msg)

	content = 'https://discord.gg/gj6YmtV'
	await reply(message, content)

@shadow()
async def stophangman(client, message, **kwargs):
	if not events.hangmanactive:
		embed = emb.error('Can’t abort hangman because it’s not running.')
		await reply(message, emb=embed)
		return
	elif not is_mod(message.author) and message.author.id != events.hangmanstarter.id:
		embed = emb.error('Can’t abort hangman because you haven’t started this game.')
		await reply(message, emb=embed)
		return

	events.hangmanactive = False
	content = 'Game of hangman aborted. The word was: **{}**'.format(events.hangmanchosenword)
	await client.send_message(events.botschannel, content)

@shadow()
async def source(client, message, **kwargs):
	content = 'Source code to the bot: https://gitgud.io/infoteddy/bracketed_backslash'
	await reply(message, content)

@shadow(aliases=['findup'])
async def findu(client, message, **kwargs):
	if kwargs['arguments'] == None:
		targetmember = message.author
	else:
		targetmember = utils.match_input(
			'member', kwargs['arguments'], server=message.server
		)
	if targetmember == None:
		embed = emb.error('Unable to find that member. ' + t['specify_user'])
		await reply(message, emb=embed)
		return
	displaymatch = '<@{}>'.format(targetmember.id)
	if targetmember.game == None:
		memberhasgame = False
		displaygamestatus = 'Not Playing'
		displaygamename = 'Not Playing'
		displaygameurlstatus = 'No Stream Link'
		displaygameurl = 'No Stream Link'
		pass
	else:
		memberhasgame = True
	if memberhasgame:
		if targetmember.game.type == 0 or targetmember.game.type == None:
			displaygamestatus = 'Playing'
			displaygamename = utils.mdspecialchars(targetmember.game.name)
		if targetmember.game.type == 1:
			displaygamestatus = 'Streaming'
			displaygamename = utils.mdspecialchars(targetmember.game.name)
		if targetmember.game.url == None:
			displaygameurlstatus = 'No Stream Link'
			displaygameurl = 'No Stream Link'
		else:
			displaygameurlstatus = 'Stream Link'
			displaygameurl = utils.mdspecialchars(targetmember.game.url)
	embed = discord.Embed(description='Matched ' + displaymatch, colour=targetmember.colour)
	embed.set_image(url=targetmember.avatar_url)
	embed.add_field(name='Nickname' if targetmember.nick != None else 'No Nickname', value=utils.mdspecialchars(targetmember.nick) if targetmember.nick != None else 'No Nickname')
	embed.add_field(name='Username', value=utils.mdspecialchars(targetmember.name))
	embed.add_field(name='Discriminator', value='#{}'.format(targetmember.discriminator))
	embed.add_field(name='User ID', value=targetmember.id)
	embed.add_field(name='Bot', value='Yes' if is_bot(targetmember) else 'No')
	embed.add_field(name=displaygamestatus, value=displaygamename)
	embed.add_field(name=displaygameurlstatus, value=displaygameurl)
	embed.add_field(name='Status', value='Do Not Disturb' if str(targetmember.status) == 'dnd' else str(targetmember.status).title())
	embed.add_field(name='Default Avatar', value=str(targetmember.default_avatar).title())
	embed.add_field(name='Joined Server At', value=time.strftime(config.get_s('timeformat', message.server.id), targetmember.joined_at.timetuple()))
	embed.add_field(name='Joined Discord At', value=time.strftime(config.get_s('timeformat', message.server.id), targetmember.created_at.timetuple()))
	embed.add_field(name='Color', value='_(default)_' if str(targetmember.colour) == '#000000' else str(targetmember.colour).upper())
	# IMPORTANT: in `embed.add_field()`, `name` or `value` cannot be an empty string or you will get a 400 bad request when sending it
	# (i learned that the hard way)
	# (that was about twenty restarts smh)
	await reply(message, emb=embed)

@shadow(servonly=True)
async def findc(client, message, **kwargs):
	if not kwargs['arguments']:
		# No channel for me to get? Have a list of the server's channels, then.

		# Lists
		tchans = ''
		vchans = ''

		# Numbers
		tchanc = 0
		vchanc = 0

		# Generation of the lists
		for c in sorted(message.server.channels, key=lambda c: c.position):
			apnd = '**{name}** ({id})\n'.format(
				name=utils.mdspecialchars(c.name),
				id=c.id,
			)
			if c.type == discord.ChannelType.text:
				tchans += apnd
				tchanc += 1
			elif c.type == discord.ChannelType.voice:
				vchans += apnd
				vchanc += 1

		# Some servers can have no voice channels. You can't have no text channels, though.
		vchans = '_(none)_' if not vchans else vchans

		em = discord.Embed(colour=message.server.me.colour)
		em.set_thumbnail(url=message.server.icon_url)

		# Some servers have a lot of channels that can't be fit in one embed field.
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
		await reply(message, emb=em)
		return

	tgt = utils.match_input('channel', kwargs['arguments'], server=message.server)
	if not tgt:
		em = emb.error('Unable to find that channel. ' + t['specify_channel'])
		await reply(message, emb=em)
		return

	readbleby = 0
	for i in message.server.members:
		readbleby += 1 if tgt.permissions_for(i).read_messages else 0

	em = discord.Embed(description='Matched ' + tgt.mention, colour=message.server.me.colour)
	em.set_thumbnail(url=message.server.icon_url)
	em.add_field(name='Name', value=utils.mdspecialchars(tgt.name))
	em.add_field(name='ID', value=tgt.id)
	em.add_field(name='Type', value=str(tgt.type).title())
	em.add_field(name='Default', value='Yes' if tgt.is_default else 'No')
	em.add_field(
		name='Position',
		value='{0} from the top of {1} list'.format(
			str(tgt.position), str(tgt.type),
		),
	)
	em.add_field(
		name='Topic' if tgt.topic else 'No Topic',
		value=tgt.topic if tgt.topic else 'No Topic',
	)
	em.add_field(
		name='Created At',
		value=time.strftime(
			config.get_s('timeformat', message.server.id),
			tgt.created_at.timetuple(),
		),
	)
	em.add_field(
		name='User Limit',
		value='N/A' if tgt.type != discord.ChannelType.voice else str(tgt.user_limit),
	)
	em.add_field(
		name='Voice Members',
		value=(
			'N/A' if tgt.type != discord.ChannelType.voice else
			str(len(tgt.voice_members))
		),
	)
	em.add_field(
		name='Bitrate',
		value=(
			'N/A' if tgt.type != discord.ChannelType.voice else
			str(int(tgt.bitrate / 1000)) + ' kbps'
		),
	)
	em.add_field(name='Specific Overwrites', value=str(len(tgt.overwrites) - 1))
	em.add_field(
		name='Readable By',
		value=(
			'N/A' if tgt.type != discord.ChannelType.text else
			str(readbleby) + ' members'
		),
	)
	await reply(message, emb=em)

@shadow(auth=is_mod, aliases=['voiceunmute'])
async def voicemute(client, message, **kwargs):
	targetmember = utils.match_input('member', kwargs['arguments'], server=message.server)
	content = None
	try:
		if targetmember.voice.voice_channel == None:
			embed = emb.error('User is not in a voice channel.')
		elif kwargs['command'] == 'voicemute':
			await client.server_voice_state(targetmember, mute=1)
			content = targetmember.mention
			embed = emb.success('Voice muted <@{}>.'.format(targetmember.id))
		elif kwargs['command'] == 'voiceunmute':
			await client.server_voice_state(targetmember, mute=0)
			content = targetmember.mention
			embed = emb.success('Voice unmuted <@{}>.'.format(targetmember.id))
	except AttributeError:
		embed = emb.error(t['specify_user'])
	except discord.errors.Forbidden:
		embed = emb.error(t['no_permission'])
	await reply(message, content, emb=embed)

@shadow()
async def votevoicemute(client, message, **kwargs):
	# TODO start supporting this. When voting, require (part of) name (or id/mention/disc/you know the drill) if more than one vote is running
	if len(votemutes) >= 1:
		embed = emb.error('Multiple votes running at the same time is not yet supported.')
		await reply(message, emb=embed)
		return

	targetmember = utils.match_input('member', kwargs['arguments'], server=message.server)
	try:
		if message.author.voice.voice_channel == None:
			embed = emb.error('You have to be in a voice channel to be able to start a vote.')
		elif targetmember.voice.voice_channel == None:
			embed = emb.error('User is not in a voice channel.')
		elif targetmember.id in votemutes:
			embed = emb.warning('There is already a vote running for this user. Type **`\\vy`** to vote yes.')
		else:
			# Count the amount of people in all the voice channels
			voicechatters = 0
			for chan in message.server.channels:
				if str(chan.type) == 'voice':
					voicechatters += len(chan.voice_members)

			if voicechatters < config.get_s('votevmute_minmembers', message.server.id):
				embed = emb.warning('There are not enough members in voice channels to start a vote.')
				await reply(message, emb=embed)
				return

			votemutes[targetmember.id] = {
				'starttime': int(time.time()),
				'proponents': [message.author.id],
				'opponents': []
			}
			content = 'A vote has been started to voice mute <@{}>.\nTo vote in favor of muting, type **`\\vy`**.\nTo vote against muting, type **`\\vn`**.\nModerators can cancel the vote by typing **`\\vc`**.'.format(targetmember.id)
			await replyattach(message, images.votebar(1/voicechatters*100, 0, config.get_s('votevmute_threshold', message.server.id)), 'temp.png', content)
			return
	except AttributeError:
		embed = emb.error(t['specify_user'])
	await reply(message, emb=embed)

@shadow(aliases=['vn'])
async def vy(client, message, **kwargs):
	if len(votemutes) == 0:
		embed = emb.error('There are currently no votes running.')
	elif len(votemutes) > 1:
		embed = emb.error('Multiple votes running at the same time is not yet supported.')
	else:
		# First, who are we going to mute, again?
		for m in votemutes:
			mutee = m
			break

		if message.author.voice.voice_channel == None:
			embed = emb.error('You’re not in any voice channel.')
			await reply(message, emb=embed)
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

		if message.author.id in votemutes[mutee][side]:
			embed = emb.warning('You have already voted that.')
			await reply(message, emb=embed)
			return

		votemutes[mutee][side].append(message.author.id)

		if message.author.id in votemutes[mutee][oppositeside]:
			# Changing your mind, huh?
			content = 'Changed vote to be {}.'.format(resulttext)
			votemutes[mutee][oppositeside].remove(message.author.id)

		# For the amount of people who voted, only count those who are still inside the channel!
		voicechatters = 0
		numproponents = 0
		numopponents  = 0
		for chan in message.server.channels:
			if str(chan.type) == 'voice':
				voicechatters += len(chan.voice_members)

				for voicemember in chan.voice_members:
					if voicemember.id in votemutes[mutee]['proponents']:
						numproponents += 1
					if voicemember.id in votemutes[mutee]['opponents']:
						numopponents  += 1

		percpro = numproponents/voicechatters*100
		percopp = numopponents /voicechatters*100

		if percpro >= config.get_s('votevmute_threshold', message.server.id):
			targetmember = utils.match_input('member', mutee, server=message.server)
			await client.server_voice_state(targetmember, mute=1)
			content += '\n{}% of the members have now voted in favor of muting, so <@{}> is now voice muted.'.format(round(percpro,1), mutee)
			del votemutes[mutee]
		elif percopp > 100-config.get_s('votevmute_threshold', message.server.id):
			content += '\n{}% of the members have now voted against muting, so <@{}> is not getting voice muted.'.format(round(percopp,1), mutee)
			del votemutes[mutee]

		await replyattach(message, images.votebar(percpro, percopp, config.get_s('votevmute_threshold', message.server.id)), 'temp.png', content)
		return
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def vc(client, message, **kwargs):
	if len(votemutes) == 0:
		embed = emb.error('There are currently no votes running.')
	elif len(votemutes) > 1:
		embed = emb.error('Multiple votes running at the same time is not yet supported.')
	else:
		# We're going to cancel the vote on whom?
		for m in votemutes:
			mutee = m
			break

		del votemutes[mutee]
		embed = emb.success('The vote on <@{}> has been vetoed.'.format(mutee))
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def rolerst(client, message, **kwargs):
	try:
		targetmember = utils.match_input(
			'member', kwargs['arguments'], server=message.server,
		)
		await removeRestrictiveRoles(targetmember, message.server)
	except(AttributeError, TypeError):
		embed = emb.error(t['specify_user'])
		await reply(message, emb=embed)
		return
	embed = emb.success('Reset roles for <@{}> back to normal.'.format(targetmember.id))
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def expires(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Please input at least a relative time.')
		await reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ', 1)

	expirytime = parsereltime(splitargs[0])
	if expirytime is None:
		embed = emb.error((
				'Invalid expiry time. Please input a relative time '
				'in the format `[#d][#h][#m][#s]`, for example: '
				'`7d12h`, `1h`, `1d`, `1d2h3m4s`, `1d20s` or '
				'whatever combination you can think of. The units '
				'have to be in the correct order, though.'
			)
		)
		await reply(message, emb=embed)
		return

	if len(splitargs) < 2:
		if events.latestroled is None:
			embed = emb.error((
					'Nobody has gotten a restrictive role this session. '
					'Please provide any member identification instead.'
				)
			)
			await reply(message, emb=embed)
			return
		targetmemberid = events.latestroled
	else:
		try:
			targetmember = utils.match_input(
				'member', splitargs[1], server=message.server,
			)
			targetmemberid = targetmember.id
		except AttributeError:
			embed = emb.error(t['specify_user'])
			await reply(message, emb=embed)
			return

	addexpiryentry(message.server.id, targetmemberid, expirytime)

	rolexpiresave()
	await handleExpiryTimer()

	embed = emb.success('Roles for <@{}> will be reset {}'.format(
			targetmemberid, reltime(expirytime)
		)
	)
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def expiryremove(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Please enter something.')
		await reply(message, emb=embed)
		return

	try:
		targetmember = utils.match_input(
			'member', kwargs['arguments'], server=message.server,
		)
		if removeexpiryentry(message.server.id, targetmember.id):
			embed = emb.success(
				'Roles for <@{}> will no longer automatically expire.'.format(
					targetmember.id
				)
			)
			rolexpiresave()
		else:
			embed = emb.error(
				'Could not find <@!{}> in the expiry list.'.format(
					targetmember.id
				)
			)
		await reply(message, emb=embed)
	except AttributeError:
		embed = emb.error(t['specify_user'])
		await reply(message, emb=embed)
		return

@shadow()
async def expirylist(client, message, **kwargs):
	if message.channel.is_private:
		if not kwargs['arguments']:
			embed = emb.error('You should probably specify a server.')
			await reply(message, emb=embed)
			return
		server = utils.match_input('server', kwargs['arguments'], client=client)
		if not server or (message.author not in server.members and not kwargs['sudo']):
			embed = emb.error(
				(
					'Either the bot isn’t in that server,'
					' you aren’t in that server,'
					' or that server doesn’t exist.'
				),
			)
			await reply(message, emb=embed)
			return
		content = 'Expiry list for server **{0.name}** ({0.id}):\n'.format(server)
	else:
		server = message.server
		content = ''

	if server.id in events.rolexpires:
		for k, v in sorted(events.rolexpires[server.id].items(), key=lambda i: i[1]['time']):
			content += '<@{}>: {}\n'.format(k, reltime(v['time']))

	if content == '':
		content = 'No expiry timers are currently running.'

	embed = emb.info(content)
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def rolecacherst(client, message, **kwargs):
	if config.get_s('rolecachemode', message.server.id) == 0:
		embed = emb.error(t['rolecachedisabled'])
		await reply(message, emb=embed)
		return
	elif kwargs['arguments'] == None:
		embed = emb.error('Please give an ID.')
		await reply(message, emb=embed)
		return
	elif utils.match_input('member', kwargs['arguments'], server=message.server) != None:
		embed = emb.error('That member is apparently still on this server! Not removing from the cache.')
		await reply(message, emb=embed)
		return

	if removerolecache(kwargs['arguments'], message.server.id):
		embed = emb.success('Member {} successfully removed from role cache.'.format(kwargs['arguments']))
		await reply(message, emb=embed)
		rolecachesave()
	else:
		embed = emb.error('Member {} cannot be found in the role cache. Please note you have to enter an ID, not any form of name!'.format(kwargs['arguments']))
		await reply(message, emb=embed)

@shadow(auth=is_mod)
async def rolecacheadd(client, message, **kwargs):
	if config.get_s('rolecachemode', message.server.id) == 0:
		embed = emb.error(t['rolecachedisabled'])
		await reply(message, emb=embed)
		return
	elif kwargs['arguments'] == None:
		embed = emb.error('Please give two IDs.')
		await reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split()
	if utils.match_input('member', splitargs[0], server=message.server) != None:
		embed = emb.error('That member is apparently still on this server! Not doing anything.')
		await reply(message, emb=embed)
		return

	if splitargs[1] == None:
		embed = emb.error('Please give two IDs.')
		await reply(message, emb=embed)
		return

	if splitargs[0] not in events.memberroles[message.server.id]:
		events.memberroles[message.server.id][splitargs[0]] = []

	events.memberroles[message.server.id][splitargs[0]].append(splitargs[1])
	rolecachesave()

	embed = emb.success('Successfully added role {} to member {} in the role cache.'.format(splitargs[1], splitargs[0]))
	await reply(message, emb=embed)

@shadow()
async def rolesync(client, message, **kwargs):
	perms = discord.Channel.permissions_for(message.channel, message.author)
	if not perms.manage_roles:
		embed = emb.error(t['you_no_permission'])
		logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await reply(message, emb=embed)
		return
	elif config.get_s('rolecachemode', message.server.id) == 0:
		embed = emb.error(t['rolecachedisabled'])
		await reply(message, emb=embed)
		return

	for mem in message.server.members:
		updaterolecache(mem, message.server.id)

	rolecachesave()

	embed = emb.success('Synced roles.')
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def rolecacheinfo(client, message, **kwargs):
	if config.get_s('rolecachemode', message.server.id) == 0:
		embed = emb.error(t['rolecachedisabled'])
		await reply(message, emb=embed)
		return
	if not kwargs['arguments'] in events.memberroles[message.server.id]:
		embed = emb.error('That member is not in the role cache.')
		await reply(message, emb=embed)
		return

	content = 'According to the role cache, this member has the following roles: ' + listroles_id(events.memberroles[message.server.id][kwargs['arguments']])

	await reply(message, content)

@shadow(aliases=['rule'], servonly=True)
async def rules(client, message, **kwargs):
	if message.server.id in events.disabledrules and not is_mod(message.author):
		embed = emb.error('The rules system is currently disabled for this server.')
		await reply(message, emb=embed)
		return
	if not message.server.id in events.rules:
		embed = emb.warning('Rules are not (yet) set for this server.')
		await reply(message, emb=embed)
		return
	if kwargs['arguments'] != None and kwargs['arguments'].isdigit():
		try:
			events.rules[message.server.id][int(kwargs['arguments'])-1]

			# Oh, we survived this? That means the given specific rule exists!
			content = 'Rule **{}** for server `{}`:\n{}'.format(int(kwargs['arguments']), wrapbackticks(message.server.name), events.rules[message.server.id][int(kwargs['arguments'])-1])
			await reply(message, content)
			return
		except IndexError:
			# But only if the rules actually don't exist
			if int(kwargs['arguments']) in funnynumbers:
				content = respondtorule(kwargs['arguments'])
				await reply(message, content)
				return
			pass
	n = 1
	content = 'Rules for server `{}`:{}'.format(wrapbackticks(message.server.name), ' (Disabled)' if message.server.id in events.disabledrules else '')
	for rule in events.rules[message.server.id]:
		content += '\n**{}.** {}'.format(n, rule)
		n += 1
	await reply(message, content)

@shadow(servonly=True)
async def rulefind(client, message, **kwargs):
	if message.server.id in events.disabledrules and not is_mod(message.author):
		embed = emb.error('The rules system is currently disabled for this server.')
		await reply(message, emb=embed)
		return
	if not message.server.id in events.rules:
		embed = emb.warning('Rules are not (yet) set for this server.')
		await reply(message, emb=embed)
		return
	if kwargs['arguments'] == None:
		embed = emb.error('Please enter a search term.')
		await reply(message, emb=embed)
		return
	matched = False
	n = 1
	content = 'Rules for server **``{}``** matching **``{}``**:'.format(wrapbackticks(message.server.name), wrapbackticks(kwargs['arguments']))
	for rule in events.rules[message.server.id]:
		if rule.lower().find(kwargs['arguments'].lower()) != -1:
			content += '\n**{}.** {}'.format(n, rule)
			matched = True
		n += 1
	if not matched:
		embed = emb.warning('No rules on server `{}` matching `{}`.'.format(wrapbackticks(message.server.name), wrapbackticks(kwargs['arguments'])))
		await reply(message, emb=embed)
		return
	await reply(message, content)

@shadow(aliases=['addrule'])
async def ruleadd(client, message, **kwargs):
	if not is_mod(message.author):
		# Okay, so they're not allowed to mess with the rules - but we want to respond to some particular things as well.
		splitargs = kwargs['arguments'].split(' ', 1)
		if splitargs[0].isdigit() and int(splitargs[0]) in funnynumbers:
			content = respondtorule(splitargs[0])
			await reply(message, content)
			return
		elif splitargs[0].isdigit() and int(splitargs[0]) > len(events.rules[message.server.id]):
			embed = emb.warning('Why are you mentioning the number if you want to add this as the last rule?')
			await reply(message, emb=embed)
			return

		# Ok good, they're not doing something weird or trying to be funny.
		embed = emb.error(t['mod_only'])
		logfailedcommand(kwargs['command'], kwargs['arguments'], message)

		await reply(message, emb=embed)
		return
	if kwargs['arguments'] == None:
		embed = emb.error('I’m not going to think up any rules by myself.')
		await reply(message, emb=embed)
		return
	if not message.server.id in events.rules:
		events.rules[message.server.id] = []

	splitargs = kwargs['arguments'].split(' ', 1)
	if splitargs[0].isdigit():
		if int(splitargs[0]) > len(events.rules[message.server.id]):
			content = '**Why are you mentioning the number if you’re adding this at the end?**\n'
		else:
			content = ''
		events.rules[message.server.id].insert(int(splitargs[0])-1, splitargs[1])
		content += 'New rule {} inserted:\n{}'.format(int(splitargs[0]), splitargs[1])      # Yes, this one is "inserted"...
	else:
		events.rules[message.server.id].append(kwargs['arguments'])
		content = 'New rule {} added:\n{}'.format(len(events.rules[message.server.id]), kwargs['arguments']) # ...and this one is "added". That is on purpose, not an inconsistency.
	embed = emb.success(content)
	rulesave()
	await reply(message, emb=embed)

@shadow(auth=is_mod, aliases=['editrule'])
async def ruleedit(client, message, **kwargs):
	if kwargs['arguments'] == None:
		embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
		await reply(message, emb=embed)
		return
	if not message.server.id in events.rules:
		embed = emb.error('No rules to edit.')
		await reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ', 1)
	if splitargs[0].isdigit():
		try:
			events.rules[message.server.id][int(splitargs[0])-1]
		except IndexError:
			embed = emb.error('Rule {} does not appear to exist.'.format(int(splitargs[0])))
			await reply(message, emb=embed)
			return

		embed = emb.success('Rule {} successfully edited from:\n{}\nTo:\n{}'.format(int(splitargs[0]), events.rules[message.server.id][int(splitargs[0])-1], splitargs[1]))

		events.rules[message.server.id][int(splitargs[0])-1] = splitargs[1]
		rulesave()
	else:
		embed = emb.error('Invalid rule number given, just check the help entry.')
	await reply(message, emb=embed)

@shadow(auth=is_mod, aliases=['moverule'])
async def rulemove(client, message, **kwargs):
	if kwargs['arguments'] == None:
		embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
		await reply(message, emb=embed)
		return
	if not message.server.id in events.rules:
		embed = emb.error('No rules to move.')
		await reply(message, emb=embed)
		return

	splitargs = kwargs['arguments'].split(' ', 1)
	if splitargs[0].isdigit() and splitargs[1].isdigit():
		try:
			events.rules[message.server.id][int(splitargs[0])-1]
			events.rules[message.server.id][int(splitargs[1])-1]
		except IndexError:
			embed = emb.error('Either rule {} does not exist or {} is not a slot it can be moved to.'.format(int(splitargs[0]), int(splitargs[1])))
			await reply(message, emb=embed)
			return

		rulecontent = events.rules[message.server.id][int(splitargs[0])-1]
		events.rules[message.server.id].remove(events.rules[message.server.id][int(splitargs[0])-1])
		events.rules[message.server.id].insert(int(splitargs[1])-1, rulecontent)
		rulesave()

		embed = emb.success('Rule {} successfully moved to number {}.'.format(int(splitargs[0]), int(splitargs[1])))
	else:
		embed = emb.error('Invalid rule number(s) given, just check the help entry.')
	await reply(message, emb=embed)

@shadow(auth=is_mod, aliases=['removerule'])
async def ruleremove(client, message, **kwargs):
	if kwargs['arguments'] == None:
		embed = emb.error('This command expects you to enter some more info, maybe read its help entry.')
		await reply(message, emb=embed)
		return
	if not message.server.id in events.rules:
		embed = emb.error('No rules to delete.')
		await reply(message, emb=embed)
		return

	if kwargs['arguments'].isdigit():
		try:
			events.rules[message.server.id][int(kwargs['arguments'])-1]
		except IndexError:
			embed = emb.error('Rule {} does not appear to exist.'.format(int(kwargs['arguments'])))
			await reply(message, emb=embed)
			return

		embed = emb.success('Rule {} successfully removed:\n{}'.format(int(kwargs['arguments']), events.rules[message.server.id][int(kwargs['arguments'])-1]))

		events.rules[message.server.id].remove(events.rules[message.server.id][int(kwargs['arguments'])-1])
		rulesave()
	else:
		embed = emb.error('Invalid rule number given, just check the help entry.')
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def rulemaint(client, message, **kwargs):
	if message.server.id in events.disabledrules:
		events.disabledrules.remove(message.server.id)
		embed = emb.success('Rules system enabled for this server.')
	else:
		events.disabledrules.append(message.server.id)
		embed = emb.success('Rules system disabled for this server.')
	with open('disabledrules.json', 'w') as outfile:
		json.dump(events.disabledrules, outfile)
	await reply(message, emb=embed)

@shadow()
async def info(client, message, **kwargs):
	persontocheck = utils.match_input('member', kwargs['arguments'], server=message.server)
	yesperm = '☑'
	noperm = '❎'
	try:
		perms = discord.Channel.permissions_for(message.channel, persontocheck)
	except AttributeError:
		embed = emb.error(t['specify_user'])
		await reply(message, emb=embed)
		return

	leftover = []
	for detected_p in iter(perms):
		leftover.append(detected_p[0])

	content = 'Permissions for **``{}``**`#{}` in <#{}>:\n**`Server Owner:`** {}'.format(persontocheck.name, persontocheck.discriminator, message.channel.id, yesperm if persontocheck == persontocheck.server.owner else noperm)

	for stored_p in permissionlabels:
		if not stored_p[0] in leftover:
			content += '\n**`{}:`** NOT USED'.format(stored_p[1])
		else:
			content += '\n**`{}:`** {}'.format(stored_p[1], yesperm if getattr(perms, stored_p[0]) else noperm)
			leftover.remove(stored_p[0])
		if perms.administrator:
			await reply(message, content)
			return

	for left_p in leftover:
		# Apparently these permissions are new
		content += '\n`{}:` {}'.format(left_p, yesperm if getattr(perms, left_p) else noperm)

	await reply(message, content)

@shadow()
async def teddy(client, message, **kwargs):
	content = 'xd'
	await reply(message, content)

@shadow()
async def samar(client, message, **kwargs):
	content = 'Why does he like Undertale?'
	await reply(message, content)

@shadow()
async def lui(client, message, **kwargs):
	content = 'i think /r/undertale is a pretty cool guy, eh deletes messages and doesnt afraid of lying'
	await reply(message, content)

@shadow()
async def shiny(client, message, **kwargs):
	content = 'moar liek shittykitty amirite'
	await reply(message, content)

@shadow()
async def tainy(client, message, **kwargs):
	content = random.choice([
		'moar liek stainy amirite',
		'moar like painy amirite',
	])
	await reply(message, content)

@shadow()
async def fuckingdense(client, message, **kwargs):
	content = random.choice([
		'I cant believe you destroyed my recreation of something better than the original Back to VVVVVV. I wish it was never against the rules in the 1st place. It took me forever to make it, and as a consequence for releasing it, I get this. Hate. Hate! HATE! You never did that when Dimension Anomaly came out! Next time, you better not send hate stuff',
		'Stop! I have children!',
		'Well. Well well well. Welly well well well. Well well well welly well well welly. Dimension anomaly still had effort, just with 3 dimensions. VVVVVV, Open, and ZYX. You dont want me to spam again, do you? If so, then dont give hatred for a simple remodified level. FIQ made the original, I recieved permission, and I got to make it slightly better and more challenging! Why, Vultarix...? :verdigris: Why? :vitellary: WHY? :victoria: We were on our way to REAL victory... :vermillion: On our way to making up for LAST time! :vermillion: Whyd you have to SCREW IT UP? :violet: Ahahahahaha... :viridian: Is this REVENGE? :vermillion: Making me watch you act so pure and happy, while I...? :victoria: ... :victoria: No. :verdigris: NO. :vermillion: I KNOW what youre doing. :vermillion: You just wanna see what its all like. :vermillion: Before we TEAR IT AWAY from them. :vermillion: Ahahahahaha... :vermillion: Genius, Vultarix. :vermillion: Well, Ill let you mess around. :viridian: I KNOW youll come back eventually. :vermillion: And when that time comes... :vermillion: Vultarix. :viridian: Ill be waiting for you. :viridian:',
		'Well. I guess the hate I received is critical. I never wanted hatred from everyone. Every time I do this thing, THIS. I get THIS. Hatred, hatred, everywhere! And to think Dimension Anomaly wasnt good enough! Look. Look! LOOK! Its a nightmare, I tell ya!',
		'Well. Well well well. Welly well well well. Well well well welly well well welly. You never accepted the fact it took me a bunch of days to deal with this. I had to copy the ROOMS, not remove the SCRIPTS. ... And now Im done with your hatred for what I do and how I do it. Im telling FIQ about what you said about Back to VVVVVV II... Through PM.',
		'THATS IT. I KNOW WHAT I MUST DO.',
	])
	await reply(message, content)

@shadow()
async def kys(client, message, **kwargs):
	content = 'nah'
	await reply(message, content)

@shadow()
async def botok(client, message, **kwargs):
	embed = emb.success('Bot is okay.')
	await reply(message, emb=embed)

@shadow()
async def uptime(client, message, **kwargs):
	hostuptime = subprocess.Popen(['uptime', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
	embed = discord.Embed(colour=col.r_success, timestamp=message.timestamp)
	embed.set_author(name='Uptime Statistics', icon_url=client.user.avatar_url)
	embed.set_thumbnail(url=client.user.avatar_url)
	embed.set_footer(text='Uptime Statistics', icon_url=client.user.avatar_url)
	embed.add_field(name='Boot Time', value=boottime)
	try:
		now = config.get_s('timeformat', message.server.id)
	except AttributeError:
		now = config.get_s('timeformat')
	embed.add_field(name='Current Time', value=time.strftime(now))
	embed.add_field(name='Bot Uptime', value=reltime(boottimeunix, True))
	embed.add_field(name='Host Uptime', value=hostuptime.decode('utf-8'))
	await reply(message, emb=embed)

@shadow()
async def invite(client, message, **kwargs):
	content = (
		'**`tOLP Discord`** – the server it’s built for. Join at __https://discord.gg/0r76El7PzkPMhSBF__.\n'
		'**`Aperture Science`** – the bot’s testing server. Join at __https://discord.gg/0skUn2HYSEHxw9Dg__.'
	)
	await reply(message, content)

@shadow()
async def version(client, message, **kwargs):
	embed = discord.Embed(colour=col.r_success, timestamp=message.timestamp)
	embed.set_author(name='Version Information', icon_url=client.user.avatar_url)
	embed.set_thumbnail(url=client.user.avatar_url)
	embed.set_footer(text='Version Information', icon_url=client.user.avatar_url)
	embed.set_thumbnail(url=client.user.avatar_url)
	embed.add_field(name='\\[\\\\\\]', value='{}, last updated {}'.format(botversion, modificationtimecache))
	embed.add_field(name='discord.py', value='{} {}'.format(discord.version_info.releaselevel, discord.__version__))
	embed.add_field(name='Python', value=sys.version)
	embed.add_field(name='PIL', value=__import__("PIL").VERSION)
	await reply(message, emb=embed)

@shadow(auth=is_mod)
async def getrawmessagecontent(client, message, **kwargs):
	try:
		argsplit = kwargs['arguments'].split(' ', 1)
		if len(argsplit) == 1:
			# Just the message ID, try finding it in all the channels
			getmessage = None
			for channel in message.server.channels:
				try:
					getmessage = await client.get_message(channel, argsplit[0])
					break
				except discord.errors.HTTPException:
					# If I can/may not view this message, or it's
					# not in this channel, then forget about it
					pass
			if getmessage == None:
				raise KeyError("Not found")
		else:
			arg0 = argsplit[0]
			arg1 = argsplit[1]
			channelid = arg0[2:-1]
			getchannel = client.get_channel(channelid)
			getmessage = await client.get_message(getchannel, arg1)
		content = '``{}``'.format(wrapbackticks(getmessage.content[:1900]))
		await reply(message, content)
		if getmessage.embeds != []:
			content = '``{}``'.format(wrapbackticks(getmessage.embeds[:1900]))
			await reply(message, content)
		return
	except AttributeError:
		embed = emb.error('Invalid arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
	except IndexError:
		embed = emb.error('Invalid amount of arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
	except (discord.errors.HTTPException, KeyError):
		embed = emb.error('Invalid channel or message ID given. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
	await reply(message, emb=embed)

@shadow()
async def countpins(client, message, **kwargs):
	if kwargs['arguments'] == None:
		getchannel = message.channel
	else:
		channelid = kwargs['arguments'][2:-1]
		getchannel = client.get_channel(channelid)
	try:
		pins = await client.pins_from(getchannel)
		content = '{} currently has {} pins, {} remaining.'.format(getchannel.mention, len(pins), 50-len(pins))
		await replyattach(message, images.progressbar(len(pins)*2), 'temp.png', content)
	except AttributeError:
		embed = emb.error('The channel doesn’t exist, has been deleted, or it’s not a channel at all. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
		await reply(message, emb=embed)

@shadow(servonly=True)
async def countallpins(client, message, **kwargs):
	await client.send_typing(message.channel)
	content = ''
	for chan in sorted(message.server.channels, key=lambda c: c.position):
		if str(chan.type) == 'text':
			try:
				pins = await client.pins_from(chan)
				content += '{} – {} pins, {} remaining\n'.format(chan.mention, len(pins), 50-len(pins))
			except discord.errors.Forbidden:
				content += '{} - Unable to get data\n'.format(chan.mention)
	await reply(message, content)

@shadow()
async def _math(client, message, **kwargs):
	# what kind of stupid language uses elif instead of elseif or else if?
	try:
		cmdbits = kwargs['arguments'].split() # should split it so [0] is number, [1] is operand, [2] is second number
	except AttributeError:
		embed = emb.error('Invalid arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
		await reply(message, emb=embed)
		return
	try:
		if len(cmdbits) != 3: # the arguments should be [number], [operand], [number]
			embed = emb.error('Invalid amount of arguments passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
			await reply(message, emb=embed)
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
			for i in range(int(numbers[1])): # decimal range isn't
				out = out ** oper # iterate until tetration is finished
		else: #invalid operand, we don't care what the inputs are
			embed = emb.error('Invalid operands passed. Input `{invoker}help {command}` for more information.'.format(invoker=invoker, command=kwargs['command']))
			await reply(message, emb=embed)
			return
	except OverflowError:
		embed = emb.error('Overflow error.')
		await reply(message, emb=embed)
		return
	except ValueError:
		embed = emb.error('You should probably enter in numbers.')
		await reply(message, emb=embed)
		return
	# end
	content = '{number1} {operand} {number2} = {out}'.format(number1=cmdbits[0], operand=cmdbits[1], number2=cmdbits[2], out=out)
	embed = discord.Embed(title='Math Output', description=content, colour=col.r_success)
	await reply(message, emb=embed)

@shadow(auth=is_operator)
async def gamestatus(client, message, **kwargs):
	await client.change_presence(game=discord.Game(name=kwargs['arguments']))
	embed = emb.success('Set game status to: ``{}``'.format(wrapbackticks(kwargs['arguments'])))
	await reply(message, emb=embed)

@shadow(auth=is_host, aliases=['evalfile', 'setvar'])
async def _eval(client, message, **kwargs):
	try:
		if kwargs['command'] == 'eval':
			evaluate = eval(kwargs['arguments'])
			if inspect.isawaitable(evaluate):
				evaluate = await evaluate
		elif kwargs['command'] == 'evalfile':
			evalfile = open('eval.txt', 'r')
			evalstring = evalfile.read()
			evaluate = eval(evalstring)
			evalfile.close()
		elif kwargs['command'] == 'setvar':
			splitargs = kwargs['arguments'].split(' ', 1)
			evaluate = eval(splitargs[1])
			if inspect.isawaitable(evaluate):
				evaluate = await evaluate
			evaluate = setglobal(splitargs[0], evaluate)
		content = '```py\n{}```'.format(wrapbackticks(str(evaluate)))
	except Exception:
		content = '```py\n{}```'.format(wrapbackticks(traceback.format_exc()))
	if len(content) > 2000:
		print((
			'The result of your latest evaluation command is:\n'
			'{}\n'
			'End of results.'
		).format(content))
		embed = emb.warning('Content too large to print. Printing to terminal instead.')
		await reply(message, emb=embed)
		return
	await reply(message, content)

@shadow(aliases=['serverban', 'unserverban'])
async def kick(client, message, **kwargs):
	targetmember = utils.match_input('member', kwargs['arguments'], server=message.server)
	try:
		if kwargs['command'] == 'kick':
			if not message.author.server_permissions.kick_members and \
			not kwargs['sudo']:
				logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(t['you_no_permission'])
				await reply(message, emb=embed)
				return
			await client.kick(targetmember)
		elif kwargs['command'] == 'serverban':
			if not message.author.server_permissions.ban_members and not kwargs['sudo']:
				logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(t['you_no_permission'])
				await reply(message, emb=embed)
				return
			await client.ban(targetmember, 0)
		elif kwargs['command'] == 'serverunban':
			if not message.author.server_permissions.ban_members and not kwargs['sudo']:
				logfailedcommand(kwargs['command'], kwargs['arguments'], message)
				embed = emb.error(t['you_no_permission'])
				await reply(message, emb=embed)
				return
			await client.unban(message.server, targetmember)
		content = targetmember.mention
		embed = emb.success('{}ed <@{}>.'.format(kwargs['command'].title() if kwargs['command'] == 'kick' else kwargs['command'].title() + 'n', targetmember.id))
	except AttributeError:
		content = ''
		embed = emb.error(t['specify_user'])
	except discord.errors.Forbidden:
		content = ''
		embed = emb.error(t['no_permission'])
	await reply(message, content, emb=embed)

@shadow()
async def bans(client, message, **kwargs):
	try:
		bans = await client.get_bans(message.server)
	except discord.errors.Forbidden:
		embed = emb.error(t['no_permission'])
		await reply(message, emb=embed)
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
	embed.set_thumbnail(url=message.server.icon_url)
	await reply(message, emb=embed)

@shadow(auth=is_operator)
async def reloadstrings(client, message, **kwargs):
	loadstrings()
	embed = emb.success('Reloaded strings.')
	await reply(message, emb=embed)

@shadow()
async def join(client, message, **kwargs):
	embed = emb.error('What an odd place to be using this command!')
	await reply(message, emb=embed)

@shadow(auth=is_tntgb_mod, aliases=['b_mod'])
async def b(client, message, **kwargs):
	if message.server.id != events.tntgbserver:
		embed = emb.error(t['tntgb_only'])
		await reply(message, emb=embed)
		return
	# Who are we banning, and for what reason?
	if kwargs['arguments'].find('\n') != -1:
		splitargs = kwargs['arguments'].split('\n', 1)
	elif kwargs['arguments'].find(' ') != -1:
		splitargs = kwargs['arguments'].split(' ', 1)
	else:
		splitargs = [kwargs['arguments'], '(no given reason)']

	banningnonmod = True
	announcemsg = ''
	specialchannel = getspecialchannel(message.channel.server)
	try:
		targetmember = utils.match_input('member', splitargs[0], server=message.server)
		if targetmember != None and is_tntgb_banned(targetmember):
			embed = emb.warning('{} is already banned!'.format(targetmember.mention))
			await client.send_message(specialchannel, embed=embed)
			banningnonmod = False  # See this as "don't set expiry timer"
		elif targetmember != None and is_tntgb_mod(targetmember):
			if kwargs['command'] != 'b_mod':
				embed = emb.warning(
					(
						'{} is a mod, please use `\\b_mod` instead '
						'to cause the oldest two bans to be lifted!'
					).format(targetmember.mention)
				)
				await client.send_message(specialchannel, embed=embed)

				# We're doing this in a public channel
				await client.delete_message(message)
				messages_deleted_by_bot.append(message)

				return

			# Get oldest two bans here and expire them
			expiredmentions = []

			# Technical messages:
			content = 'Lifted bans:'

			for i in range(0,2):
				currentexpiry = getearliestexpiry(message.server.id)

				if currentexpiry == None:
					continue

				try:
					await removeRestrictiveRoles(
						message.server.get_member(currentexpiry[0]),
						message.server
					)
					content +='\n<@!{}> lifted normally'.format(
						currentexpiry[0]
					)
				except (AttributeError, TypeError):
					# Look in the role cache
					if removerolecache(currentexpiry[0], message.server.id):
						rolecachesave()
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
					await editexpirymessage(message.server, thisexpiry)
				if not removeexpiryentry(message.server.id, currentexpiry[0]):
					try:
						em = emb.warning((
							'Could not remove expiry entry for '
							'<@!{}>! Debug: S:{} M:{} SI:{} MI:{}'
						).format(
							currentexpiry[0],
							message.server.id,
							currentexpiry[0],
							message.server.id in events.rolexpires,
							currentexpiry[0] in events.rolexpires
						))
						await client.send_message(specialchannel, embed=em)
					except:
						em = emb.error((
							'Something happened : Something happened :('
							'\n\nIn fact, you are seeing this because '
							'Dav didn\'t know whether he should make '
							'`rolexpires` global or not, and he made '
							'precisely the wrong choice, or he made '
							'some other kind of lame mistake. You '
							'want to know which one, huh? Here it is:'
							'\n{}'
						).format(traceback.format_exc()))
						await client.send_message(specialchannel, embed=em)
				expiredmentions.append('<@!{}>'.format(currentexpiry[0]))

			rolexpiresave()

			# Send administration info
			embed = emb.info(content)
			await client.send_message(specialchannel, embed=embed)

			# Now annouce it to the world
			if len(expiredmentions) == 2:
				whose = 'The bans on {} and {} have'.format(
					expiredmentions[0], expiredmentions[1]
				)
			elif len(expiredmentions) == 1:
				whose = 'The ban on {} has'.format(
					expiredmentions[0]
				)
			elif len(expiredmentions) == 0:
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
			await client.send_message(events.banlogchannel_tntgb, announcemsg)
			banningnonmod = False
		else:
			await client.replace_roles(targetmember,
				discord.utils.get(message.server.roles,
					id='243076976565288960'
				)
			)
			announcemsg = '{} has been banned for 5 days by {} in {} for {}.'.format(
				targetmember.mention,
				message.author.display_name,
				message.channel.mention,
				splitargs[1]
			)
			content = '⛔ ' + announcemsg
			sentmessage = await client.send_message(events.banlogchannel_tntgb, content)
	except (AttributeError,TypeError):
		embed = emb.error(t['specify_user'])
		await client.send_message(specialchannel, embed=embed)
		banningnonmod = False

	# Now delete the calling message
	await client.delete_message(message)
	messages_deleted_by_bot.append(message)

	if banningnonmod:
		# Also set an expiry timer
		expirytime = parsereltime('5d')

		addexpiryentry(message.server.id, targetmember.id, expirytime,
			e_channel=sentmessage.channel.id, e_message=sentmessage.id,
			e_newcontent='[LIFTED] ' + announcemsg,
			p_channel=events.banlogchannel_tntgb.id,
			p_content='The ban on {} has expired.'.format(targetmember.mention)
		)

		rolexpiresave()
		await handleExpiryTimer()

@shadow()
async def selfban(client, message, **kwargs):
	if message.server.id != events.tntgbserver:
		embed = emb.error(t['tntgb_only'])
		await reply(message, emb=embed)
		return
	if is_tntgb_banned(message.author):
		# Wait, what?
		embed = emb.warning('How, then? You are already banned!')
		await reply(message, emb=embed)
		return
	if is_tntgb_mod(message.author):
		specialchannel = getspecialchannel(message.channel.server)
		embed = emb.warning('Sorry, moderators cannot use `\selfban`!')
		await client.send_message(specialchannel, embed=embed)

		# We're doing this in a public channel
		await client.delete_message(message)
		messages_deleted_by_bot.append(message)

		return

	if kwargs['arguments'] == None or kwargs['arguments'] == '':
		kwargs['arguments'] = '(no given reason)'

	await client.replace_roles(message.author,
		discord.utils.get(message.server.roles,
			id='243076976565288960'
		)
	)
	announcemsg = '{} has carried out a self-ban for 5 days in {} for {}.'.format(
		message.author.mention,
		message.channel.mention,
		kwargs['arguments']
	)
	content = '⛔ ' + announcemsg
	sentmessage = await client.send_message(events.banlogchannel_tntgb, content)

	# Now delete the calling message
	await client.delete_message(message)
	messages_deleted_by_bot.append(message)

	# Also set an expiry timer
	expirytime = parsereltime('5d')

	addexpiryentry(message.server.id, message.author.id, expirytime,
		e_channel=sentmessage.channel.id, e_message=sentmessage.id,
		e_newcontent='[LIFTED] ' + announcemsg,
		p_channel=events.banlogchannel_tntgb.id,
		p_content='The ban on {} has expired.'.format(message.author.mention)
	)

	rolexpiresave()
	await handleExpiryTimer()

@shadow(auth=is_tntgb_mod, aliases=['b_left', 'b_offserver'])
async def b_id(client, message, **kwargs):
	if message.server.id != events.tntgbserver:
		embed = emb.error(t['tntgb_only'])
		await reply(message, emb=embed)
		return
	# Who are we banning, and for what reason?
	if kwargs['arguments'].find('\n') != -1:
		splitargs = kwargs['arguments'].split('\n', 1)
	elif kwargs['arguments'].find(' ') != -1:
		splitargs = kwargs['arguments'].split(' ', 1)
	else:
		splitargs = [kwargs['arguments'], '(no given reason)']

	# Now look if we can actually find the member. We're only looking for IDs, though!
	input = splitargs[0]
	if input.startswith('<@!') and input.endswith('>'):
		input = input[3:-1] # Extract the ID from it
	elif input.startswith('<@') and input.endswith('>'):
		input = input[2:-1] # Same

	targetmember = message.server.get_member(input)

	if targetmember == None:
		# Just as I thought, they left
		if not removerolecache(input, message.server.id):
			embed = emb.error((
				'Member {} cannot be found in the role cache. '
				'Please note you have to enter an ID, not any form of name!'
			).format(input))
			await reply(message, emb=embed)
			return

		# Okay, removing their entry altogether was a bit drastic
		events.memberroles[message.server.id][input] = []
		events.memberroles[message.server.id][input].append('243076976565288960')

		# Alright, just send a message about it now!
		# The extra space is intentional, it's a 'hidden' indicator to
		# see whether the ban was made after the person left the server
		announcemsg = '<@!{}>  has been banned for 5 days by {} in {} for {}.'.format(
			input,
			message.author.display_name,
			message.channel.mention,
			splitargs[1]
		)
		content = '⛔ ' + announcemsg
		sentmessage = await client.send_message(events.banlogchannel_tntgb, content)

		# Now delete the calling message
		await client.delete_message(message)
		messages_deleted_by_bot.append(message)

		# Also set an expiry timer
		expirytime = parsereltime('5d')

		addexpiryentry(message.server.id, input, expirytime,
			e_channel=sentmessage.channel.id, e_message=sentmessage.id,
			e_newcontent='[LIFTED] ' + announcemsg,
			p_channel=events.banlogchannel_tntgb.id,
			p_content='The ban on <@!{}> has expired.'.format(input)
		)

		rolexpiresave()
		await handleExpiryTimer()
	else:
		# Okay, they are on the server, so why not use \b?
		await b(client, message, **kwargs)

@shadow(auth=is_tntgb_mod, aliases=['banrevert'])
async def revertban(client, message, **kwargs):
	if message.server.id != events.tntgbserver:
		embed = emb.error(t['tntgb_only'])
		await reply(message, emb=embed)
		return

	specialchannel = getspecialchannel(message.channel.server)
	try:
		targetmember = utils.match_input(
			'member', kwargs['arguments'], server=message.server,
		)

		await removeRestrictiveRoles(targetmember, message.server)

		embed = emb.info('Ban on {} was reverted by {}.'.format(
				targetmember.mention, message.author.mention
			)
		)
		await client.send_message(specialchannel, embed=embed)

		# That member is also in the role cache. Right?
		if message.server.id not in events.rolexpires or \
		targetmember.id not in events.rolexpires[message.server.id]:
			embed = emb.warning('Could not find {} in the role cache!'.format(
					targetmember.mention
				)
			)
			await client.send_message(specialchannel, embed=embed)
			return

		# It's even longer this time
		thisexpiry = events.rolexpires[message.server.id][targetmember.id]
		if thisexpiry['msgedit_message'] != '0':
			thisexpiry['msgedit_newcontent'] = ''
			await editexpirymessage(message.server, thisexpiry)

		removeexpiryentry(message.server.id, targetmember.id)
		rolexpiresave()
	except (AttributeError,TypeError):
		embed = emb.error(t['specify_user'])
		await client.send_message(specialchannel, embed=embed)

@shadow(auth=is_admin, aliases=['tntgb_maint_p'])
async def tntgb_maint(client, message, **kwargs):
	if message.server.id != events.tntgbserver:
		embed = emb.error(t['tntgb_only'])
		await reply(message, emb=embed)
		return
	splitargs = kwargs['arguments'].split(' ')

	if kwargs['command'] == 'tntgb_maint_p':
		embed = emb.info('Opening prompt for `{}`'.format(splitargs[0]))
		await reply(message, emb=embed)

	try:
		while True:
			if kwargs['command'] == 'tntgb_maint_p':
				message2 = await client.wait_for_message(
					timeout=120,
					author=message.author,
					channel=message.channel
				)
				if message2 == None:
					embed = emb.info('Timed out, closing prompt')
					await reply(message, emb=embed)
					break
				if message2.content == 'exit':
					embed = emb.info('Ok, closing prompt')
					await reply(message, emb=embed)
					break
				splitargs[1] = message2.content
			output = ''
			if splitargs[0] == 'liftmsg':
				getmessage = await client.get_message(events.banlogchannel_tntgb, splitargs[1])
				content = getmessage.content
				if content.find('⛔') == -1:
					embed = emb.error('Cannot find the ⛔!')
					await reply(message, emb=embed)
					return
				content = content.replace('⛔', '[LIFTED]', 1)
				await client.edit_message(getmessage, new_content=content)
				output = 'Edited successfully.'
			elif splitargs[0] == 'addtimer':
				getmessage = await client.get_message(events.banlogchannel_tntgb, splitargs[1])
				content = getmessage.content
				m = re.search('<@!?([0-9]+)>', content)
				if m == None:
					embed = emb.error('m is None! Maybe I couldn’t find the mention.')
					await reply(message, emb=embed)
					return
				userid = m.group(1)
				newexpires = parsereltime('5d',
					now=time.mktime(getmessage.timestamp.timetuple())
				)

				sentbybot = False
				if getmessage.author == client.user:
					sentbybot = True

					if content.find('⛔') == -1:
						embed = emb.error('Cannot find the ⛔!')
						await reply(message, emb=embed)
						return
					content = content.replace('⛔', '[LIFTED]', 1)

					addexpiryentry(message.server.id, userid, newexpires,
						e_channel=getmessage.channel.id, e_message=getmessage.id,
						e_newcontent=content,
						p_channel=events.banlogchannel_tntgb.id,
						p_content='The ban on <@!{}> has expired.'.format(userid)
					)
				else:
					addexpiryentry(message.server.id, userid, newexpires,
						e_channel='0', e_message='0',
						e_newcontent='',
						p_channel=events.banlogchannel_tntgb.id,
						p_content='The ban on <@!{}> has expired.'.format(userid)
					)

				output = 'I found the member <@!{}>, and it expires {}. Also, the message was {} sent by me. Did I do it right?'.format(
					userid, reltime(newexpires),
					"" if sentbybot else "not"
				)

				rolexpiresave()
				await handleExpiryTimer()

			embed = emb.success('Nothing appears to have gone wrong. Output:\n'+output)
			await reply(message, emb=embed)

			if kwargs['command'] != 'tntgb_maint_p':
				break
	except:
		embed = emb.error('You don’t know what you’re doing, do you.\n`{}`'.format(
			traceback.format_exc())
		)
		await reply(message, emb=embed)

@shadow(auth=is_operator)
async def uploadfile(client, message, **kwargs):
	disalwfiles = ['bot_token.conf']
	try:
		if not os.path.abspath(kwargs['arguments']).startswith(os.getcwd()):
			e = emb.error('Cannot access paths above working directory.')
			await reply(message, emb=e)
			return
		elif kwargs['arguments'] in disalwfiles:
			e = emb.error('Cannot upload ``{file}``.'.format(
				file=kwargs['arguments'],
				)
			)
			await reply(message, emb=e)
			return
		await client.send_file(
			message.channel,
			kwargs['arguments'],
			content=events.msg_start,
		)
		return
	except FileNotFoundError:
		e = emb.error('That file does not exist.')
	except IsADirectoryError:
		e = emb.error('That file is a directory.')
	except AttributeError:
		e = emb.error('You should probably enter in something.')
	except:
		e = emb.error('`Something happened : Something happened :(`')
		raise
	await reply(message, emb=e)

@shadow(auth=is_mod, aliases=['blackunlist'], servonly=True)
async def blacklist(client, message, **kwargs):
	tgtmem = utils.match_input('member', kwargs['arguments'], server=message.server)
	if tgtmem == None:
		embed = emb.error('Unable to find that member. ' + t['specify_user'])
		await reply(message, emb=embed)
		return
	if not config.is_detached('blacklist', message.server.id):
		config.detach('blacklist', message.server.id)
	if kwargs['command'] == 'blacklist':
		if tgtmem.id in config.get_s('blacklist', message.server.id):
			embed = emb.error('{0.mention} is already blacklisted.'.format(tgtmem))
			await reply(message, emb=embed)
			return
		config.insert_s('blacklist', tgtmem.id, message.server.id)
		config.saveconfig()
		embed = emb.success('Blacklisted {0.mention} from this server.'.format(tgtmem))
		await reply(message, emb=embed)
		return
	elif kwargs['command'] == 'blackunlist':
		if tgtmem.id not in config.get_s('blacklist', message.server.id):
			embed = emb.error('{0.mention} is not blacklisted.'.format(tgtmem))
			await reply(message, emb=embed)
			return
		config.remove_s('blacklist', tgtmem.id, message.server.id)
		config.saveconfig()
		embed = emb.success('Blackunlisted {0.mention} from this server.'.format(tgtmem))
		await reply(message, emb=embed)
		return

@shadow()
async def _(client, message, **kwargs):
	con = message.author.mention + (
		'\n'
		'```fix\n'
		'Luigi: have you ever by accident pressed another key at the same time you have pressed enter?\'\n'
		'Luigi: ugh\n'
		'ShinyWolf07: \\\n'
		'ShinyWolf07: this\n'
		'Luigi: is\n'
		'Luigi: cancer\n'
		'ShinyWolf07: I always do th\n'
		'ShinyWolf07: its so annoyng\n'
		'ShinyWolf07: \\\n'
		'ShinyWolf07: UGh\\\n'
		'Luigi: xd\n'
		'Luigi: x\n'
		'Luigi: d\n'
		'Luigi: d\n'
		'ShinyWolf07: xd\\\n'
		'Luigi: x\n'
		'ShinyWolf07: F***!!!!!|\n'
		'Luigi: XD\n'
		'ShinyWolf07: ARGH\\\n'
		'Luigi: This is funny to watch you\n'
		'Luigi: Did you make popcorn\n'
		'ShinyWolf07: xd ikr \\\n'
		'ShinyWolf07: ...\n'
		'ShinyWolf07: -_-\\\n'
		'ShinyWolf07: GAH\\\n'
		'Luigi: don\'t you mean ...\\\n'
		'ShinyWolf07: ...\n'
		'ShinyWolf07: sigh\n'
		'Luigi: 10/10 would watch again```'
	)
	await reply(message, con)

@shadow()
async def __002Aformatting__002A(client, message, **kwargs):
	con = 'That’s italicized formatting.'
	await reply(message, con)

@shadow()
async def __002Fr__002Fundertale(client, message, **kwargs):
	con = (
		'They banned someone for posting an honest review of Undertale.'
		' Seriously, don’t go there if you don’t want to be censored.'
	)
	await reply(message, con)

@shadow(auth=is_operator)
async def sudo(client, message, **kwargs):
	try:
		command = kwargs['arguments'].split(' ', 1)[0]
	except AttributeError:
		e = emb.error('You should probably put something in.')
		await reply(message, emb=e)
		return

	# TODO: This is the command-parsing code copied from main.py, but with some changes.
	# Put the command-parsing code in a function instead.
	if message.content.startswith(invoker):
		altinvokeractive = False
	elif message.content.startswith(altinvoker):
		altinvokeractive = True
	if command in commands:
		func = commands[command]
	else:
		# Check if it's an alias
		for c, p in commands.items():
			if p[2] != None and command in p[2]:
				func = commands[c]
				break
		else:
			e = emb.warning(
				(
					'Invalid command. Input `\help` for'
					' a list of valid commands.'
				)
			)
			await reply(message, emb=e)
			return
	if func[1] == is_host and not func[1](message.author):
		e = emb.error(t['you_no_permission'])
		logfailedcommand(kwargs['command'], kwargs['arguments'], message)
		await reply(message, emb=e)
		return
	logcommand(kwargs['command'], kwargs['arguments'], message)
	kwargs['command'] = command
	if altinvokeractive:
		clean_command = message.clean_content.split(altinvoker, 1)[1]
	else:
		clean_command = message.clean_content.split(invoker, 1)[1]
	try:
		kwargs['arguments'] = kwargs['arguments'].split(' ', 1)[1]
		kwargs['clean_arguments'] = clean_command.split(' ', 2)[2]
	except IndexError:
		kwargs['arguments'] = None
		kwargs['clean_arguments'] = None
	kwargs['sudo'] = True
	await func[0](client, message, **kwargs)

@shadow(auth=is_channel_manager, servonly=True)
async def joinchannel(client, message, **kwargs):
	splitargs = kwargs['arguments'].split(' ')
	if len(splitargs) != 2:
		em = emb.error(
			(
				'Invalid amount of arguments passed.'
				' Input `{invoker}help {command}` for more information.'
			).format(
				invoker=invoker,
				command=kwargs['command'],
			),
		)
	if splitargs[0] == 'set':
		try:
			chan = client.get_channel(splitargs[1][2:-1])
		except IndexError:
			em = emb.error('You should probably enter in a channel.')
			await reply(message, emb=em)
			return
		if not chan:
			em = emb.error(
				(
					'Invalid channel. The channel must be a'
					' channel mention, i.e. in `<#ID>` form.'
				)
			)
			await reply(message, emb=em)
			return
		if not config.is_detached('joinchannel', message.server.id):
			config.detach('joinchannel', message.server.id)
		config.set_s('joinchannel', chan.id, message.server.id)
		config.saveconfig()
		em = emb.success(
			'Set {0.mention} to be the join channel for this server.'.format(chan)
		)
		await reply(message, emb=em)
		return
	elif splitargs[0] == 'unset':
		if not config.is_detached('joinchannel', message.server.id):
			config.detach('joinchannel', message.server.id)
		config.restore_default('joinchannel', message.server.id)
		config.saveconfig()
		em = emb.success('Unset the join channel for this server.')
		await reply(message, emb=em)
		return
	elif splitargs[0] == 'get':
		chanid = config.get_s('joinchannel', message.server.id)
		if chanid == '0':
			em = emb.info('There is no join channel set for this server.')
		else:
			chan = message.server.get_channel(chanid)
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
		await reply(message, emb=em)
	else:
		em = emb.error(
			(
				'Invalid arguments.'
				' Input `{invoker}help {command}` for more information.'
			).format(
				invoker=invoker,
				command=kwargs['command'],
			)
		)
		await reply(message, emb=em)
		return

@shadow(servonly=True)
async def testroleconditional(client, message, **kwargs):
	try:
		splitargs = kwargs['arguments'].split(' ')

		tgtmem = utils.match_input('member', splitargs[0], server=message.server)
		if tgtmem == None:
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
		await reply(message, emb=embed)
		raise

	await reply(message, emb=embed)

@shadow(auth=is_admin, servonly=True)
async def addcustomrolecommand(client, message, **kwargs):
	try:
		splitargs = kwargs['arguments'].split(' ')

		splitargs[5]
	except (AttributeError, IndexError):
		embed = emb.error('Invalid amount of arguments specified, please see the `\help`')
		await reply(message, emb=embed)
		return

	if splitargs[1] not in ('self', 'input'):
		embed = emb.error('`{}` is an invalid target, please see the `\help`'.format(
				utils.mdspecialchars(splitargs[1])
			)
		)
		await reply(message, emb=embed)
		return
	if splitargs[2] not in ('no', 'input', 'command') and parsereltime(splitargs[2]) is None:
		embed = emb.error('The expiry `{}` is invalid, please see the `\help`'.format(
				utils.mdspecialchars(splitargs[2])
			)
		)
		await reply(message, emb=embed)
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
		await reply(message, emb=embed)
		return
	if splitargs[4] == '[]':
		giveroles = []
	else:
		giveroles = splitargs[4][1:-1].split(',')

	if splitargs[5] == '[]':
		takeroles = []
	else:
		takeroles = splitargs[5][1:-1].split(',')

	if customcommands.exists(message.server, splitargs[0]):
		embed = emb.error('The custom command `{}` already exists!'.format(
				utils.mdspecialchars(splitargs[0])
			)
		)
		await reply(message, emb=embed)
		return

	builtin_alias_exists = False

	for c, p in commands.items():
		if p[2] is not None and splitargs[0] in p[2]:
			builtin_alias_exists = True
			break

	if builtin_alias_exists or splitargs[0] in commands:
		embed = emb.error('`{}` is already a built-in {} command!'.format(
				utils.mdspecialchars(splitargs[0]),
				utils.mdspecialchars('[\]')
			)
		)
		await reply(message, emb=embed)
		return

	customcommands.add_custom_command(message.server, splitargs[0],
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
	await reply(message, emb=embed)

@shadow(auth=is_admin, servonly=True)
async def addcustomaliascommand(client, message, **kwargs):
	try:
		splitargs = kwargs['arguments'].split(' ')

		splitargs[1]
	except (AttributeError, IndexError):
		embed = emb.error('Invalid amount of arguments specified, please see the `\help`')
		await reply(message, emb=embed)
		return

	if customcommands.exists(message.server, splitargs[0]):
		embed = emb.error('The custom command `{}` already exists!'.format(
				utils.mdspecialchars(splitargs[0])
			)
		)
		await reply(message, emb=embed)
		return

	builtin_alias_exists = 0  # 0 for false, 1 for command exists, 2 for aliased exists

	for c, p in commands.items():
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
		await reply(message, emb=embed)
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
		await reply(message, emb=embed)
		return

	if splitargs[0] == splitargs[1]:
		embed = emb.error((
				'Aliases do recursively call the run function... '
				'Maybe you can come up with something more creative?'
			)
		)
		await reply(message, emb=embed)
		return

	customcommands.add_custom_command(message.server, splitargs[0],
		{
			'type': 'alias',
			'to': splitargs[1]
		}
	)
	customcommands.save()

	if customcommands.exists(message.server, splitargs[1]):
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
	await reply(message, emb=embed)

@shadow(auth=is_admin, servonly=True)
async def removecustomcommand(client, message, **kwargs):
	if kwargs['arguments'] is None:
		embed = emb.error('Please supply the name of the command to remove.')
		await reply(message, emb=embed)
		return

	if not customcommands.exists(message.server, kwargs['arguments']):
		embed = emb.error('The custom command to remove doesn’t exist.')
		await reply(message, emb=embed)
		return

	customcommands.remove_custom_command(message.server, kwargs['arguments'])
	customcommands.save()

	embed = emb.success('Command `\{}` has been removed.'.format(
			utils.mdspecialchars(kwargs['arguments'])
		)
	)
	await reply(message, emb=embed)
