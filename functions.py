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

# every function below here is custom-defined and not a part of discord.py

def listroles(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '<@&{}>'.format(role.id)
	return returnage

def listroles_id(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '<@&{}>'.format(role)
	return returnage

def getspecialchannel(server):
	theconfig = config.get_s('specialchannel', server.id)
	if theconfig != '0':
		return client.get_channel(id=theconfig)
	else:
		return server.default_channel

def getspecialchannel_reply(message):
	if message.server == None:
		return message.channel
	specialchannel = getspecialchannel(message.server)
	if specialchannel == message.server.default_channel:
		return message.channel
	return specialchannel

def reltime(timestamp, noago=False):
	timestamp = int(timestamp)
	now = int(time.time())
	sdt = now - timestamp
	dt = math.fabs(sdt)

	if dt == 0:
		return 'now'
	elif dt < 60:
		solong = '{}s'.format(int(dt))
	elif dt < 60*60:
		dm = math.floor(dt/60)
		ds = dt-dm*60
		solong = '{}m{}s'.format(dm, int(ds))
	elif dt < 24*60*60:
		dh = math.floor(dt/3600)
		dm = math.floor((dt-dh*3600)/60)
		#ds = dt-dh*3600-dm*60
		solong = '{}h{}m'.format(dh, dm)
	else:
		dd = math.floor(dt/86400)
		dh = math.floor((dt-dd*86400)/3600)
		solong = '{}d{}h'.format(dd, dh)

	if sdt >= 0:
		if noago:
			return solong
		return '{} ago'.format(solong)
	return '{} in the future'.format(solong)

def parsereltime(inputstr, relative=False, now=None):
	# if relative is true then we only get the amount of seconds from now, if false we get a unix timestamp.
	if now == None:
		now = int(time.time())
	total = 0

	m = re.search("^((?P<d>[0-9]+)d)?((?P<h>[0-9]+)h)?((?P<m>[0-9]+)m)?((?P<s>[0-9]+)s)?$", inputstr)

	if m == None:
		return None

	ds = m.group('d')
	if ds != None:
		total += int(ds)*86400
	hs = m.group('h')
	if hs != None:
		total += int(hs)*3600
	ms = m.group('m')
	if ms != None:
		total += int(ms)*60
	ss = m.group('s')
	if ss != None:
		total += int(ss)

	if relative:
		return total
	else:
		return now+total

async def handleExpiryTimer():
	"""Sets the timer correctly to the first event
	If time is in the past, call autoExpiry immediately
	Can be called on startup, when changing something, or at the end of autoExpiry
	"""
	global exptimer

	# Cancel the existing timer, if it's running
	if exptimer != None:
		exptimer.cancel()
		exptimer = None  # Because there's no Timer.isCanceled()

	entriesleft = False

	for serverid in events.rolexpires:  # Merge with next for maybe
		if len(events.rolexpires[serverid]) > 0:
			entriesleft = True
			break

	if not entriesleft:
		# We're finished
		logging.info('Did not set expiry timer because there\'s no expiry entry left')
		return

	timelowscore = 9999999999

	for serverid in events.rolexpires:
		for userid in events.rolexpires[serverid]:
			if events.rolexpires[serverid][userid]['time'] < timelowscore:
				timelowscore = events.rolexpires[serverid][userid]['time']

	if timelowscore <= int(time.time()):
		logging.info('Immediately calling autoExpiry() because we’re overdue in resetting someone’s roles')
		await autoExpiry()
	else:
		timertime = (timelowscore - time.time()) + 2  # 2 seconds extra, just to make sure we're not getting problems due to being one second off
		exptimer = Timer(timertime, callAutoExpiry)
		exptimer.start()
		logging.info('Set expiry timer for {} seconds'.format(timertime))

def callAutoExpiry():
	asyncio.run_coroutine_threadsafe(autoExpiry(), client.loop)

async def autoExpiry():
	"""Called by timers
	Actually resets roles
	Calls back handleTimer to set the next timer
	"""
	now = int(time.time())

	# So apparently someone needs to be unbanned?
	for serverid in events.rolexpires:
		content = ''
		successfulresets = []

		cserver = discord.utils.get(client.servers, id=serverid)
		for userid in events.rolexpires[serverid]:
			if events.rolexpires[serverid][userid]['time'] <= now:
				try:
					await removeRestrictiveRoles(cserver.get_member(userid), cserver)
					content += '\nRoles for <@!{}> reset.'.format(userid)
				except (AttributeError, TypeError):
					# Look if they are in the role cache, and reset it there instead.
					if removerolecache(userid, serverid):
						content += '\n<@!{}> was supposed to have their roles reset now, they aren’t on the server, but they’ve successfully been removed from the role cache.'.format(userid)
						rolecachesave()
					else:
						content += '\n<@!{}> was supposed to have their roles reset now, but they can be found neither on the server nor in the role cache!'.format(userid)

				# Shorten the following thing so we don't have to keep typing it.
				thisexpiry = events.rolexpires[serverid][userid]
				if thisexpiry['msgedit_message'] != '0':
					await editexpirymessage(cserver, thisexpiry)
				if thisexpiry['msgpost_channel'] != '0':
					# We want to announce it with a new message!
					await client.send_message(
						discord.utils.get(cserver.channels,
							id=thisexpiry['msgpost_channel']
						),
						thisexpiry['msgpost_content']
					)

				successfulresets.append(userid)
		for userid in successfulresets:
			removeexpiryentry(serverid, userid)

		if len(successfulresets) > 0:
			if content == '':
				content = '\n(never mind, nobody has been found!)'

			content = '**Auto expiry:**' + content

			await client.send_message(getspecialchannel(cserver), content)

	rolexpiresave()

	await handleExpiryTimer()

async def removeRestrictiveRoles(member, server):
	try:
		await givetakeroles(
			member, server,
			config.get_s('defaultbotroles' if member.bot else 'defaultroles',server.id),
			config.get_s('restrictiveroles', server.id)
		)
	except (AttributeError,TypeError) as e:
		raise e

async def givetakeroles(member, server, giveids, takeids):
	badroles = [] # All the roles that are potentially deleted
	removingtheseroles = [] # Roles that the user has which will be deleted
	addingtheseroles = [] # Roles that the user doesn't have which will be added
	otherroles = [] # Other roles the user has

	for rid in takeids:
		badroles.append(
			discord.utils.get(server.roles, id=rid)
		)
	for rid in giveids:
		addingtheseroles.append(
			discord.utils.get(server.roles, id=rid)
		)
	for role in member.roles:
		if role in badroles:
			# This member has that bad role, we need to get rid of it!
			removingtheseroles.append(role)
			continue
		if role in addingtheseroles:
			# Oh, we already have that one
			addingtheseroles.remove(role)
		if not role.is_everyone:
			# If we're going to need to replace roles, keep these the same!
			otherroles.append(role)
	if len(addingtheseroles) == 0 and len(removingtheseroles) == 0:
		# Well what are we doing here?
		return
	if len(addingtheseroles) > 0 and len(removingtheseroles) > 0:
		# Replace - luckily the union of these is this simple!
		await client.replace_roles(member, *addingtheseroles, *otherroles)
	elif len(addingtheseroles) > 0:
		# Only adding
		await client.add_roles(member, *addingtheseroles)
	else:
		# Only removing
		await client.remove_roles(member, *removingtheseroles)


async def editexpirymessage(cserver, thisexpiry):
	# We want to edit a message to reflect the ban!
	getmessage = await client.get_message(
		discord.utils.get(cserver.channels,
			id=thisexpiry['msgedit_channel']
		),
		thisexpiry['msgedit_message']
	)
	if thisexpiry['msgedit_newcontent'] == '':
		await client.delete_message(getmessage)
	else:
		await client.edit_message(getmessage, new_content=thisexpiry['msgedit_newcontent'])

def addexpiryentry(serverid, memberid, expirytime,
                   e_channel='0', e_message='0', e_newcontent='',
                   p_channel='0', p_content=''):
	if not serverid in events.rolexpires:
		events.rolexpires[serverid] = {}

	events.rolexpires[serverid][memberid] = {
		'time': expirytime,
		'msgedit_channel': e_channel,
		'msgedit_message': e_message,
		'msgedit_newcontent': e_newcontent,
		'msgpost_channel': p_channel,
		'msgpost_content': p_content,
	}

def removeexpiryentry(serverid, memberid):
	if not serverid in events.rolexpires:
		return False

	if not memberid in events.rolexpires[serverid]:
		return False

	del events.rolexpires[serverid][memberid]
	return True

def getearliestexpiry(serverid):  # Returns: [userid, entry]
	if not serverid in events.rolexpires or len(events.rolexpires[serverid]) == 0:
		return None

	timelowscore = 9999999999
	earliestuserid = '0'
	earliestexpiry = None  # Entry

	for userid in events.rolexpires[serverid]:
		if events.rolexpires[serverid][userid]['time'] < timelowscore:
			timelowscore = events.rolexpires[serverid][userid]['time']
			earliestuserid = userid
			earliestexpiry = events.rolexpires[serverid][userid]

	return [earliestuserid, earliestexpiry]

async def fetch(url):
	async with ClientSession() as session:
		async with session.get(url) as response:
			return await response.read()

def logfailedcommand(command, arguments, message):
	if arguments == None:
		arguments = ''
	logging.info('{} {} attempted by {}#{} (uuid {}) at {} utc but failed'.format(command, arguments, message.author.name, message.author.discriminator, message.author.id, message.timestamp))

def logcommand(command, arguments, message):
	if arguments == None:
		arguments = ''
	logging.info('{} {} called by {}#{} (uuid {}) at {} utc'.format(command, arguments, message.author.name, message.author.discriminator, message.author.id, message.timestamp))

def infourl(query):
	return 'https://tolp2.nl/showdiscordinfo.php?' + query

def logdisabled(key, server):
	checks = [key, key.split('_')[0] + '_*', '*']

	if any(x in config.get_s('disabledlogs', server.id) for x in checks):
		return True
	if any(x in config.get_s('enabledlogs', server.id) for x in checks):
		return False
	return True

def respondtorule(rule):
	if int(rule) == 37:
		return 'Funny and original, nothing to see here.'
	return 'Wow, you’re the FIRST one to come up with that. I wish I could be as funny as you, I dunno how I’m ever gonna top "rule {}", though. That shit is genius.'.format(rule)

async def newmemberroles(member, specialchannel, bypassjoinchannel):
	if config.get_s('rolecachemode', member.server.id) == 1 and is_bot(member):
		# Give them the bot roles!
		addingtheseroles = []
		for rid in config.get_s('defaultbotroles', member.server.id):
			addingtheseroles.append(
				discord.utils.get(member.server.roles, id=rid)
			)
		await client.add_roles(member, *addingtheseroles) # bot role
		return

	if config.get_s('rolecachemode', member.server.id) != 0 and member.server.id in events.memberroles:
		# Are they in our database of members which had roles before?
		if member.id in events.memberroles[member.server.id]:
			addingtheseroles = []
			# They're found in the database! Give them the groups they should have
			for rid in events.memberroles[member.server.id][member.id]:
				addingrole = discord.utils.get(member.server.roles, id=rid)
				if addingrole.is_everyone:
					continue
				addingtheseroles.append(addingrole)
			await client.add_roles(member, *addingtheseroles)
			content = '<@!{id}> ({id}) found in the role cache\n'.format(id=member.id)
			value = '_{} role'.format(str(len(addingtheseroles)))
			value += 's:' if len(addingtheseroles) != 1 else ':'
			value += listroles(addingtheseroles) + '_'
			content += 'Given them back their roles:\n' + value
			await client.send_message(specialchannel, content)
		elif config.get_s('rolecachemode', member.server.id) == 1 or bypassjoinchannel:
			# Not found, so just give them the default roles
			addingtheseroles = []
			for rid in config.get_s('defaultroles', member.server.id):
				addingtheseroles.append(
					discord.utils.get(member.server.roles, id=rid)
				)
			await client.add_roles(member, *addingtheseroles)

def setglobal(s, x):
	globals()[s] = x
