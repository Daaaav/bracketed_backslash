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
