# encoding=utf-8

import logging
import json
import sys

import discord

import __main__
import config
import op_ids

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
