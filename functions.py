# encoding=utf-8

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
	# Just Info and Dav
	if member.id == '146814960574398464' or member.id == '159793749604433921':
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

@client.async_event
async def reply(messageobject, message):
	# Removes the need for adding msg_start manually every time
	if len(msg_start + message) >= 2000:
		# We can at least try in a totally not failsafe and kinda ugly way
		content = msg_start + message
		contentlines = content.split('\n')
		cut = math.floor(len(contentlines)/2)
		await client.send_message(messageobject.channel, '\n'.join(contentlines[:cut]))
		await client.send_message(messageobject.channel, '\n'.join(contentlines[cut:]))
		return
	await client.send_message(messageobject.channel, msg_start + message)

def mdspecialchars(string):
	return string.replace('`', u'?`?')

def isprivatemessage(server): # this is a function because so in the future more checks for if its a private message can ezily be added
	if server == None:
		return True
	else:
		return False

def helplist(cats):
	returnage = ''
	for cat in cats:
		returnage += '\n__`{}:`__'.format(cat['cat_name'])
		for cmd in cat['commands']:
			returnage += '\n`\{}` – {}'.format(cmd['name'], cmd['short'])
	return returnage

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

def updaterolecache(member):
	global memberroles
	memberroles[str(member.id)] = list(rolelist(member.roles))

def removerolecache(memberid):
	global memberroles
	try:
		del memberroles[memberid]
	except KeyError:
		return False

	return True

def rolecachesave():
	global memberroles

	with open('members.json', 'w') as outfile:
		json.dump(memberroles, outfile)

def rulesave():
	global rules

	with open('rules.json', 'w') as outfile:
		json.dump(rules, outfile)

def listroles(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '{} ({})'.format(role.name, role.id)
	return returnage

def listroles_id(lijst):
	returnage = ''
	for role in lijst:
		if returnage != '':
			returnage += ', '
		returnage += '{} ({})'.format(discord.utils.get(client.get_server('158091122747506688').roles, id=role), role)
	return returnage

def getspecialchannel(server):
	if server.id == '153368829160849408':
		return specialchannel_prod
	elif server.id == '158091122747506688':
		return specialchannel_aperture
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
