# [\] Discord bot
# Copyright 2020, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
import datetime
import logging
import re
import sqlite3

import discord

import config
import dispatch
import utils
import wrapper


# This serves as a lock, contains messages that are being starboarded at the moment
starboarding_messages = []

# Key is message id (of announcement in starboard), value is datetime when the message can be
# deleted. This is for the anti-star/unstar/star spam prevention
unstarboard_message_at = {}

# This contains (msgid, userid, is_star) tuples to prevent a race condition
banned_adders = []


### D A T A B A S E   M A N A G E M E N T ###

connection = None
cursor = None

def db_load():
	global connection, cursor

	connection = sqlite3.connect('db/starboard.sqlite')
	cursor = connection.cursor()

	cursor.execute("""
			CREATE TABLE IF NOT EXISTS 'starboard_messages' (
				'orig_message_id' INTEGER PRIMARY KEY NOT NULL,
				'guild_id' INTEGER NOT NULL,
				'channel_id' INTEGER NOT NULL,
				'author_id' INTEGER,
				'star_message_id' INTEGER
			)
		"""
	)

def db_commit():
	global connection

	connection.commit()


### E V E N T   H A N D L I N G ###

async def check_message(payload, channel, adding):
	"""This is called whenever a reaction is added or removed."""
	global banned_adders

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

	# Maybe the user is starboard-banned, trying to sneak through when someone else's reaction
	# is being counted and theirs not yet removed, so try to prevent a race condition there.
	banned_adder = adding and payload.user_id in config.get_s('starboard_bans',payload.guild_id)
	if banned_adder:
		banned_adders.append((payload.message_id, payload.user_id, is_star))

	# We need the message, maybe it's in the cache, otherwise we can always fetch it.
	orig_message = discord.utils.find(
		lambda m: m.id == payload.message_id, wrapper.client.cached_messages
	)
	if orig_message is None:
		orig_message = await channel.fetch_message(payload.message_id)

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

	# Why should other bots have a right to vote? Same with starboard-banned users.
	# I have a right to vote, but that's for administrative reasons.
	if (reaction_user.bot and reaction_user != wrapper.client.user) or banned_adder:
		if adding:
			try:
				await orig_message.remove_reaction(payload.emoji, reaction_user)
			except discord.errors.Forbidden:
				pass

		if banned_adder:
			# We can probably clean up 10 seconds later.
			await asyncio.sleep(10)
			banned_adders.remove((payload.message_id, payload.user_id, is_star))
		return

	# Okay, so now actually count which reactions exist!
	starrers = []
	nostarrers = []

	for reaction in orig_message.reactions:
		# Is this a star? A nostar? Yeah, we can re-use these variables now.
		is_star = False
		is_nostar = False

		if isinstance(reaction.emoji, discord.PartialEmoji):
			# It must be a discord.emoji.Emoji if it's from here
			continue
		elif isinstance(reaction.emoji, discord.emoji.Emoji):
			# This is a custom emote, but it has to be from this server; don't be
			# unfair. Plus, the bot has to be able to use it in the announcement.
			if reaction.emoji.guild.id != payload.guild_id or reaction.emoji.animated:
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

			# Also keep the nostar emote object handy in case we need to confirm a veto
			nostar_emote = reaction.emoji

	# We now have lists of starrers and nostarrers, but they may not be unique! (Modifiers...)
	starrers = list(set(starrers))
	nostarrers = list(set(nostarrers))

	# What if bots and selfstarrers snuck through the code above? Don't count them anyway...
	# Do not account for old starboard bans here! Imagine adding a star and then the message
	# goes OFF the starboard because two people got starboard banned...
	# Not much reason to go through old messages to remove stars either.
	nostar_mode = config.get_s('starboard_author_nostar_mode', payload.guild_id)
	starrers = list(filter(
			lambda u: not u.bot and u != orig_message.author \
			and (payload.message_id, u.id, True) not in banned_adders,
			starrers
		)
	)
	if nostar_mode == 2:
		# In mode 2, nostarring your own message is forbidden
		nostarrers = list(filter(
				lambda u: (not u.bot or u == wrapper.client.user) \
				and u != orig_message.author \
				and (payload.message_id, u.id, False) not in banned_adders,
				nostarrers
			)
		)
	else:
		# In mode 0 and 1, it is allowed.
		nostarrers = list(filter(
				lambda u: (not u.bot or u == wrapper.client.user) \
				and (payload.message_id, u.id, False) not in banned_adders,
				nostarrers
			)
		)

	# Alright, let's make up the balance.
	score = len(starrers) - max(0,
		len(nostarrers) - max(0, config.get_s('starboard_nostar_barrier', payload.guild_id))
	)

	# Enough for the starboard?
	starworthy = score >= max(1, config.get_s('starboard_threshold', payload.guild_id))

	# If we find the message should be removed, and this is True, then wait for 10 secs.
	remove_slowly = True

	# Except maybe the original sender has veto power!
	if nostar_mode == 0 and orig_message.author in nostarrers:
		starworthy = False
		remove_slowly = False

		# I'll confirm this veto, no backsies.
		if wrapper.client.user not in nostarrers:
			# While this is being done, we can finish the rest of the function
			async def confirm(orig_message_, nostar_emote_):
				try:
					await orig_message_.add_reaction(nostar_emote_)
				except discord.errors.Forbidden:
					pass
			dispatch.run(wrapper.client, confirm(orig_message, nostar_emote))

	# Have I confirmed it before?
	if wrapper.client.user in nostarrers:
		starworthy = False
		remove_slowly = False

	# Now that we know whether the message should be on the starboard or not, let's ensure
	# that's applied!
	if starworthy:
		await ensure_message_on_starboard(
			orig_message, score, len(starrers), len(nostarrers)
		)
	else:
		await ensure_message_not_on_starboard(orig_message, remove_slowly=remove_slowly)

async def remove_message(payload, channel):
	"""This is called when we know that a message is either being deleted or all its reactions
	are being removed. In other words, this message should be removed from the starboard if
	it is on it, as long as it's not past the time limit!
	"""

	# This isn't a DM, the starboard _is_ enabled, the starboard channel is not 0... right?
	if not hasattr(payload, 'guild_id'):
		return
	if not config.get_s('starboard_active', payload.guild_id):
		return
	starboard_chan_id = config.get_s('starboard_channel', payload.guild_id)
	if starboard_chan_id == 0:
		return

	# Ignore the ignored channels
	if payload.channel_id in config.get_s('starboard_ignoredchannels', payload.guild_id):
		return

	# Ignore messages on the starboard itself.
	if payload.channel_id == starboard_chan_id:
		return

	# Make sure the message isn't too old. It might be getting deleted and thus the timestamp
	# might be potentially gone, but there's always the snowflake!
	if (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(
			((payload.message_id >> 22) + 1420070400000)/1000
		)
	) > datetime.timedelta(
		seconds=config.get_s('starboard_timelimit', payload.guild_id)
	):
		return

	# Now make sure we won't see it on the starboard anymore.
	await ensure_message_not_on_starboard(id=payload.message_id, guild_id=payload.guild_id)


### M A I N   F U N C T I O N S ###

def acquire_starboard_message_lock(message):
	"""A message can only be starboarded by one event at a time.
	This function is called in ensure_message_on_starboard to "request" if it can starboard the
	message, and this will return True if granted, False if already requested earlier.
	"""
	global starboarding_messages

	if message in starboarding_messages:
		logging.warning(
			(
				'acquire_starboard_message_lock prevented message {} on guild {} '
				'from being posted on starboard twice!'
			).format(
				message.id, message.guild.name
			)
		)
		return False
	starboarding_messages.append(message)
	return True

async def ensure_message_on_starboard(message, score, num_stars, num_nostars):
	"""The goal of this function is to ensure the message is on the starboard with the correct
	tally, whether it's already on the starboard, or still has to be posted.
	"""
	global cursor

	# Is it on the starboard already?
	cursor.execute("""
			SELECT star_message_id
			FROM starboard_messages
			WHERE orig_message_id=?
			LIMIT 1
		""",
		(message.id,)
	)

	# Might be None, might be a 1-tuple
	result = cursor.fetchone()

	if result is None:
		# Maybe we're not the only one with this exact idea!
		if not acquire_starboard_message_lock(message):
			return

		await post_starboard_message(message, score, num_stars, num_nostars)
	else:
		# star_message_id itself might be None, in that case, ignore this entire message.
		if result[0] is None:
			return

		# It's already on the starboard, we might need to change the tallies.
		# We got here, after all!
		await edit_starboard_message(message, score, num_stars, num_nostars, result[0])

async def ensure_message_not_on_starboard(message=None, id=None, remove_slowly=False, guild_id=None):
	"""The goal of this function is to ensure the message is not on the starboard, whether it
	was in fact on the starboard, or never even was.
	"""
	global cursor, starboarding_messages

	# We might not have the full message, since it MIGHT've gotten deleted. We MUST have at
	# least an ID in that case though.
	if id is None:
		id = message.id
	if guild_id is None:
		guild_id = message.guild.id

	# Maybe we starboarded this before? Sorry I didn't tidy up. Give it another chance later.
	starboarding_messages = list(filter(lambda m: m.id != id, starboarding_messages))

	# Is it actually on the starboard?
	cursor.execute("""
			SELECT star_message_id
			FROM starboard_messages
			WHERE orig_message_id=?
			LIMIT 1
		""",
		(id,)
	)

	# Might be None, might be a 1-tuple
	result = cursor.fetchone()

	if result is None or result[0] is None:
		# Okay, cool, nothing to do!
		return

	# Now remove the message
	await remove_starboard_message(id, result[0], guild_id, remove_slowly)

async def post_starboard_message(message, score, num_stars, num_nostars):
	"""Post an announcement to the starboard for a not-yet-starboarded message"""
	global cursor

	# What's this guild's starboard channel? There must be one.
	starboard_chan = message.guild.get_channel(
		config.get_s('starboard_channel', message.guild.id)
	)

	try:
		starboard_message = await starboard_chan.send(
			star_message_contents(message, score, num_stars, num_nostars),
			embed=star_message_embed(message, score)
		)

		cursor.execute("""
				INSERT INTO starboard_messages
				(orig_message_id, guild_id, channel_id, author_id, star_message_id)
				VALUES
				(?, ?, ?, ?, ?)
			""",
			(
				message.id, message.guild.id, message.channel.id, message.author.id,
				starboard_message.id
			)
		)
		db_commit()
	except discord.errors.Forbidden:
		logging.warning(
			(
				'Bot has no permission to send message to starboard on guild {}. '
				'Will send a 🔑 reaction on the original message.'
			).format(message.guild.name)
		)
		await message.add_reaction('🔑')

async def edit_starboard_message(message, score, num_stars, num_nostars, starboard_message_id):
	"""Edit a starboard announcement"""

	# Before we look up the message, were we going to delete the message before?
	if starboard_message_id in unstarboard_message_at:
		# Then don't, the last required star came back in time.
		del unstarboard_message_at[starboard_message_id]

	starboard_message = discord.utils.find(
		lambda m: m.id == starboard_message_id, wrapper.client.cached_messages
	)
	if starboard_message is None:
		# Hoped I could get the message from the cache, but alas. Now we need to get
		# the starboard channel as well.
		starboard_chan = message.guild.get_channel(
			config.get_s('starboard_channel', message.guild.id)
		)
		starboard_message = await starboard_chan.fetch_message(starboard_message_id)

		# If it doesn't exist, just give up. Someone must've deleted it.
		if starboard_message is None:
			return

	if starboard_message.embeds:
		# Not including `embed` leaves it unedited, but we want to change the color.
		# We don't want message edits to randomly show up with a new star,
		# just leave it how it got on the starboard.
		embed = starboard_message.embeds[0]
		embed.color = star_gradient_color(score)
		await starboard_message.edit(
			content=star_message_contents(message, score, num_stars, num_nostars),
			embed=embed
		)
	else:
		# Were we not allowed to add an embed? We'll have to deal with it.
		await starboard_message.edit(
			content=star_message_contents(message, score, num_stars, num_nostars)
		)

async def remove_starboard_message(message_id, starboard_message_id, guild_id, remove_slowly):
	"""Remove a starboard announcement"""

	starboard_message = discord.utils.find(
		lambda m: m.id == starboard_message_id, wrapper.client.cached_messages
	)
	if starboard_message is None:
		# Hoped I could get the message from the cache, but alas. Now we need to get
		# the starboard channel as well.
		starboard_chan = wrapper.client.get_channel(
			config.get_s('starboard_channel', guild_id)
		)
		starboard_message = await starboard_chan.fetch_message(starboard_message_id)

		# If it doesn't exist, just give up. Someone must've deleted it.
		if starboard_message is None:
			return

	# Maybe we were already planning to remove the message in a few seconds!
	if remove_slowly and starboard_message_id in unstarboard_message_at:
		if unstarboard_message_at[starboard_message_id] < datetime.datetime.now():
			# If it should be deleted now, maybe it's not getting done. Let's do it now.
			remove_slowly = False
		else:
			# It's already planned, don't reschedule it for even later.
			return

	if remove_slowly:
		# We can remove the message after 10 seconds; 9 for certainty.
		unstarboard_message_at[starboard_message_id] = (
			datetime.datetime.now() + datetime.timedelta(seconds=9)
		)
		await asyncio.sleep(10)

		# Still not changed?
		if starboard_message_id not in unstarboard_message_at \
		or unstarboard_message_at[starboard_message_id] > datetime.datetime.now():
			# Never mind!
			return

		del unstarboard_message_at[starboard_message_id]

	await starboard_message.delete()

	cursor.execute("""
			DELETE FROM starboard_messages
			WHERE orig_message_id=?
			LIMIT 1
		""",
		(message_id,)
	)
	db_commit()

def detach_all_starboard_messages(guild_id):
	"""Remove all entries in the starboard_messages table for a particular guild, so that
	existing announcements will cease being used, and will remain there as-is.
	This should be used when switching to a different starboard channel or something;
	Used by itself, messages will spontaneously appear another time on the starboard when
	starred again.
	"""
	global cursor

	cursor.execute("""
			DELETE FROM starboard_messages
			WHERE guild_id=?
		""",
		(guild_id,)
	)
	db_commit()

def ignore_danny_stars(messages, rdanny_id):
	"""Takes a list of Messages which are sent by R. Danny, or follow the format of R. Danny's
	starboard messages.
	IDs are read from these messages, and will be inserted in our database as having NULL
	star_message_id values, so that our bot ignores those messages. This way, you can
	transition from R. Danny's to [\]'s starboard very smoothly, without duplicate
	announcements, starboard downtime or temporarily low time limits.
	"""
	global cursor

	db_messages = []
	for message in messages:
		if message.author.id != rdanny_id:
			continue

		m = re.search("\<#(?P<chan>[0-9]+)\> ID: (?P<msg>[0-9]+)", message.content)

		if m.group('chan') is None or m.group('msg') is None:
			continue

		db_messages.append(
			(int(m.group('msg')), message.guild.id, int(m.group('chan')), None, None)
		)

	cursor.executemany("""
			INSERT OR IGNORE INTO starboard_messages
			(orig_message_id, guild_id, channel_id, author_id, star_message_id)
			VALUES
			(?, ?, ?, ?, ?)
		""",
		db_messages
	)
	db_commit()

	return len(db_messages)

def guild_starboard_emote(is_star, guild_id):
	"""Return a guild's star or nostar, as string that can be used in a message text"""

	if is_star:
		config_key = 'starboard_star'
	else:
		config_key = 'starboard_nostar'

	guild_star = config.get_s(config_key, guild_id)
	if guild_star.isdigit() and str(int(guild_star)) == guild_star:
		# Custom emote.
		emote = wrapper.client.get_emoji(int(guild_star))
		if emote is None:
			# Is this emote not on this server or what? Does it even exist?
			return '<:INVALID:{}>'.format(guild_star)
		return '<:{}:{}>'.format(emote.name, guild_star)
	else:
		# Unicode emoji. And if this is arbitrary, like a URL to be evil or so,
		# how did this message get on the starboard in the first place?!
		return guild_star

def star_emote(score, guild_id):
	"""Return the emote that should be used at the start of a starboard message, as string
	that can be used in a message text.
	"""

	guild_star = guild_starboard_emote(True, guild_id)
	if guild_star != config.get_default('starboard_star'):
		return guild_star

	if score < 5:
		return '⭐'
	elif score < 10:
		return '🌟'
	elif score < 25:
		return '💫'
	else:
		return '✨'

def star_gradient_color(score):
	"""Return the color that the starboard announcement embed should have for a given score"""

	p = min(score/13, 1.0)

	red = 255
	green = int((194 * p) + (253 * (1 - p)))
	blue = int((12 * p) + (247 * (1 - p)))
	return (red << 16) + (green << 8) + blue

def star_message_contents(message, score, num_stars, num_nostars):
	"""Return the main message contents of a starboard announcement for a given score and
	number of stars
	"""

	permalink_setting = config.get_s('starboard_permalink', message.guild.id)
	if permalink_setting == 1:
		maybe_permalink = '\n{}'.format(message.jump_url)
	elif permalink_setting == 0:
		maybe_permalink = '     ID: {}'.format(message.id)
	else:
		maybe_permalink = ''

	if config.get_s('starboard_nostar_barrier', message.guild.id) == -1:
		return '{} **{}**     {}{}'.format(
			star_emote(score, message.guild.id), score,
			message.channel.mention,
			maybe_permalink
		)

	return '{} **{}**     ( {} {}  |  {} {} )     {}{}'.format(
		star_emote(score, message.guild.id), score,
		guild_starboard_emote(True, message.guild.id), num_stars,
		guild_starboard_emote(False, message.guild.id), num_nostars,
		message.channel.mention,
		maybe_permalink
	)

def star_message_embed(message, score):
	"""Return the starboard announcement embed for a given message and its score"""
	if config.get_s('starboard_permalink', message.guild.id) == 2:
		maybe_permalink = '[→ Go to message]({})\n'.format(message.jump_url)
	else:
		maybe_permalink = ''

	embed = discord.Embed(
		description=maybe_permalink + message.content,
		color = star_gradient_color(score),
		timestamp = message.created_at
	).set_author(
		name=message.author.display_name,
		icon_url=message.author.avatar_url_as(format='png')
	)

	# For attachments and embeds, we want the following:
	# - If attachments exist, they are listed, except if only one image is attached.
	# - If image attachments exist, the first image attachment is embedded.
	# - That means, if an image attachment exists along with other attachments, all attachments
	#   are listed including the embedded image
	# - If the message has embeds of type 'rich', mention the count of that. Other embed types
	#   really aren't mentionworthy, they just supplement posted links that will show up in the
	#   message contents anyway
	# - If 'image', 'gifv' or 'video' type embeds exist, and an image attachment did not
	#   already set the embed image, then embed the first of these embeds.
	# - If an embed should set the embed image, then embeds of type 'image' should use the url
	#   attribute and embeds of type 'gifv' or 'video' should use thumbnail_url.
	attachments_are_listed = False
	attachment_list = []
	embed_image_unset = True
	number_rich_embeds = 0

	def is_image_url(url):
		return url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))

	if message.attachments:
		attachments_are_listed = (
			len(message.attachments) > 1 or not is_image_url(message.attachments[0].url)
		)
		for message_attach in message.attachments:
			if is_image_url(message_attach.url) and embed_image_unset:
				embed.set_image(url=message_attach.url)
				embed_image_unset = False
			attachment_list.append('[{}]({})'.format(
					message_attach.filename, message_attach.url
				)
			)
	if message.embeds:
		for message_embed in message.embeds:
			if message_embed.type == 'rich':
				number_rich_embeds += 1
			elif message_embed.type == 'image':
				if embed_image_unset \
				and message_embed.url is not discord.Embed.Empty:
					embed.set_image(url=message_embed.url)
					embed_image_unset = False
			elif message_embed.type in ('gifv', 'video'):
				if embed_image_unset \
				and message_embed.thumbnail.url is not discord.Embed.Empty:
					embed.set_image(url=message_embed.thumbnail.url)
					embed_image_unset = False

	if attachments_are_listed:
		embed.add_field(name='📎', value='\n'.join(attachment_list), inline=False)

	if number_rich_embeds == 1:
		embed.set_footer(text='📄 Message has a rich embed')
	elif number_rich_embeds > 1:
		embed.set_footer(text='📄 Message has {} rich embeds'.format(number_rich_embeds))

	return embed
