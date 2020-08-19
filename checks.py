#!/usr/bin/python3.5
# encoding=utf-8

"""
[\] bot, will be used for tolp server
Copyright (C) 2016  Info Teddy

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, only version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import discord

import config
import op_ids

def is_admin(member):
	try:
		perms = member.guild_permissions
	except AttributeError:
		return False
	if perms.administrator:
		return True
	return False

def is_mod(member):
	# Same here. No need to use is_admin and is_mod in the same conditional.
	try:
		perms = member.guild_permissions
	except AttributeError:
		return False
	if perms.manage_messages:
		return True
	return is_admin(member) # Admins have moderator powers, too

def is_channel_manager(member):
	try:
		return member.guild_permissions.manage_channels
	except AttributeError:
		return False

def is_role_manager(member):
	try:
		return member.guild_permissions.manage_roles
	except AttributeError:
		return False

def is_bot(member):
	# Alright then.
	if member.bot:
		return True
	return False

def is_operator(member):
	return member.id in op_ids.ids['operators'] or member.id == op_ids.ids['host']

def is_tntgb_mod(member):
	if member.guild is None or \
	(not config.is_detached('tntgb', member.guild.id)) or \
	'mod_role' not in config.get_s('tntgb', member.guild.id):
		return False

	return discord.utils.find(
		lambda r: r.id == config.get_s('tntgb', member.guild.id)['mod_role'],
		member.roles,
	) is not None

def is_tntgb_banned(member):
	if member.guild is None or not config.is_detached('restrictiveroles', member.guild.id):
		return False

	for role_id in config.get_s('restrictiveroles', member.guild.id):
		if \
		discord.utils.find(lambda r: r.id == role_id, member.guild.roles) in member.roles:
			return True
	return False

def is_host(member):
	return member.id == op_ids.ids['host']
