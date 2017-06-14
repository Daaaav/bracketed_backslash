# encoding=utf-8

import datetime
import logging
import json
import os
import sys
import time

import discord

import __main__
import checks
import config
import commands
import customcommands
import emb
import op_ids
import utils

hangmanchosenword = ''
hangmanattempts = 0
hangmantotalattempts = 0
hangmanactive = False
hangmanstarter = None
guessedletters = [False]*26
algeraden = False

async def on_ready():
	global memberroles, rules, disabledrules, botschannel, botschannel_tntgb, banlogchannel_tntgb, productionserver, tntgbserver, rolexpires, opserver, opserver_botservers
	productionserver = '153368829160849408'
	tntgbserver = '242099933665034240'
	server = discord.utils.get(__main__.client.servers, id=productionserver)
	server_tntgb = discord.utils.get(__main__.client.servers, id=tntgbserver)
	specialchannel_prod = discord.utils.get(server.channels, id='234185735266238464')
	botschannel = discord.utils.get(server.channels, id='201130047736643584')
	botschannel_tntgb = discord.utils.get(server_tntgb.channels, id='266626198249930764')
	banlogchannel_tntgb = discord.utils.get(server_tntgb.channels, id='242253449922609152')
	opserver = discord.utils.find(lambda s: s.id == __main__.opserverid, __main__.client.servers)
	opserver_botservers = discord.utils.find(
		lambda c: c.id == '291764490578558977',
		opserver.channels,
	)
	logging.info('logged in as {} with id {}'.format(
			__main__.client.user.name, __main__.client.user.id,
		),
	)
	await __main__.client.change_presence(game=discord.Game(name=config.get_s('gamestatus')))
	embed = discord.Embed(
		title='🔌BOT CONNECTED',
		colour=discord.utils.find(
			lambda s: s.id == op_ids.ids['opserver'], __main__.client.servers,
		).me.colour,
	)
	embed.add_field(name='Startup Time', value=__main__.reltime(__main__.boottimeunix))
	await __main__.client.send_message(
		discord.Object(op_ids.ids['opserver_chans']['connections']),
		embed=embed,
	)

	try:
		with open('memberroles.json', 'r') as infile:
			memberroles = json.load(infile)

		# Now look what I've woken up to.
		for ser in memberroles:
			if config.get_s('rolecachemode', ser) == 0:
				continue
			rcwarnings = ''
			for mem in __main__.client.get_server(ser).members:
				if not str(mem.id) in memberroles[ser]:
					if len(mem.roles) >= 2:
						rcwarnings += '\nUser {}#{} ({}) is not in the cache! (They’re suddenly in the server.) Adding their roles to the cache now.'.format(mem.name, mem.discriminator, mem.id)
						memberroles[ser][str(mem.id)] = list(__main__.rolelist(mem.roles)) # Possibly redundant list() tbh, just making sure since I can't test and I don't know python well enough to know whether it's redundant
					continue
				if set(memberroles[ser][str(mem.id)]) != set(__main__.rolelist(mem.roles)):
					rcwarnings += (
						'\n'
						'User {}#{} ({}) has different roles than in the cache! Maybe you want to correct things.\n'
						'    **`Cached:`** {}\n'
						'    **`Seen:`** {}'
					).format(
						mem.name, mem.discriminator, mem.id,
						__main__.listroles_id(memberroles[ser][str(mem.id)]),
						__main__.listroles(mem.roles),
					)
			if rcwarnings != '':
				logging.warn('Role cache warnings for server {}: {}'.format(
						ser, rcwarnings
					)
				)
				rcwarnings = (
					'**User role cache warning.**\n'
					'Full warning output has been sent to the terminal.\n'
					+ rcwarnings
				)
				await __main__.client.send_message(
					__main__.getspecialchannel(
						discord.utils.get(__main__.client.servers, id=ser)
					),
					rcwarnings[:1900]
				)

	except FileNotFoundError:
		# Maybe we do have an old members.json?
		try:
			with open('members.json', 'r') as infile:
				memberrolesold = json.load(infile)
			# Convert it to the new system where all servers can use it!
			logging.info('CONVERTING OLD members.json TO memberroles.json')
			memberroles = {productionserver: memberrolesold}

			with open('memberroles.json', 'w') as outfile:
				json.dump(memberroles, outfile)

			logging.info('Exiting (aka restarting) now to make the conversion go smoothly...')
			await __main__.client.logout()
			sys.exit(43)
		except FileNotFoundError:
			logging.info('memberroles file does not exist yet so creating it now')
			memberroles = {}

			with open('memberroles.json', 'w') as outfile:
				json.dump(memberroles, outfile)

			await __main__.client.send_message(specialchannel_prod, 'Members file didn’t yet exist, created a new one. Please run `\\rolesync` to sync up the roles cache.')

	try:
		with open('rules.json', 'r') as infile:
			rules = json.load(infile)
	except FileNotFoundError:
		logging.info('rules file does not exist yet so creating it now')
		rules = {}

		with open('rules.json', 'w') as outfile:
			json.dump(rules, outfile)

		await __main__.client.send_message(specialchannel_prod, 'Rules file didn’t exist yet, created a new one.')

	try:
		with open('disabledrules.json', 'r') as infile:
			disabledrules = json.load(infile)
	except FileNotFoundError:
		logging.info('disabledrules file does not exist yet so creating it now')
		disabledrules = []

		with open('disabledrules.json', 'w') as outfile:
			json.dump(disabledrules, outfile)

		await __main__.client.send_message(specialchannel_prod, 'Disabledrules file didn’t exist yet, created a new one.')

	try:
		with open('rolexpires.json', 'r') as infile:
			rolexpires = json.load(infile)
	except FileNotFoundError:
		logging.info('rolexpires file does not exist yet so creating it now')
		rolexpires = {}

		with open('rolexpires.json', 'w') as outfile:
			json.dump(rolexpires, outfile)

		await __main__.client.send_message(specialchannel_prod, 'Rolexpires file didn’t exist yet, created a new one.')

	await __main__.handleExpiryTimer()

	for chan in __main__.client.get_all_channels():
		if chan.type == discord.ChannelType.text:
			msgs = __main__.client.logs_from(chan)
			try:
				async for m in msgs:
					__main__.client.messages.append(m)
			except discord.errors.Forbidden:
				logging.info(
					(
						'Failed to retrieve message history for'
						' {serv.name} ({serv.id})#{chan.name} ({chan.id}).'
					).format(serv=chan.server, chan=chan)
				)

	# Now set up our own cache, that Discord.py won't remove messages from before telling us!
	for m in __main__.client.messages:
		__main__.owncache.append(m.id)

async def on_message(m):
	__main__.owncache.append(m.id)

	if m.author == __main__.client.user or m.author.bot:
		return

	if m.channel.is_private:
		e = discord.Embed(
			description=m.content,
			timestamp=m.timestamp,
			colour=__main__.client.get_server(op_ids.ids['opserver']).me.colour,
		)
		e.set_author(name=m.author.name, icon_url=m.author.avatar_url)
		e.set_footer(text=utils.id_summary(uid=m.author.id, mid=m.id, cid=m.channel.id))
		await __main__.client.send_message(
			__main__.client.get_channel(op_ids.ids['opserver_chans']['direct_messages']),
			embed=e,
		)

	global msg_start, hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, \
	hangmanstarter, guessedletters, algeraden, latestroled
	schan = __main__.getspecialchannel_reply(m)
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
	priv = __main__.isprivatemessage(m.server)

	if type(m.author) != discord.User and m.author.status == discord.Status.offline and \
	not __main__.logdisabled('invisible_sentmessage', m.server):
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
			url=__main__.infourl(
				'userid={0.author.id}&messageid={0.id}'
			).format(m)
		)
		await __main__.client.send_message(schan, embed=e)

	if not priv and m.tts:
		e = discord.Embed(
			title=(
				':microphone2:Message {0.id} was sent with TTS'
				' in {0.channel.mention}'
			).format(m),
			description=m.content,
			colour=m.author.colour,
			timestamp=m.timestamp
		)
		e.set_author(
			name=m.author.display_name,
			icon_url=m.author.avatar_url
		)
		e.add_field(
			name='Message author',
			value='<@!{id}> ({id})'.format(id=m.author.id)
		)
		await __main__.client.send_message(schan, embed=e)

	if not priv and m.attachments != []:
		a = await __main__.fetch(m.attachments[0]['url'])
		fn = (
			'{atchcche}/{id}_{fn}'
		).format(
			atchcche=__main__.attachcache,
			id=m.attachments[0]['id'],
			fn=m.attachments[0]['filename'],
		)
		with open(fn, 'wb') as f:
			f.write(a)
			f.close()

	if not priv and m.embeds != []:
		for n, e in enumerate(m.embeds):
			if e['type'] == 'image':
				# get the filename from the url
				# i.e. the part after the last forward slash
				fn = e['url'].split('/')[-1]

				# fetch the embed preview discord fetches
				img = await __main__.fetch(e['thumbnail']['proxy_url'])

				# cache the image
				dfn = '{embedcache}/{m.id}_{n}_{fn}'.format(
					embedcache=__main__.embedcache,
					m=m,
					n=n,
					fn=fn,
				)
				with open(dfn, 'wb') as f:
					f.write(img)
					f.close()

	if not priv and m.author.id in config.get_s('blacklist', m.server.id):
		return

	if priv and m.author.id in config.get_s('blacklist'):
		return

	if m.content.startswith(__main__.invoker):
		altinvokeractive = False
		hangmaninvokeractive = False
		pass
	elif m.content.startswith(__main__.altinvoker):
		altinvokeractive = True
		hangmaninvokeractive = False
		pass
	elif m.content.startswith(__main__.hangmaninvoker):
		hangmaninvokeractive = True
		pass
	else:
		# Not of the bot's interest, but is this in the join channel for this server?
		if not priv and \
		config.get_s('rolecachemode', m.server.id) == 2 and \
		m.channel.id == config.get_s('joinchannel', m.server.id):
			await __main__.client.delete_message(m)
			__main__.messages_deleted_by_bot.append(m)
		return

	if priv:
		invokesymbol = '@'
	elif checks.is_mod(m.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'
	if hangmaninvokeractive:
		if not hangmanactive:
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
			await __main__.client.send_message(m.channel, msg_start, embed=e)
		if m.channel.id != '201130047736643584':
			return
		hangmanguessed = m.content[1:]

		if len(hangmanguessed) == 1:
			# Have we already used that letter? And is it a valid letter?
			if __main__.alphabet.find(hangmanguessed.upper()) == -1:
				e = emb.error(
					'The character ``{}`` is invalid.'
					.format(utils.wrapbackticks(hangmanguessed.upper()))
				)
				await __main__.client.send_message(m.channel, msg_start, embed=e)
				return
			if guessedletters[__main__.alphabet.find(hangmanguessed.upper())]:
				e = emb.error(
					'The letter **{}** has already been used.'
					.format(hangmanguessed.upper())
				)
				await __main__.client.send_message(m.channel, msg_start, embed=e)
				return
			# Ok, so does this letter occur in the word?
			if hangmanchosenword.upper().find(hangmanguessed.upper()) != -1:
				# Set the guessed letter correctly
				guessedletters[__main__.alphabet.find(hangmanguessed.upper())] = True

				con = '**{ltr}** is correct!\n{worddisp}'.format(
						ltr=hangmanguessed.upper(),
						worddisp=__main__.hangmanworddisp(hangmanchosenword)
					)
				msg = msg_start + con
				await __main__.client.send_message(m.channel, msg)

				if algeraden:
					hangmanactive = False
					con = (
						'You guessed the word correctly!'
						' You made {n} mistakes in total.'
						.format(n=hangmantotalattempts-hangmanattempts)
					)
					await __main__.client.send_message(m.channel, con)
					return
			else:
				# Set the guessed letter correctly, and it has to be a letter
				guessedletters[__main__.alphabet.find(hangmanguessed.upper())] = True
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					con = (
						'**{ltr}** is incorrect! Game over.'
						' The word was: **{word}**'
					).format(
						ltr=hangmanguessed.upper(),
						word=hangmanchosenword,
					)
					msg = msg_start + con
					await __main__.client.send_message(m.channel, msg)
					return
				else:
					if hangmanattempts != 1:
						plural = 's'
					else:
						plural = ''
					con = (
						'**{ltr}** is incorrect!'
						' {attempts} attempt{pl} left.\n'
						'{worddisp}'
					).format(
						ltr=hangmanguessed.upper(),
						attempts=hangmanattempts,
						pl=plural,
						worddisp=__main__.hangmanworddisp(hangmanchosenword),
					)
					msg = msg_start + con
					await __main__.client.send_message(m.channel, msg)
					return
		else:
			# We're guessing the entire word. Well, is it the word?
			if hangmanguessed.lower() == hangmanchosenword.lower():
				hangmanactive = False
				con = (
					'You guessed the word ({word}) correctly!'
					' You made {n} mistakes in total.'
				).format(
					word=hangmanchosenword,
					n=hangmantotalattempts-hangmanattempts,
				)
				msg = msg_start + con
				await __main__.client.send_message(m.channel, msg)
				return
			elif len(hangmanguessed) != len(hangmanchosenword):
				# We're not even trying. It's not the same length.

				# if before was "not even trying", this is -1 trying
				if len(hangmanguessed) == 0:
					e = emb.error('You should probably enter in a letter.')
					await __main__.client.send_message(m.channel, msg_start, embed=e)
					return
				e = emb.error(
					(
						'**``{guess}``** isn’t even the same length'
						' as the correct word. Please try again.'
					).format(
						guess=utils.wrapbackticks(hangmanguessed)
					)
				)
				await __main__.client.send_message(m.channel, msg_start, embed=e)
				return
			else:
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					con = (
						'**{guess}** is not the word! Game over.'
						' The word was: **{word}**'
					).format(
						guess=hangmanguessed,
						word=hangmanchosenword,
					)
					msg = msg_start + con
					await __main__.client.send_message(m.channel, msg)
					return
				else:
					con = (
						'**{guess}** is not the word!'
						' {n} attempts left.\n{worddisp}'
					).format(
						guess=hangmanguessed,
						n=hangmanattempts,
						worddisp=__main__.hangmanworddisp(hangmanchosenword),
					)
					msg = msg_start + con
					await __main__.client.send_message(m.channel, msg)
					return

		return

	elif altinvokeractive:
		command = m.content.split(__main__.altinvoker, 1)[1]
		clean_command = m.clean_content.split(__main__.altinvoker, 1)[1]
	else:
		command = m.content.split(__main__.invoker, 1)[1]
		clean_command = m.clean_content.split(__main__.invoker, 1)[1]
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
	config.get_s('rolecachemode', m.server.id) == 2 and \
	m.channel.id == config.get_s('joinchannel', m.server.id):
		# Join channel
		if command == 'join' and len(m.author.roles) <= 1:
			await __main__.newmemberroles(m.author, __main__.getspecialchannel(m.server), True)
		await __main__.client.delete_message(m)
		__main__.messages_deleted_by_bot.append(m)
		return
	# But react to the message as a hint to the message sender
	if not priv and \
	not checks.is_mod(m.author) and \
	m.channel.id != '201130047736643584' and \
	m.server.id == productionserver and \
	not (checks.is_dev(m.author) and m.channel.id == '238423391571279872') and \
	not command in ('rule', 'rules', 'rulefind', 'rulesfind') and \
	not (m.channel.id == '256924583737819146' and command in ('votevoicemute', 'vy', 'vn')):
		if __main__.is_valid_command(command) and command != '':
			await __main__.client.add_reaction(
				m,
				discord.utils.get(
					m.server.emojis,
					id='262051482549878796',
				),
			)
		return
	if not priv and \
	m.server.id == tntgbserver and \
	m.channel != botschannel_tntgb and \
	not checks.is_tntgb_mod(m.author) and \
	command != 'selfban':
		return
	if not priv and \
	not checks.is_mod(m.author) and \
	not config.get_s('alloweverywhere', m.server.id) and \
	not m.channel.id in config.get_s('allowedchannels', m.server.id):
		return
	if not priv and command in config.get_s('disabledcommands', m.server.id):
		e = emb.error('This command is currently disabled{onthisserv}.'.format(
			onthisserv=(
				' on this server'
				if config.is_detached('disabledcommands', m.server.id) else
				'')
			)
		)
		await __main__.reply(m, emb=e)
		return

	if priv and command in config.get_s('disabledcommands'):
		e = emb.error('This command is currently disabled.')
		await __main__.reply(m, emb=e)
		return

	if command in commands.commands:
		func = commands.commands[command]
	elif customcommands.exists(m.server, command):
		try:
			await customcommands.run(
				m.server, command, m, arguments, clean_arguments, invokesymbol
			)
		except discord.errors.Forbidden:
			e = emb.error(__main__.t['no_permission'])
			await __main__.reply(m, emb=e)
			raise
		except Exception:
			e = emb.error(__main__.t['generic_error'])
			await __main__.reply(m, emb=e)
			raise
		return
	else:
		# Check if it's an alias
		for c, p in commands.commands.items():
			if p[2] != None and command in p[2]:
				func = commands.commands[c]
				break
		else:
			if (not priv and config.get_s('notify_invalidcmd', m.server.id)) or \
			(priv and config.get_s('notify_invalidcmd')):
				e = emb.warning(
					(
						'Invalid command. Input `\help` for'
						' a list of valid commands.'
					)
				)
				await __main__.reply(m, emb=e)
			return

	if m.channel.is_private and func[3]:
		e = emb.error(__main__.t['noprivate'])
		await __main__.reply(m, emb=e)
		return
	if func[1] != None and not func[1](m.author):
		e = emb.error(__main__.t['you_no_permission'])
		__main__.logfailedcommand(command, arguments, m)
		await __main__.reply(m, emb=e)
		return
	kwargs = {
		'command': command,
		'arguments': arguments,
		'clean_arguments': clean_arguments,
		'invokesymbol': invokesymbol,
		'sudo': False,
	}
	try:
		await func[0](__main__.client, m, **kwargs)
	except discord.errors.Forbidden:
		e = emb.error(__main__.t['no_permission'])
		await __main__.reply(m, emb=e)
		raise
	except Exception:
		e = emb.error(__main__.t['generic_error'])
		await __main__.reply(m, emb=e)
		raise

async def on_message_delete(msg):
	__main__.deleted_messages.append(msg)
	if __main__.isprivatemessage(msg.server):
		return
	if msg.author == __main__.client.user:
		__main__.logging.info(
			(
				'bot message {0.id} by user {1.name}#{1.discriminator} ({1.id})'
				' in channel {2.id} ({2.name}) at {0.timestamp} utc deleted,'
				' original content is \n{0.content}'
			).format(msg, msg.author, msg.channel)
		)
		return
	if (msg.content == '' and msg.attachments == []) \
	or __main__.logdisabled('message_delete', msg.server):
		return
	schan = __main__.getspecialchannel_reply(msg)
	em = discord.Embed(
		title=(
			'\N{NO ENTRY SIGN}MESSAGE {withatch}DELETED (SENT {reltime} IN #{chan})'
		).format(
			withatch='WITH ATTACHMENT ' if msg.attachments != [] else '',
			reltime=__main__.reltime(time.mktime(msg.timestamp.timetuple())),
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
	await __main__.client.send_message(schan, embed=em)
	if msg.attachments != []:
		fp = (
				'{atchcche}/{id}_{fn}'
		).format(
			atchcche=__main__.attachcache,
			id=msg.attachments[0]['id'],
			fn=msg.attachments[0]['filename'],
		)
		if os.path.isfile(fp):
			con = (
				'_\N{PAPERCLIP}The attachment for message {0.id} is attached._'
			).format(msg)
			try:
				await __main__.client.send_file(
					destination=schan,
					content=con,
					fp=fp,
					filename=msg.attachments[0]['filename'],
				)
			except discord.HTTPException:
				con = (
					'_Failed to upload the attachment for message {0.id}._'
				).format(msg)
				await __main__.client.send_message(schan, con)
		else:
			con = (
				'_The attachment for message {0.id} was not found'
				' in the message attachments cache._'
			).format(msg)
			await __main__.client.send_message(schan, con)
	if msg in __main__.messages_deleted_by_bot:
		__main__.messages_deleted_by_bot.remove(msg)
		return
	dthreshold = datetime.timedelta(
		seconds=config.get_s('deleted_message_resend_timer', msg.server.id),
	)
	if (datetime.datetime.now() - msg.timestamp) < dthreshold and \
	not msg.author.bot:
		if config.get_s('deleted_message_resend_content', msg.server.id):
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
		await __main__.client.send_message(msg.channel, embed=em)

async def on_message_edit(old, new):
	if __main__.isprivatemessage(old.server):
		return
	schan = __main__.getspecialchannel_reply(new)
	if not old.pinned and new.pinned and not __main__.logdisabled('message_pin', new.server):
		em = discord.Embed(
			title=(
				'\N{PUSHPIN}MESSAGE PINNED (SENT {reltime} IN #{chan})'
			).format(
				reltime=__main__.reltime(time.mktime(new.timestamp.timetuple())),
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
		await __main__.client.send_message(schan, embed=em)
	if old.pinned and not new.pinned and not __main__.logdisabled('message_unpin', new.server):
		em = discord.Embed(
			title=(
				'\N{PUSHPIN}MESSAGE UNPINNED (SENT {reltime} IN #{chan})'
			).format(
				reltime=__main__.reltime(time.mktime(new.timestamp.timetuple())),
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
		await __main__.client.send_message(schan, embed=em)

	# Preliminary checkings
	if old.content == new.content:
		# Must be the message being pinned and/or embed(s) displaying
		# Actually, TTS and rich embeds could also have changed,
		# but this is just a refactor
		return

	if not __main__.logdisabled('message_edit', new.server):
		if len(new.content) > 1024 or len(new.content) > 1024:
			em = discord.Embed(
				title=(
					'\N{MEMO}MESSAGE EDITED (SENT {reltime} IN #{chan}).'
					' The older content is:'
				).format(
					reltime=__main__.reltime(time.mktime(new.timestamp.timetuple())),
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
			await __main__.client.send_message(schan, embed=em)
			em = discord.Embed(
				title=(
					'MESSAGE EDITED (SENT {reltime} IN #{chan}).'
					' The newer content is:'
				).format(
					reltime=__main__.reltime(time.mktime(new.timestamp.timetuple())),
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
			await __main__.client.send_message(schan, embed=em)
		else:
			em = discord.Embed(
				title=(
					'\N{MEMO}MESSAGE EDITED (SENT {reltime} IN #{chan})'
				).format(
					reltime=__main__.reltime(time.mktime(new.timestamp.timetuple())),
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
			await __main__.client.send_message(schan, embed=em)

	# Turning off this logging also turns off the feature
	if not __main__.logdisabled('message_overedit', new.server):
		# Delete a message if it has been edited more than 5 times in 30 seconds
		await utils.handle_minute_message_edits(new, schan)

async def on_member_update(before, after):
	specialchannel = __main__.getspecialchannel(after.server)
	if before.nick != after.nick and not __main__.logdisabled('member_nickname', after.server):
		embed = discord.Embed(title='🇳📟CHANGED NICKNAME'.format(id=after.id), colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=__main__.infourl('userid={}'.format(after.id)))
		if before.nick is None:
			embed.add_field(name='No Older Nickname', value='_No Older Nickname_')
		else:
			embed.add_field(name='Older Nickname', value=utils.mdspecialchars(before.nick))
		embed.add_field(name='\u200b', value='\u200b')
		if after.nick is None:
			embed.add_field(name='No Newer Nickname', value='_No Newer Nickname_')
		else:
			embed.add_field(name='Newer Nickname', value=utils.mdspecialchars(after.nick))
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.roles != after.roles:
		if __main__.logdisabled('member_roleadd', after.server):
			addedroles = []
		else:
			addedroles   = list(set(after.roles) - set(before.roles))

		if __main__.logdisabled('member_roleremove', after.server):
			removedroles = []
		else:
			removedroles = list(set(before.roles) - set(after.roles))

		if len(addedroles) > 0 or len(removedroles) > 0:
			if len(addedroles) > 0 and len(removedroles) > 0:
				embed = discord.Embed(title='ROLES CHANGED FOR USER')
			elif len(addedroles) > 1:
				embed = discord.Embed(title='ROLES ADDED TO USER')
			elif len(addedroles) == 1:
				embed = discord.Embed(title='ROLE ADDED TO USER')
			elif len(removedroles) > 1:
				embed = discord.Embed(title='ROLES REMOVED FROM USER')
			elif len(removedroles) == 1:
				embed = discord.Embed(title='ROLE REMOVED FROM USER')

			embed.set_author(
				name=after.display_name,
				icon_url=after.avatar_url,
				url=__main__.infourl('userid={}'.format(after.id))
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
			await __main__.client.send_message(specialchannel, embed=embed)

		if config.get_s('rolecachemode', after.server.id) != 0:
			__main__.updaterolecache(after)
			__main__.rolecachesave()
	if before.name != after.name and not __main__.logdisabled('member_username', after.server):
		description = '🇺📟CHANGED USERNAME'.format(id=after.id)
		if before.discriminator != after.discriminator:
			description += ' AND DISCRIMINATOR 🔸'
		embed = discord.Embed(title=description, colour=after.colour)
		embed.set_author(name=after.display_name, icon_url=after.avatar_url, url=__main__.infourl('userid={}'.format(after.id)))
		embed.add_field(name='Older Username', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Username', value=utils.mdspecialchars(after.name))
		if before.discriminator != after.discriminator:
			embed.add_field(name='Older Discriminator', value=before.discriminator, inline=False)
			embed.add_field(name='Newer Discriminator', value=after.discriminator)
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.avatar_url != after.avatar_url and ((not __main__.logdisabled('member_botavatar', after.server)) if checks.is_bot(after) else (not __main__.logdisabled('member_avatar', after.server))):
		embed = discord.Embed(description='👥<@!{id}> ({id}) changed avatar'.format(id=after.id), colour=after.colour, timestamp=datetime.datetime.now())
		embed.set_author(name=after.display_name, icon_url=after.avatar_url)
		embed.set_thumbnail(url=before.avatar_url)
		embed.set_image(url=after.avatar_url)
		embed.add_field(name='Older Avatar URL: None' if before.avatar_url == '' else 'Older Avatar URL (Thumbnail)', value='No Older Avatar URL' if before.avatar_url == '' else before.avatar_url)
		embed.add_field(name='Newer Avatar URL: None' if after.avatar_url == '' else 'Newer Avatar URL (Inset Image)', value='No Newer Avatar URL' if after.avatar_url == '' else after.avatar_url, inline=False)
		await __main__.client.send_message(specialchannel, embed=embed)

async def on_member_join(member):
	if not __main__.logdisabled('member_join', member.server):
		specialchannel = __main__.getspecialchannel(member.server)
		embed = discord.Embed(description='➡<@!{id}> ({id}) joined server'.format(id=member.id), colour=member.server.me.colour, timestamp=datetime.datetime.now())
		embed.add_field(
			name='This server now has',
			value=str(member.server.member_count) + ' members',
		)
		embed.set_author(name=member.display_name)
		embed.set_thumbnail(url=member.avatar_url)
		await __main__.client.send_message(specialchannel, embed=embed)
	await __main__.newmemberroles(member, specialchannel, False)

async def on_member_remove(member):
	if not __main__.logdisabled('member_remove', member.server):
		specialchannel = __main__.getspecialchannel(member.server)
		embed = discord.Embed(description='🚪<@!{id}> ({id}) removed from server'.format(id=member.id), colour=member.colour, timestamp=datetime.datetime.now())
		embed.add_field(name='Originally joined server', value=__main__.reltime(time.mktime(member.joined_at.timetuple())))
		embed.add_field(
			name='This server now has',
			value=str(member.server.member_count) + ' members',
		)
		embed.set_author(name=member.display_name, icon_url=member.avatar_url)
		embed.set_thumbnail(url=member.avatar_url)
		await __main__.client.send_message(specialchannel, embed=embed)

async def on_member_ban(member):
	if __main__.logdisabled('member_ban', member.server):
		return
	specialchannel = __main__.getspecialchannel(member.server)

	msg = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(utils.wrapbackticks(member.name), member.discriminator, member.id, member.server.name, member.server.id)
	await __main__.client.send_message(specialchannel, msg)

async def on_member_unban(server, user):
	if __main__.logdisabled('member_unban', server):
		return
	specialchannel = __main__.getspecialchannel(server)
	msg = '**`>`**<:doormat:239361673532669953>`user` **``{}``**`#{}` `({}) unbanned from server {} ({})`'.format(utils.wrapbackticks(user.name), user.discriminator, user.id, server.name, server.id)
	await __main__.client.send_message(specialchannel, msg)

async def on_typing(channel, user, when):
	try:
		specialchannel = __main__.getspecialchannel(channel.server)
	except AttributeError: # this would happen if the typing event is in a private message
		return
	if specialchannel.id == channel.server.default_channel.id:
		specialchannel = channel
	if str(user.status) == 'offline' and not __main__.logdisabled('invisible_typing', channel.server):
		embed = discord.Embed(title='👻INVISIBLE WHILE TYPING IN {}'.format(channel.mention), colour=user.colour)
		embed.set_author(name=user.display_name, icon_url=user.avatar_url, url=__main__.infourl('userid={}'.format(user.id)))
		await __main__.client.send_message(specialchannel, embed=embed)
	else:
		return # practically unnecessary, but this is for if we want to do things when members type later

async def on_server_role_create(r):
	if __main__.logdisabled('role_create', r.server):
		return
	schan = __main__.getspecialchannel(r.server)
	embed = discord.Embed(
		title='ROLE ADD AT {time}'.format(time=str(r.created_at)),
		description=utils.mdspecialchars(r.name),
		colour=r.colour,
	)
	await __main__.client.send_message(schan, embed=embed)

async def on_server_role_delete(r):
	if __main__.logdisabled('role_delete', r.server):
		return
	schan = __main__.getspecialchannel(r.server)
	embed = discord.Embed(
		title='ROLE REMOVE',
		description=utils.mdspecialchars(r.name),
		colour=r.colour,
	)
	embed.add_field(name='Original Creation Time', value=str(r.created_at))
	await __main__.client.send_message(schan, embed=embed)

async def on_server_role_update(before, after):
	specialchannel = __main__.getspecialchannel(before.server)
	# If the name changed
	if before.name != after.name and not __main__.logdisabled('role_rename', before.server):
		embed = discord.Embed(title='ROLE NAME CHANGE', description=utils.mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Name', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=utils.mdspecialchars(after.name))
		await __main__.client.send_message(specialchannel, embed=embed)
	# If "display online members separately" changed
	if before.hoist != after.hoist:
		# If the role has been hoisted
		if before.hoist == 0 and after.hoist == 1 and not __main__.logdisabled(
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
			await __main__.client.send_message(specialchannel, embed=embed)
		# If the role has been lowered
		if before.hoist == 1 and after.hoist == 0 and not __main__.logdisabled(
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
			await __main__.client.send_message(specialchannel, embed=embed)
	# If "allow everyone to mention this role" changed
	if before.mentionable != after.mentionable:
		# If the role is now mentionable
		if before.mentionable == 0 and after.mentionable == 1 and not __main__.logdisabled(
			'role_mentionable', before.server
		):
			msg = '**`>`**`role` **``{}``** `({}) is now mentionable`'.format(utils.wrapbackticks(after.name), after.id)
			await __main__.client.send_message(specialchannel, msg)
		# If the role is no longer mentionable
		if before.mentionable == 1 and after.mentionable == 0 and not __main__.logdisabled(
			'role_unmentionable', before.server
		):
			msg = '**`>`**`role` **``{}``** `({}) is no longer mentionable`'.format(utils.wrapbackticks(after.name), after.id)
			await __main__.client.send_message(specialchannel, msg)
	# If the role has been moved up or down in the hierarchy
	if before.position != after.position and not __main__.logdisabled('role_hierarchy', before.server):
		# The role has been moved down
		if before.position > after.position:
			msg = '**`>`**`role` **``{}``** `({}) has been moved down by {} roles ({} to {})`'.format(utils.wrapbackticks(after.name), after.id, before.position - after.position, before.position, after.position)
			await __main__.client.send_message(specialchannel, msg)
		# The role has been moved up
		if before.position < after.position:
			msg = '**`>`**`role` **``{}``** `({}) has been moved up by {} roles ({} to {})`'.format(utils.wrapbackticks(after.name), after.id, after.position - before.position, before.position, after.position)
			await __main__.client.send_message(specialchannel, msg)
	# If the role color has changed
	if before.colour != after.colour and not __main__.logdisabled('role_color', before.server):
		embed = discord.Embed(title='ROLE COLOR CHANGE', description=utils.mdspecialchars(after.name), colour=after.colour)
		embed.add_field(name='Older Color', value='(default)' if before.colour.value == 0 else str(before.colour).upper())
		embed.add_field(name='Newer Color', value='(default)' if after.colour.value == 0 else str(after.colour).upper())
		await __main__.client.send_message(specialchannel, embed=embed)
	# If any of the permissions has changed
	if before.permissions != after.permissions and not __main__.logdisabled(
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
		await __main__.client.send_message(specialchannel, embed=e)

async def on_reaction_add(r, u):
	if __main__.isprivatemessage(r.message.server) or __main__.logdisabled('reaction_add', r.message.server):
		return
	specialchannel = __main__.getspecialchannel(r.message.server)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION ADDED TO MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=__main__.reltime(time.mktime(r.message.timestamp.timetuple())),
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	embed.set_author(
		name=u.display_name,
		icon_url=u.avatar_url,
		url=__main__.infourl('userid={}&messageid={}'.format(u.id, r.message.id))
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
	await __main__.client.send_message(specialchannel, embed=embed)

async def on_reaction_remove(r, u):
	if __main__.isprivatemessage(r.message.server) or __main__.logdisabled('reaction_remove', r.message.server):
		return
	specialchannel = __main__.getspecialchannel(r.message.server)
	try:
		iscustomemote = True
		emotename = r.emoji.name
	except AttributeError:
		iscustomemote = False
		emotename = r.emoji
	embed = discord.Embed(
		title='REACTION REMOVED FROM MESSAGE (SENT {rtime} IN {c.mention})'.format(
			rtime=__main__.reltime(time.mktime(r.message.timestamp.timetuple())),
			c=r.message.channel,
		),
		description=r.message.content,
		colour=u.colour,
	)
	embed.set_author(
		name=u.display_name,
		icon_url=u.avatar_url,
		url=__main__.infourl('userid={}&messageid={}'.format(u.id, r.message.id))
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
	await __main__.client.send_message(specialchannel, embed=embed)

async def on_reaction_clear(m, rs):
	if __main__.isprivatemessage(m.server) or __main__.logdisabled('reaction_clear', m.server):
		return
	schan = __main__.getspecialchannel(m.server)
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
			rtime=__main__.reltime(time.mktime(m.timestamp.timetuple())),
			c=m.channel,
		),
		description=m.content,
		colour=m.author.colour,
	)
	embed.add_field(name='Message ID (temp)', value=m.id)
	embed.add_field(name='Reactions', value=rlist)
	await __main__.client.send_message(schan, embed=embed)

async def on_server_update(before, after):
	specialchannel = __main__.getspecialchannel(after)
	if before.icon != after.icon and not __main__.logdisabled('server_icon', after):
		embed = discord.Embed(description='Server changed icon')
		embed.set_thumbnail(url=before.icon_url)
		embed.add_field(name='Older Icon URL: None' if before.icon_url == '' else 'Older Icon URL (Thumbnail)', value='No Older Icon URL' if before.icon_url == '' else before.icon_url)
		embed.add_field(name='Newer Icon URL: None' if after.icon_url == '' else 'Newer Icon URL (Inset Image)', value='No Newer Icon URL' if after.icon_url == '' else after.icon_url)
		embed.set_image(url=after.icon_url)
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.name != after.name and not __main__.logdisabled('server_rename', after):
		embed = discord.Embed(description='Server changed name')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Name', value=utils.mdspecialchars(before.name))
		embed.add_field(name='Newer Name', value=utils.mdspecialchars(after.name))
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.region != after.region and not __main__.logdisabled('server_region', after):
		embed = discord.Embed(description='VOICE REGION CHANGE')
		embed.set_thumbnail(url=after.icon_url)
		embed.add_field(name='Older Region', value=str(before.region))
		embed.add_field(name='Newer Region', value=str(after.region))
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.afk_timeout != after.afk_timeout and not __main__.logdisabled('server_afktimeout', after):
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
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.afk_channel != after.afk_channel and not __main__.logdisabled('server_afkchannel', after):
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
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.verification_level != after.verification_level and not __main__.logdisabled(
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
		await __main__.client.send_message(specialchannel, embed=embed)
	if before.mfa_level != after.mfa_level and not __main__.logdisabled('server_2fa', after):
		if before.mfa_level == 0 and after.mfa_level == 1:
			embed=discord.Embed(description='SERVER 2FA ENABLED')
		elif before.mfa_level == 1 and after.mfa_level == 0:
			embed=discord.Embed(description='SERVER 2FA DISABLED')
		await __main__.client.send_message(specialchannel, embed=embed)

async def on_server_emojis_update(b, a):
	try:
		schan = __main__.getspecialchannel(a[0].server)
	except IndexError:
		schan = __main__.getspecialchannel(b[0].server)
	if __main__.logdisabled('server_emotes', schan.server):
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
		await __main__.client.send_message(schan, embed=embed)
		return
	embed = discord.Embed(description=desc)
	embed.add_field(name='Emotes', value=elist)
	await __main__.client.send_message(schan, embed=embed)

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
			await __main__.client.edit_channel_permissions(vtc, new, ow)
			break

		if old.voice.voice_channel and old.voice.voice_channel == vvc:
			# Left the voice channel
			await __main__.client.delete_channel_permissions(vtc, new)
			break

async def on_channel_create(c):
	if c.type == discord.ChannelType.private or __main__.logdisabled('channel_add', c.server):
		return
	schan = __main__.getspecialchannel(c.server)
	embed = discord.Embed(
		description='{type} CHANNEL ADD\n{0.name} ({0.id})'.format(
			c,
			type=str(c.type).upper(),
		),
	)
	await __main__.client.send_message(schan, embed=embed)

async def on_channel_delete(c):
	if c.type == discord.ChannelType.private or __main__.logdisabled('channel_remove', c.server):
		return
	schan = __main__.getspecialchannel(c.server)
	embed = discord.Embed(
		description='{type} CHANNEL REMOVE\n{0.name} ({0.id})'.format(
			c,
			type=str(c.type).upper(),
		),
	)
	await __main__.client.send_message(schan, embed=embed)

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
	mchan = __main__.client.get_channel(event['d']['channel_id'])
	if mchan.type == discord.ChannelType.private:
		return

	if event['t'] == 'MESSAGE_DELETE':
		if __main__.logdisabled('message_deleteuncached', mchan.server):
			return
		# Check if on_message_delete() was already called by this message
		# If it was, then return
		if discord.utils.find(lambda m: m.id == event['d']['id'], __main__.client.messages) != None:
			# If the message lingers in deleted_messages, it doesn't really matter for now
			return
		if event['d']['id'] in __main__.owncache:
			# Already removed from the cache, but we still haven't run on_message_delete
			# This happens all the time.
			__main__.owncache.remove(event['d']['id'])
			return
		for m in __main__.deleted_messages:
			if m.id == event['d']['id']:
				# on_message_delete was faster
				__main__.deleted_messages.remove(m)
				return

		schan = __main__.getspecialchannel(
			mchan.server
		)
		e = discord.Embed(
			title='UNCACHED MESSAGE DELETED IN {0.mention}'.format(mchan),
			url=__main__.infourl('messageid=' + event['d']['id']),
			description=(
				'Since this message is uncached, I can’t give you'
				' any more information than its ID and its channel.'
			),
			colour=mchan.server.me.colour,
		)
		await __main__.client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_UPDATE':
		if __main__.logdisabled('message_updateuncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['id'], __main__.client.messages) != None:
			return

		schan = __main__.getspecialchannel(mchan.server)
		athr = mchan.server.get_member(event['d']['author']['id'])
		e = discord.Embed(
			title=(
				'UNCACHED MESSAGE UPDATED (SENT {rltm}'
				' IN {0.mention}).'
				' NEWER CONTENT AND PROPERTIES:'
			).format(
				mchan,
				rltm=__main__.reltime(
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
			url=__main__.infourl(
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
				'``{}``'.format(utils.wrapbackticks(str(event['d']['embeds']['rich'])))
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
		await __main__.client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_REACTION_ADD':
		if __main__.logdisabled('reaction_adduncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['message_id'], __main__.client.messages) \
		!= None:
			return

		schan = __main__.getspecialchannel(mchan.server)
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
			url=__main__.infourl(
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
		await __main__.client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_REACTION_REMOVE':
		if __main__.logdisabled('reaction_removeuncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['message_id'], __main__.client.messages) \
		!= None:
			return

		schan = __main__.getspecialchannel(mchan.server)
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
			url=__main__.infourl(
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
		await __main__.client.send_message(schan, embed=e)
	elif event['t'] == 'MESSAGE_REACTION_REMOVE_ALL':
		if __main__.logdisabled('reaction_clearuncached', mchan.server):
			return
		# Check if the message is in the cache and return if it is
		if discord.utils.find(lambda m: m.id == event['d']['message_id'], __main__.client.messages) \
		!= None:
			return

		schan = __main__.getspecialchannel(mchan.server)
		e = discord.Embed(
			title=(
				'REACTIONS CLEARED FROM UNCACHED MESSAGE'
				' IN {0.mention}'
			).format(mchan),
			url=__main__.infourl('messageid=' + event['d']['message_id']),
			description=(
				'Since this message is uncached, I can’t give you'
				' any more information than its ID and its channel.'
			),
			colour=mchan.server.me.colour,
		)
		await __main__.client.send_message(schan, embed=e)

async def on_channel_update(b, a):
	if a.type == discord.ChannelType.private or __main__.logdisabled('channel_rename', a.server):
		return
	schan = __main__.getspecialchannel(a.server)
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
		await __main__.client.send_message(schan, embed=e)

async def on_server_join(serv):
	em = discord.Embed(
		title='BOT ADDED TO SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(serv.name),
			id=serv.id,
		),
		colour=opserver.me.colour,
	)
	em.set_image(url=serv.icon_url)
	await __main__.client.send_message(opserver_botservers, embed=em)

async def on_server_remove(serv):
	em = discord.Embed(
		title='BOT REMOVED FROM SERVER',
		description='**{name}** ({id})'.format(
			name=utils.mdspecialchars(serv.name),
			id=serv.id,
		),
		colour=opserver.me.colour,
	)
	em.set_image(url=serv.icon_url)
	await __main__.client.send_message(opserver_botservers, embed=em)
