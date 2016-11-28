# encoding=utf-8

import __main__
import col

# This file contains templates for messages

def success(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return __main__.discord.Embed(title='✅', description=desc, colour=col.r_success)

def warning(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return __main__.discord.Embed(title='⚠', description=desc, colour=col.r_warning)

def error(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return __main__.discord.Embed(title='❗', description=desc, colour=col.r_error)
