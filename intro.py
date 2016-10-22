#!/usr/bin/python
# encoding=utf-8

# [\] bot, will be used for tolp server
# this source code should be licensed under gplv3

import discord
import os
import sys
import urllib
import warnings
import random
import re
import time

client = discord.Client() # defines all client.* commands

invoker = '\\' # command invoker
altinvoker = 'ok glass, ' # alt command invoker
hangmaninvoker = '-'

# Hangman stuff
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
hangmanchosenword = ''
hangmanattempts = 0
hangmantotalattempts = 0
hangmanactive = False
hangmanstarter = None
guessedletters = [False]*26
algeraden = False

timeformat = '%Y-%m-%d %H:%M:%S (%Z)'
boottime = time.strftime(timeformat)

token_config = open('bot_token.conf', 'r')

token = token_config.readline(60).split('\n')[0] # read sixty characters also FUCKING NEWLINES

specialchannel = discord.Object(id='234185735266238464')
botschannel = discord.Object(id='201130047736643584')
productionserver = '153368829160849408'
server = client.get_server(productionserver) # defines all server.* commands

t = {
	'op_only': 'Permission denied. This command can only be used by Info Teddy or Dav999.',
	'mod_only': 'Permission denied. This command can only be used by a moderator or administrator.',
	'specify_user': 'Please specify a user ID, a username, a username and discriminator, or a nickname.',
	'accepts_user': 'Accepts as an argument a user ID, nickname, username, discriminator, or username and discriminator.',
	'production_only': 'Production server only!',
	'noprivate': 'This command cannot be run inside a private conversation! You can probably guess why.',
	'its_meme': 'It’s a meme command.',
}

cmds = [
	{
		'cat_name': 'General Commands',
		'commands': {
			'help': {
				'short': 'Lists commands and their descriptions.',
				'extra': 'Any arguments passed to `\help` will make `\help` try to look up more in-depth description of the command.'
			},
			'source': {
				'short': 'Gives the link to the source code to the bot.',
				'extra': 'It’s hosted on __https://gitgud.io/__.'
			},
			'echo': {
				'short': 'Echoes your input.',
				'extra': 'Now, you could say that the bot echoed your input already, but it’s still better to have a dedicated echo command.'
			},
			'info': {
				'short': 'Unfinished command to get information about a user.',
				'extra': ''
			},
			'findu': {
				'short': 'Find a user by (part of) their nickname/username case-insensitively, or their discriminator, or whatever.',
				'extrafull': 'Find a user by (part of) their nickname/username case-insensitively, or their discriminator, or whatever. Shows ID, nickname, username, and discriminator.'
			},
			'findup': {
				'short': 'Same as `\\findu`, but also pings the user.',
				'extrafull': 'Find a user by (part of) their nickname/username case-insensitively, or their discriminator, or whatever. Shows ID, nickname, username, and discriminator. Warning: This pings the user.'
			},
			'hangman': {
				'short': 'Initiate a game of hangman (use \stophangman to stop). Send via PM with a custom word.',
				'extra': 'Ported from DavBot!'
			},
			'stophangman': {
				'short': 'Stop the current game of hangman.',
				'extra': 'Can only be done by the one who started the game or a moderator.'
			},
		}
	},
	{
		'cat_name': 'Bot Commands',
		'commands': {
			'botok': {
				'short': 'Pings the bot.',
				'extra': 'If the bot is okay, the bot will respond with “Bot is okay”.'
			},
			'uptime': {
				'short': 'Prints the time the bot was booted.',
				'extra': 'Doesn’t yet give the amount of time between the boot and now, but does give those timestamps.'
			},
			'restart': {
				'short': 'Restarts the bot.',
				'extra': ''
			},
			'kill': {
				'short': 'Kills the bot. This method does not kill it cleanly.',
				'extra': ''
			},
		}
	},
	{
		'cat_name': 'Moderation Commands',
		'commands': {
			'softban': {
				'short': 'Gives a user the `Banned` role.',
				'extra': t['accepts_user']
			},
			'nononly': {
				'short': 'Gives a user the `Nonsense-Only` role.',
				'extra': t['accepts_user']
			},
			'nogenmen': {
				'short': 'Gives a user the `No General Mentions` role.',
				'extra': t['accepts_user']
			},
			'nocedule': {
				'short': 'Gives a user the `No CE/DU/LE` role.',
				'extra': t['accepts_user']
			},
			'notts': {
				'short': 'Gives a user the `No TTS` role.',
				'extra': t['accepts_user']
			},
			'nonick': {
				'short': 'Removes from a user the `tOLPer` role, and gives them the `tOLPer who can’t change nickname` role.',
				'extra': t['accepts_user']
			},
			'rolerst': {
				'short': 'Resets the roles for a user back to the normal state.',
				'extra': 'Removes all restrictive roles from a user, and gives back the `tOLPer` role if necessary.\n' + t['accepts_user']
			},
		}
	},
]

meme_cmds = [
	{
		'cat_name': 'Meme Commands',
		'commands': {
			'': {
				'short': 'Mentions you.',
				'extra': 'Don’t type this command in if you don’t want to be mentioned.'
			},
			'teddy': {
				'short': 'The obvious counterpart to `\info`.',
				'extra': t['its_meme']
			},
			'samar': {
				'short': 'The true name.',
				'extra': t['its_meme']
			},
			'lui': {
				'short': 'Obligatory “pretty cool guy” meme.',
				'extra': t['its_meme']
			},
			'shiny': {
				'short': 'He’s a shiny trinket.',
				'extra': t['its_meme']
			},
			'tainy': {
				'short': 'Unobtaining is his name.',
				'extra': t['its_meme']
			},
			'kys': {
				'short': 'Will the bot listen?',
				'extra': t['its_meme']
			},
			'*formatting*': {
				'short': 'This is an example of italicized formatting.',
				'extra': t['its_meme']
			},
			'/r/undertale': {
				'short': 'This is going to give my bot cancer.',
				'extra': t['its_meme']
			},
		}
	}
]

@client.async_event
def on_ready():
	print('[info] logged in as {} with id {}'.format(client.user.name, client.user.id))
	yield from client.change_presence(game=discord.Game(name='​')) # the game name is u+200b

@client.async_event
def on_message(message):
	global msg_start, hangmanchosenword, hangmanattempts, hangmantotalattempts, hangmanactive, hangmanstarter, guessedletters, algeraden

	if message.author == client.user: # is the message sent by the bot
		return # do nothing

	isprivate = isprivatemessage(message.server) # cant use isprivatemessage = isprivatemessage(), otherwise python will think "holy fuck a variable was referenced before assignment"

	if not isprivate and str(message.author.status) == 'offline':
		msg_start = '**`>`**:ghost:`user` {}`#{}` `({}) was invisible when sending message {} in channel` <#{}> `at {} UTC`'.format(message.author.name, message.author.discriminator, message.author.id, message.id, message.channel.id, message.timestamp)
		if message.server.id != productionserver:
			yield from client.send_message(message.channel, msg_start)
		else:
			yield from client.send_message(specialchannel, msg_start)
		pass

	if message.attachments != []:
		msg_start = '**`>`**:paperclip:`user` {}`#{}` `({}) attached a file to message {} in channel` <#{}> `at {} UTC`\n'.format(message.author.name, message.author.discriminator, message.author.id, message.id, message.channel.id, message.timestamp)
		content = '_`The attachment is:`_\n' + message.attachments[0]['url']
		msg = msg_start + content
		if message.server.id != productionserver:
			yield from client.send_message(message.channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)

	if message.content.startswith(invoker): # does the message start with command invoker
		altinvokeractive = False
		hangmaninvokeractive = False
		pass # continue, go on
	elif message.content.startswith(altinvoker): # does the message start with alt invoker
		altinvokeractive = True
		hangmaninvokeractive = False
		pass
	elif message.content.startswith(hangmaninvoker):
		hangmaninvokeractive = True
		pass
	else:
		return
	if hangmaninvokeractive:
		if not hangmanactive:
			return
		msg_start = '**`>`**{}**`:`** {}\n'.format(message.author.name, message.content)
		if isprivate:
			content = 'Sorry, guesses are not accepted via PM!'
			msg = msg_start + content
			yield from client.send_message(message.channel, msg)
		if message.channel.id != '201130047736643584':
			return
		hangmanguessed = message.content[1:]

		if len(hangmanguessed) == 1:
			# Have we already used that letter? And is it a valid letter?
			if alphabet.find(hangmanguessed.upper()) == -1:
				msg = msg_start + content
				content = 'The letter **{}** is invalid.'.format(hangmanguessed.upper())
				yield from client.send_message(message.channel, msg)
				return
			if guessedletters[alphabet.find(hangmanguessed.upper())]:
				content = 'The letter **{}** has already been used.'.format(hangmanguessed.upper())
				msg = msg_start + content
				yield from client.send_message(message.channel, msg)
				return
			# Ok, so does this letter occur in the word?
			if hangmanchosenword.upper().find(hangmanguessed.upper()) != -1:
				# Set the guessed letter correctly
				guessedletters[alphabet.find(hangmanguessed.upper())] = True

				content = '**{}** is correct!\n{}'.format(hangmanguessed.upper(), hangmanworddisp(hangmanchosenword))
				msg = msg_start + content
				yield from client.send_message(message.channel, msg)

				if algeraden:
					hangmanactive = False
					content = 'You guessed the word correctly! You made {} mistakes in total.'.format(hangmantotalattempts-hangmanattempts)
					msg = msg_start + content
					yield from client.send_message(message.channel, msg)
			else:
				# Set the guessed letter correctly, and it has to be a letter
				guessedletters[alphabet.find(hangmanguessed.upper())] = True
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					content = '**{}** is incorrect! Game over. The word was: **{}**'.format(hangmanguessed.upper(), hangmanchosenword)
					msg = msg_start + content
					yield from client.send_message(message.channel, msg)
				else:
					content = '**{}** is incorrect! {} attempts left.\n{}'.format(hangmanguessed.upper(), hangmanattempts, hangmanworddisp(hangmanchosenword))
					msg = msg_start + content
					yield from client.send_message(message.channel, msg)
		else:
			# We're guessing the entire word. Well, is it the word?
			if hangmanguessed.lower() == hangmanchosenword.lower():
				hangmanactive = False
				content = 'You guessed the word ({}) correctly! You made {} mistakes in total.'.format(hangmanchosenword, hangmantotalattempts-hangmanattempts)
				msg = msg_start + content
				yield from client.send_message(message.channel, msg)
			elif len(hangmanguessed) != len(hangmanchosenword):
				# We're not even trying. It's not the same length.
				content = '**{}** isn\'t even the same length as the correct word. Please try again.'.format(hangmanguessed)
				msg = msg_start + content
				yield from client.send_message(message.channel, msg)
			else:
				hangmanattempts -= 1

				if hangmanattempts == 0:
					hangmanactive = False
					msg = msg_start + content
					content = '**{}** is not the word! Game over. The word was: **{}**'.format(hangmanguessed, hangmanchosenword)
					yield from client.send_message(message.channel, msg)
				else:
					content = '**{}** is not the word! {} attempts left.\n{}'.format(hangmanguessed, hangmanattempts, hangmanworddisp(hangmanchosenword))
					msg = msg_start + content
					yield from client.send_message(message.channel, msg)

		return

	elif altinvokeractive:
		command = message.content.split(altinvoker, 1)[1]
		msg_start = '**`>`**{}**`:`** {}\n'.format(message.author.name, message.content) # shows what the user put in, without main invoker
	else:
		command = message.content.split(invoker, 1)[1] # removes invoker from the message
		msg_start = '**`>`**{}**`:`** \\{}\n'.format(message.author.name, message.content) # shows what the user put in

	if not isprivate and not is_mod(message.author) and message.channel.id != '201130047736643584' and message.server.id == productionserver:
		return
	try:
		arguments = command.split (' ', 1)[1]
	except IndexError:
		arguments = None
	command = command.split (' ', 1)[0]
	if command == 'help':
		content = '`[\]` is a bot written by Info Teddy and Dav999 in Python utilizing `discord.py`, for use on the tOLP Discord server.' + helplist(cmds)

		# General
		if arguments == 'useless':
			content = '`useless` – You found a secret, congratulations. The command to get this help message will change sometimes.' + helplist(meme_cmds)
		elif arguments == None:
			pass
		else:
			matched = False
			for i in range(0,2):
				for cat in (cmds if i == 0 else meme_cmds): # Good enough replacement to union
					for cmd in cat['commands']: # Maybe have a nested try-except KeyError instead of looping through every command
						if arguments == cmd:
							try:
								content = '`\{}` – {}'.format(cmd, cat['commands'][cmd]['extrafull'])
							except KeyError:
								content = '`\{}` – {}\n{}'.format(cmd, cat['commands'][cmd]['short'], cat['commands'][cmd]['extra'])
							matched = True
							break
					if matched:
						break

			if not matched:
				content = 'Invalid arguments passed. Input `\help` for a list of valid commands to pass as arguments.'
		yield from reply(message, content)
	elif command == 'restart':
		if message.author.id != '146814960574398464' and message.author.id != '159793749604433921':
			content = t['op_only']
			print ('[info] bot restart tried to be called by {}#{} (uuid {}) at {} utc but failed'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		content = 'Restarting.'
		print('[info] bot restart called by {}#{} (uuid {}) at {} utc'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		yield from reply(message, content)
		yield from os.execl(__file__, '')
	elif command == 'kill':
		if message.author.id != '146814960574398464' and message.author.id != '159793749604433921':
			content = t['op_only']
			print('[info] bot kill tried to be called by {}#{} (uuid {}) at {} utc but failed'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		content = 'Killing.'
		print('[info] bot kill called by {}#{} (uuid {}) at {} utc'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		yield from reply(message, content)
		yield from sys.exit()
	elif command == 'echo':
		if arguments == None:
			arguments = ''
		yield from reply(message, arguments)
	elif command == '':
		content = '''<@{}>
```fix
Luigi: have you ever by accident pressed another key at the same time you have pressed enter?'
Luigi: ugh
ShinyWolf07: \\
ShinyWolf07: this
Luigi: is
Luigi: cancer
ShinyWolf07: I always do th
ShinyWolf07: its so annoyng
ShinyWolf07: \\
ShinyWolf07: UGh\\
Luigi: xd
Luigi: x
Luigi: d
Luigi: d
ShinyWolf07: xd\\
Luigi: x
ShinyWolf07: F***!!!!!|
Luigi: XD
ShinyWolf07: ARGH\\
Luigi: This is funny to watch you
Luigi: Did you make popcorn
ShinyWolf07: xd ikr \\
ShinyWolf07: ...
ShinyWolf07: -_-\\
ShinyWolf07: GAH\\
Luigi: don't you mean ...\\
ShinyWolf07: ...
ShinyWolf07: sigh
Luigi: 10/10 would watch again```'''.format(message.author.id)
		yield from reply(message, content)
	elif command == 'hangman':
		if hangmanactive:
			content = 'ERROR: Hangman is already running. It can be aborted by the starter or by a mod with \stophangman.'
			yield from reply(message, content)
			return
		if not isprivatemessage(message.server):
			content = 'For now, this can only be run via DM.'
			yield from reply(message, content)
			return
		if arguments == None:
			content = 'Please specify a word.'
			yield from reply(message, content)
			return
		if not arguments.isalpha():
			content = 'ERROR: Words can only consist of letters A-Z'
			yield from reply(message, content)
			return
		if len(arguments) > 50:
			content = 'ERROR: Sorry, but your word is too long. It can be 50 characters max.'
			yield from reply(message, content)
			return

		hangmanchosenword = arguments
		hangmanattempts = 10
		hangmantotalattempts = 10
		hangmanactive = True
		hangmanstarter = message.author
		guessedletters = [False]*26

		content = 'New game of hangman initiated by <@{}> with a custom word. Guess letters by chatting "{}" followed by the letter (for example {}a) or the word. {} attempts left.\n{}'.format(hangmanstarter.id, hangmaninvoker, hangmaninvoker, hangmanattempts, hangmanworddisp(hangmanchosenword))
		yield from client.send_message(botschannel, content)
	elif command == 'stophangman':
		if not hangmanactive:
			content = 'ERROR: Can\'t abort hangman because it\'s not running.'
			yield from reply(message, content)
			return
		elif not is_mod(message.author) and message.author.id != hangmanstarter.id:
			content = 'ERROR: Can\'t abort hangman because you haven\'t started this game.'
			yield from reply(message, content)
			return

		hangmanactive = False
		content = 'Game of hangman aborted. The word was: **{}**'.format(hangmanchosenword)
		yield from client.send_message(botschannel, content)
	elif command == 'source':
		content = 'Source code to the bot: __https://gitgud.io/infoteddy/bracketed_backslash__'
		yield from reply(message, content)
	elif command == 'findu' or command == 'findup':
		targetmember = get_member_input(message.server, arguments)
		if targetmember == None:
			content = 'Unable to find that member. ' + t['specify_user']
			yield from reply(message, content)
			return
		if targetmember.nick == None:
			displaynick = '**`No Nickname`**'
		else:
			displaynick = '**`Nickname:`** ``​{}​``'.format(mdspecialchars(targetmember.nick))
		if targetmember.game == None:
			memberhasgame = False
			displaygame = '**`Not Playing`**'
			displaygameurl = '**`No Stream Link`**'
			pass
		else:
			memberhasgame = True
		if memberhasgame:
			if targetmember.game.type == 0 or targetmember.game.type == None:
				displaygame = '**`Playing:`** ' + targetmember.game.name
			if targetmember.game.type == 1:
				displaygame = '**`Streaming:`** ' + targetmember.game.name
			if targetmember.game.url == None:
				displaygameurl = '**`No Stream Link`**'
			else:
				displaygameurl = '**`Stream Link:`** <{}>'.format(targetmember.game.url) # the angled brackets are to make discord not preview the link
		if command == "findup":
			displaymatch = '<@{}>'.format(targetmember.id)
		else:
			displaymatch = '__@{}__'.format(targetmember.display_name)
		if str(targetmember.status) == 'online':
			statuss = 'online:232230526331650058'
		elif str(targetmember.status) == 'offline' or str(targetmember.status) == 'invisible':
			statuss = 'invisible:232230525711024129'
		elif str(targetmember.status) == 'idle':
			statuss = 'idle:232230526067408896'
		elif str(targetmember.status) == 'dnd' or str(targetmember.status) == 'do_not_disturb':
			statuss = 'dnd:232230526109351938'

		content = 'Matched {} <:{}>\n**`User ID:`** `{}`\n{}\n**`Username:`** {}\n**`Discriminator:`** `#{}`\n{}\n{}'.format(displaymatch, statuss, targetmember.id, displaynick, targetmember.name, targetmember.discriminator, displaygame, displaygameurl)
		yield from reply(message, content)
	elif command == 'softban':
		if not is_mod(message.author):
			content = t['mod_only']
			print('[info] softban attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			yield from reply(message, content)
			return

		try:
			targetmember = get_member_input(message.server, arguments)
			yield from client.remove_roles(targetmember,
				discord.utils.get(message.server.roles, id='173240966575161344'), # nonsense-only
				discord.utils.get(message.server.roles, id='216647716531339264'), # no general mentions
				discord.utils.get(message.server.roles, id='222046096216686592'), # no cedule
				discord.utils.get(message.server.roles, id='215954720555139073'), # no tts
			)
			yield from client.add_roles(targetmember, discord.utils.get(message.server.roles, id='220643748508467220')) # The banned role
		except(AttributeError,TypeError):
			content = t['specify_user']
			yield from reply(message, content)
			return

		content = ':no_entry: <@{}> has been softbanned.'.format(targetmember.id)
		yield from reply(message, content)
	elif command == 'nononly' or command == 'nogenmen' or command == 'nocedule' or command == 'notts':
		if not is_mod(message.author):
			content = t['mod_only']
			print('[info] {} attempted by {}#{} (uuid {}) at {} utc but failed'.format(command, message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			yield from reply(message, content)
			return
		roletoadd = {
			'nononly': '173240966575161344',
			'nogenmen': '216647716531339264',
			'nocedule': '222046096216686592',
			'notts': '215954720555139073'
		}
		rolelabel = {
			'nononly': 'Nonsense-Only',
			'nogenmen': 'No General Mentions',
			'nocedule': 'No Custom Emotes/Direct Uploads/Link Embeds',
			'notts': 'No TTS'
		}
		try:
			targetmember = get_member_input(message.server, arguments)
			yield from client.add_roles(targetmember, discord.utils.get(message.server.roles, id=roletoadd[command]))
		except(AttributeError,TypeError):
			content = t['specify_user']
			yield from reply(message, content)
			return
		content = 'Gave <@{}> the {} role.'.format(targetmember.id, rolelabel[command])
		yield from reply(message, content)
	elif command == 'nonick':
		if not is_mod(message.author):
			content = t['mod_only']
			print('[info] nonick attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			yield from reply(message, content)
			return
		try:
			targetmember = get_member_input(message.server, arguments)
			yield from client.add_roles(targetmember, discord.utils.get(message.server.roles, id='236925451216355338'))
			yield from client.remove_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
		except(AttributeError,TypeError):
			content = t['specify_user']
			yield from reply(message, content)
			return
		content = 'Gave <@{}> the tOLPer who can’t change nickname role, and removed the tOLPer role from them.'.format(targetmember.id)
		yield from reply(message, content)
		return
	elif command == 'rolerst':
		if not is_mod(message.author):
			content = t['mod_only']
			print('[info] rolerst attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = t['production_only']
			yield from reply(message, content)
			return

		try:
			targetmember = get_member_input(message.server, arguments)
			yield from client.remove_roles(targetmember,
				discord.utils.get(message.server.roles, id='173240966575161344'), # nonsense-only
				discord.utils.get(message.server.roles, id='216647716531339264'), # no general mentions
				discord.utils.get(message.server.roles, id='222046096216686592'), # no cedule
				discord.utils.get(message.server.roles, id='215954720555139073'), # no tts
				discord.utils.get(message.server.roles, id='220643748508467220'), # banned
				discord.utils.get(message.server.roles, id='236925451216355338'), # tolper who cant change nickname
			)
			if not is_bot(targetmember):
				yield from client.add_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
		except(AttributeError,TypeError):
			content = t['specify_user']
			yield from reply(message, content)
			return
		content = 'Reset roles for <@{}> back to normal.'.format(targetmember.id)
		yield from reply(message, content)
	elif command == 'info':
		content = str(message.author.permissions_in(message.channel))
		perms = discord.Channel.permissions_for(message.channel, message.author)
		if perms.administrator:
			content = 'is admin???//'
		else:
			content = 'is not admin???//'
		yield from reply(message, content)
	elif command == 'teddy':
		content = 'xd'
		yield from reply(message, content)
	elif command == 'samar':
		content = 'Why does he like Undertale?'
		yield from reply(message, content)
	elif command == 'lui':
		content = 'i think /r/undertale is a pretty cool guy, eh deletes messages and doesnt afraid of lying'
		yield from reply(message, content)
	elif command == 'shiny':
		content = 'moar liek shittykitty amirite'
		yield from reply(message, content)
	elif command == 'tainy':
		rngint = random.randint(0,1)
		if rngint == 0:
			content = 'moar liek stainy amirite'
		else:
			content = 'moar like painy amirite'
		yield from reply(message, content)
	elif command == 'kys':
		content = 'nah'
		yield from reply(message, content)
	elif command == 'botok':
		content = 'Bot is okay.'
		yield from reply(message, content)
	elif command == 'uptime':
		content = 'Boot time:       `{}`\nCurrent time: `{}`'.format(boottime, time.strftime(timeformat))
		yield from reply(message, content)
	elif command == '*formatting*':
		content = 'That’s italicized formatting.'
		yield from reply(message, content)
	elif command == '/r/undertale':
		content = 'They banned someone for posting an honest review of Undertale. Seriously, don’t go there if you don’t want to be censored.'
		yield from reply(message, content)
	else:
		if altinvokeractive:
			return # do not print error message if command is invalid
		else:
			content = 'Invalid command. Input `\help` for a list of valid commands.'
			yield from reply(message, content)

@client.async_event
def on_message_delete(message): # when a message gets deleted
	if message.author == client.user: # is the deleted message originally sent by the bot
		print('bot message {} by user {}#{} ({}) in channel {} ({}) at {} utc deleted, original content is \n{}'.format(message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.channel.name, message.timestamp, message.content))
		return
	if message.content == '' and message.attachments == []:
		return
	msg_start = '**`>`**:no_entry_sign:`message {} by user` {}`#{}` `({}) in channel` <#{}> `at {} UTC deleted`\n'.format(message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.timestamp)
	content = '_`The original content is:`_\n' + message.content
	msg = msg_start + content
	if len(msg) >= 2000:
		content = '_`The original content is (part 1):`_\n' + message.content
		msg = msg_start + content
		msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		if len(msg_split [0]) >= 2000:
			msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		content1 = msg_split[0]
		content2 = '_`The original content is (part 2):`_\n' + msg_split[1]
		msg1 = content1
		msg2 = msg_start + content2
		if message.server.id != productionserver:
			yield from client.send_message(message.channel, msg1)
			yield from client.send_message(message.channel, msg2)
		else:
			yield from client.send_message(specialchannel, msg1)
			yield from client.send_message(specialchannel, msg2)
	else:
		if message.server.id != productionserver:
			yield from client.send_message(message.channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
	if message.attachments != []:
		content = '_`The original attachment is:`_\n' + str(message.attachments)
		msg = msg_start + content
		if message.server.id != productionserver:
			yield from client.send_message(message.channel, msg)
		else:
			yield from client.send_message(specialchannel)

@client.async_event
def on_message_edit(before, after): # when a message gets edited
	# preliminary checkings
	if before.content == after.content:
		return # must be the message being pinned and/or embed(s) displaying
	if before.author == client.user or after.author == client.user: # the bot doesnt edits its own messages, so throw a warning
		warnings.warn('this is the bots own message and the bot doesnt edit messages\nid of before: {}\nid of after: {}'.format (before.id, after.id))
		return
	# checks succeeded
	msg_start = '**`>`**:pencil:`message {} by user` {}`#{}` `({}) in channel` <#{}> `at {} UTC edited`\n'.format(before.id, before.author.name, before.author.discriminator, before.author.id, before.channel.id, before.timestamp)
	content = '_`The older content is:`_\n' + before.content
	msg = msg_start + content
	if len(msg) >= 2000:
		content = '_`The older content is (part 1):`_\n' + before.content
		msg = msg_start + content
		msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		if len(msg_split [0]) >= 2000:
			msg_split = [msg[i:i+2000] for i in range (0, len(msg), 2000)]
		content1 = msg_split[0]
		content2 = '_`The older content is (part 2):`_\n' + msg_split[1]
		msg1 = content1
		msg2 = msg_start + content2
		if before.server.id != productionserver:
			yield from client.send_message(before.channel, msg1)
			yield from client.send_message(before.channel, msg2)
		else:
			yield from client.send_message(specialchannel, msg1)
			yield from client.send_message(specialchannel, msg2)
	else:
		if before.server.id != productionserver:
			yield from client.send_message(before.channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
	msg_start = '**`>`**`message {} by user` {}`#{}` `({}) in channel` <#{}> `at {} UTC edited`\n'.format(after.id, after.author.name, after.author.discriminator, after.author.id, after.channel.id, after.timestamp)
	content = '_`The newer content is:`_\n' + after.content
	msg = msg_start + content
	if len(msg) >= 2000:
		content = '_`The newer content is (part 1):`_\n' + after.content
		msg = msg_start + content
		msg_split = [msg[i:i+2000] for i in range(0, len(msg), 2000)]
		if len(msg_split[0]) >= 2000:
			msg_split = [msg[i:i+2000] for i in range (0, len(msg), 2000)]
		content1 = msg_split [0]
		content2 = '_`The newer content is (part 2):`_\n' + msg_split[1]
		msg1 = content1
		msg2 = msg_start + content2
		if after.server.id != productionserver:
			yield from client.send_message(after.channel, msg1)
			yield from client.send_message(after.channel, msg2)
		else:
			yield from client.send_message(specialchannel, msg1)
			yield from client.send_message(specialchannel, msg2)
	else:
		if after.server.id != productionserver:
			yield from client.send_message(after.channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)

@client.async_event
def on_member_update(before, after):
	if before.nick != after.nick:
		msg_start = '**`>`**:regional_indicator_n::pager:`user` {}`#{}` `({}) changed nickname`\n'.format(before.name, before.discriminator, before.id)
		if before.nick == None:
			content = '_`The older nickname is:`_ `(none)`'
		else:
			content = '_`The older nickname is:`_\n' + before.nick
		msg = msg_start + content
		if before.server.id != productionserver:
			yield from client.send_message(before.server.default_channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
		msg_start = '**`>`**`user` {}`#{}` `({}) changed nickname`\n'.format(after.name, after.discriminator, after.id)
		if after.nick == None:
			content = '_`The newer nickname is:`_ `(none)`'
		else:
			content = '_`The newer nickname is:`_\n' + after.nick
		msg = msg_start + content
		if after.server.id != productionserver:
			yield from client.send_message(after.server.default_channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
	if before.roles != after.roles:
		if len(before.roles) > len(after.roles): # if a role has been removed
			roleremoved = list(set(before.roles).symmetric_difference(set(after.roles)))[0]
			msg_start = '**`>`**`user` {}`#{}` `({}) has role {} ({}) removed`'.format(before.name, before.discriminator, before.id, roleremoved.name, roleremoved.id)
			if before.server.id != productionserver:
				yield from client.send_message(before.server.default_channel, msg_start)
			else:
				yield from client.send_message(specialchannel, msg_start)
		if len(before.roles) < len(after.roles): # if a role has been added
			roleadded = list(set(after.roles).symmetric_difference(set(before.roles)))[0]
			msg_start = '**`>`**`user` {}`#{}` `({}) has role {} ({}) added`'.format(after.name, after.discriminator, after.id, roleadded.name, roleadded.id)
			if after.server.id != productionserver:
				yield from client.send_message(after.server.default_channel, msg_start)
			else:
				yield from client.send_message(specialchannel, msg_start)
	if before.name != after.name:
		msg_start = '**`>`**:regional_indicator_u::pager:`user {} changed username`\n'.format(before.id)
		content = '_`The older username is:`_\n{}\n_`The older discriminator is:`_ `#{}`'.format(before.name, before.discriminator)
		msg = msg_start + content
		if before.server.id != productionserver:
			yield from client.send_message(before.server.default_channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
		msg_start = '**`>`**`user {} changed username`\n'.format(after.nick, after.id)
		content = '_`The newer username is:`_\n{}\n_`The newer discriminator is:`_ `#{}`'.format(after.name, after.discriminator)
		msg = msg_start + content
		if after.server.id != productionserver:
			yield from client.send_message(after.server.default_channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
	if before.avatar_url != after.avatar_url:
		msg_start = '**`>`**`user` {}`#{}` `({}) changed avatar`'.format(before.name, before.discriminator, before.id)
		content = '_`The older avatar URL is:`_ ' + before.avatar_url
		msg = msg_start + content
		if before.server.id != productionserver:
			yield from client.send_message(before.server.default_channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
		msg_start = '**`>`**`user` {}`#{}` `changed avatar`'.format(after.name, after.discriminator, after.id)
		content = '_`The newer avatar URL is:`_ ' + after.avatar_url
		msg = msg_start + content
		if after.server.id != productionserver:
			yield from client.send_message(after.server.default_channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)

@client.async_event
def on_member_join(member):
	msg = '**`>`**:arrow_right:`user` {}`#{}` `({}) joined server {} ({})`'.format(member.name, member.discriminator, member.id, member.server.name, member.server.id)
	if member.server.id != productionserver:
		yield from client.send_message(member.server.default_channel, msg)
	else:
		yield from client.send_message(specialchannel, msg)
		if is_bot(member):
			yield from client.add_roles(member, discord.utils.get(member.server.roles, id='201129507967598592')) # bot role
			return
		# TODO: Look up that member in our database, to see if this user should get a restrictive group again.
		# If someone is just a tOLPer, they won't be in the database.
		if False:
			# They're found in the database! Give them the groups they should have
			pass
		else:
			# Not found, so they're just a tOLPer.
			yield from client.add_roles(member, discord.utils.get(member.server.roles, id='231644869351833600')) # The tOLPer role

@client.async_event
def on_member_remove(member):
	msg = '**`>`**:door:`user` {}`#{}` `({}) removed from server {} ({})`'.format (member.name, member.discriminator, member.id, member.server.name, member.server.id)
	if member.server.id != productionserver:
		yield from client.send_message(member.server.default_channel, msg)
	else:
		yield from client.send_message(specialchannel, msg)

@client.async_event
def on_typing(channel, user, when):
	if str(user.status) == 'offline':
		msg = '**`>`**:ghost:`user` {}`#{}` `({}) was invisible while typing in channel` <#{}> `at {}`'.format(user.name, user.discriminator, user.id, channel.id, when)
		if user.server.id != productionserver:
			yield from client.send_message(channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
	else:
		return # practically unnecessary, but this is for if we want to do things when members type later

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
def reply(messageobject, message):
	# Removes the need for adding msg_start manually every time
	yield from client.send_message(messageobject.channel, msg_start + message)

def mdspecialchars(string):
	out = re.sub('`(\w+)`', u'`​\\1​`', string) # there are two u+200b characters on this line, find a way to see them if you cant
	print(out)
	return out

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
			returnage += '\n`\{}` – {}'.format(cmd, cat['commands'][cmd]['short'])
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

client.run (token)
