# encoding=utf-8

import datetime
import json
import logging
import time

import discord

import config
import utils
import wrapper


# The starboard is major enough to warrant its own data file.
# That has ['guilds'], which has guild IDs as keys, and each guild is a dict which has a ['stars'],
# which is a dict of starboarded messages.
# These ['stars'] dicts have message IDs of each starboarded message as keys, and info about that
# starred message:
# ['a']: announcement ID, so the ID of the repost on the starboard
# Example: starboard_data['guilds']['1111']['stars']['2222']['a'] is the announcement ID of starred
# message 2222 in guild 1111
starboard_data = {}


def save_config():
	global starboard_data

	with open('starboard_data.json', 'w') as outfile:
		json.dump(starboard_data, outfile)

def load_blank_config():
	global starboard_data

	starboard_data = {
		'guilds': {},
	}
	save_config()

def load_config():
	global starboard_data

	try:
		with open('starboard_data.json', 'r') as infile:
			starboard_data = json.load(infile)
	except FileNotFoundError:
		logging.info('Did not find a starboard config file so making a new one')
		load_blank_config()


def config_insert_guild(guild):
	global starboard_data

	starboard_data['guilds'][guild.id] = {
		'stars': {}
	}
	save_config()


async def check_message(payload, channel):
	# This isn't a DM, the starboard _is_ enabled, the starboard channel is not 0... right?
	if not hasattr(payload, 'guild_id'):
		return
	if not config.get_s('starboard_active', payload.guild_id):
		return
	starboard_chan_id = config.get_s('starboard_channel', payload.guild_id)
	if starboard_chan_id == 0:
		return

	# Ignore the starboard itself.
	if payload.channel_id == starboard_chan_id:
		return

	# Also ignore the ignored channels.
	if payload.channel_id in config.get_s('starboard_ignoredchannels', payload.guild_id):
		return

	# If everything's in order, only stars or nostars should affect this message
	emote_star = config.get_s('starboard_star', payload.guild_id)
	emote_nostar = config.get_s('starboard_nostar', payload.guild_id)

	# TODO: check if payload.emoji is a star or nostar for optimization!

	orig_message = discord.utils.find(
		lambda m: m.id == payload.message_id, wrapper.client._connection._messages
	)
	TEMP_FROM_CACHE = True
	if orig_message is None:
		TEMP_FROM_CACHE = False
		orig_message = await channel.get_message(payload.message_id)

	# Make sure the message isn't too old.
	if (datetime.datetime.now() - orig_message.created_at) > datetime.timedelta(
		seconds=config.get_s('starboard_timelimit', payload.guild_id)
	):
		logging.info('Potential starrable message is too old, namely {}'.format(datetime.datetime.now() - orig_message.created_at))
		return

	logging.info('Potential starrable message is new enough, namely {}'.format(datetime.datetime.now() - orig_message.created_at))

	# Okay, so which reactions exist?
	starrers = set()
	nostarrers = set()

	# TODO continue, but this is a test for now.
	for reaction in orig_message.reactions:
		logging.info(
			(
				'MAYBE potential star candidate in guild "{}", msg w contents "{}" and emote:\n'
				'reaction.emoji type: {}\n'
				'so is it a custom emote: {}\n'
				'reaction.emoji as str: {}\n'
				'reaction.emoji.id IF type is Emoji: {}\n'
				'also guild it belongs to then: {}, this guild is {}\n'
				'{}'
			).format(
				channel.guild.name, orig_message.content,
				type(reaction.emoji),
				isinstance(reaction.emoji, discord.emoji.Emoji),
				str(reaction.emoji),
				reaction.emoji.id if isinstance(reaction.emoji, discord.emoji.Emoji) else 'but it isn\'t',
				reaction.emoji.guild.id if isinstance(reaction.emoji, discord.emoji.Emoji) else 'but it isn\'t', payload.guild_id,
				'Message was from cache yay' if TEMP_FROM_CACHE else 'Grumble I had to fetch the message from Discord'
			)
		)

async def remove_message(payload, channel):
	# TODO
	pass
