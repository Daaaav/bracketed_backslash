#!/usr/bin/python3.5
# encoding=utf-8

import datetime
import time

import discord

import __main__

def mdspecialchars(string, character='\\'):
	"""Escapes Markdown formatting for use in message output to Discord
	This does not escape emojis until I figure out how to detect fucking emojis
	"""
	specialchars = ['\\', '*', '_', '~', '`', '<', '>', '[', ']', '(', ')', ':']
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

async def handle_minute_message_edits(msg, schan):
	if not msg.id in __main__.minutemessageedits:
		__main__.minutemessageedits[msg.id] = [int(time.time())]
	else:
		edittime = int(time.time())
		while True:
			if edittime in __main__.minutemessageedits[msg.id]:
				edittime += .1
			else:
				__main__.minutemessageedits[msg.id].append(edittime)
				break
		if len(__main__.minutemessageedits[msg.id]) >= 5:
			await handle_delete_overedited_message(msg, schan)

		# While we're at it, also clean up other messages.

		# Copy because we may be removing elements from here
		for k in list(__main__.minutemessageedits):
			if k != msg.id:
				for i in list(__main__.minutemessageedits[k]):
					if i < (int(time.time())-30):
						__main__.minutemessageedits[k].remove(i)
				if len(__main__.minutemessageedits[k]) == 0:
					del __main__.minutemessageedits[k]

async def handle_delete_overedited_message(msg, schan):
	# Copy the list, we may be removing elements from here
	for i in list(__main__.minutemessageedits[msg.id]):
		if i < (int(time.time())-30):
			__main__.minutemessageedits[msg.id].remove(i)

	if len(__main__.minutemessageedits[msg.id]) >= 5:
		# Ok, that's enough editing.
		try:
			await __main__.client.delete_message(msg)
			__main__.messages_deleted_by_bot.append(msg)
			em = discord.Embed(
				title=('\N{MEMO}' * 5) + (
					'Message {0.id} was edited too many times in'
					' {0.channel.mention} and has been deleted by me'
				).format(msg),
				description=msg.content,
				colour=msg.author.colour,
				timestamp=datetime.datetime.now(),
			)
			em.set_author(
				name=msg.author.display_name,
				icon_url=msg.author.avatar_url,
			)
			em.add_field(
				name='Message author',
				value='<@!{0}> ({0})'.format(msg.author.id),
			)
		except discord.errors.NotFound:
			em = discord.Embed(
				title=(
					'\N{MEMO}' * 5
				) + (
					'Message {0.id} was edited too many times in'
					' {0.channel.mention} but they deleted it before I could'
				).format(msg),
				description=msg.content,
				colour=msg.author.colour,
				timestamp=datetime.datetime.now(),
			)
			em.set_author(
				name=msg.author.display_name,
				icon_url=msg.author.avatar_url,
			)
			em.add_field(
				name='Message author',
				value='<@!{id}> ({id})'.format(id=msg.author.id),
			)
		await __main__.client.send_message(schan, embed=em)

		# Also actually reply
		await __main__.client.send_message(
			msg.channel,
			(
				'{0.author.mention}. Were you going to stop editing that message?'
			).format(msg),
		)
