#!/usr/bin/python3

# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import inspect
import importlib
import pkgutil
import sys

import bot
import wrapper

# We expect other files to modify this via '__main__.exitcode = ...'
exit_code = 0

def reload_bot():
	global bot
	bot = importlib.reload(bot)

	include = [name for _, name, _ in pkgutil.iter_modules(['.'])]
	include.remove('bot')
	include.remove('wrapper')
	include.remove('main')

	recursive_reload(bot, include=include)

	bot.config.load()
	bot.load_events()
	bot.customcommands.commands = bot.customcommands.load()
	bot.starboard.db_load()
	bot.reaction_roles.db_load()

def recursive_reload(module, *, include=None):
	if not hasattr(recursive_reload, 'reloaded_modules'):
		recursive_reload.reloaded_modules = []

	if include is None:
		include = []

	for name, member in inspect.getmembers(module, inspect.ismodule):
		if name in include and name not in recursive_reload.reloaded_modules:
			recursive_reload.reloaded_modules.append(name)
			setattr(module, name, importlib.reload(member))
			recursive_reload(member, include=include)

	wrapper.set_current_commit()

with open('bot_token.conf', 'r') as f:
	token = f.readline().strip()

if __name__ == '__main__':
	wrapper.client.run(token, root_logger=True)
	sys.exit(exit_code)
