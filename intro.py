#!/usr/bin/python
# encoding=utf-8

# [\] bot, will be used for tolp server
# this source code should be licensed under gplv3

import discord
import os
import sys
import urllib.request
import json

client = discord.Client () # defines all client.* commands
invoker = '\\' # command invoker
altinvoker = 'ok glass, ' # alt command invoker

token_config = open ('bot_token.conf', 'r')

token = token_config.readline (60).split ('\n') [0] # read sixty characters also FUCKING NEWLINES

specialchannel = discord.Object (id='234185735266238464')
productionserver = '153368829160849408'

server = client.get_server('153368829160849408') # defines all server.* commands

@client.async_event
def on_ready ():
	print ('[info] logged in as {} with id {}'.format (client.user.name, client.user.id))
	yield from client.change_presence (game=discord.Game (name='​')) # the game name is u+200b

@client.async_event
def on_message (message):
	if message.author == client.user: # is the message sent by the bot
		return # do nothing

	if message.content.startswith (invoker): # does the message start with command invoker
		altinvokeractive = False
		pass # continue, go on

	elif message.content.startswith (altinvoker): # does the message start with alt invoker
		altinvokeractive = True
		pass

	else:
		return

	if altinvokeractive:
		command = message.content.split (altinvoker, 1) [1]
		msg_start = '**`>`**{}**`:`** {}\n'.format (message.author.name, message.content) # shows what the user put in, without main invoker

	else:
		yield from client.send_typing (message.channel)
		command = message.content.split (invoker, 1) [1] # removes invoker from the message
		msg_start = '**`>`**{}**`:`** \\{}\n'.format (message.author.name, message.content) # shows what the user put in

	try:
		arguments = command.split (' ', 1) [1]

	except IndexError:
		arguments = None

	command = command.split (' ', 1) [0]

	if command == 'help':
		content = '''`[\]` is a bot written by Info Teddy in Python utilizing `discord.py`, for use on the tOLP Discord server.
Special thanks to Dav999 for giving input and feedback on the bot.
__`Commands:`__
`\help` – Lists commands and their descriptions.
`\source` – Luigi Master hates open source. But this command gives the link to the source code to the bot.
`\echo` – Echoes your input.
`\info` – Unfinished command to get information about a user.
`\\teddy` – The obvious counterpart to `\info`.
`\samar` – The true name.
`\lui` – Obligatory “pretty cool guy” meme.
`\shiny` – He’s a shiny trinket.
`\\tainy` – Unobtaining is his name.
`\kys` – Will the bot listen?
`\*formatting*` – This is an example of italicized formatting.
`\\botok` – Pings the bot.
`\\restart` – Restarts the bot.
`\kill` – Kills the bot. This method does not kill it cleanly.
`\\nononly` - Restrict a user to only chat in the <#173239163666038784> channel'''
		if arguments == 'help':
			content = '''`\help` – Lists commands and their descriptions.
Any arguments passed to `\help` will make `\help` try to look up more in-depth description of the command.'''

		elif arguments == 'source':
			content = '''`\source` – Luigi Master hates open source. But this command gives the link to the source code to the bot.
It’s hosted on __https://gitgud.io/__.'''

		elif arguments == 'echo':
			content = '''`\echo` – Echoes your input.
Now, you could say that the bot echoed your input already, but it’s still better to have a dedicated echo command.'''

		elif arguments == 'info':
			content = '`\info` – Unfinished command to get information about a user.'

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

		elif arguments == 'botok':
			content = '''`\\botok` – Pings the bot.
If the bot is okay, the bot will respond with “Bot is okay”.'''

		elif arguments == 'restart':
			content = '`\\restart` - Restarts the bot.'

		elif arguments == 'kill':
			content = '`\kill` – Kills the bot. This method does not kill it cleanly.'

		elif arguments == 'nononly':
			content = '`\\nononly` - Restrict a user to only chat in the <#173239163666038784> channel. Accepts a user ID as an argument.'

		elif arguments == None:
			pass

		else:
			content = 'Invalid arguments passed. Input `\help` for a list of valid commands to pass as arguments.'

		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'restart':
		if not is_admin(message.author.id):
			content = 'Permission denied. This command can only be used by Info Teddy or Dav999.'
			msg = msg_start + content
			print ('[info] bot restart tried to be called by {}#{} (uuid {}) at {} utc but failed'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from client.send_message (message.channel, msg)
			return

		content = 'Restarting.'
		msg = msg_start + content
		print ('[info] bot restart called by {}#{} (uuid {}) at {} utc'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		yield from client.send_message (message.channel, msg)
		yield from os.execl(__file__, '')

	elif command == 'kill':
		if not is_admin(message.author.id):
			content = 'Permission denied. This command can only be used by Info Teddy or Dav999.'
			msg = msg_start + content
			print ('[info] bot kill tried to be called by {}#{} (uuid {}) at {} utc but failed'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from client.send_message (message.channel, msg)
			return

		content = 'Killing.'
		msg = msg_start + content
		print ('[info] bot kill called by {}#{} (uuid {}) at {} utc'.format (message.author.name, message.author.discriminator, message.author.id, message.timestamp))
		yield from client.send_message (message.channel, msg)
		yield from sys.exit ()

	elif command == 'echo':
		if arguments == None:
			arguments = ''

		content = arguments
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'source':
		content = 'Source code to the bot: __https://gitgud.io/infoteddy/bracketed_backslash__'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'nononly':
		if not is_mod(message.author.id):
			content = 'Permission denied, this can only be done by a moderator or admin.'
			msg = msg_start + content
			print('[info] nononly attempted by {}#{} (uuid {}) at {} utc but failed'.format(message.author.name, message.author.discriminator, message.author.id, message.timestamp))
			yield from client.send_message(message.channel, msg)
			return
		elif message.server.id != productionserver:
			content = 'Production server only!'
			msg = msg_start + content
			yield from client.send_message(message.channel, msg)
			return
		elif arguments == None:
			content = 'Please specify a user ID.'
			msg = msg_start + content
			yield from client.send_message(message.channel, msg)
			return
		
		# Maybe check for my permissions and for whether this ID is actually a member?
		yield from client.add_roles(discord.Object(id=arguments), discord.utils.get(server.roles, id='173240966575161344')) # The nonsense-only role
		content = 'Gave <@' + arguments + '> the Nonsense-Only role.'
		msg = msg_start + content
		yield from client.send_message(message.channel, msg)

	elif command == 'info':
		content = str (message.author.permissions_in (message.channel))
		perms = discord.Channel.permissions_for (message.channel, message.author)
		print (perms)
		content = 'Unfinished command. This command currently sends output to Info Teddy.'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'teddy':
		content = 'xd'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'samar':
		content = 'Why does he like Undertale?'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'lui':
		content = 'i think /r/undertale is a pretty cool guy, eh deletes messages and doesnt afraid of lying'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'shiny':
		content = 'moar liek shittykitty amirite'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'tainy':
		content = 'moar liek stainy amirite'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'kys':
		content = 'nah'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == 'botok':
		content = 'Bot is okay.'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	elif command == '*formatting*':
		content = 'That’s italicized formatting.'
		msg = msg_start + content
		yield from client.send_message (message.channel, msg)

	else:
		if altinvokeractive:
			return # do not print error message if command is invalid

		else:
			content = 'Invalid command. Input `\help` for a list of valid commands.'
			msg = msg_start + content
			yield from client.send_message (message.channel, msg)

@client.async_event
def on_message_delete (message): # when a message gets deleted
	if message.author == client.user: # is the deleted message originally sent by the bot
		print ('bot message {} by user {}#{} ({}) in channel {} ({}) at {} utc deleted'.format (message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.channel.name, message.timestamp))
		return

	if message.content == '' and message.attachments == []:
		return

	if message.server.id != productionserver:
		yield from client.send_typing (message.channel)

	else:
		yield from client.send_typing (specialchannel)

	msg_start = '**`>`**:no_entry_sign:`message {} by user` {}`#{}` `({}) in channel` <#{}> `at {} UTC deleted`\n'.format (message.id, message.author.name, message.author.discriminator, message.author.id, message.channel.id, message.timestamp)
	content = '_`The original content is:`_\n' + message.content
	msg = msg_start + content
	if len (msg) >= 2000:
		content = '_`The original content is (part 1):`_\n' + message.content
		msg = msg_start + content
		msg_split = [ msg [i : i+2000] for i in range (0, len (msg), 2000) ]
		if len (msg_split [0]) >= 2000:
			msg_split = [ msg [i : i+2000] for i in range (0, len (msg), 2000) ]

		content1 = msg_split [0]
		content2 = '_`The original content is (part 2):`_\n' + msg_split [1]
		msg1 = content1
		msg2 = msg_start + content2
		if message.server.id != productionserver:
			yield from client.send_message (message.channel, msg1)
			yield from client.send_typing (message.channel)
			yield from client.send_message (message.channel, msg2)
			yield from client.send_typing (message.channel)

		else:
			yield from client.send_message (specialchannel, msg1)
			yield from client.send_typing (specialchannel)
			yield from client.send_message (specialchannel, msg2)
			yield from client.send_typing (specialchannel)

	else:
		if message.server.id != productionserver:
			yield from client.send_message (message.channel, msg)

		else:
			yield from client.send_message (specialchannel, msg)

	if message.attachments != []:
		content = '_`The original attachment is:`_\n' + str (message.attachments)
		msg = msg_start + content

		if message.server.id != productionserver:
			yield from client.send_message (message.channel, msg)

		else:
			yield from client.send_message (specialchannel)

@client.async_event
def on_message_edit (before, after): # when a message gets edited
	# preliminary checkings
	if before.author == client.user or after.author == client.user: # the bot doesnt edits its own messages, so throw a warning
		warnings.warn ('this is the bots own message and the bot doesnt edit messages\nid of before: {}\nid of after: {}'.format (before.id, after.id))
		return

	if before.content == after.content:
		return # must be the message being pinned and/or embed(s) displaying

	# checks succeeded

	if before.server.id != productionserver:
		yield from client.send_typing (before.channel)

	else:
		yield from client.send_typing (specialchannel)

	msg_start = '**`>`**:pencil:`message {} by user` {}`#{}` `({}) in channel` <#{}> `at {} UTC edited`\n'.format (before.id, before.author.name, before.author.discriminator, before.author.id, before.channel.id, before.timestamp)
	content = '_`The older content is:`_\n' + before.content
	msg = msg_start + content
	if len (msg) >= 2000:
		content = '_`The older content is (part 1):`_\n' + before.content
		msg = msg_start + content
		msg_split = [ msg [i : i+2000] for i in range (0, len (msg), 2000) ]
		if len (msg_split [0]) >= 2000:
			msg_split = [ msg [i : i+2000] for i in range (0, len (msg), 2000) ]

		content1 = msg_split [0]
		content2 = '_`The older content is (part 2):`_\n' + msg_split [1]
		msg1 = content1
		msg2 = msg_start + content2
		if before.server.id != productionserver:
			yield from client.send_message (before.channel, msg1)
			yield from client.send_typing (before.channel)
			yield from client.send_message (before.channel, msg2)
		else:
			yield from client.send_message (specialchannel, msg1)
			yield from client.send_typing (specialchannel)
			yield from client.send_message (specialchannel, msg2)

	else:
		if before.server.id != productionserver:
			yield from client.send_message (before.channel, msg)

		else:
			yield from client.send_message (specialchannel, msg)

	if after.server.id != productionserver:
		yield from client.send_typing (after.channel)

	else:
		yield from client.send_typing (specialchannel)

	msg_start = '**`>`**`message {} by user` {}`#{}` `({}) in channel` <#{}> `at {} UTC edited`\n'.format (after.id, after.author.name, after.author.discriminator, after.author.id, after.channel.id, after.timestamp)
	content = '_`The newer content is:`_\n' + after.content
	msg = msg_start + content
	if len (msg) >= 2000:
		content = '_`The newer content is (part 1):`_\n' + after.content
		msg = msg_start + content
		msg_split = [ msg [i : i+2000] for i in range (0, len (msg), 2000) ]
		if len (msg_split [0]) >= 2000:
			msg_split = [ msg [i : i+2000] for i in range (0, len (msg), 2000) ]

		content1 = msg_split [0]
		content2 = '_`The newer content is (part 2):`_\n' + msg_split [1]
		msg1 = content1
		msg2 = msg_start + content2
		if after.server.id != productionserver:
			yield from client.send_message (after.channel, msg1)
			yield from client.send_typing (after.channel)
			yield from client.send_message (after.channel, msg2)

		else:
			yield from client.send_message (specialchannel, msg1)
			yield from client.send_typing (specialchannel)
			yield from client.send_message (specialchannel, msg2)

	else:
		if after.server.id != productionserver:
			yield from client.send_message (after.channel, msg)

		else:
			yield from client.send_message (specialchannel, msg)

@client.async_event
def on_member_update (before, after):
	if client.user == before and client.user == after:
		return

	if before.nick == after.nick:
		return # only looking for nick changes right now

	if before.server.id != productionserver:
		yield from client.send_typing (before.server.default_channel)

	else:
		yield from client.send_typing (specialchannel)

	msg_start = '**`>`**:pager:`user` {}`#{}` `({}) changed nickname`\n'.format (before.name, before.discriminator, before.id)
	content = '_`The older nickname is:`_\n' + str (before.nick)
	msg = msg_start + content

	if before.server.id != productionserver:
		yield from client.send_message (before.server.default_channel, msg)
		yield from client.send_typing (after.server.default_channel)

	else:
		yield from client.send_message (specialchannel, msg)
		yield from client.send_typing (specialchannel)

	msg_start = '**`>`**`user` {}`#{}` `({}) changed nickname`\n'.format (after.name, after.discriminator, after.id)
	content = '_`The newer nickname is:`_\n' + str (after.nick)
	msg = msg_start + content

	if after.server.id != productionserver:
		yield from client.send_message (after.server.default_channel, msg)

	else:
		yield from client.send_message (specialchannel, msg)

@client.async_event
def on_member_join (member):
	if member.server.id != productionserver:
		yield from client.send_typing (member.server.default_channel)

	else:
		yield from client.send_typing (specialchannel)

	msg = '**`>`**:arrow_right:`user` {}`#{}` `({}) joined server {} ({})`'.format (member.name, member.discriminator, member.id, member.server.name, member.server.id)

	if member.server.id != productionserver:
		yield from client.send_message (member.server.default_channel, msg)

	else:
		yield from client.send_message (specialchannel, msg)

@client.async_event
def on_member_remove (member):
	if member.server.id != productionserver:
		yield from client.send_typing (member.server.default_channel)

	else:
		yield from client.send_typing (specialchannel)

	msg = '**`>`**:door:`user` {}`#{}` `({}) removed from server {} ({})`'.format (member.name, member.discriminator, member.id, member.server.name, member.server.id)

	if member.server.id != productionserver:
		yield from client.send_message (member.server.default_channel, msg)

	else:
		yield from client.send_message (specialchannel, msg)

def is_admin(memberid):
	# This should probably be changed to a membergroup/permissions check, but this works for now.
	if memberid == '146814960574398464' or memberid == '159793749604433921': # these are the ids of info teddy and dav999
		return True

	return False

def is_mod(memberid):
	# Same here. No need to use is_admin and is_mod in the same conditional.
	if memberid == '152931944357691394': # Format
		return True
	
	return is_admin(memberid) # Admins have moderator powers, too

client.run (token)
