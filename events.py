# encoding=utf-8

import logging
import json
import sys

import discord

import __main__
import config
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
			__main__.wrapbackticks(m.content[:100]).replace('discord.gg', 'discord\u200b.gg')
		)
	) if len(m.content) > 100 else (
		'``{}``'.format(__main__.wrapbackticks(m.content))
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
	elif __main__.is_mod(m.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'
	if hangmaninvokeractive:
		if not hangmanactive:
			return
		if __main__.is_mod(m.author):
			msg_start = (
				'**`>`**``{name}``**`#`**{indisp}\n'
			).format(
				name=__main__.wrapbackticks(m.author.name),
				indisp=indisp,
			)
		else:
			msg_start = (
				'**`>`**``{name}``**`$`**{indisp}\n'
			).format(
				name=__main__.wrapbackticks(m.author.name),
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
					.format(__main__.wrapbackticks(hangmanguessed.upper()))
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
						guess=__main__.wrapbackticks(hangmanguessed)
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
		name=__main__.wrapbackticks(m.author.name),
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
	not __main__.is_mod(m.author) and \
	m.channel.id != '201130047736643584' and \
	m.server.id == productionserver and \
	not (__main__.is_dev(m.author) and m.channel.id == '238423391571279872') and \
	not command in ['rule', 'rules', 'rulefind', 'rulesfind'] and \
	not (m.channel.id == '256924583737819146' and command in ['votevoicemute', 'vy', 'vn']):
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
	not __main__.is_tntgb_mod(m.author) and \
	command != 'selfban':
		return
	if not priv and \
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

	if command in __main__.commands:
		func = __main__.commands[command]
	else:
		# Check if it's an alias
		for c, p in __main__.commands.items():
			if p[2] != None and command in p[2]:
				func = __main__.commands[c]
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
	except Exception:
		e = emb.error(__main__.t['generic_error'])
		await __main__.reply(m, emb=e)
		raise

