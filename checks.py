# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

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
