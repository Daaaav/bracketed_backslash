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

import inspect
import importlib
import logging
import pkgutil

import bot
import wrapper

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

logging.basicConfig(level=logging.INFO)

with open('bot_token.conf', 'r') as f:
	token = f.readline(60).split('\n')[0]

if __name__ == '__main__':
	wrapper.client.run(token)
