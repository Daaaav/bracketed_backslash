#!/usr/bin/python3.5
# encoding=utf-8

def mdspecialchars(string, character='\\'):
	"""Escapes Markdown formatting for use in message output to Discord
	This does not escape emojis until I figure out how to detect fucking emojis
	"""
	specialchars = ['\\', '*', '_', '~', '`', '<', '>', '[', ']', '(', ')']
	try:
		for char in specialchars:
			string = string.replace(char, '\\' + char)
		return string
	except AttributeError:
		return string

def id_summary(uid=None, mid=None, cid=None):
	"""Return a oneline summary of IDs."""
	summary = ''
	if uid:
		summary += ' \N{BUST IN SILHOUETTE}' + uid
	if mid:
		summary += ' \N{SPEECH BALLOON}' + mid
	if cid:
		summary += ' \N{TELEVISION}' + cid
	if summary.startswith(' '):
		summary = summary[1:]
	return summary
