# encoding=utf-8

import datetime
import logging
import json
import os
import sys
import time

import discord

import bot
import checks
import config
import commands
import customcommands
import emb
import hangman
import op_ids
import utils

memberroles = {}
rolexpires = {}
rules = {}
disabledrules = []
botschannel = None
botschannel_tntgb = None
banlogchannel_tntgb = None
opguild = None
opguild_botguilds = None
productionguild = 153368829160849408
tntgbguild = 242099933665034240

msg_start = ''
latestroled = ''

async def on_ready():
	global memberroles, rules, disabledrules, botschannel, botschannel_tntgb, \
	banlogchannel_tntgb, rolexpires, opguild, opguild_botguilds
	guild = discord.utils.get(bot.client.guilds, id=productionguild)
	guild_tntgb = discord.utils.get(bot.client.guilds, id=tntgbguild)
	specialchannel_prod = discord.utils.get(guild.channels, id=234185735266238464)
	botschannel = discord.utils.get(guild.channels, id=201130047736643584)
	botschannel_tntgb = discord.utils.get(guild_tntgb.channels, id=266626198249930764)
	banlogchannel_tntgb = discord.utils.get(guild_tntgb.channels, id=242253449922609152)
	opguild = discord.utils.find(lambda s: s.id == bot.opguildid, bot.client.guilds)
	opguild_botguilds = discord.utils.find(
		lambda c: c.id == 291764490578558977,
		opguild.channels,
	)
	logging.info('logged in as %s with id %s', bot.client.user.name, bot.client.user.id)
	await bot.client.change_presence(game=discord.Game(name=config.get_s('gamestatus')))
	embed = discord.Embed(
		title='🔌BOT CONNECTED',
		colour=discord.utils.find(
			lambda s: s.id == op_ids.ids['opguild'], bot.client.guilds,
		).me.colour,
	)
	embed.add_field(name='Startup Time', value=utils.reltime(bot.boottimeunix))
	await bot.client.get_channel(int(op_ids.ids['opguild_chans']['connections'])).send(
		embed=embed,
	)

	try:
		with open('memberroles.json', 'r') as infile:
			memberroles = json.load(infile)

		# Now look what I've woken up to.
		for gld in memberroles:
			if config.get_s('rolecachemode', gld) == 0:
				continue
			rcwarnings = ''
			for mem in bot.client.get_guild(gld).members:
				if not str(mem.id) in memberroles[gld]:
					if len(mem.roles) >= 2:
						rcwarnings += '\nUser {}#{} ({}) is not in the cache! (They’re suddenly in the server.) Adding their roles to the cache now.'.format(mem.name, mem.discriminator, mem.id)

						# Possibly redundant list() tbh, just making sure
						# since I can't test and I don't know python well
						# enough to know whether it's redundant
						memberroles[gld][str(mem.id)] = \
						list(utils.rolelist(mem.roles))

					continue
				if set(memberroles[gld][str(mem.id)]) != \
				set(utils.rolelist(mem.roles)):
					rcwarnings += (
						'\n'
						'User {}#{} ({}) has different roles than in the cache! Maybe you want to correct things.\n'
						'    **`Cached:`** {}\n'
						'    **`Seen:`** {}'
					).format(
						mem.name, mem.discriminator, mem.id,
						utils.listroles_id(memberroles[gld][str(mem.id)]),
						utils.listroles(mem.roles),
					)
			if rcwarnings:
				logging.warning(
					'Role cache warnings for server %s: %s',
					gld,
					rcwarnings,
				)
				rcwarnings = (
					'**User role cache warning.**\n'
					'Full warning output has been sent to the terminal.\n'
					+ rcwarnings
				)
				await utils.getspecialchannel(
						discord.utils.get(bot.client.guilds, id=gld)
				).send(rcwarnings[:1900])

	except FileNotFoundError:
		# Maybe we do have an old members.json?
		try:
			with open('members.json', 'r') as infile:
				memberrolesold = json.load(infile)
			# Convert it to the new system where all guilds can use it!
			logging.info('CONVERTING OLD members.json TO memberroles.json')
			memberroles = {productionguild: memberrolesold}

			with open('memberroles.json', 'w') as outfile:
				json.dump(memberroles, outfile)

			logging.info('Exiting (aka restarting) now to make the conversion go smoothly...')
			await bot.client.logout()
			sys.exit(43)
		except FileNotFoundError:
			logging.info('memberroles file does not exist yet so creating it now')

			with open('memberroles.json', 'w') as outfile:
				json.dump(memberroles, outfile)

			await specialchannel_prod.send(
				'Members file didn’t yet exist, created a new one.'
				' Please run `\\rolesync` to sync up the roles cache.',
			)

	try:
		with open('rules.json', 'r') as infile:
			rules = json.load(infile)
	except FileNotFoundError:
		logging.info('rules file does not exist yet so creating it now')

		with open('rules.json', 'w') as outfile:
			json.dump(rules, outfile)

		await specialchannel_prod.send('Rules file didn’t exist yet, created a new one.')

	try:
		with open('disabledrules.json', 'r') as infile:
			disabledrules = json.load(infile)
	except FileNotFoundError:
		logging.info('disabledrules file does not exist yet so creating it now')

		with open('disabledrules.json', 'w') as outfile:
			json.dump(disabledrules, outfile)

		await specialchannel_prod.send(
			'Disabledrules file didn’t exist yet, created a new one.',
		)

	try:
		with open('rolexpires.json', 'r') as infile:
			rolexpires = json.load(infile)
	except FileNotFoundError:
		logging.info('rolexpires file does not exist yet so creating it now')

		with open('rolexpires.json', 'w') as outfile:
			json.dump(rolexpires, outfile)

		await specialchannel_prod.send(
			'Rolexpires file didn’t exist yet, created a new one.',
		)

	await utils.handleExpiryTimer()

	for chan in bot.client.get_all_channels():
		if isinstance(chan, discord.TextChannel):
			msgs = chan.history()
			try:
				async for m in msgs:
					bot.client._connection._messages.append(m)
			except discord.errors.Forbidden:
				logging.info(
					'Failed to retrieve message history for'
					' %s (%s)#%s (%s).',
					chan.guild.name, chan.guild.id, chan.name, chan.id,
				)

	# Now set up our own cache, that Discord.py won't remove messages from before telling us!
	for m in bot.client._connection._messages:
		bot.owncache.append(m.id)

async def on_message(m):
	bot.owncache.append(m.id)

	if m.author == bot.client.user or m.author.bot:
		return

	if isinstance(m.channel, discord.abc.PrivateChannel):
		e = discord.Embed(
			description=m.content,
			timestamp=m.created_at,
			colour=bot.client.get_guild(op_ids.ids['opguild']).me.colour,
		)
		e.set_author(name=m.author.name, icon_url=m.author.avatar_url)
		e.set_footer(text=utils.id_summary(uid=m.author.id, mid=m.id, cid=m.channel.id))
		await bot.client.get_channel(op_ids.ids['opguild_chans']['direct_messages']).send(
			embed=e,
		)

	global msg_start
	schan = utils.getspecialchannel_reply(m)
	indisp = (
		(
			'``{}``**`…`**'
		).format(
			utils.wrapbackticks(m.content[:100]).replace('discord.gg', 'discord\u200b.gg')
		)
	) if len(m.content) > 100 else (
		'``{}``'.format(utils.wrapbackticks(m.content))
		.replace('\n', '``**`\\n`**``​')
		.replace('discord.gg', 'discord\u200b.gg')
	)
	if indisp[-12:] == '``**`\\n`**``​':
		indisp += '``'
	priv = utils.isprivatemessage(m.guild)

	if not priv and \
	m.author.status is discord.Status.offline and \
	not utils.logdisabled('invisible_sentmessage', m.guild):
		e = discord.Embed(
			title=(
				':ghost:INVISIBLE WHILE SENDING MESSAGE IN {chanmen}'
			).format(
				chanmen=m.channel.mention
			),
			description=m.content,
			colour=m.author.colour
		)
		e.set_author(
			name=m.author.display_name,
			icon_url=m.author.avatar_url,
			url=utils.infourl(
				'userid={0.author.id}&messageid={0.id}'
			).format(m)
		)
		await schan.send(embed=e)

	if not priv and m.tts:
		e = discord.Embed(
			title=(
				':microphone2:Message {0.id} was sent with TTS'
				' in {0.channel.mention}'
			).format(m),
			description=m.content,
			colour=m.author.colour,
			timestamp=m.created_at,
		)
		e.set_author(
			name=m.author.display_name,
			icon_url=m.author.avatar_url
		)
		e.add_field(
			name='Message author',
			value='<@!{id}> ({id})'.format(id=m.author.id)
		)
		await schan.send(embed=e)

	if not priv and m.attachments:
		a = await utils.fetch(m.attachments[0].url)
		fn = (
			'{atchcche}/{id}_{fn}'
		).format(
			atchcche=bot.attachcache,
			id=m.attachments[0].id,
			fn=m.attachments[0].filename,
		)
		with open(fn, 'wb') as f:
			f.write(a)
			f.close()

	if not priv and m.embeds != []:
		for n, e in enumerate(m.embeds):
			if e.type == 'image':
				# get the filename from the url
				# i.e. the part after the last forward slash
				fn = e.url.split('/')[-1]

				# fetch the embed preview discord fetches
				img = await utils.fetch(e.thumbnail.proxy_url)

				# cache the image
				dfn = '{embedcache}/{m.id}_{n}_{fn}'.format(
					embedcache=bot.embedcache,
					m=m,
					n=n,
					fn=fn,
				)
				with open(dfn, 'wb') as f:
					f.write(img)
					f.close()

	if not priv and m.author.id in config.get_s('blacklist', m.guild.id):
		return

	if priv and m.author.id in config.get_s('blacklist'):
		return

	if m.content.startswith(bot.invoker):
		altinvokeractive = False
		hangmaninvokeractive = False
	elif m.content.startswith(bot.altinvoker):
		altinvokeractive = True
		hangmaninvokeractive = False
	elif m.content.startswith(bot.hangmaninvoker):
		hangmaninvokeractive = True
	else:
		# Not of the bot's interest, but is this in the join channel for this guild?
		if not priv and \
		config.get_s('rolecachemode', m.guild.id) == 2 and \
		m.channel.id == config.get_s('joinchannel', m.guild.id):
			await m.delete()
			bot.messages_deleted_by_bot.append(m)
		return

	if priv:
		invokesymbol = '@'
	elif checks.is_mod(m.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'
	if hangmaninvokeractive:
		if m.channel.id not in hangman.games:
			return
		hm_inst = hangman.games[m.channel.id]
		if not hm_inst.active:
			# We didn't clean up?
			del hangman.games[m.channel.id]
			return
		if checks.is_mod(m.author):
			msg_start = (
				'**`>`**``{name}``**`#`**{indisp}\n'
			).format(
				name=utils.wrapbackticks(m.author.name),
				indisp=indisp,
			)
		else:
			msg_start = (
				'**`>`**``{name}``**`$`**{indisp}\n'
			).format(
				name=utils.wrapbackticks(m.author.name),
				indisp=indisp,
			)
		if priv:
			e = emb.error('Guesses are not accepted via PM.')
			await m.channel.send(msg_start, embed=e)
			return
		hangmanguessed = m.content[1:]

		if len(hangmanguessed) == 1:
			# Have we already used that letter? And is it a valid letter?
			if not hangman.validletter(hangmanguessed):
				e = emb.error(
					'The character ``{}`` is invalid.'
					.format(utils.wrapbackticks(hangmanguessed.upper()))
				)
				await m.channel.send(msg_start, embed=e)
				return
			if hm_inst.alreadyguessed(hangmanguessed):
				e = emb.error(
					'The letter **{}** has already been used.'
					.format(hangmanguessed.upper())
				)
				await m.channel.send(msg_start, embed=e)
				return
			# Ok, so does this letter occur in the word?
			if hm_inst.guess(hangmanguessed):
				# It does!
				con = '**{ltr}** is correct!\n{worddisp}'.format(
						ltr=hangmanguessed.upper(),
						worddisp=hm_inst.worddisp()
					)
				msg = msg_start + con

				if hm_inst.fullyguessed():
					msg += (
						'\nYou guessed the word correctly!'
						' You made {n} mistakes in total.'
						.format(n=hm_inst.mistakes)
					)
					await m.channel.send(msg)
					return

				await m.channel.send(msg)
			else:
				# It doesn't.
				if hm_inst.isgameover():
					con = (
						'**{ltr}** is incorrect! Game over.'
						' The word was: **{word}**'
					).format(
						ltr=hangmanguessed.upper(),
						word=hm_inst.word,
					)
					msg = msg_start + con
					await m.channel.send(msg)
					return
				else:
					attleft = hm_inst.attemptsleft()
					if attleft != 1:
						plural = 's'
					else:
						plural = ''
					con = (
						'**{ltr}** is incorrect!'
						' {attempts} attempt{pl} left.\n'
						'{worddisp}'
					).format(
						ltr=hangmanguessed.upper(),
						attempts=attleft,
						pl=plural,
						worddisp=hm_inst.worddisp(),
					)
					msg = msg_start + con
					await m.channel.send(msg)
					return
		else:
			# We're guessing the entire word. Well, is it the word?
			if not hm_inst.correctlength(hangmanguessed):
				# We're not even trying. It's not the same length.

				if not hangmanguessed:
					# if before was "not even trying", this is -1 trying
					e = emb.error('You should probably enter in a letter.')
					await m.channel.send(msg_start, embed=e)
					return
				e = emb.error(
					(
						'**``{guess}``** isn’t even the same length'
						' as the correct word. Please try again.'
					).format(
						guess=utils.wrapbackticks(hangmanguessed)
					)
				)
				await m.channel.send(msg_start, embed=e)
				return
			elif hm_inst.fullwordguess(hangmanguessed):
				con = (
					'You guessed the word ({word}) correctly!'
					' You made {n} mistakes in total.'
				).format(
					word=hm_inst.word,
					n=hm_inst.mistakes,
				)
				msg = msg_start + con
				await m.channel.send(msg)
				return

			if hm_inst.isgameover():
				con = (
					'**{guess}** is not the word! Game over.'
					' The word was: **{word}**'
				).format(
					guess=hangmanguessed,
					word=hm_inst.word,
				)
				msg = msg_start + con
				await m.channel.send(msg)
				return

			attleft = hm_inst.attemptsleft()
			if attleft != 1:
				plural = 's'
			else:
				plural = ''
			con = (
				'**{guess}** is not the word!'
				' {attempts} attempt{pl} left.\n{worddisp}'
			).format(
				guess=hangmanguessed,
				attempts=attleft,
				pl=plural,
				worddisp=hm_inst.worddisp(),
			)
			msg = msg_start + con
			await m.channel.send(msg)
			return

		return

	elif altinvokeractive:
		command = m.content.split(bot)[1]
		clean_command = m.clean_content.split(bot.altinvoker, 1)[1]
	else:
		command = m.content.split(bot.invoker, 1)[1]
		clean_command = m.clean_content.split(bot.invoker, 1)[1]
	msg_start = (
		'**`>`**``{name}``**`{invsym}`**{indisp}\n'
	).format(
		name=utils.wrapbackticks(m.author.name),
		invsym=invokesymbol,
		indisp=indisp,
	)
	try:
		arguments = command.split(' ', 1)[1]
		clean_arguments = clean_command.split(' ', 1)[1]
	except IndexError:
		arguments = None
		clean_arguments = None
	command = command.split(' ', 1)[0]
	clean_command = clean_command.split(' ', 1)[0]
	# Prevent access to those who aren't supposed to send messages
	if not priv and \
	config.get_s('rolecachemode', m.guild.id) == 2 and \
	m.channel.id == config.get_s('joinchannel', m.guild.id):
		# Join channel
		if command == 'join' and len(m.author.roles) <= 1:
			await utils.newmemberroles(m.author, utils.getspecialchannel(m.guild), True)
		await m.delete()
		bot.messages_deleted_by_bot.append(m)
		return
	# But react to the message as a hint to the message sender
	if not priv and \
	not checks.is_mod(m.author) and \
	m.channel.id != 201130047736643584 and \
	m.guild.id == productionguild and \
	not (checks.is_dev(m.author) and m.channel.id == 238423391571279872) and \
	not command in ('rule', 'rules', 'rulefind', 'rulesfind') and \
	not (m.channel.id == 256924583737819146 and command in ('votevoicemute', 'vy', 'vn')):
		if utils.is_valid_command(command) and command != '':
			await m.add_reaction(
				discord.utils.get(
					m.guild.emojis,
					id=262051482549878796,
				),
			)
		return
	if not priv and \
	m.guild.id == tntgbguild and \
	m.channel != botschannel_tntgb and \
	not checks.is_tntgb_mod(m.author) and \
	command != 'selfban':
		return
	if not priv and \
	not checks.is_mod(m.author) and \
	not config.get_s('alloweverywhere', m.guild.id) and \
	not m.channel.id in config.get_s('allowedchannels', m.guild.id) and \
	not command in config.get_s('globalcommands', m.guild.id):
		return
	if not priv and command in config.get_s('disabledcommands', m.guild.id):
		e = emb.error('This command is currently disabled{onthisguild}.'.format(
			onthisguild=(
				' on this server'
				if config.is_detached('disabledcommands', m.guild.id) else
				'')
			)
		)
		await bot.reply(m, emb=e)
		return

	if priv and command in config.get_s('disabledcommands'):
		e = emb.error('This command is currently disabled.')
		await bot.reply(m, emb=e)
		return

	if command in commands.commands:
		func = commands.commands[command]
	elif customcommands.exists(m.guild, command):
		try:
			await customcommands.run(
				m.guild, command, m, arguments, clean_arguments, invokesymbol
			)
		except discord.errors.Forbidden:
			e = emb.error(bot.t['no_permission'])
			await bot.reply(m, emb=e)
			raise
		except Exception:
			e = emb.error(bot.t['generic_error'])
			await bot.reply(m, emb=e)
			raise
		return
	else:
		# Check if it's an alias
		for c, p in commands.commands.items():
			if p[2] is not None and command in p[2]:
				func = commands.commands[c]
				break
		else:
			if (not priv and config.get_s('notify_invalidcmd', m.guild.id)) or \
			(priv and config.get_s('notify_invalidcmd')):
				e = emb.warning(
					(
						'Invalid command. Input `\help` for'
						' a list of valid commands.'
					)
				)
				await bot.reply(m, emb=e)
			return

	if isinstance(m.channel, discord.abc.PrivateChannel) and func[3]:
		e = emb.error(bot.t['noprivate'])
		await bot.reply(m, emb=e)
		return
	if func[1] is not None and not func[1](m.author):
		e = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(command, arguments, m)
		await bot.reply(m, emb=e)
		return
	kwargs = {
		'command': command,
		'arguments': arguments,
		'clean_arguments': clean_arguments,
		'invokesymbol': invokesymbol,
		'sudo': False,
	}
	try:
		await func[0](bot.client, m, **kwargs)
	except discord.errors.Forbidden:
		e = emb.error(bot.t['no_permission'])
		await bot.reply(m, emb=e)
		raise
	except Exception:
		e = emb.error(bot.t['generic_error'])
		await bot.reply(m, emb=e)
		raise

async def on_message_delete(msg):
	bot.deleted_messages.append(msg)
	if utils.isprivatemessage(msg.guild):
		return
	if msg.author == bot.client.user:
		logging.info(
			'bot message %s by user %s#%s (%s)'
			' in channel %s (%s) at %s utc deleted,'
			' original content is\n%s',
			msg.id, msg.author.name, msg.author.discriminator, msg.author.id,
			msg.channel.id, msg.channel.name, msg.created_at,
			msg.content,
		)
		return
	if (msg.content == '' and msg.attachments == []) \
	or utils.logdisabled('message_delete', msg.guild):
		return
	schan = utils.getspecialchannel_reply(msg)
	em = discord.Embed(
		title=(
			'\N{NO ENTRY SIGN}MESSAGE {withatch}DELETED (SENT {reltime} IN #{chan})'
		).format(
			withatch='WITH ATTACHMENT ' if msg.attachments != [] else '',
			reltime=utils.reltime(time.mktime(msg.created_at.timetuple())),
			chan=utils.mdspecialchars(msg.channel.name),
		),
		description=msg.content,
		colour=msg.author.colour,
	)
	em.set_author(
		name=msg.author.display_name,
		icon_url=msg.author.avatar_url,
	)
	em.set_footer(text=utils.id_summary(uid=msg.author.id, mid=msg.id, cid=msg.channel.id))
	await schan.send(embed=em)
	if msg.attachments != []:
		fp = (
				'{atchcche}/{id}_{fn}'
		).format(
			atchcche=bot.attachcache,
			id=msg.attachments[0]['id'],
			fn=msg.attachments[0]['filename'],
		)
		if os.path.isfile(fp):
			con = (
				'_\N{PAPERCLIP}The attachment for message {0.id} is attached._'
			).format(msg)
			try:
				await schan.send(
					con,
					file=discord.File(
						fp,
						filename=msg.attachments[0]['filename'],
					),
				)
			except discord.HTTPException:
				con = (
					'_Failed to upload the attachment for message {0.id}._'
				).format(msg)
				await schan.send(con)
		else:
			con = (
				'_The attachment for message {0.id} was not found'
				' in the message attachments cache._'
			).format(msg)
			await schan.send(con)
	if msg in bot.messages_deleted_by_bot:
		bot.messages_deleted_by_bot.remove(msg)
		return
	dthreshold = datetime.timedelta(
		seconds=config.get_s('deleted_message_resend_timer', msg.guild.id),
	)
	if (datetime.datetime.now() - msg.created_at) < dthreshold and \
	not msg.author.bot:
		if config.get_s('deleted_message_resend_content', msg.guild.id):
			em = discord.Embed(
				title='UNDELETED MESSAGE',
				description=msg.content,
				colour=msg.author.colour,
			)
			em.set_footer(
				text='This message was resent as it was deleted too recently.',
			)
		else:
			em = discord.Embed(title='Message was deleted', colour=msg.author.colour)
			em.set_footer(
				text=(
					'This notification was sent because a message by this'
					' user was deleted too recently.'
				),
			)
		em.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
		await msg.channel.send(embed=em)

async def on_message_edit(old, new):
	if utils.isprivatemessage(old.guild):
		return
	schan = utils.getspecialchannel_reply(new)
	if not old.pinned and new.pinned and not utils.logdisabled('message_pin', new.guild):
		em = discord.Embed(
			title=(
				'\N{PUSHPIN}MESSAGE PINNED (SENT {reltime} IN #{chan})'
			).format(
				reltime=utils.reltime(time.mktime(new.created_at.timetuple())),
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
		await schan.send(embed=em)
	if old.pinned and not new.pinned and not utils.logdisabled('message_unpin', new.guild):
		em = discord.Embed(
			title=(
				'\N{PUSHPIN}MESSAGE UNPINNED (SENT {reltime} IN #{chan})'
			).format(
				reltime=utils.reltime(time.mktime(new.created_at.timetuple())),
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
		await schan.send(embed=em)

	# Preliminary checkings
	if old.content == new.content:
		# Must be the message being pinned and/or embed(s) displaying
		# Actually, TTS and rich embeds could also have changed,
		# but this is just a refactor
		return

	if not utils.logdisabled('message_edit', new.guild):
		if len(new.content) > 1024 or len(new.content) > 1024:
			em = discord.Embed(
				title=(
					'\N{MEMO}MESSAGE EDITED (SENT {reltime} IN #{chan}).'
					' The older content is:'
				).format(
					reltime=utils.reltime(
						time.mktime(
							new.created_at.timetuple(),
						),
					),
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
			await schan.send(embed=em)
			em = discord.Embed(
				title=(
					'MESSAGE EDITED (SENT {reltime} IN #{chan}).'
					' The newer content is:'
				).format(
					reltime=utils.reltime(
						time.mktime(
							new.created_at.timetuple(),
						),
					),
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
			await schan.send(embed=em)
		else:
			em = discord.Embed(
				title=(
					'\N{MEMO}MESSAGE EDITED (SENT {reltime} IN #{chan})'
				).format(
					reltime=utils.reltime(
						time.mktime(
							new.created_at.timetuple(),
						),
					),
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
			await schan.send(embed=em)

	# Turning off this logging also turns off the feature
	if not utils.logdisabled('message_overedit', new.guild):
		# Delete a message if it has been edited more than 5 times in 30 seconds
		await utils.handle_minute_message_edits(new, schan)

async def on_member_update(before, after):
	specialchannel = utils.getspecialchannel(after.guild)
	if before.nick != after.nick and not utils.logdisabled('member_nickname', after.guild):
		embed = discord.Embed(title='🇳📟CHANGED NICKNAME'.format(id=after.id), colour=after.colour)
		embed.set_author(
			name=after.display_name,
			icon_url=after.avatar_url,
			url=utils.infourl('userid=' + after.id),
		)
		if before.nick is None:
			embed.add_field(name='No Older Nickname', value='_No Older Nickname_')
		else:
			embed.add_field(name='Older Nickname', value=utils.mdspecialchars(before.nick))
		embed.add_field(name='\u200b', value='\u200b')
		if after.nick is None:
			embed.add_field(name='No Newer Nickname', value='_No Newer Nickname_')
		else:
			embed.add_field(name='Newer Nickname', value=utils.mdspecialchars(after.nick))
		await specialchannel.send(embed=embed)
	if before.roles != after.roles:
		if utils.logdisabled('member_roleadd', after.guild):
			addedroles = []
		else:
			addedroles   = list(set(after.roles) - set(before.roles))

		if utils.logdisabled('member_roleremove', after.guild):
			removedroles = []
		else:
			removedroles = list(set(before.roles) - set(after.roles))

		if addedroles or removedroles:
			title = ''
			if addedroles and removedroles:
				title = 'ROLES CHANGED FOR USER'
			elif len(addedroles) > 1:
				title = 'ROLES ADDED TO USER'
			elif len(addedroles) == 1:
				title = 'ROLE ADDED TO USER'
			elif len(removedroles) > 1:
				title = 'ROLES REMOVED FROM USER'
			elif len(removedroles) == 1:
				title = 'ROLE REMOVED FROM USER'

			embed = discord.Embed(title=title)

			embed.set_author(
				name=after.display_name,
				icon_url=after.avatar_url,
				url=utils.infourl('userid=' + after.id),
			)
			for role in addedroles:
				embed.add_field(
					name='Added role',
					value=utils.mdspecialchars('{} ({})'.format(
							role.name, role.id
						)
					)
				)
			for role in removedroles:
				embed.add_field(
					name='Removed role',
					value=utils.mdspecialchars('{} ({})'.format(
							role.name, role.id
						)
					)
				)
			await specialchannel.send(embed=embed)

		if config.get_s('rolecachemode', after.guild.id) != 0:
			utils.updaterolecache(after)
			utils.rolecachesave()
	if before.name != after.name and not utils.logdisabled('member_username', after.guild):
		description = '🇺📟CHANGED USERNAME'.format(id=after.id)
		if before.discriminator != after.discriminator:
			description += ' AND DISCRIMINATOR 🔸'
		embed = discord.Embed(title=description, colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=utils.infourl('userid=' + after.id))
		embed.add_field(name='Older Username', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Username', value=utils.mdspecialchars(after.name))
		if before.discriminator != after.discriminator:
			embed.add_field(name='Older Discriminator', value=before.discriminator, inline=False)
			embed.add_field(name='Newer Discriminator', value=after.discriminator)
		await specialchannel.send(embed=embed)
	if before.avatar_url != after.avatar_url and \
	(not utils.logdisabled('member_botavatar', after.guild) \
	if checks.is_bot(after) \
	else not utils.logdisabled('member_avatar', after.guild)):
		embed = discord.Embed(description='👥<@!{id}> ({id}) changed avatar'.format(id=after.id), colour=after.colour, timestamp=datetime.datetime.now())
		embed.set_author(name=after.display_name, icon_url=after.avatar_url)
		embed.set_thumbnail(url=before.avatar_url)
		embed.set_image(url=after.avatar_url)
		embed.add_field(name='Older Avatar URL: None' if before.avatar_url == '' else 'Older Avatar URL (Thumbnail)', value='No Older Avatar URL' if before.avatar_url == '' else before.avatar_url)
		embed.add_field(name='Newer Avatar URL: None' if after.avatar_url == '' else 'Newer Avatar URL (Inset Image)', value='No Newer Avatar URL' if after.avatar_url == '' else after.avatar_url, inline=False)
		await specialchannel.send(embed=embed)

async def on_member_join(member):
	if not utils.logdisabled('member_join', member.guild):
		specialchannel = utils.getspecialchannel(member.guild)
		embed = discord.Embed(
			description='➡<@!{id}> ({id}) joined server'.format(id=member.id),
			colour=member.guild.me.colour,
			timestamp=datetime.datetime.now(),
		)
		embed.add_field(
			name='This server now has',
			value=str(member.guild.member_count) + ' members',
		)
		embed.set_author(name=member.display_name)
		embed.set_thumbnail(url=member.avatar_url)
		await specialchannel.send(embed=embed)
	await utils.newmemberroles(member, specialchannel, False)

async def on_member_remove(member):
	if not utils.logdisabled('member_remove', member.guild):
		specialchannel = utils.getspecialchannel(member.guild)
		embed = discord.Embed(description='🚪<@!{id}> ({id}) removed from server'.format(id=member.id), colour=member.colour, timestamp=datetime.datetime.now())
		embed.add_field(name='Originally joined server', value=utils.reltime(time.mktime(member.joined_at.timetuple())))
		embed.add_field(
			name='This server now has',
			value=str(member.guild.member_count) + ' members',
		)
		embed.set_author(name=member.display_name, icon_url=member.avatar_url)
		embed.set_thumbnail(url=member.avatar_url)
		await specialchannel.send(embed=embed)

async def on_member_ban(guild, user):
	if utils.logdisabled('member_ban', guild):
		return
	specialchannel = utils.getspecialchannel(guild)

	msg = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(
		utils.wrapbackticks(user.name), user.discriminator, user.id, guild.name, guild.id,
	)
	await specialchannel.send(msg)

async def on_member_unban(guild, user):
	if utils.logdisabled('member_unban', guild):
		return
	specialchannel = utils.getspecialchannel(guild)
	msg = (
		'**`>`**<:doormat:239361673532669953>`user` **``{}``**`#{}` `({})'
		' unbanned from server {} ({})`'
	).format(
		utils.wrapbackticks(user.name), user.discriminator, user.id, guild.name, guild.id,
	)
	await specialchannel.send(msg)

async def on_typing(channel, user, when):
	try:
		specialchannel = bot.getspecialchannel(channel.guild)
	except AttributeError: # this would happen if the typing event is in a private message
		return
	if specialchannel.id == channel.guild.default_channel.id:
		specialchannel = channel
	if str(user.status) == 'offline' and \
	not utils.logdisabled('invisible_typing', channel.guild):
		embed = discord.Embed(title='👻INVISIBLE WHILE TYPING IN {}'.format(channel.mention), colour=user.colour)
		embed.set_author(name=user.display_name, icon_url=user.avatar_url, url=utils.infourl('userid={}'.format(user.id)))
		await specialchannel.send(embed=embed)
	else:
		return # practically unnecessary, but this is for if we want to do things when members type later

async def on_guild_role_create(r):
	if utils.logdisabled('role_create', r.guild):
		return
	schan = utils.getspecialchannel(r.guild)
	embed = discord.Embed(
		title='ROLE ADD AT {time}'.format(time=str(r.created_at)),
		description=utils.mdspecialchars(r.name),
		colour=r.colour,
	)
	await schan.send(embed=embed)

async def on_guild_role_delete(r):
	if utils.logdisabled('role_delete', r.guild):
		return
	schan = utils.getspecialchannel(r.guild)
	embed = discord.Embed(
		title='ROLE REMOVE',
		description=utils.mdspecialchars(r.name),
		colour=r.colour,
	)
	embed.add_field(name='Original Creation Time', value=str(r.created_at))
	await schan.send(embed=embed)

async def on_guild_role_update(before, after):
	specialchannel = utils.getspecialchannel(before.guild)
	# If the name changed
	if before.name != after.name and not utils.logdisabled('role_rename', before.guild):
		embed = discord.Embed(title='ROLE NAME CHANGE', description=utils.mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Name', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=utils.mdspecialchars(after.name))
		await specialchannel.send(embed=embed)
	# If "display online members separately" changed
	if before.hoist != after.hoist:
		# If the role has been hoisted
		if before.hoist == 0 and after.hoist == 1 and not utils.logdisabled(
			'role_hoist', before.guild
		):
			embed = discord.Embed(
				title='ROLE HOIST',
				description='{name}\nID: {id}'.format(
					name=utils.mdspecialchars(after.name),
					id=after.id,
				),
				colour=after.colour,
			)
			await specialchannel.send(embed=embed)
		# If the role has been lowered
		if before.hoist == 1 and after.hoist == 0 and not utils.logdisabled(
			'role_unhoist', before.guild
		):
			embed = discord.Embed(
				title='ROLE UNHOIST',
				description='{name}\nID: {id}'.format(
					name=utils.mdspecialchars(after.name),
					id=after.id,
				),
				colour=after.colour,
			)
			await specialchannel.send(embed=embed)
	# If "allow everyone to mention this role" changed
	if before.mentionable != after.mentionable:
		# If the role is now mentionable
		if before.mentionable == 0 and after.mentionable == 1 and not utils.logdisabled(
			'role_mentionable', before.guild
		):
			msg = '**`>`**`role` **``{}``** `({}) is now mentionable`'.format(utils.wrapbackticks(after.name), after.id)
			await specialchannel.send(msg)
		# If the role is no longer mentionable
		if before.mentionable == 1 and after.mentionable == 0 and not utils.logdisabled(
			'role_unmentionable', before.guild
		):
			msg = '**`>`**`role` **``{}``** `({}) is no longer mentionable`'.format(utils.wrapbackticks(after.name), after.id)
			await specialchannel.send(msg)
	# If the role has been moved up or down in the hierarchy
	if before.position != after.position and not utils.logdisabled('role_hierarchy', before.guild):
		# The role has been moved down
		if before.position > after.position:
			msg = '**`>`**`role` **``{}``** `({}) has been moved down by {} roles ({} to {})`'.format(utils.wrapbackticks(after.name), after.id, before.position - after.position, before.position, after.position)
			await specialchannel.send(msg)
		# The role has been moved up
		if before.position < after.position:
			msg = '**`>`**`role` **``{}``** `({}) has been moved up by {} roles ({} to {})`'.format(utils.wrapbackticks(after.name), after.id, after.position - before.position, before.position, after.position)
			await specialchannel.send(msg)
	# If the role color has changed
	if before.colour != after.colour and not utils.logdisabled('role_color', before.guild):
		embed = discord.Embed(title='ROLE COLOR CHANGE', description=utils.mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Color', value='(default)' if before.colour.value == 0 else str(before.colour).upper())
		embed.add_field(name='Newer Color', value='(default)' if after.colour.value == 0 else str(after.colour).upper())
		await specialchannel.send(embed=embed)
	# If any of the permissions has changed
	if before.permissions != after.permissions and not utils.logdisabled(
		'role_permissions', before.guild
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
		await specialchannel.send(embed=e)

async def on_reaction_add(r, u):
	if utils.isprivatemessage(r.message.guild) \
	or utils.logdisabled('reaction_add', r.message.guild):
		return
	specialchannel = utils.getspecialchannel(r.message.guild)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION ADDED TO MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=utils.reltime(time.mktime(r.message.created_at.timetuple())),
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	embed.set_author(
		name=u.display_name,
		icon_url=u.avatar_url,
		url=utils.infourl('userid={}&messageid={}'.format(u.id, r.message.id))
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
	await specialchannel.send(embed=embed)

async def on_reaction_remove(r, u):
	if utils.isprivatemessage(r.message.guild) \
	or utils.logdisabled('reaction_remove', r.message.guild):
		return
	specialchannel = utils.getspecialchannel(r.message.guild)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION REMOVED FROM MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=utils.reltime(time.mktime(r.message.created_at.timetuple())),
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	embed.set_author(
		name=u.display_name,
		icon_url=u.avatar_url,
		url=utils.infourl('userid={}&messageid={}'.format(u.id, r.message.id))
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
	await specialchannel.send(embed=embed)

async def on_reaction_clear(m, rs):
	if utils.isprivatemessage(m.guild) or utils.logdisabled('reaction_clear', m.guild):
		return
	schan = utils.getspecialchannel(m.guild)
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
			rtime=utils.reltime(time.mktime(m.created_at.timetuple())),
			c=m.channel,
		),
		description=m.content,
		colour=m.author.colour,
	)
	embed.add_field(name='Message ID (temp)', value=m.id)
	embed.add_field(name='Reactions', value=rlist)
	await schan.send(embed=embed)

async def on_guild_update(before, after):
	specialchannel = utils.getspecialchannel(after)
	if before.icon != after.icon and not utils.logdisabled('guild_icon', after):
		embed = discord.Embed(description='Server changed icon')
		embed.set_thumbnail(url=before.icon_url)
		embed.add_field(name='Older Icon URL: None' if before.icon_url == '' else 'Older Icon URL (Thumbnail)', value='No Older Icon URL' if before.icon_url == '' else before.icon_url)
		embed.add_field(name='Newer Icon URL: None' if after.icon_url == '' else 'Newer Icon URL (Inset Image)', value='No Newer Icon URL' if after.icon_url == '' else after.icon_url)
		embed.set_image(url=after.icon_url)
		await specialchannel.send(embed=embed)
	if before.name != after.name and not utils.logdisabled('guild_rename', after):
		embed = discord.Embed(description='Server changed name')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Name', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=utils.mdspecialchars(after.name))
		await specialchannel.send(embed=embed)
	if before.region != after.region and not utils.logdisabled('guild_region', after):
		embed = discord.Embed(description='VOICE REGION CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Region', value=str(before.region))
		embed.add_field(name='Newer Region', value=str(after.region))
		await specialchannel.send(embed=embed)
	if before.afk_timeout != after.afk_timeout and \
	not utils.logdisabled('guild_afktimeout', after):
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
		await specialchannel.send(embed=embed)
	if before.afk_channel != after.afk_channel and \
	not utils.logdisabled('guild_afkchannel', after):
		embed = discord.Embed(description='AFK CHANNEL CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(
			name='Older Channel: None' if before.afk_channel is None else 'Older Channel',
			value='No Older Channel' if before.afk_channel is None else '{name} ({0.id})'.format(before.afk_channel, name=utils.mdspecialchars(before.afk_channel.name)),
		)
		embed.add_field(
			name='Newer Channel: None' if after.afk_channel is None else 'Newer Channel',
			value='No Newer Channel' if after.afk_channel is None else '{name} ({0.id})'.format(after.afk_channel, name=utils.mdspecialchars(after.afk_channel.name)),
		)
		await specialchannel.send(embed=embed)
	if before.verification_level != after.verification_level and not utils.logdisabled(
		'guild_verificationlevel', after
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
		await specialchannel.send(embed=embed)
	if before.mfa_level != after.mfa_level and not utils.logdisabled('guild_2fa', after):
		if before.mfa_level == 0 and after.mfa_level == 1:
			embed=discord.Embed(description='SERVER 2FA ENABLED')
		elif before.mfa_level == 1 and after.mfa_level == 0:
			embed=discord.Embed(description='SERVER 2FA DISABLED')
		await specialchannel.send(embed=embed)

async def on_guild_emojis_update(guild, b, a):
	if utils.logdisabled('guild_emotes', guild):
		# We could split this into separate emotes_* log types
		return
	schan = utils.getspecialchannel(guild)
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
		await schan.send(embed=embed)
		return
	embed = discord.Embed(description=desc)
	embed.add_field(name='Emotes', value=elist)
	await schan.send(embed=embed)

async def on_voice_state_update(member, old, new):
	if old.voice_channel == new.voice_channel:
		return

	vtcs = [
		member.guild.get_channel(i) for i in config.get_s(
			'voicechat_channel_text', new.guild.id,
		)
	]
	vvcs = [
		member.guild.get_channel(i) for i in config.get_s(
			'voicechat_channel_voice', new.guild.id,
		)
	]

	for vtc, vvc in zip(vtcs, vvcs):
		if new.voice_channel and new.voice_channel == vvc:
			# Joined the voice channel
			ow = discord.PermissionOverwrite(read_messages=True)
			await vtc.set_permissions(member, ow)
			break

		if old.voice_channel and old.voice_channel == vvc:
			# Left the voice channel
			await vtc.set_permissions(new, None)
			break

async def on_guild_channel_create(c):
	if utils.logdisabled('channel_add', c.guild):
		return
	schan = utils.getspecialchannel(c.guild)
	embed = discord.Embed(
		description='{type} CHANNEL ADD\n{0.name} ({0.id})'.format(
			c,
			type=str(c.type).upper(),
		),
	)
	await schan.send(embed=embed)

async def on_guild_channel_delete(c):
	if utils.logdisabled('channel_remove', c.guild):
		return
	schan = utils.getspecialchannel(c.guild)
	embed = discord.Embed(
		description='{type} CHANNEL REMOVE\n{0.name} ({0.id})'.format(
			c,
			type=str(c.type).upper(),
		),
	)
	await schan.send(embed=embed)

async def on_raw_message_delete(message_id, channel_id):
	# We must first know what channel it is
	mchan = bot.client.get_channel(channel_id)
	if isinstance(mchan, discord.abc.PrivateChannel) or \
	utils.logdisabled('message_deleteuncached', mchan.guild):
			return
	# Check if on_message_delete() was already called by this message
	# If it was, then return
	if discord.utils.find(
		lambda m: m.id == message_id, bot.client._connection._messages,
	) != None:
		# If the message lingers in deleted_messages, it doesn't really matter for now
		return
	if message_id in bot.owncache:
		# Already removed from the cache, but we still haven't run on_message_delete
		# This happens all the time.
		bot.owncache.remove(message_id)
		return
	for m in bot.deleted_messages:
		if m.id == message_id:
			# on_message_delete was faster
			bot.deleted_messages.remove(m)
			return

	schan = utils.getspecialchannel(mchan.guild)
	e = discord.Embed(
		title='UNCACHED MESSAGE DELETED IN {0.mention}'.format(mchan),
		url=utils.infourl('messageid=' + message_id),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID and its channel.'
		),
		colour=mchan.guild.me.colour,
	)
	await schan.send(embed=e)

async def on_raw_message_edit(message_id, data):
	# We must first know what channel it is
	mchan = bot.client.get_channel(data['channel_id'])
	if isinstance(mchan, discord.abc.PrivateChannel) or \
	utils.logdisabled('message_updateuncached', mchan.guild):
		return
	# Check if the message is in the cache and return if it is
	if discord.utils.find(
		lambda m: m.id == message_id, bot.client._connection._messages,
	) != None:
		return

	schan = utils.getspecialchannel(mchan.guild)
	athr = mchan.guild.get_member(data['author']['id'])
	e = discord.Embed(
		title=(
			'UNCACHED MESSAGE UPDATED (SENT {rltm}'
			' IN {0.mention}).'
			' NEWER CONTENT AND PROPERTIES:'
		).format(
			mchan,
			rltm=utils.reltime(
				time.mktime(
					discord.utils.parse_time(data['timestamp']).timetuple(),
				)
			),
		),
		description=data['content'],
		colour=athr.colour,
	)
	e.set_author(
		name=athr.display_name,
		icon_url=athr.avatar_url,
		url=utils.infourl(
			(
				'userid={uid}&messageid={mid}'
			).format(
				uid=athr.id,
				mid=data['id'],
			),
		)
	)
	e.add_field(
		name='Pinned',
		value='Yes' if data['pinned'] else 'No',
	)
	e.add_field(
		name='TTS',
		value='Yes' if data['tts'] else 'No',
	)
	e.add_field(
		name='Rich Embed',
		value=(
			'``{}``'.format(utils.wrapbackticks(str(data['embeds']['rich'])))
			if 'rich' in data['embeds']
			else '(none)'
		),
	)
	e.set_footer(
		text=(
			'Since this message is uncached,'
			' I can’t give you its older properties.'
		)
	)
	await schan.send(embed=e)

async def on_raw_reaction_add(emoji, message_id, channel_id, user_id):
	# We must first know what channel it is
	mchan = bot.client.get_channel(channel_id)
	if isinstance(mchan, discord.abc.PrivateChannel) or \
	utils.logdisabled('reaction_adduncached', mchan.guild):
		return

	# Check if the message is in the cache and return if it is
	if discord.utils.find(
		lambda m: m.id == message_id, bot.client._connection._messages,
	) != None:
		return

	schan = utils.getspecialchannel(mchan.guild)
	athr = mchan.guild.get_member(user_id)
	mdetails = athr.mention
	if athr.status == discord.Status.offline:
		mdetails += ' (Invisible)'
	e = discord.Embed(
		title='REACTION ADDED TO UNCACHED MESSAGE IN {0.mention}'.format(mchan),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID, author, and channel.'
		),
		colour=mchan.guild.me.colour,
	)
	e.set_author(
		name=athr.display_name,
		icon_url=athr.avatar_url,
		url=utils.infourl(
			(
				'userid={uid}&messageid={mid}'
			).format(
				uid=athr.id,
				mid=message_id,
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
			name=emoji.name,
			id=emoji.id,
		) if emoji.id is not None else emoji.name,
	)
	await schan.send(embed=e)

async def on_raw_reaction_remove(emoji, message_id, channel_id, user_id):
	# We must first know what channel it is
	mchan = bot.client.get_channel(channel_id)
	if isinstance(mchan, discord.abc.PrivateChannel) or \
	utils.logdisabled('reaction_removeuncached', mchan.guild):
		return
	# Check if the message is in the cache and return if it is
	if discord.utils.find(
		lambda m: m.id == message_id, bot.client._connection._messages,
	) != None:
		return

	schan = utils.getspecialchannel(mchan.guild)
	athr = mchan.guild.get_member(user_id)
	mdetails = athr.mention
	e = discord.Embed(
		title='REACTION REMOVED FROM UNCACHED MESSAGE IN {0.mention}'.format(mchan),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID, author, and channel.'
		),
		colour=mchan.guild.me.colour,
	)
	e.set_author(
		name=athr.display_name,
		icon_url=athr.avatar_url,
		url=utils.infourl(
			(
				'userid={uid}&messageid={mid}'
			).format(
				uid=athr.id,
				mid=message_id,
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
			name=emoji.name,
			id=emoji.id,
		) if emoji.id is not None else emoji.name,
	)
	await schan.send(embed=e)

async def on_raw_reaction_clear(message_id, channel_id):
	# We must first know what channel it is
	mchan = bot.client.get_channel(channel_id)
	if isinstance(mchan, discord.abc.PrivateChannel) or \
	utils.logdisabled('reaction_clearuncached', mchan.guild):
		return
	# Check if the message is in the cache and return if it is
	if discord.utils.find(
		lambda m: m.id == message_id, bot.client._connection._messages,
	) != None:
		return

	schan = utils.getspecialchannel(mchan.guild)
	e = discord.Embed(
		title=(
			'REACTIONS CLEARED FROM UNCACHED MESSAGE'
			' IN {0.mention}'
		).format(mchan),
		url=utils.infourl('messageid=' + message_id),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID and its channel.'
		),
		colour=mchan.guild.me.colour,
	)
	await schan.send(embed=e)

async def on_guild_channel_update(b, a):
	if utils.logdisabled('channel_rename', a.guild):
		return
	schan = utils.getspecialchannel(a.guild)
	if b.name != a.name:
		e = discord.Embed(
			title='{type} CHANNEL UPDATE'.format(type=str(a.type).upper()),
			description=(
				'**{name}** ({id})'
			).format(
				name=utils.mdspecialchars(a.name),
				id=a.id,
			),
			colour=a.guild.me.colour,
		)
		e.add_field(name='Older Name', value=utils.mdspecialchars(b.name))
		e.add_field(name='Newer Name', value=utils.mdspecialchars(a.name))
		await schan.send(embed=e)

async def on_guild_join(guild):
	em = discord.Embed(
		title='BOT ADDED TO SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(guild.name),
			id=guild.id,
		),
		colour=opguild.me.colour,
	)
	em.set_image(url=guild.icon_url)
	await opguild_botguilds.send(embed=em)

async def on_guild_remove(guild):
	em = discord.Embed(
		title='BOT REMOVED FROM SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(guild.name),
			id=guild.id,
		),
		colour=opguild.me.colour,
	)
	em.set_image(url=guild.icon_url)
	await opguild_botguilds.send(embed=em)
