# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import emb
import json
import logging
import re
import time
from typing import Optional

import discord

import checks
import commands as commands_py
import events
import bot
import utils
import wrapper

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


def save():
	with open('customcommands.json', 'w') as outfile:
		json.dump(commands, outfile)

def load():
	try:
		with open('customcommands.json', 'r') as infile:
			return {int(k): v for k, v in json.load(infile).items()}
	except FileNotFoundError:
		logging.info('Did not find customcommands file so making a new one')
		save()
		return {}

commands = {}
commands = load()

initialized_slash = False


def add_custom_command(guild, command, dictionary):
	"""Add a custom command. Assumes non-DM, assumes the command doesn't already exist
	(otherwise it'll just be overwritten).
	"""
	if guild.id not in commands:
		commands[guild.id] = {}
	commands[guild.id][command] = dictionary

	commands_py.slashtree.remove_command(command, guild=guild)
	add_slash_command(guild, command, dictionary)

def remove_custom_command(guild, command):
	"""Remove a custom command. Assumes non-DM, assumes the command exists.
	"""
	if guild.id not in commands:
		return
	del commands[guild.id][command]

	commands_py.slashtree.remove_command(command, guild=guild)

def any_commands(guild):
	"""Returns True if the guild has at least one custom command
	"""
	if guild is None:
		return False
	if guild.id not in commands:
		return False
	if len(commands[guild.id]) == 0:
		return False
	return True

def list_commands(guild):
	"""Returns a list of all commands on the guild.
	"""
	if not any_commands(guild):
		return []
	return commands[guild.id]

def list_commands_help(guild):
	"""Returns a list of all commands on the guild as help entries.
	"""
	cmdlist = list_commands(guild)
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

def exists(guild, command):
	"""Returns True if the given custom command exists on the given guild, False if not.
	"""
	if not any_commands(guild):
		return False
	if command not in commands[guild.id]:
		return False
	return True

async def run(
	guild, command, sender, arguments,
	recursivecall=False, referrers=None
):
	"""Run the given custom command. Assumes that you checked if the command exists, and that
	this isn't in a direct message conversation.
	"""
	infinities = ('forever','infinity','inf','none','x','∞','no')

	if not recursivecall:
		referrers = []

	com = commands[guild.id][command]

	if com['type'] == 'role':
		requiredargs = 0

		# How is expiry decided?
		if com['expiry'] == 'input_strict':
			requiredargs += 1
		elif com['expiry'] not in ('no', 'input'):
			expiryarg = com['expiry']

		# Who gets the role change?
		if com['target'] == 'self':
			targetmember = sender
		elif com['target'] == 'input':
			requiredargs += 1

		if requiredargs > 0:
			if arguments is None:
				# This requires arguments, but we've not been given any.
				if requiredargs == 2:
					expected = (
						'a relative expiry time and a member '
						'representation as arguments'
					)
				elif com['expiry'] == 'input_strict':
					expected = 'a relative expiry time as an argument'
				elif com['expiry'] == 'input':
					expected = (
						'optionally a relative expiry time, but must be '
						'given a member representation'
					)
				else:
					expected = 'a member representation as an argument'
				return emb.error((
						'No arguments specified. This command '
						'expects {}.'
					).format(expected)
				)

		if requiredargs == 2:
			# Both a mandatory expiry time as a member representation
			splitargs = arguments.split(' ', 1)
			try:
				expiryarg = splitargs[0]
				memberarg = splitargs[1]
			except IndexError:
				return emb.error((
						'Not enough arguments specified. '
						'This command expects both a relative '
						'expiry time and a member representation '
						'as arguments.'
					)
				)
		elif com['expiry'] == 'input':
			# We may give an expiry time, but we don't have to.
			if requiredargs == 1:
				# The name is required, though!
				splitargs = arguments.split(' ', 1)
				if len(splitargs) == 2:
					# Expiry time was not required, but we have it!
					# ...Unless it's actually part of a name.
					if utils.parsereltime(splitargs[0]) is None and \
					splitargs[0] not in infinities:
						expiryarg = 'x'
						memberarg = arguments
					else:
						expiryarg = splitargs[0]
						memberarg = splitargs[1]
				elif len(splitargs) == 1:
					# This is only one word, so it must be a name.
					expiryarg = 'x'
					memberarg = arguments
				else:
					# Nothing?
					return emb.error((
							'No arguments specified. This '
							'command can optionally be given a '
							'relative expiry time, but expects '
							'a member representation.'
						)
					)
			else:
				# Maybe we have input, maybe we don't!
				if arguments is not None:
					expiryarg = arguments
				else:
					expiryarg = 'x'
		elif com['expiry'] == 'input_strict':
			expiryarg = arguments
		elif requiredargs > 0:
			memberarg = arguments

		# Before we change any roles, prepare expiry, just in case it's invalid.
		setexpirytimer = False
		if com['expiry'] != 'no' and expiryarg not in infinities:
			setexpirytimer = True
			expirytime = utils.parsereltime(expiryarg)
			if expirytime is None:
				return emb.error((
						'Invalid expiry time. Please input a relative time '
						'in the format `[#d][#h][#m][#s]`, for example: '
						'`7d12h`, `1h`, `1d`, `1d2h3m4s`, `1d20s` or '
						'whatever combination you can think of. The units '
						'have to be in the correct order, though.\n'
						'Roles have not been changed.'
					)
				)

		if com['target'] == 'input':
			try:
				targetmember = utils.match_input(guild.members, discord.Member, memberarg)

				# Very quick fix
				if targetmember is None:
					raise AttributeError('Target member is None')
			except (AttributeError, TypeError):
				return emb.error(bot.t['specify_user'])

		# And are we allowed to do this?
		if not parseroleconditional(com['precondition'], sender, targetmember):
			return emb.error((
					'You cannot do that. Maybe you are not allowed to use '
					'this command, or you cannot use it on {}.'
				).format(
					targetmember.mention
				)
			)

		# Now let's apply the change.
		await utils.givetakeroles(
			targetmember, guild, com['giverole'], com['takerole']
		)

		if len(com['giverole']) > 0 and len(com['takerole']) > 0:
			embed = emb.success((
					'Successfully given {} the role{} {} '
					'and took the role{} {}.'
				).format(
					targetmember.mention,
					's' if len(com['giverole']) > 1 else '',
					utils.listroles_id(com['giverole']),
					's' if len(com['takerole']) > 1 else '',
					utils.listroles_id(com['takerole'])
				)
			)
		elif len(com['giverole']) > 0:
			embed = emb.success((
					'Successfully given {} the role{} {}.'
				).format(
					targetmember.mention,
					's' if len(com['giverole']) > 1 else '',
					utils.listroles_id(com['giverole'])
				)
			)
		elif len(com['takerole']) > 0:
			embed = emb.success((
					'Successfully taken the role{} {} from {}.'
				).format(
					's' if len(com['takerole']) > 1 else '',
					utils.listroles_id(com['takerole']),
					targetmember.mention
				)
			)
		else:
			embed = emb.success('Successfully done nothing to {}’s roles.'.format(
					targetmember.mention
				)
			)

		# Does it expire?
		if setexpirytimer:
			# It does!
			utils.addexpiryentry(guild.id, targetmember.id, expirytime)
			utils.rolexpiresave()
			await utils.handleExpiryTimer()

		# Do we want to remember the member for an `\expires`?
		if com['setlatestroled']:
			events.latestroled = targetmember.id

		return embed

	elif com['type'] == 'alias':
		if command in referrers:
			return emb.error((
					'An admin is looking for some amusement... '
					'Maybe it will work with a longer chain?'
				)
			)
		referrers.append(command)

		if exists(guild, com['to']):
			return await run(
				guild,
				com['to'],
				sender,
				arguments,
				True,
				referrers
			)
		else:
			return emb.error(
				'This command is an alias of `{}`, which does not exist!'.format(
					com['to']
				)
			)
	else:
		return emb.error('Custom command type `{}` not supported!'.format(com['type']))

def parseroleconditional(condstring, caller, target, recursivecall=0):
	"""Parses a role conditional expression and returns its result

	condstring: An expression. Expressions work like this:
	TERM = any | true | false | self | M.mod | M.admin | M.bot | M.<roleid>
	.       | M.<AGE><AGEOP><reltime> | ~TERM | TERM&TERM | TERM|TERM | (TERM)
	M = c | caller | t | target
	AGE = aa | js
	AGEOP = < | >

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
		caller.aa>30d	true if caller's account age is at least 30 days
		t.js<2d12h	true if target joined server less than 2 days and 12 hours ago
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
					m = re.search(r'\(\<{i}\>(.*?)\)\<{i}\>'.format(i=level),
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
	m = re.match(r'^(?P<a>c(aller)?|t(arget)?)\.(?P<b>mod|admin|bot)$', condstring)
	if m is not None:
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
	m = re.match(r'^c(aller)?\.([0-9]+)$', condstring)
	if m is not None:
		for role in caller.roles:
			if role.id == int(m.group(2)):
				return True
		return False
	m = re.match(r'^t(arget)?\.([0-9]+)$', condstring)
	if m is not None:
		if target is None:
			raise InvalidExpression((
					'There is no target member, '
					'but `{}` references one.'
				).format(condstring)
			)
		for role in target.roles:
			if role.id == int(m.group(2)):
				return True
		return False

	# New in 2020: time since joining time and account age!
	m = re.match(
		r'^(?P<a>c(aller)?|t(arget)?)\.(?P<check>aa|js)(?P<op><|>)(?P<reltime>[0-9a-z]+)$',
		condstring
	)
	if m is not None:
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

		if m.group('check') == 'aa':
			checktime = checkmember.created_at
		elif m.group('check') == 'js':
			# "In certain cases, this can be None." Okay! Whatever!
			if checkmember.joined_at is None:
				raise InvalidExpression('Server join date cannot be checked!')
			checktime = checkmember.joined_at
		else:
			raise UnexpectedExprParserState((
					'Internal error, member `{}` '
					'unexpectedly passed regex'
				).format(m.group('a'))
			)

		# Convert the time expression to a number of seconds
		barrier_age = utils.parsereltime(m.group('reltime'), True)
		if barrier_age is None:
			raise InvalidExpression('Time expression {} is invalid!'.format(
					m.group('reltime')
				)
			)

		# Also get the actual number of seconds we want to check
		# By the way, <datetime.datetime>.timestamp()
		# is equal to time.mktime(<datetime.datetime>.timetuple())
		candidate_age = time.time() - checktime.timestamp()

		if m.group('op') == '<':
			# Candidate age must be younger than barrier age
			return candidate_age < barrier_age
		elif m.group('op') == '>':
			# Candidate age must be at least barrier age
			return candidate_age >= barrier_age

		raise UnexpectedExprParserState((
				'Internal error, member `{}` '
				'unexpectedly passed regex'
			).format(m.group('a'))
		)

	# Only split the expression into terms and operators if we haven't already done so!
	if recursivecall < 2:
		# At this point, we probably have something more exciting, like ~, & or |
		while '~~' in condstring:
			condstring = condstring.replace('~~', '')
		condstring = condstring.replace('~', 'null~')

		# That means we need to check whether this has the correct syntax.
		# Are all characters valid? We're also not expecting any brackets anymore
		m = re.match(r'.*?([^a-z0-9\.\~\|\&<>])', condstring)
		if m is not None:
			raise InvalidExpression('Syntax error, unrecognized `{}`'.format(
				utils.mdspecialchars(m.group(1))
			)
		)
		# No two operators in a row?
		m = re.match(r'(.*?)([\~\|\&]{2})', condstring)
		if m is not None:
			raise InvalidExpression('Syntax error at `{}`'.format(m.group(2)))
		# No operator at the end of the line?
		m = re.match(r'(.*?)[\~\|\&]$', condstring)
		if m is not None:
			raise InvalidExpression('Syntax error, unexpected end of expression')
		# Nor at the beginning?
		m = re.match(r'([\~\|\&])', condstring)
		if m is not None:
			raise InvalidExpression((
					'Syntax error, unexpected `{}` '
					'at start of expression'
				).format(m.group(1))
			)
		# ARE there any operators? We're expecting at least something right now...
		m = re.match(r'(.*?)([\~\|\&])', condstring)
		if m is None:
			raise InvalidExpression('Unknown term `{}`'.format(
					utils.mdspecialchars(condstring)
				)
			)

		# Okay, time to handle this expression!
		return solveroleconditionalarrays(
			re.split(r'[\~\|\&]', condstring), # Split by operators: get list of terms
			re.split(r'[^\~\|\&]+', stripterms(condstring)), # Split by terms: get list
			caller,                                          #             of operators
			target
		)

	# If we're here, it's not that the input consists of multiple terms with operators.
	# I have to conclude that I have no idea what the it's supposed to mean.
	raise InvalidExpression('Unknown term `{}`'.format(condstring))

def stripterms(condstring):
	"""Strips the terms at the beginning and end of a conditional expression.
	"""
	return re.sub(r'^([^\~\|\&]+)|([^\~\|\&]+)$', '', condstring)

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


def list_role_names(guild, role_ids):
	last = len(role_ids) - 1
	index = 0
	ret = ''
	for rid in role_ids:
		if index > 0:
			if index == last:
				ret += ' and '
			else:
				ret += ', '
		role = guild.get_role(rid)
		if role is None:
			ret += '@?'
		else:
			ret += '@{}'.format(role.name)
		index += 1
	return ret

def upper_first(string):
	if string == '':
		return ''
	return string[0].upper() + string[1:]

def describe(guild, dictionary, prefix):
	# Describe a custom command for help purposes.

	# Special case for the server name:
	# If it ends with something between parentheses, then remove that.
	# It's mostly things like (Merry Christmas!), or long quotes,
	# that make the server name hard to fit in the slash command description limit
	guild_name = guild.name
	if guild_name[-1] == ')':
		left_paren = guild_name.rfind(' (')
		if left_paren != -1:
			guild_name = guild_name[:left_paren]
	guild_prefix = '[{}] '.format(guild_name)

	if dictionary['type'] == 'alias':
		return guild_prefix + 'Alias of {}{}'.format(prefix, dictionary['to'])
	if dictionary['type'] != 'role':
		return guild_prefix + 'Custom server-specific command'

	self = dictionary['target'] == 'self'

	give_action = None
	take_action = None

	if len(dictionary['giverole']) > 0:
		give_action = 'give{} the {} role{}'.format(
			' yourself' if self else '',
			list_role_names(guild, dictionary['giverole']),
			's' if len(dictionary['giverole']) > 1 else '',
		)
	if len(dictionary['takerole']) > 0:
		take_action = 'take{} {} role{}'.format(
			' your' if self else ' the',
			list_role_names(guild, dictionary['takerole']),
			's' if len(dictionary['takerole']) > 1 else ''
		)

	if give_action is not None and take_action is not None:
		return guild_prefix + upper_first(give_action) + ' and ' + take_action
	if give_action is not None:
		return guild_prefix + upper_first(give_action)
	if take_action is not None:
		return guild_prefix + upper_first(take_action)
	return guild_prefix + 'No action configured'


def load_all_slash_commands():
	# Load all slash commands into the tree, done during startup
	global initialized_slash

	if initialized_slash:
		return

	for guild in wrapper.client.guilds:
		for command in list_commands(guild):
			add_slash_command(guild, command, commands[guild.id][command])

	initialized_slash = True

def add_slash_command(guild, command, dictionary):
	"""Adds a slash command variant of this custom command to the tree.

	Assumes syncing is done separately (either by \\addcustomrolecommand,
	or during initial setup, with \\syncslash servers)
	"""
	if dictionary['type'] == 'alias':
		return

	commands_py.slashtree.add_command(
		BBCustomCommand(guild, command, dictionary),
		guild=guild
	)

class BBCustomCommand(discord.app_commands.Command):
	def __init__(self, guild, command, dictionary):
		if dictionary['type'] == 'alias':
			# If we have an alias command, we're in luck!
			# We now have to redirect to the final command in the chain!
			# ... or we FIXME this later, don't make a BBCustomCommand for an alias
			pass

		# There are 6 possible combinations for custom commands:
		# - expiry can be mandatory, optional, or never used
		# - member can be mandatory or never used
		if dictionary['expiry'] == 'input_strict':
			# Expiry is mandatory
			if dictionary['target'] == 'input':
				callback = self.entry_EXPIRY_MEMBER
			else:
				callback = self.entry_EXPIRY
		elif dictionary['expiry'] == 'input':
			# Expiry is optional
			if dictionary['target'] == 'input':
				callback = self.entry_expiry_MEMBER
			else:
				callback = self.entry_expiry
		else:
			# Expiry is never used
			if dictionary['target'] == 'input':
				callback = self.entry_MEMBER
			else:
				callback = self.entry

		super().__init__(
			name = command,
			description = describe(guild, dictionary, '/'),
			callback = callback
		)

	async def entry_EXPIRY_MEMBER(self, interaction:discord.Interaction, expiry:str, member:discord.Member):
		'''Custom role command on this server

		Parameters
		-----------
		expiry: str
			Example: “7d12h”, “1h”, “1d”, “1d2h3m4s”, “1d20s”, or for no expiry: “inf”, “none”, “x”, “no”
		member: discord.Member
			The member to target
		'''
		await self.run_with_legacy_args(interaction, '{} {}'.format(expiry.replace(' ', ''), member.id))

	async def entry_EXPIRY(self, interaction:discord.Interaction, expiry:str):
		'''Custom role command on this server

		Parameters
		-----------
		expiry: str
			Example: “7d12h”, “1h”, “1d”, “1d2h3m4s”, “1d20s”, or for no expiry: “inf”, “none”, “x”, “no”
		'''
		await self.run_with_legacy_args(interaction, expiry.replace(' ', ''))

	async def entry_expiry_MEMBER(self, interaction:discord.Interaction, expiry:Optional[str], member:discord.Member):
		'''Custom role command on this server

		Parameters
		-----------
		expiry: Optional[str]
			Example: “7d12h”, “1h”, “1d”, “1d2h3m4s”, “1d20s”, or for no expiry: “inf”, “none”, “x”, “no”
		member: discord.Member
			The member to target
		'''
		if expiry is not None:
			arguments = '{} {}'.format(expiry.replace(' ', ''), member.id)
		else:
			arguments = '{}'.format(member.id)

		await self.run_with_legacy_args(interaction, arguments)

	async def entry_expiry(self, interaction:discord.Interaction, expiry:Optional[str]):
		'''Custom role command on this server

		Parameters
		-----------
		expiry: Optional[str]
			Example: “7d12h”, “1h”, “1d”, “1d2h3m4s”, “1d20s”, or for no expiry: “inf”, “none”, “x”, “no”
		'''
		arguments = None
		if expiry is not None:
			arguments = expiry.replace(' ', '')

		await self.run_with_legacy_args(interaction, arguments)

	async def entry_MEMBER(self, interaction:discord.Interaction, member:discord.Member):
		'''Custom role command on this server

		Parameters
		-----------
		member: discord.Member
			The member to target
		'''
		await self.run_with_legacy_args(interaction, '{}'.format(member.id))

	async def entry(self, interaction:discord.Interaction):
		'''Custom role command on this server'''
		await self.run_with_legacy_args(interaction, None)

	async def run_with_legacy_args(self, interaction:discord.Interaction, arguments):
		if interaction.command is None:
			embed = emb.error('Command could not be found in tree!')
			await interaction.response.send_message(embed=embed)
			return

		if not exists(interaction.guild, interaction.command.name):
			embed = emb.error('Command does not exist!')
			await interaction.response.send_message(embed=embed)
			return

		try:
			assert isinstance(interaction.user, discord.Member)
			embed = await run(
				interaction.guild, interaction.command.name, interaction.user, arguments
			)
			await interaction.response.send_message(embed=embed)
		except discord.errors.Forbidden:
			embed = emb.error(bot.t['no_permission'])
			await interaction.response.send_message(embed=embed)
			raise
		except Exception:
			embed = emb.error(bot.t['generic_error'])
			await interaction.response.send_message(embed=embed)
			raise
