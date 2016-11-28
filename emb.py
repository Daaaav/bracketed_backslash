# encoding=utf-8

import __main__
import col

def success(message):
	return __main__.discord.Embed(title=message, colour=col.r_success)
