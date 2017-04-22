#!/usr/bin/python3.5
# encoding=utf-8

import re

import __main__
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
			raise UnexpectedExprParserState((
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
		if m == None:
			raise InvalidExpression('Unknown term `{}`'.format(condstring))

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
