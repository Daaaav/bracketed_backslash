# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import discord
import col

# This file contains templates for messages

def success(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return discord.Embed(title='✅', description=desc, colour=col.r_success)

def warning(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return discord.Embed(title='⚠', description=desc, colour=col.r_warning)

def error(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return discord.Embed(title='❗', description=desc, colour=col.r_error)

def info(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return discord.Embed(title='ℹ', description=desc, colour=col.r_info)


