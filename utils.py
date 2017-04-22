#!/usr/bin/python3.5
# encoding=utf-8

import datetime
import time
import re # TODO: Can be removed when parseroleconditional() is moved out

import discord

import __main__

def mdspecialchars(string, character='\\'):
	"""Return a Markdown-escaped version of a given string, for use in message output."""
	notspecialchars = ' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
	try:
		newstring = ''
		for i in string:
			newstring += character + i if i not in notspecialchars else i
		return newstring
	except AttributeError:
		return string

def id_summary(uid=None, mid=None, cid=None, rid=None):
	"""Return a oneline summary of IDs."""
	summary = ''
	if uid:
		summary += ' \N{BUST IN SILHOUETTE}' + uid
	if mid:
		summary += ' \N{SPEECH BALLOON}' + mid
	if cid:
		summary += ' \N{TELEVISION}' + cid
	if rid:
		summary += ' \N{KEY}' + rid
	if summary.startswith(' '):
		summary = summary[1:]
	return summary

async def handle_minute_message_edits(msg, schan):
	if not msg.id in __main__.minutemessageedits:
		__main__.minutemessageedits[msg.id] = [int(time.time())]
	else:
		edittime = int(time.time())
		while True:
			if edittime in __main__.minutemessageedits[msg.id]:
				edittime += .1
			else:
				__main__.minutemessageedits[msg.id].append(edittime)
				break
		if len(__main__.minutemessageedits[msg.id]) >= 5:
			await handle_delete_overedited_message(msg, schan)

		# While we're at it, also clean up other messages.

		# Copy because we may be removing elements from here
		for k in list(__main__.minutemessageedits):
			if k != msg.id:
				for i in list(__main__.minutemessageedits[k]):
					if i < (int(time.time())-30):
						__main__.minutemessageedits[k].remove(i)
				if len(__main__.minutemessageedits[k]) == 0:
					del __main__.minutemessageedits[k]

async def handle_delete_overedited_message(msg, schan):
	# Copy the list, we may be removing elements from here
	for i in list(__main__.minutemessageedits[msg.id]):
		if i < (int(time.time())-30):
			__main__.minutemessageedits[msg.id].remove(i)

	if len(__main__.minutemessageedits[msg.id]) >= 5:
		# Ok, that's enough editing.
		try:
			await __main__.client.delete_message(msg)
			__main__.messages_deleted_by_bot.append(msg)
			em = discord.Embed(
				title=('\N{MEMO}' * 5) + (
					'Message {0.id} was edited too many times in'
					' {0.channel.mention} and has been deleted by me'
				).format(msg),
				description=msg.content,
				colour=msg.author.colour,
				timestamp=datetime.datetime.now(),
			)
			em.set_author(
				name=msg.author.display_name,
				icon_url=msg.author.avatar_url,
			)
			em.add_field(
				name='Message author',
				value='<@!{0}> ({0})'.format(msg.author.id),
			)
		except discord.errors.NotFound:
			em = discord.Embed(
				title=(
					'\N{MEMO}' * 5
				) + (
					'Message {0.id} was edited too many times in'
					' {0.channel.mention} but they deleted it before I could'
				).format(msg),
				description=msg.content,
				colour=msg.author.colour,
				timestamp=datetime.datetime.now(),
			)
			em.set_author(
				name=msg.author.display_name,
				icon_url=msg.author.avatar_url,
			)
			em.add_field(
				name='Message author',
				value='<@!{id}> ({id})'.format(id=msg.author.id),
			)
		await __main__.client.send_message(schan, embed=em)

		# Also actually reply
		await __main__.client.send_message(
			msg.channel,
			(
				'{0.author.mention}. Were you going to stop editing that message?'
			).format(msg),
		)

def match_input(objtype, request, *, server=None, client=None):
	"""Return a member/server/channel/role/emoji object given an input which could be anything
	that identifies that object. If it can't be found, return None.

	objtype: A string that specifies the type of object to search for. Can be either 'member',
	'server', 'channel', 'role', or 'emoji'.

	request: A string that will be tried to be matched to.

	server (optional): A discord.Server object, which is the scope of where
	members/channels/roles/emojis will be searched. Defaults to None.

	client (optional): A discord.Client object, which is the scope of where servers will be
	searched. Defaults to None.

	The following priority is used:
	1) (Members only) Mention: <@146814960574398464> or <@!146814960574398464>
	2) (Channels only) Mention: <#153368829160849408>
	3) (Roles only) Mention: <@&153369506813706240>
	4) (Emojis only) Emoji: <:unjoy:263889385492185088>
	5) ID: 146814960574398464
	6) (Members only) Username/Username+Discriminator (Discord tag)/Nickname, whatever
	discord.Server.get_member_named() accepts: Info Teddy, Info Teddy#3737, info teddy
	7) Name: tOLP, general, Owner, unjoy
	8) (Members only) Case-insensitive nickname complete match: info teddy
	9) Case-insensitive name complete match: Info Teddy, tolp, owner
	10) (Members only) Case-insensitive nickname partial match: info
	11) Case-insensitive name partial match: Info, tOL, own
	12) (Members only) Discriminator only (either with or without #): 3737
	"""
	acceptvals = ('member', 'server', 'channel', 'role', 'emoji')
	if objtype not in acceptvals:
		raise ValueError('objtype has to be one of ' + str(acceptvals))

	# Is there a Discord server in between us, did we get a client,
	# or is the request anything at all?
	if (not server and objtype != 'server') or \
	(not client and objtype == 'server') or \
	not request:
		return None

	# Is this a mention, or an emoji? If so, extract the ID from it
	if request.startswith('<') and request.endswith('>'):
		if (objtype == 'member' and request[1:3] == '@!') or \
		(objtype == 'role' and request[1:3] == '@&'):
			request = request[3:-1]
		elif (objtype == 'member' and request[1] == '@') or \
		(objtype == 'channel' and request[1] == '#'):
			request = request[2:-1]
		elif objtype == 'emoji' and request[1] == request[-20] == ':':
			request = request[-19:-1]

	# Now get the object from the ID
	tgt = server.get_member(request) if objtype == 'member' else \
	client.get_server(request) if objtype == 'server' else \
	server.get_channel(request) if objtype == 'channel' else \
	discord.utils.find(lambda r: r.id == request, server.roles) if objtype == 'role' else \
	discord.utils.find(lambda e: e.id == request, server.emojis) if objtype == 'emoji' else None

	if not tgt:
		# Not an ID

		if objtype == 'member':
			tgt = server.get_member_named(request) if objtype == 'member' else tgt

			if not tgt:
				# Not found by server.get_member_named()

				# Everything else fails? Then try searching.
				# Nicknames have priority, then usernames.
				# Maybe we're entering just a discriminator, match those as well.
				nickmatched = False
				usermatched = None
				nickfound = None
				userfound = None
				discmatched = None
				for mem in server.members:
					if mem.nick and mem.nick.lower() == request.lower():
						tgt = mem
						nickmatched = True
						break
					if mem.name.lower() == request.lower():
						usermatched = mem
						break
					if mem.nick and \
					mem.nick.lower().find(request.lower()) != -1:
						nickfound = mem
						break
					if mem.name.lower().find(request.lower()) != -1:
						userfound = mem
						break
					if mem.discriminator == request or \
					(request.startswith('#') and \
					mem.discriminator == request[1:]):
						discmatched = mem
						break
				tgt = nickmatched if nickmatched else \
				usermatched if usermatched else \
				nickfound if nickfound else \
				userfound if userfound else \
				discmatched

		else:
			namematched = None
			namefound = None

			searchthru = client.servers if objtype == 'server' else \
			server.channels if objtype == 'channel' else \
			server.roles if objtype == 'role' else \
			server.emojis if objtype == 'emoji' else None
			for i in searchthru:
				if i.name.lower() == request.lower():
					namematched = i
					break
				if i.name.lower().find(request.lower()) != -1:
					namefound = i
					break
			tgt = namematched if namematched else namefound

	return tgt

def parseroleconditional(condstring, caller, target, recursivecall=0):
	"""Parses a role conditional expression and returns its result

	condstring: An expression. Expressions work like this:
	TERM = any | true | false | M.mod | M.admin | M.bot | M.<roleid> | ~TERM | TERM&TERM
	.       | TERM|TERM | (TERM)
	M = c | caller | t | target

	Terms (variations are not limited to this, some obvious things get omitted down the list):
		any             true
		true            true
		false           false
		caller.mod      true if caller is moderator (else false)
		c.mod           identical
		target.mod      true if target is moderator
		t.mod           identical
		caller.admin    true if caller is administrator
		c.admin         identical (you get the idea, c. == caller. and t. == target.)
		target.admin    true if target is administrator
		target.bot      true if target is a bot (and yes, caller.bot also exists)
		caller.12345    true if caller has role with ID 12345
		target.12345    true if target has role with ID 12345
		~TERM           inverts TERM: true if TERM evaluates to false
		.               example: ~c.mod returns true if the caller is not a moderator
		TERMA&TERMB     true if both TERMA and TERMB evaluate to true
		TERMA|TERMB     true if either TERMA or TERMB evaluates to true (or both ofc)
		(TERM)          evaluate what is within brackets first
		.               for example, ~(c.mod|t.mod) first checks whether either the caller
		.               or target is a moderator, and then inverts the result of that.
		.               ~c.mod|t.mod checks whether either the caller is not a mod or the
		.               target IS a mod. Just like (~c.mod)|t.mod if you prefer.

	Examples:                          True if:
		c.mod                      Caller is a mod
		caller.admin&~target.mod   Caller is an admin and target is not a mod
		t.12345                    Target has role with ID 12345
		c.mod&(t.12345|t.24680)    Caller is mod AND target has role 12345 or 24680
		c.mod&false                Never - always false
		any                        Always true
		c.admin&target.bot         Calle is admin and target is bot


	caller: Member object which calls the command

	target: Member object to which the command is applied. May be the same as caller

	(recursivecall: Skip certain steps because of recursive calls - do not use)

	"""
	if recursivecall == 0:
		# Either case is fine, and spaces don't mean anything.
		condstring = condstring.lower().replace(' ', '')

		# First make the brackets more manageable.
		condstring, bracketshighscore = bracketlevels(condstring)

		if bracketshighscore > -1:
			# There are brackets. Handle them from innermost to outermost.
			for level in range(bracketshighscore, -1, -1):
				levelexists = True
				while levelexists:
					# Find the first set of brackets on this level
					m = re.search('\(\<{i}\>(.*?)\)\<{i}\>'.format(i=level),
						condstring
					)

					if m == None:
						levelexists = False
					else:
						# No side effects, so if we say the same thing
						# multiple times, we can replace them all at once!
						# m.group(0) is (<i>XX)<i>, m.group(1) is XX
						condstring = condstring.replace(
							m.group(0), str(parseroleconditional(
								m.group(1),
								caller,
								target,
								1
							)).lower()
						)

	# Now just look at the terms we can solve without any brackets or fancy operators at all!
	if condstring in ('any', 'true'):
		return True
	if condstring == 'false':
		return False
	if recursivecall == 2 and condstring == 'null':
		# This is used for ~, which takes 1 argument, not 2
		return None

	# .mod / .admin / .bot
	m = re.match('^(?P<a>c(aller)?|t(arget)?)\.(?P<b>mod|admin|bot)$', condstring)
	if m != None:
		if m.group('a') in ('c', 'caller'):
			checkmember = caller
		elif m.group('a') in ('t', 'target'):
			checkmember = target
		else:
			raise ValueError((
					'Internal error, member `{}` '
					'unexpectedly passed regex'
				).format(m.group('a'))
			)

		if m.group('b') == 'mod':
			return __main__.is_mod(checkmember)
		if m.group('b') == 'admin':
			return __main__.is_admin(checkmember)
		if m.group('b') == 'bot':
			return __main__.is_bot(checkmember)

		raise ValueError('Internal error, property `{}` unexpectedly passed regex'.format(
				m.group('b')
			)
		)

	# Role ID?
	m = re.match('^c(aller)?\.([0-9]+)$', condstring)
	if m != None:
		for role in caller.roles:
			if role.id == m.group(2):
				return True
		return False
	m = re.match('^t(arget)?\.([0-9]+)$', condstring)
	if m != None:
		for role in target.roles:
			if role.id == m.group(2):
				return True
		return False

	# Only split the expression into terms and operators if we haven't already done so!
	if recursivecall < 2:
		# At this point, we probably have something more exciting, like ~, & or |
		while '~~' in condstring:
			condstring = condstring.replace('~~', '')
		condstring = condstring.replace('~', 'null~')

		# That means we need to check whether this has the correct syntax.
		# Are all characters valid? We're also not expecting any brackets anymore
		m = re.match('.*?([^a-z0-9\.\~\|\&])', condstring)
		if m != None:
			raise ValueError('Syntax error, unrecognized `{}`'.format(
				mdspecialchars(m.group(1))
			)
		)
		# No two operators in a row?
		m = re.match('(.*?)([\~\|\&]{2})', condstring)
		if m != None:
			raise ValueError('Syntax error at `{}`'.format(m.group(2)))
		# No operator at the end of the line?
		m = re.match('(.*?)[\~\|\&]$', condstring)
		if m != None:
			raise ValueError('Syntax error, unexpected end of expression')
		# Nor at the beginning?
		m = re.match('([\~\|\&])', condstring)
		if m != None:
			raise ValueError((
					'Syntax error, unexpected `{}`'
					'at start of expression'
				).format(m.group(1))
			)

		# Okay, time to handle this expression!
		return solveroleconditionalarrays(
			re.split('[\~\|\&]', condstring), # Split by operators: get list of terms
			re.split('[^\~\|\&]+', stripterms(condstring)), # Split by terms: get list
			caller,                                         #             of operators
			target
		)

	# If we're here, it's not that the input consists of multiple terms with operators.
	# I have to conclude that I have no idea what the it's supposed to mean.
	raise ValueError('Unknown term `{}`'.format(condstring))

def stripterms(condstring):
	"""Strips the terms at the beginning and end of a conditional expression.
	"""
	return re.sub('^([^\~\|\&]+)|([^\~\|\&]+)$', '', condstring)

def solveroleconditionalarrays(terms, operators, caller, target):
	"""This function handles role conditional expressions which have operators in them.

	It is passed two lists:

	terms: an array of all the non-operators/terms
	operators: an array of all the operators in between the terms

	Therefore, in case of the expression c.mod&t.mod|t.bot, the following lists are used:

	terms = ["c.mod", "t.mod", "t.bot"]
	operators = ["&", "|"]
	"""
	# First check if the dimensions match
	if len(terms)-1 != len(operators):
		raise ValueError('Unexpected term/operator array dimensions (`{}-1 != {}`)'.format(
				len(terms), len(operators)
			)
		)

	# Now solve all the sub-terms
	terms_evaluated = []
	for term in terms:
		terms_evaluated.append(parseroleconditional(term, caller, target, 2))

	# [ ~ ]
	i = 0
	while True:
		if i >= (len(operators)-1):
			break

		if operators[i] == '~':
			solveroleconditionaloperation(terms_evaluated, operators, i,
				not terms_evaluated[i+1]  # Operation
			)
			i -= 1

		i += 1

	# [ & ]
	i = 0
	while True:
		if i >= (len(operators)-1):
			break

		if operators[i] == '&':
			solveroleconditionaloperation(terms_evaluated, operators, i,
				terms_evaluated[i] and terms_evaluated[i+1]  # Operation
			)
			i -= 1

		i += 1

	# [ | ]
	i = 0
	while True:
		if i >= (len(operators)-1):
			break

		if operators[i] == '|':
			solveroleconditionaloperation(terms_evaluated, operators, i,
				terms_evaluated[i] or terms_evaluated[i+1]  # Operation
			)
			i -= 1

		i += 1

	# If everything went well, we now have an empty operators list, and a terms list with 1 bool
	if len(terms_evaluated) != 1 or len(operators) != 0:
		raise ValueError((
				'Unexpected final term/operator array dimensions: {} {} '
				'(should be 1 0).'
				' op.(0)={}'.format(operators[0]) if len(operators) > 0 else ''
			).format(len(terms_evaluated), len(operators))
		)

	# Everything did go well!
	return terms_evaluated[0]

def solveroleconditionaloperation(terms_evaluated, operators, i, result):
	"""Replaces terms_evaluated[i] by result, and removes terms_evaluated[i+1] and operators[i]

	In other words, this applies the result of
	terms_evaluated[i] operators[i] terms_evaluated[i+1], given the result
	"""
	terms_evaluated[i] = result
	del terms_evaluated[i+1]
	del operators[i]

def bracketlevels(condstring):
	"""Changes input string so that brackets have an indication of what level they are on.

	Changes (a(bc)) to (<0>a(<1>bc)<1>)<0>

	Also returns what the innermost level is, to be used later to determine where to start.
	"""
	bracketslevel = 0
	bracketshighscore = -1
	output = ''

	for c in condstring:
		if c == '(':
			output += '(<{}>'.format(bracketslevel)
			if bracketslevel > bracketshighscore:
				bracketshighscore = bracketslevel
			bracketslevel += 1
		elif c == ')':
			bracketslevel -= 1
			output += ')<{}>'.format(bracketslevel)
		else:
			output += c

	if bracketslevel != 0:
		raise ValueError('Invalid conditional string; mismatched brackets')

	return output, bracketshighscore
