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


async def check_message(payload, channel, adding):
	# This isn't a DM, the starboard _is_ enabled, the starboard channel is not 0... right?
	if not hasattr(payload, 'guild_id'):
		return
	if not config.get_s('starboard_active', payload.guild_id):
		return
	starboard_chan_id = config.get_s('starboard_channel', payload.guild_id)
	if starboard_chan_id == 0:
		return

	# If everything's in order, only stars or nostars should affect this message
	emote_star = config.get_s('starboard_star', payload.guild_id)
	emote_nostar = config.get_s('starboard_nostar', payload.guild_id)

	# Let's look at what this new reaction is for a second.
	is_star = False
	is_nostar = False

	# payload.emoji is always a PartialEmoji, not str
	if payload.emoji.is_custom_emoji():
		# We can't check whether the emote is from this server yet, but we'll find out.
		if str(payload.emoji.id) == emote_star:
			is_star = True
		if str(payload.emoji.id) == emote_nostar:
			is_nostar = True
	elif payload.emoji.is_unicode_emoji():
		# This should be a unicode emote, but don't forget about skintone and gender
		# modifiers and such. Thumbs up can be set as star, for example.
		if payload.emoji.name.startswith(emote_star):
			is_star = True
		if payload.emoji.name.startswith(emote_nostar):
			is_nostar = True

	# If this is not a star nor a nostar, then we can jump off without missing anything.
	if not is_star and not is_nostar:
		return

	# Maybe nostars are even disabled!
	if not is_star and config.get_s('starboard_nostar_barrier', payload.guild_id) == -1:
		return

	# Ignore the ignored channels
	if payload.channel_id in config.get_s('starboard_ignoredchannels', payload.guild_id):
		return

	# We need the message, maybe it's in the cache, otherwise we can always fetch it.
	orig_message = discord.utils.find(
		lambda m: m.id == payload.message_id, wrapper.client._connection._messages
	)
	if orig_message is None:
		orig_message = await channel.get_message(payload.message_id)

	# We only really need the User, not Member.
	reaction_user = wrapper.client.get_user(payload.user_id)

	# Ignore messages on the starboard itself.
	if payload.channel_id == starboard_chan_id:
		# Lots of reasons not to support starring messages via the starboard:
		# - R.Danny doesn't add permalinks so the original message is harder to get to,
		#   [\] does add permalinks so it's really easy to just star the original message
		# - Not many people do it anyway
		# - More complex to program
		# - It's more misleading when looking at the number of reactions on the message
		# - What happens if a message goes under the limit despite having extra stars on
		#   the starboard? "Whoops, 1 star too few, make that 3 too few now"
		if adding:
			try:
				await orig_message.remove_reaction(payload.emoji, reaction_user)
			except discord.errors.Forbidden:
				pass
		return

	# Make sure the message isn't too old.
	if (datetime.datetime.now() - orig_message.created_at) > datetime.timedelta(
		seconds=config.get_s('starboard_timelimit', payload.guild_id)
	):
		return

	# People can't star their own messages, and maybe can't nostar them, if configured like so.
	author_permitted = not is_star
	if is_nostar and config.get_s('starboard_author_nostar_mode', payload.guild_id) == 2:
		author_permitted = False

	# So you're not starring your own message, right? smh
	if not author_permitted and orig_message.author.id == payload.user_id:
		if adding:
			try:
				await orig_message.remove_reaction(payload.emoji, reaction_user)
			except discord.errors.Forbidden:
				pass
		return

	# Why should bots have a right to vote?
	if reaction_user.bot:
		if adding:
			try:
				await orig_message.remove_reaction(payload.emoji, reaction_user)
			except discord.errors.Forbidden:
				pass
		return

	# Okay, so now actually count which reactions exist!
	starrers = []
	nostarrers = []

	for reaction in orig_message.reactions:
		# Is this a star? A nostar? Yeah, we can re-use these variables now.
		is_star = False
		is_nostar = False

		if isinstance(reaction.emoji, discord.emoji.Emoji):
			# This is a custom emote, but it has to be from this server; don't be
			# unfair. Plus, the bot has to be able to use it in the announcement.
			if reaction.emoji.guild.id != payload.guild_id:
				continue

			if str(reaction.emoji.id) == emote_star:
				is_star = True
			if str(reaction.emoji.id) == emote_nostar:
				is_nostar = True
		else:
			# Again, account for skintone and gender modifiers.
			if reaction.emoji.startswith(emote_star):
				is_star = True
			if reaction.emoji.startswith(emote_nostar):
				is_nostar = True

		if not is_star and not is_nostar:
			# Nothing to do here!
			continue

		# Nostars can be disabled
		if not is_star and config.get_s('starboard_nostar_barrier', payload.guild_id) == -1:
			continue

		# So who has used this reaction?
		if is_star:
			starrers.extend(await reaction.users().flatten())
		if is_nostar:
			nostarrers.extend(await reaction.users().flatten())

	# We now have lists of starrers and nostarrers, but they may not be unique! (Modifiers...)
	starrers = list(set(starrers))
	nostarrers = list(set(nostarrers))

	# What if bots, selfstarrers, etc snuck through the code above? Don't count them anyway...
	nostar_mode = config.get_s('starboard_author_nostar_mode', payload.guild_id)
	starrers = list(filter(lambda u: not u.bot and u != orig_message.author, starrers))
	if nostar_mode == 2:
		# In mode 2, nostarring your own message is forbidden
		nostarrers = list(filter(lambda u: not u.bot and u != orig_message.author, nostarrers))
	else:
		# In mode 0 and 1, it is allowed.
		nostarrers = list(filter(lambda u: not u.bot, nostarrers))

	# Alright, let's make up the balance.
	score = len(starrers) - max(0,
		len(nostarrers) - max(0,config.get_s('starboard_nostar_barrier', payload.guild_id))
	)

	# Enough for the starboard?
	starworthy = score >= config.get_s('starboard_threshold', payload.guild_id)

	# Except maybe the original sender has veto power!
	if nostar_mode == 0 and orig_message.author in nostarrers:
		starworthy = False

	# Now that we know whether the message should be on the starboard or not, is it already?
	#if .
	logging.info('Should message be on the starboard? {} valid stars, {} valid nostars, so total is {}, answer is {}'.format(
			len(starrers), len(nostarrers), score, starworthy
		)
	)


async def remove_message(payload, channel):
	# TODO
	pass
