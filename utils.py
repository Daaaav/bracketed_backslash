#!/usr/bin/python3.5
# encoding=utf-8

def mdspecialchars(string, character='\\'):
	"""Escapes Markdown formatting for use in message output to Discord
	This does not escape emojis until I figure out how to detect fucking emojis
	"""
	specialchars = ['\\', '*', '_', '~', '`', '<', '>']
	try:
		for char in specialchars:
			string = string.replace(char, '\\' + char)
		return string
	except AttributeError:
		return string
