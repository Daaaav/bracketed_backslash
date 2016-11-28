# encoding=utf-8

import __main__
import col

# This file contains templates for messages

def success(message, addingfields=False):
	if addingfields:
		desc = '_{}_'.format(message)
	else:
		desc = message
	return __main__.discord.Embed(description=desc, colour=col.r_success)
