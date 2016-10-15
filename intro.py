#!/usr/bin/python
# encoding=utf-8

# [\] bot, will be used for tolp server
# this source code should be licensed under gplv3

import discord
import os
import sys
import urllib
import warnings

client = discord.Client() # defines all client.* commands

invoker = '\\' # command invoker
altinvoker = 'ok glass, ' # alt command invoker

token_config = open('bot_token.conf', 'r')

token = token_config.readline(60).split('\n')[0] # read sixty characters also FUCKING NEWLINES

specialchannel = discord.Object(id='234185735266238464')
productionserver = '153368829160849408'
server = client.get_server(productionserver) # defines all server.* commands

@client.async_event
def on_ready():
	print('[info] logged in as {} with id {}'.format(client.user.name, client.user.id))
	yield from client.change_presence(game=discord.Game(name='​')) # the game name is u+200b

@client.async_event
def on_message(message):
	global msg_start

	if message.author == client.user: # is the message sent by the bot
		return # do nothing

	if str(message.author.status) == 'offline':
		if message.server.id != productionserver:
			yield from client.send_typing(message.channel)
		else:
			yield from client.send_typing(specialchannel)
		msg_start = '**`>`**`user` {}`#{}` `({}) was invisible when sending message {} at {} UTC`'.format(message.author.name, message.author.discriminator, message.author.id, message.id, message.timestamp)
		if message.server.id != productionserver:
			yield from client.send_message(message.channel, msg_start)
		else:
			yield from client.send_message(specialchannel, msg_start)
		pass

	if message.content.startswith(invoker): # does the message start with command invoker
		altinvokeractive = False
		pass # continue, go on
	elif message.content.startswith(altinvoker): # does the message start with alt invoker
		altinvokeractive = True
		pass
	else:
		return
	if altinvokeractive:
		command = message.content.split(altinvoker, 1)[1]
		msg_start = '**`>`**{}**`:`** {}\n'.format(message.author.name, message.content) # shows what the user put in, without main invoker
	else:
		yield from client.send_typing(message.channel)
		command = message.content.split(invoker, 1)[1] # removes invoker from the message
		msg_start = '**`>`**{}**`:`** \\{}\n'.format(message.author.name, message.content) # shows what the user put in

	if not is_mod(message.author) and message.channel.id != '201130047736643584' and message.server.id == productionserver:
		content = 'Non-staff members can only use me in <#201130047736643584> from now on.'
		yield from reply(message, content)
		return
	try:
		arguments = command.split (' ', 1)[1]
	except IndexError:
		arguments = None
	command = command.split (' ', 1)[0]
	if command == 'help':
		content = '''`[\]` is a bot written by Info Teddy and Dav999 in Python utilizing `discord.py`, for use on the tOLP Discord server.
__`General Commands:`__
`\help` – Lists commands and their descriptions.
`\source` – Luigi Master hates open source. But this command gives the link to the source code to the bot.
`\echo` – Echoes your input.
`\info` – Unfinished command to get information about a user.
__`Bot Commands:`__
`\\botok` – Pings the bot.
`\\restart` – Restarts the bot.
`\kill` – Kills the bot. This method does not kill it cleanly.
__`Moderation Commands:`__
`\softban` - Softban a user.
`\\nononly` - Restrict a user to only chat in the <#173239163666038784> channel.
`\\nogenmen` - Gives a user the `No General Mentions` role.
`\\nocedule` - Gives a user the role that prevents custom emotes, direct uploads and link embeds.
`\\notts` - Gives a user the `No TTS` role.
`\\rolerst` - Reset roles for a user.'''

		# General
		if arguments == 'help':
			content = '''`\help` – Lists commands and their descriptions.
Any arguments passed to `\help` will make `\help` try to look up more in-depth description of the command.'''
		elif arguments == invoker or arguments == altinvoker:
			content = '''`\` – Mentions you.
Don’t type this command in if you don’t want to be mentioned.'''
		elif arguments == 'source':
			content = '''`\source` – Luigi Master hates open source. But this command gives the link to the source code to the bot.
It’s hosted on __https://gitgud.io/__.'''
		elif arguments == 'echo':
			content = '''`\echo` – Echoes your input.
Now, you could say that the bot echoed your input already, but it’s still better to have a dedicated echo command.'''
		elif arguments == 'info':
			content = '`\info` – Unfinished command to get information about a user.'
		elif arguments == 'meme':
			content = '''`\meme` – You found a secret, congratulations. The command to get this help message will change sometimes.
__`Meme Commands:`__
`\` – Mentions you.
`\\teddy` – The obvious counterpart to `\info`.
`\samar` – The true name.
`\lui` – Obligatory “pretty cool guy” meme.
`\shiny` – He’s a shiny trinket.
`\\tainy` – Unobtaining is his name.
`\kys` – Will the bot listen?
`\*formatting*` – This is an example of italicized formatting.'''
		elif arguments == 'teddy':
			content = '''`\\teddy` – The obvious counterpart to `\info`.
It’s a meme command.'''
		elif arguments == 'samar':
			content = '''`\samar` – The true name.
It’s a meme command.'''
		elif arguments == 'lui':
			content = '''`\lui` – Obligatory “pretty cool guy” meme.
It’s a meme command.'''
		elif arguments == 'shiny':
			content = '''`\shiny` – He’s a shiny trinket.
It’s a meme command.'''
		elif arguments == 'tainy':
			content = '''`\\tainy` – Unobtaining is his name.
It’s a meme command.'''
		elif arguments == 'kys':
			content = '''`\kys` – Will the bot listen?
It’s a meme command.'''
		elif arguments == '*formatting*':
			content = '''`\*formatting*` – This is an example of italicized formatting.
It’s a meme command.'''

		# Bot
		elif arguments == 'botok':
			content = '''`\\botok` – Pings the bot.
If the bot is okay, the bot will respond with “Bot is okay”.'''
		elif arguments == 'restart':
			content = '`\\restart` - Restarts the bot.'
		elif arguments == 'kill':
			content = '`\kill` – Kills the bot. This method does not kill it cleanly.'

		# Moderation
		elif arguments == 'softban':
			content = '`\softban` - Softban a user by giving them the Banned role. Accepts a user ID as an argument.'
		elif arguments == 'nononly':
			content = '`\\nononly` - Restrict a user to only chat in the <#173239163666038784> channel. Accepts a user ID as an argument.'
		elif arguments == 'nogenmen':
			content = '`\\nogenmen` - Gives a user the `No General Mentions` role. Accepts a user ID as an argument.'
		elif arguments == 'nocedule':
			content = '`\\nocedule` - Gives a user the role that prevents custom emotes, direct uploads and link embeds. Accepts a user ID as an argument.'
		elif arguments == 'notts':
			content = '`\\notts` - Gives a user the `No TTS` role. Accepts a user ID as an argument.'
		elif arguments == 'rolerst':
			content = '`\\rolerst` - Reset roles for a user. Accepts a user ID as an argument, and changes the user\'s roles back to normal.'


		elif arguments == None:
			pass
		else:
			content = 'Invalid arguments passed. Input `\help` for a list of valid commands to pass as arguments.'
		yield from reply(message, content)
	elif command == 'restart':
		if message.author.id != '146814960574398464' and message.author.id != '159793749604433921':
			content = 'Permission denied. This command can only be used by Info Teddy or Dav999.'
			print ('[info] bot restart tried to be called by {}#{} (uuid {}) at {} utc but failed'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		content = 'Restarting.'
		print('[info] bot restart called by {}#{} (uuid {}) at {} utc'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		yield from reply(message, content)
		yield from os.execl(__file__, '')
	elif command == 'kill':
		if message.author.id != '146814960574398464' and message.author.id != '159793749604433921':
			content = 'Permission denied. This command can only be used by Info Teddy or Dav999.'
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
		content = '<@{}>'.format(message.author)
		yield from reply(message, content)
	elif command == 'source':
		content = 'Source code to the bot: __https://gitgud.io/infoteddy/bracketed_backslash__'
		yield from reply(message, content)
	elif command == 'softban':
		if not is_mod(message.author):
			content = 'Permission denied. This command can only be used by a moderator or administrator.'
			print('[info] softban attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = 'Production server only!'
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
			content = 'Please specify a user ID, a username, a username and discriminator, or a nickname.'
			yield from reply(message, content)
			return

		content = ':no_entry: <@{}> has been softbanned.'.format(targetmember.id)
		yield from reply(message, content)
	elif command == 'nononly' or command == 'nogenmen' or command == 'nocedule' or command == 'notts':
		if not is_mod(message.author):
			content = 'Permission denied. This command can only be used by a moderator or administrator.'
			print('[info] {} attempted by {}#{} (uuid {}) at {} utc but failed'.format(command, message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = 'Production server only!'
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
			content = 'Please specify a user ID, a username, a username and discriminator, or a nickname.'
			yield from reply(message, content)
			return
		content = 'Gave <@{}> the {} role.'.format(targetmember.id, rolelabel[command])
		yield from reply(message, content)
	elif command == 'nonick':
		if not is_mod(message.author):
			content = 'Permission denied. This command can only be used by a moderator or administrator.'
			print('[info] nonick attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = 'Proudction server only!'
			yield from reply(message, content)
			return
		try:
			targetmember = get_member_input(message.server, arguments)
			yield from client.add_roles(targetmember, discord.utils.get(message.server.roles, id='236925451216355338'))
			yield from client.remove_roles(targetmember, discord.utils.get(message.server.roles, id='231644869351833600'))
		except(AttributeError,TypeError):
			content = 'Please specify a user ID, a username, a username and discriminator, or a nickname.'
			yield from reply(message, content)
			return
		content = 'Gave <@{}> the tOLPer who can’t change nickname role.\nRemoved from <@{}> the tOLPer role.'.format(targetmember.id, targetmember.id)
		yield from reply(message, content)
		return
	elif command == 'rolerst':
		if not is_mod(message.author):
			content = 'Permission denied. This command can only be used by a moderator or administrator.'
			print('[info] rolerst attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from reply(message, content)
			return
		elif message.server.id != productionserver:
			content = 'Production server only!'
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
			content = 'Please specify a user ID, a username, a username and discriminator, or a nickname.'
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
		content = 'moar liek stainy amirite'
		yield from reply(message, content)
	elif command == 'kys':
		content = 'nah'
		yield from reply(message, content)
	elif command == 'botok':
		content = 'Bot is okay.'
		yield from reply(message, content)
	elif command == '*formatting*':
		content = 'That’s italicized formatting.'
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
		print('bot message {} by user {}#{} ({}) in channel {} ({}) at {} utc deleted'.format(message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.channel.name, message.timestamp))
		return
	if message.content == '' and message.attachments == []:
		return
	if message.server.id != productionserver:
		yield from client.send_typing(message.channel)
	else:
		yield from client.send_typing (specialchannel)
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
			yield from client.send_typing(message.channel)
			yield from client.send_message(message.channel, msg2)
			yield from client.send_typing(message.channel)
		else:
			yield from client.send_message(specialchannel, msg1)
			yield from client.send_typing(specialchannel)
			yield from client.send_message(specialchannel, msg2)
			yield from client.send_typing(specialchannel)
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
	if before.author == client.user or after.author == client.user: # the bot doesnt edits its own messages, so throw a warning
		warnings.warn('this is the bots own message and the bot doesnt edit messages\nid of before: {}\nid of after: {}'.format (before.id, after.id))
		return
	if before.content == after.content:
		return # must be the message being pinned and/or embed(s) displaying
	# checks succeeded
	if before.server.id != productionserver:
		yield from client.send_typing(before.channel)
	else:
		yield from client.send_typing(specialchannel)
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
			yield from client.send_typing(before.channel)
			yield from client.send_message(before.channel, msg2)
		else:
			yield from client.send_message(specialchannel, msg1)
			yield from client.send_typing(specialchannel)
			yield from client.send_message(specialchannel, msg2)
	else:
		if before.server.id != productionserver:
			yield from client.send_message(before.channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)
	if after.server.id != productionserver:
		yield from client.send_typing(after.channel)
	else:
		yield from client.send_typing(specialchannel)
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
			yield from client.send_typing(after.channel)
			yield from client.send_message(after.channel, msg2)
		else:
			yield from client.send_message(specialchannel, msg1)
			yield from client.send_typing(specialchannel)
			yield from client.send_message(specialchannel, msg2)
	else:
		if after.server.id != productionserver:
			yield from client.send_message(after.channel, msg)
		else:
			yield from client.send_message(specialchannel, msg)

@client.async_event
def on_member_update (before, after):
	if client.user == before and client.user == after:
		return
	if before.nick == after.nick:
		return # only looking for nick changes right now
	if before.server.id != productionserver:
		yield from client.send_typing(before.server.default_channel)
	else:
		yield from client.send_typing(specialchannel)
	msg_start = '**`>`**:pager:`user` {}`#{}` `({}) changed nickname`\n'.format(before.name, before.discriminator, before.id)
	content = '_`The older nickname is:`_\n' + str(before.nick)
	msg = msg_start + content
	if before.server.id != productionserver:
		yield from client.send_message(before.server.default_channel, msg)
		yield from client.send_typing(after.server.default_channel)
	else:
		yield from client.send_message(specialchannel, msg)
		yield from client.send_typing(specialchannel)
	msg_start = '**`>`**`user` {}`#{}` `({}) changed nickname`\n'.format(after.name, after.discriminator, after.id)
	content = '_`The newer nickname is:`_\n' + str(after.nick)
	msg = msg_start + content
	if after.server.id != productionserver:
		yield from client.send_message(after.server.default_channel, msg)
	else:
		yield from client.send_message(specialchannel, msg)

@client.async_event
def on_member_join(member):
	if member.server.id != productionserver:
		yield from client.send_typing(member.server.default_channel)
	else:
		yield from client.send_typing(specialchannel)
	msg = '**`>`**:arrow_right:`user` {}`#{}` `({}) joined server {} ({})`'.format(member.name, member.discriminator, member.id, member.server.name, member.server.id)
	if member.server.id != productionserver:
		yield from client.send_message(member.server.default_channel, msg)
	else:
		yield from client.send_message(specialchannel, msg)
		if is_bot(member):
			yield from client.add_roles(member, discord.utils.get(member.server.roles, id='201129507967598592')) # bot role
			# TODO: make the "role added" message be sent by on_member_update()
			yield from client.send_message(specialchannel, '`Given` {}`#{}` `({}) the Bot role.`'.format(member.name, member.discriminator, member.id))
			return
		# TODO: Look up that member in our database, to see if this user should get a restrictive group again.
		# If someone is just a tOLPer, they won't be in the database.
		if False:
			# They're found in the database! Give them the groups they should have
			pass
		else:
			# Not found, so they're just a tOLPer.
			yield from client.add_roles(member, discord.utils.get(member.server.roles, id='231644869351833600')) # The tOLPer role
			yield from client.send_message(specialchannel, '`Given` {}`#{}` `({}) the tOLPer role.`'.format(member.name, member.discriminator, member.id))

@client.async_event
def on_member_remove(member):
	if member.server.id != productionserver:
		yield from client.send_typing(member.server.default_channel)
	else:
		yield from client.send_typing(specialchannel)
	msg = '**`>`**:door:`user` {}`#{}` `({}) removed from server {} ({})`'.format (member.name, member.discriminator, member.id, member.server.name, member.server.id)
	if member.server.id != productionserver:
		yield from client.send_message(member.server.default_channel, msg)
	else:
		yield from client.send_message(specialchannel, msg)

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
	8) Discriminator only
	
	"""
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

client.run (token)
