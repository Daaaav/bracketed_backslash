#!/usr/bin/python3.5
# encoding=utf-8

import emb
import json
import logging
import re

import checks
import events
import __main__ as main
import utils

class InvalidExpression(Exception):
	"""Exception that's thrown when an expression is invalid.
	"""
	pass

class UnexpectedExprParserState(Exception):
	"""Exception that's thrown when the parser detects an error that should not happen if the
	parser is bug-free. In other words, either a valid or an invalid expression caused the
	parser to be in an unexpected state, and if it was an invalid expression, that error
	should have been caught in another way.
	"""
	pass


commands = {}


def save():
	with open('customcommands.json', 'w') as outfile:
		json.dump(commands, outfile)

def load():
	try:
		with open('customcommands.json', 'r') as infile:
			# This is basically the own module, for some reason everything doesn't work
			__import__(__name__).commands = json.load(infile)
	except FileNotFoundError:
		logging.info('Did not find customcommands file so making a new one')
		save()

def add_custom_command(server, command, dictionary):
	"""Add a custom command. Assumes non-DM, assumes the command doesn't already exist
	(otherwise it'll just be overwritten).
	"""
	if server.id not in commands:
		commands[server.id] = {}
	commands[server.id][command] = dictionary

def remove_custom_command(server, command):
	"""Remove a custom command. Assumes non-DM, assumes the command exists.
	"""
	if server.id not in commands:
		return
	del commands[server.id][command]

def any_commands(server):
	"""Returns True if the server has at least one custom command
	"""
	if server is None:
		return False
	if server.id not in commands:
		return False
	if len(commands[server.id]) == 0:
		return False
	return True

def list_commands(server):
	"""Returns a list of all commands on the server.
	"""
	if not any_commands(server):
		return []
	return commands[server.id]

def list_commands_help(server):
	"""Returns a list of all commands on the server as help entries.
	"""
	cmdlist = list_commands(server)
	cmdlist_help = []
	for cmd in cmdlist:
		cmdlist_help.append(
			{
				'name': cmd,
				'short': 'Custom {} command'.format(cmdlist[cmd]['type']),
				'extra': ''
			}
		)
	return cmdlist_help

def exists(server, command):
	"""Returns True if the given custom command exists on the given server, False if not.
	"""
	if not any_commands(server):
		return False
	if command not in commands[server.id]:
		return False
	return True

async def run(
	server, command, message, arguments, clean_arguments, invokesymbol,
	recursivecall=False, referrers=None
):
	"""Run the given custom command. Assumes that you checked if the command exists, and that
	this isn't in a direct message conversation.
	"""
	if not recursivecall:
		referrers = []

	com = commands[server.id][command]

	if com['type'] == 'role':
		requiredargs = 0
		if com['expiry'] == 'input':
			requiredargs += 1
		elif com['expiry'] != 'no':
			expiryarg = com['expiry']

		# Who gets the role change?
		if com['target'] == 'self':
			targetmember = message.author
		elif com['target'] == 'input':
			requiredargs += 1

		if requiredargs > 0:
			if arguments is None:
				if requiredargs == 2:
					expected = (
						'a relative expiry time and a member '
						'representation as arguments'
					)
				elif com['expiry'] == 'input':
					expected = 'a relative expiry time as an argument'
				else:
					expected = 'a member representation as an argument'
				embed = emb.error((
						'No arguments specified. This command '
						'expects {}.'
					).format(expected)
				)
				await main.reply(message, emb=embed)
				return
			if requiredargs == 2:
				splitargs = arguments.split(' ', 1)
				try:
					expiryarg = splitargs[0]
					memberarg = splitargs[1]
				except IndexError:
					embed = emb.error((
							'Not enough arguments specified. '
							'This command expects both a relative '
							'expiry time and a member representation '
							'as arguments.'
						)
					)
					await main.reply(message, emb=embed)
					return
			elif com['expiry'] == 'input':
				expiryarg = arguments
			else:
				memberarg = arguments

		# Before we change any roles, prepare expiry, just in case it's invalid.
		setexpirytimer = False
		if com['expiry'] != 'no' and expiryarg not in (
			'forever','infinity','inf','none','x','∞','no'
		):
			setexpirytimer = True
			expirytime = main.parsereltime(expiryarg)
			if expirytime is None:
				embed = emb.error((
						'Invalid expiry time. Please input a relative time '
						'in the format `[#d][#h][#m][#s]`, for example: '
						'`7d12h`, `1h`, `1d`, `1d2h3m4s`, `1d20s` or '
						'whatever combination you can think of. The units '
						'have to be in the correct order, though.\n'
						'Roles have not been changed.'
					)
				)
				await main.reply(message, emb=embed)
				return

		if com['target'] == 'input':
			try:
				targetmember = utils.match_input('member', memberarg, server=server)
			except (AttributeError, TypeError):
				embed = emb.error(main.t['specify_user'])
				await main.reply(message, emb=embed)
				return

		# And are we allowed to do this?
		if not parseroleconditional(com['precondition'], message.author, targetmember):
			embed = emb.error((
					'You cannot do that. Maybe you are not allowed to use '
					'this command, or you cannot use it on {}.'
				).format(
					targetmember.mention
				)
			)
			await main.reply(message, emb=embed)
			return

		# Now let's apply the change.
		await main.givetakeroles(
			targetmember, message.server, com['giverole'], com['takerole']
		)

		if len(com['giverole']) > 0 and len(com['takerole']) > 0:
			embed = emb.success((
					'Successfully given {} the role{} {} '
					'and took the role{} {}.'
				).format(
					targetmember.mention,
					's' if len(com['giverole']) > 1 else '',
					main.listroles_id(com['giverole']),
					's' if len(com['takerole']) > 1 else '',
					main.listroles_id(com['takerole'])
				)
			)
		elif len(com['giverole']) > 0:
			embed = emb.success((
					'Successfully given {} the role{} {}.'
				).format(
					targetmember.mention,
					's' if len(com['giverole']) > 1 else '',
					main.listroles_id(com['giverole'])
				)
			)
		elif len(com['takerole']) > 0:
			embed = emb.success((
					'Successfully taken the role{} {} from {}.'
				).format(
					's' if len(com['takerole']) > 1 else '',
					main.listroles_id(com['takerole']),
					targetmember.mention
				)
			)
		else:
			embed = emb.success('Successfully done nothing to {}’s roles.'.format(
					targetmember.mention
				)
			)

		await main.reply(message, emb=embed)

		# Does it expire?
		if setexpirytimer:
			# It does!
			main.addexpiryentry(server.id, targetmember.id, expirytime)
			main.rolexpiresave()
			await main.handleExpiryTimer()

		# Do we want to remember the member for an `\expires`?
		if com['setlatestroled']:
			events.latestroled = targetmember.id

	elif com['type'] == 'alias':
		if command in referrers:
			embed = emb.error((
					'An admin is looking for some amusement... '
					'Maybe it will work with a longer chain?'
				)
			)
			await main.reply(message, emb=embed)
			return
		referrers.append(command)

		if exists(server, com['to']):
			await run(
				server,
				com['to'],
				message,
				arguments,
				clean_arguments,
				invokesymbol,
				True,
				referrers
			)
		else:
			embed = emb.error(
				'This command is an alias of `{}`, which does not exist!'.format(
					com['to']
				)
			)
			await main.reply(message, emb=embed)
	else:
		embed = emb.error('Custom command type `{}` not supported!'.format(com['type']))
		await main.reply(message, emb=embed)

def parseroleconditional(condstring, caller, target, recursivecall=0):
	"""Parses a role conditional expression and returns its result

	condstring: An expression. Expressions work like this:
	TERM = any | true | false | self | M.mod | M.admin | M.bot | M.<roleid> | ~TERM | TERM&TERM
	.       | TERM|TERM | (TERM)
	M = c | caller | t | target

	Terms (variations are not limited to this, some obvious things get omitted down the list):
		any             true
		true            true
		false           false
		self            true if the caller is the same person as the target (else false)
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

	The order of operations is standard boolean logic: (brackets first), then ~, then &, then |.


	caller: Member object which calls the command

	target: Member object to which the command is applied. May be the same as caller, may also
	be None

	(recursivecall: Skip certain steps because of recursive calls - do not use)

	"""
	if recursivecall == 0:
		# Either case is fine, and spaces don't mean anything.
		condstring = condstring.lower().replace(' ', '')

		# First make the brackets more manageable.
		try:
			condstring, bracketshighscore = utils.bracketlevels(condstring)
		except ValueError as e:
			raise InvalidExpression(str(e))

		if bracketshighscore > -1:
			# There are brackets. Handle them from innermost to outermost.
			for level in range(bracketshighscore, -1, -1):
				levelexists = True
				while levelexists:
					# Find the first set of brackets on this level
					m = re.search('\(\<{i}\>(.*?)\)\<{i}\>'.format(i=level),
						condstring
					)

					if m is None:
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
	if condstring == 'self':
		return caller == target
	if recursivecall == 2 and condstring == 'null':
		# This is used for ~, which takes 1 argument, not 2
		return None

	# .mod / .admin / .bot
	m = re.match('^(?P<a>c(aller)?|t(arget)?)\.(?P<b>mod|admin|bot)$', condstring)
	if m != None:
		if m.group('a') in ('c', 'caller'):
			checkmember = caller
		elif m.group('a') in ('t', 'target'):
			if target is None:
				raise InvalidExpression((
						'There is no target member, '
						'but `{}` references one.'
					).format(condstring)
				)
			checkmember = target
		else:
			raise UnexpectedExprParserState((
					'Internal error, member `{}` '
					'unexpectedly passed regex'
				).format(m.group('a'))
			)

		if m.group('b') == 'mod':
			return checks.is_mod(checkmember)
		if m.group('b') == 'admin':
			return checks.is_admin(checkmember)
		if m.group('b') == 'bot':
			return checks.is_bot(checkmember)

		raise UnexpectedExprParserState((
				'Internal error, property `{}` '
				'unexpectedly passed regex'
			).format(m.group('b'))
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
		if target is None:
			raise InvalidExpression((
					'There is no target member, '
					'but `{}` references one.'
				).format(condstring)
			)
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
			raise InvalidExpression('Syntax error, unrecognized `{}`'.format(
				utils.mdspecialchars(m.group(1))
			)
		)
		# No two operators in a row?
		m = re.match('(.*?)([\~\|\&]{2})', condstring)
		if m != None:
			raise InvalidExpression('Syntax error at `{}`'.format(m.group(2)))
		# No operator at the end of the line?
		m = re.match('(.*?)[\~\|\&]$', condstring)
		if m != None:
			raise InvalidExpression('Syntax error, unexpected end of expression')
		# Nor at the beginning?
		m = re.match('([\~\|\&])', condstring)
		if m != None:
			raise InvalidExpression((
					'Syntax error, unexpected `{}` '
					'at start of expression'
				).format(m.group(1))
			)
		# ARE there any operators? We're expecting at least something right now...
		m = re.match('(.*?)([\~\|\&])', condstring)
		if m is None:
			raise InvalidExpression('Unknown term `{}`'.format(
					utils.mdspecialchars(condstring)
				)
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
	raise InvalidExpression('Unknown term `{}`'.format(condstring))

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
		raise UnexpectedExprParserState((
				'Unexpected term/operator array '
				'dimensions (`{}-1 != {}`)'
			).format(len(terms), len(operators))
		)

	# Now solve all the sub-terms
	terms_evaluated = []
	for term in terms:
		terms_evaluated.append(parseroleconditional(term, caller, target, 2))

	# [ ~ ]
	i = 0
	while True:
		if i > (len(operators)-1):
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
		if i > (len(operators)-1):
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
		if i > (len(operators)-1):
			break

		if operators[i] == '|':
			solveroleconditionaloperation(terms_evaluated, operators, i,
				terms_evaluated[i] or terms_evaluated[i+1]  # Operation
			)
			i -= 1

		i += 1

	# If everything went well, we now have an empty operators list, and a terms list with 1 bool
	if len(terms_evaluated) != 1 or len(operators) != 0:
		if len(operators) > 0:
			extratext = ' first el of op is {}'.format(operators[0])
		else:
			extratext = ''
		raise UnexpectedExprParserState((
				'Unexpected final term/operator array dimensions: {} {} '
				'(should be 1 0).' + extratext
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
