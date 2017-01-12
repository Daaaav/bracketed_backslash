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

def is_admin(member):
	try:
		perms = member.server_permissions
	except AttributeError:
		return False
	if perms.administrator:
		return True
	return False

def is_mod(member):
	# Same here. No need to use is_admin and is_mod in the same conditional.
	try:
		perms = member.server_permissions
	except AttributeError:
		return False
	if perms.manage_messages:
		return True
	return is_admin(member) # Admins have moderator powers, too

def is_bot(member):
	# Alright then.
	if member.bot:
		return True
	return False

def is_dev(member):
	# Alright then. [2]
	for role in member.roles:
		if role.id == '238424544379928576': # [\] dev role
			return True
	return False

def is_operator(member):
	if member.id in config.get_s('operators'):
		return True
	return member.id == ownerid

def is_tntgb_mod(member):
	for role in member.roles:
		if role.id == '266590337269497856': # TNTGB moderator role
			return True
	return False

def get_member_input(server, input):
	"""Tries to return a member object given a user input which could be anything that identifies that member.

	The following priority is used:
	1) Mention: <@1234567890> or <@!1234567890>
	2) ID: 1234567890
	3) Username/Userame+discriminator/Nickname, whatever server.get_member_named() accepts
	4) Case-insensitive nickname 100% match
	5) Case-insensitive username 100% match
	6) Case-insensitive nickname partial match
	7) Case-insensitive username partial match
	8) Discriminator only (either with or without #)

	"""
	# Is there a Discord server in between us?
	if isprivatemessage(server):
		return None

	# Is this anything at all?
	if input == None:
		return None  # right back at ya

	# Is this a mention?
	if input.startswith('<@!') and input.endswith('>'):
		input = input[3:-1] # Extract the ID from it
	elif input.startswith('<@') and input.endswith('>'):
		input = input[2:-1] # Same

	targetmember = server.get_member(input)

	if targetmember == None:  # Not an ID
		targetmember = server.get_member_named(input)
		if targetmember == None:  # Not found by server.get_member_named()
			# Everything else fails? Then try searching. Nicknames have priority, then usernames.
			# Maybe we're entering just a discriminator, match those as well.
			nickmatched = False
			usermatched = None
			nickfound = None
			userfound = None
			discmatched = None
			for mem in server.members:
				if mem.nick != None and mem.nick.lower() == input.lower():
					targetmember = mem
					nickmatched = True
					break
				if mem.name.lower() == input.lower():
					usermatched = mem
				if mem.nick != None and mem.nick.lower().find(input.lower()) != -1:
					nickfound = mem
				if mem.name.lower().find(input.lower()) != -1:
					userfound = mem
				if mem.discriminator == input:
					discmatched = mem
				if input.startswith('#') and mem.discriminator == input[1:]:
					discmatched = mem

			if not nickmatched:  # No 100% nickname match
				targetmember = usermatched
				if targetmember == None:  # No 100% username match
					targetmember = nickfound
					if targetmember == None:  # No partial nickname match
						targetmember = userfound
						if targetmember == None:  # No partial username match
							targetmember = discmatched  # Last chance - just the discriminator

	return targetmember

@client.event
async def reply(messageobject, message=None, emb=None):
	# Removes the need for adding msg_start manually every time
	if message == None:
		message = ''
	if len(msg_start + message) >= 2000:
		# We can at least try in a totally not failsafe and kinda ugly way
		content = msg_start + message
		contentlines = content.split('\n')
		cut = math.floor(len(contentlines)/2)
		await client.send_message(messageobject.channel, '\n'.join(contentlines[:cut]))
		if emb != None:
			await client.send_message(messageobject.channel, '\n'.join(contentlines[cut:]), embed=emb)
		else:
			await client.send_message(messageobject.channel, '\n'.join(contentlines[cut:]))
		return
	if emb != None:
		await client.send_message(messageobject.channel, msg_start + message, embed=emb)
	else:
		await client.send_message(messageobject.channel, msg_start + message)

@client.event
async def replyattach(messageobject, filetoattach, fname, message=''):
	# Don't bother with handling >2000 character messages just yet
	await client.send_file(destination=messageobject.channel, content = msg_start + message, fp=filetoattach, filename=fname)

def wrapbackticks(string, character=u'​'):
	"""escapes backticks for use in message output to discord
	its a fucking glorified string.replace() command with some error handling
	any string this is used on should be placed in either one of the following:
	double backticks (like ``this``)
	or code blocks (like ```this```)
	"""
	try:
		return string.replace('`', u'{character}`{character}'.format(character=character))
	except AttributeError:
		return string

def mdspecialchars(string, character='\\'):
	"""escapes markdown formatting for use in message output to discord
	this does not escape emojis until i figure out how to detect fucking emojis
	its a fucking glorified for loop with some error handling
	"""
	specialchars = [
		'\\', # this should be first otherwise you will get undesirable output
		'*', # italicize and bold
		'_', # italicize [2] and underline
		'~', # hey have you ever wanted to make a shitty joke? just wrap it in two of these on each side!
		'`', # oh hey we escaped these earlier
		'<', # custom emotes and suppressing link embeds
		'>', # custom emotes and suppressing link embeds [2]
	]
	try:
		for char in specialchars:
			string = string.replace(char, '\\' + char)
		return string
	except AttributeError:
		return string

def isprivatemessage(server): # this is a function because so in the future more checks for if its a private message can ezily be added
	if server == None:
		return True
	else:
		return False

def helplist(cats, onlycat=None):
	returnage = ''
	for cat in cats:
		if (onlycat == None and cat['cat_shown']) or onlycat == cat['cat_slug']:
			if onlycat == None:
				returnage += '\n\n__`{}:`__ — For command descriptions: **`\help {}`**'.format(cat['cat_name'], cat['cat_slug'])
			else:
				if cat['cat_desc'] != '':
					returnage += cat['cat_desc']
				returnage += '\n__`{}:`__'.format(cat['cat_name'])

			first = True
			for cmd in cat['commands']:
				if onlycat == None:
					if first:
						returnage += '\n`\{}`'.format(cmd['name'])
						first = False
					else:
						returnage += '   `\{}`'.format(cmd['name'])
				else:
					returnage += '\n`\{}` – {}'.format(cmd['name'], cmd['short'])
	return returnage

def is_valid_command(com):
	global cmds
	for cat in cmds:
		for cmd in cat['commands']:
			if cmd['name'] == com:
				return True
	return False

def hangmanworddisp(theword):
	global hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, hangmanstarter, guessedletters, algeraden

	theoutput = ''
	algeraden = True

	for i in range(0, len(theword)):
		if guessedletters[alphabet.find(theword[i].upper())]:
			theoutput += '__**`{}`**__ '.format(theword[i])
		else:
			theoutput += '`_` '
			algeraden = False

	# Now display already guessed letters.
	theoutput += '    (used: '

	notnone = False

	for i in range(0, 26):
		if guessedletters[i]:
			notnone = True
			theoutput += alphabet[i]

	if not notnone:
		theoutput += 'none'

	theoutput += ')'

	return theoutput

def rolelist(roles):
	rlist = []
	for role in roles:
		rlist.append(role.id)

	return rlist

def updaterolecache(member, serverid=member.server.id):
	global memberroles
	memberroles[serverid][str(member.id)] = list(rolelist(member.roles))

def removerolecache(memberid, serverid):
	global memberroles
	try:
		del memberroles[serverid][memberid]
	except KeyError:
		return False

	return True

def rolecachesave():
	global memberroles

	with open('memberroles.json', 'w') as outfile:
		json.dump(memberroles, outfile)

def rulesave():
	global rules

	with open('rules.json', 'w') as outfile:
		json.dump(rules, outfile)

def rolexpiresave():
	global rolexpires

	with open('rolexpires.json', 'w') as outfile:
		json.dump(rolexpires, outfile)

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

@client.event
async def handleExpiryTimer():
	"""Sets the timer correctly to the first event
	If time is in the past, call autoExpiry immediately
	Can be called on startup, when changing something, or at the end of autoExpiry
	"""
	global exptimer, rolexpires

	# Cancel the existing timer, if it's running
	if exptimer != None:
		exptimer.cancel()
		exptimer = None  # Because there's no Timer.isCanceled()

	if len(rolexpires) == 0:
		# We're finished
		logging.info('Did not set expiry timer')
		return

	timelowscore = 9999999999

	for userid in rolexpires:
		if rolexpires[userid] < timelowscore:
			timelowscore = rolexpires[userid]

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

@client.event
async def autoExpiry():
	"""Called by timers
	Actually resets roles
	Calls back handleTimer to set the next timer
	"""
	global server, rolexpires, specialchannel_prod
	now = int(time.time())

	content = ''
	successfulresets = []

	# So apparently someone needs to be unbanned?
	for userid in rolexpires:
		if rolexpires[userid] <= now:
			try:
				await removeRestrictiveRoles(server.get_member(userid), server)
				content += '\nRoles for <@!{}> reset.'.format(userid)
			except (AttributeError, TypeError):
				# Look if they are in the role cache, and reset it there instead.
				if removerolecache(userid):
					content += '\n<@!{}> was supposed to have their roles reset now, they aren’t on the server, but they’ve successfully been removed from the role cache.'.format(userid)
					rolecachesave()
				else:
					content += '\n<@!{}> was supposed to have their roles reset now, but they can be found neither on the server nor in the role cache!'.format(userid)
			successfulresets.append(userid)
	for userid in successfulresets:
		del rolexpires[userid]

	rolexpiresave()

	if content == '':
		content = '\n(never mind, nobody has been found!)'

	content = '**Auto expiry:**' + content

	await client.send_message(specialchannel_prod, content)

	await handleExpiryTimer()

@client.event
async def removeRestrictiveRoles(member, server):
	try:
		await client.remove_roles(member,
			discord.utils.get(server.roles, id='173240966575161344'), # nonsense-only
			discord.utils.get(server.roles, id='216647716531339264'), # no general mentions
			discord.utils.get(server.roles, id='222046096216686592'), # no cedule
			discord.utils.get(server.roles, id='215954720555139073'), # no tts
			discord.utils.get(server.roles, id='220643748508467220'), # banned
			discord.utils.get(server.roles, id='236925451216355338'), # tolper who cant change nickname
			discord.utils.get(server.roles, id='241183168269516800'), # no reactions
		)
	except (AttributeError,TypeError) as e:
		raise e

@client.event
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
	return key in config.get_s('disabledlogs', server.id)

def respondtorule(rule):
	if int(rule) == 37:
		return 'Funny and original, nothing to see here.'
	return 'Wow, you’re the FIRST one to come up with that. I wish I could be as funny as you, I dunno how I’m ever gonna top "rule {}", though. That shit is genius.'.format(rule)

def setglobal(s, x):
	globals()[s] = x
