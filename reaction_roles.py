"""
GPLv3-only :^)
"""

import asyncio
import datetime
import sqlite3

import config
import wrapper


# Key is tuple of (user ID, role ID), value is `datetime` when reaction roles will be processed
# again. This is to prevent spamming role add/removes
remove_role_at = {}


# Database management

connection = None
cursor = None

def db_load():
	global connection, cursor

	connection = sqlite3.connect('db/reaction_roles.sqlite')
	cursor = connection.cursor()

	# Ad-hoc object incoming, because SQL doesn't support arrays
	# Also no unions, so there are both Unicode and custom emoji columns
	# And we can't execute more than one statement at a time
	# guild_id isn't stored, if you're querying the database you should have already checked
	# if the guild has reaction roles enabled in the first place
	cursor.execute("""
			CREATE TABLE IF NOT EXISTS 'reactroles_messages' (
				'channel_id' INTEGER PRIMARY KEY NOT NULL,
				'message_id' INTEGER NOT NULL
			)
		"""
	)
	cursor.execute("""
			CREATE TABLE IF NOT EXISTS 'reactroles_roles' (
				'message_id' INTEGER PRIMARY KEY NOT NULL,
				'role_id' INTEGER NOT NULL,
				'unicode_emoji' TEXT,
				'custom_emoji_id' INTEGER
			)
		"""
	)

def db_commit():
	global connection

	connection.commit()


# Event handling

async def check_message(payload, channel, adding):
	"""This is called whenever a reaction is added or removed."""
	global cursor
	guild = channel.guild

	# This isn't a DM and reaction roles ARE enabled... right?
	if (not hasattr(payload, 'guild_id')
	or not config.get_s('reaction_roles', payload.guild_id)):
		return

	# And you're also not a bot, right?
	member = guild.get_member(payload.user_id)
	# member can be None but if we're here then surely it's not
	if member.bot:
		return

	# I'm violating EAFP (Easier to Ask for Forgiveness than Permission) here in favor of
	# LBYL (Look Before You Leap), because it'd be a real shame to do all this expensive
	# database querying only for nothing to happen because we don't have permission
	our_perms = channel.permissions_for(wrapper.client.user)
	if not our_perms.manage_roles:
		# TODO: Maybe error message visible to guild administrators somewhere?
		return

	# Query database, is this message one of the messages we're looking for?
	cursor.execute("""
			SELECT message_id
			FROM reactroles_messages
			WHERE channel_id=?
		""",
		(channel.id,),
	)
	result = cursor.fetchall()

	if payload.message_id not in result:
		return

	# Make another query, to check the emoji (also checks message ID first)
	cursor.execute("""
			SELECT *
			FROM reactroles_roles
			WHERE message_id=?
	""",
	(payload.message_id,),
	)

	result = cursor.fetchall()
	if result is None or not result:
		return

	# We have the message ID, now just check the emoji

	# Don't be calling functions more than once
	custom = payload.emoji.is_custom_emoji()
	unicode = payload.emoji.is_unicode_emoji()

	role_id = None
	# The order here matches the database schema
	for _, this_role_id, unicode_emoji, custom_emoji_id in result:
		if ((custom and payload.emoji.id == custom_emoji_id)
		or (unicode and payload.emoji.name == unicode_emoji)):
			role_id = this_role_id
			break

	if role_id is None:
		return

	# We have the role ID, finally apply/remove it
	# I assume the ID exists, or if it doesn't, that this will fail silently

	# I assume there's no need to specify message ID in the reason... surely guilds won't have
	# a MASSIVE channel with tons of reaction role messages in it that they can't easily know
	# which message the user clicked on
	if adding:
		# Were we going to remove their role before?
		if (member.id, role_id) in remove_role_at:
			# Then don't
			del remove_role_at[(member.id, role_id)]

		await member.add_roles(
			role_id,
			reason=f'Member reacted to message with reaction roles in {channel.mention}',
		)
	else:
		# Did we already plan to remove the role?
		if ((member.id, role_id) in remove_role_at
		# Think about this... it should be a greater-than sign if the time hasn't come yet
		and remove_role_at[(member.id, role_id)] > datetime.datetime.now()):
			return

		# We can remove the role after 3 seconds; 2 for certainty.
		remove_role_at[(member.id, role_id)] = (
			datetime.datetime.now() + datetime.timedelta(seconds=2)
		)
		await asyncio.sleep(3)

		# Still going to be removed?
		if ((member.id, role_id) not in remove_role_at
		or remove_role_at[(member.id, role_id)] > datetime.datetime.now()):
			# Never mind!
			return

		del remove_role_at[(member.id, role_id)]

		await member.remove_roles(
			role_id,
			reason=f'Member’s reaction to message with reaction roles was removed in {channel.mention}',
		)
