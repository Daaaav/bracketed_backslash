# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
import dataclasses
import datetime
import sqlite3
from typing import Union

import discord

import config
import dispatch
import utils
import wrapper


@dataclasses.dataclass
class RoleDelta:
	"""Stores a set of role changes, along with tracking how they got there."""
	add_roles: set[int] # role IDs
	remove_roles: set[int] # role IDs
	channels: set[int] # channel IDs
	messages: set[int] # message IDs
	num_reacts: int
	num_unreacts: int

# Key is user ID, value is `datetime` to apply its change in `queued`
cooldown = {}

# Key is user ID, value is RoleDelta
queued = {}

# Contains user IDs
locked = set()


# Database management

connection = None
cursor = None

def db_load() -> None:
	global connection, cursor

	connection = sqlite3.connect('db/reaction_roles.sqlite')
	cursor = connection.cursor()

	# Ad-hoc object incoming, because SQL doesn't support arrays
	# Also no unions, so there are both Unicode and custom emoji columns
	# guild_id isn't stored, if you're querying the database you should have already checked
	# if the guild has reaction roles enabled in the first place
	cursor.executescript("""
			CREATE TABLE IF NOT EXISTS 'reactroles_groups' (
				'group_id' INTEGER PRIMARY KEY NOT NULL,
				'channel_id' INTEGER NOT NULL,
				'max_count' INTEGER NOT NULL
			);
			CREATE TABLE IF NOT EXISTS 'reactroles_messages' (
				'message_id' INTEGER PRIMARY KEY NOT NULL,
				'group_id' INTEGER NOT NULL
			);
			CREATE TABLE IF NOT EXISTS 'reactroles_roles' (
				'message_id' INTEGER NOT NULL,
				'role_id' INTEGER NOT NULL,
				'unicode_emoji' TEXT,
				'custom_emoji_id' INTEGER,
				PRIMARY KEY ('message_id', 'role_id')
			);
		"""
	)

def db_commit() -> None:
	global connection

	connection.commit()

def db_get_groups(channel_id: int) -> list:
	global cursor

	cursor.execute("""
			SELECT group_id, max_count
			FROM reactroles_groups
			WHERE channel_id=?
		""",
		(channel_id,),
	)

	return cursor.fetchall()

def db_get_messages(channel_id: int) -> list[int]:
	global cursor

	groups = db_get_groups(channel_id)

	messages = []

	for group_id, _ in groups:
		cursor.execute("""
				SELECT message_id
				FROM reactroles_messages
				WHERE group_id=?
			""",
			(group_id,),
		)
		messages += [tuple_[0] for tuple_ in cursor.fetchall()]

	return messages

def db_get_entries(message_id: int) -> list:
	global cursor

	cursor.execute("""
			SELECT *
			FROM reactroles_roles
			WHERE message_id=?
		""",
		(message_id,),
	)

	return cursor.fetchall()

def db_get_group_id(message_id: int) -> int:
	global cursor

	cursor.execute("""
			SELECT group_id
			FROM reactroles_messages
			WHERE message_id=?
		""",
		(message_id,),
	)

	result = [tuple_[0] for tuple_ in cursor.fetchall()]

	assert len(result) == 1
	assert isinstance(result[0], int)

	return result[0]

def db_get_max_count(group_id: int) -> int:
	global cursor

	cursor.execute("""
			SELECT max_count
			FROM reactroles_groups
			WHERE group_id=?
		""",
		(group_id,),
	)

	result = [tuple_[0] for tuple_ in cursor.fetchall()]

	assert len(result) == 1
	assert isinstance(result[0], int)

	return result[0]

def db_get_group_entries(group_id: int) -> list:
	global cursor

	cursor.execute("""
			SELECT message_id
			FROM reactroles_messages
			WHERE group_id=?
		""",
		(group_id,),
	)

	message_ids = [tuple_[0] for tuple_ in cursor.fetchall()]

	retval = []

	for message_id in message_ids:
		cursor.execute("""
				SELECT *
				FROM reactroles_roles
				WHERE message_id=?
			""",
			(message_id,),
		)

		entries = cursor.fetchall()

		for entry in entries:
			retval.append((message_id,) + entry)

	return retval


# Event handling

async def check_message(
	payload: discord.RawReactionActionEvent, channel: discord.abc.Messageable, adding: bool
) -> None:
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
	our_perms = channel.guild.me.guild_permissions
	if not our_perms.manage_roles:
		# TODO: Maybe error message visible to guild administrators somewhere?
		return

	# Query database, is this message one of the messages we're looking for?
	result = db_get_messages(channel.id)

	entry = discord.utils.find(lambda i: i == payload.message_id, result)
	if entry is None:
		return

	# Get max count, requires knowing the group ID
	group_id = db_get_group_id(payload.message_id)
	max_count = db_get_max_count(group_id)

	# Make another query, to check the emoji (also checks message ID first)
	entries = db_get_entries(payload.message_id)
	if entries is None or not entries:
		return

	# We have the message ID, now just check the emoji

	# Don't be calling functions more than once
	custom = payload.emoji.is_custom_emoji()
	unicode = payload.emoji.is_unicode_emoji()

	role_id = None
	# The order here matches the database schema
	for _, this_role_id, unicode_emoji, custom_emoji_id in entries:
		if ((custom and payload.emoji.id == custom_emoji_id)
		or (unicode and payload.emoji.name == unicode_emoji)):
			role_id = this_role_id
			break

	if role_id is None:
		return

	# We have the role ID, finally apply/remove it
	# I assume the ID exists, or if it doesn't, that this will fail silently

	def update_role_delta(
		member_id: int,
		*,
		add_roles: set[int] = None,
		remove_roles: set[int] = None,
		channels: set[int],
		messages: set[int],
		num_reacts: int = 0,
		num_unreacts: int = 0,
	):
		assert add_roles is not None or remove_roles is not None

		if add_roles is None:
			add_roles = set()
		if remove_roles is None:
			remove_roles = set()

		if member_id not in queued:
			queued[member_id] = RoleDelta(
				add_roles=set(add_roles),
				remove_roles=set(remove_roles),
				channels=set(channels),
				messages=set(messages),
				num_reacts=num_reacts,
				num_unreacts=num_unreacts,
			)
		else:
			queued[member_id].add_roles.update(add_roles)
			queued[member_id].remove_roles.update(remove_roles)
			queued[member_id].channels.update(channels)
			queued[member_id].messages.update(messages)
			queued[member_id].num_reacts += num_reacts
			queued[member_id].num_unreacts += num_unreacts

	# I assume there's no need to specify message ID in the reason... surely guilds won't have
	# a MASSIVE channel with tons of reaction role messages in it that they can't easily know
	# which message the user clicked on
	reason = f'Member reacted to message with reaction roles in #{channel.name}'
	reason = f'Member’s reaction to message with reaction roles was removed in #{channel.name}'
	if adding:
		if max_count > 0:
			group_entries = db_get_group_entries(group_id)
			role_ids = [this_role_id for _, _, this_role_id, _, _ in group_entries]

			already_role_ids = set()

			if member.id in queued:
				for role_id in queued[member.id].add_roles:
					already_role_ids.add(role_id)

			for role in member.roles:
				if (role.id in role_ids
				and (member.id not in queued
				or role.id not in queued[member.id].remove_roles)):
					already_role_ids.add(role.id)

			already_role_ids = list(already_role_ids)

			# + 1 to account for the new role we're going to add
			num_already = len(already_role_ids) + 1

			remove_roles = set()
			if num_already > max_count:
				for i in range(0, num_already - max_count):
					remove_roles.add(already_role_ids[i])

			update_role_delta(
				member.id,
				add_roles={role_id},
				remove_roles=remove_roles,
				channels={channel.id},
				messages={payload.message_id},
				num_reacts=1,
			)

			# Remove the reactions of the roles we just removed.
			# Not strictly necessary, but it's a more transparent interface
			# This will be a dispatch that executes later, so we don't trip over ourselves
			# and think that the reaction removal we just did was caused by the member
			async def remove_reaction(message_, emoji_, member_):
				await asyncio.sleep(3)
				try:
					await message_.remove_reaction(emoji_, member_)
				except (discord.Forbidden, discord.NotFound):
					pass

			for this_message_id, _, this_role_id, unicode_emoji, custom_emoji_id in group_entries:
				assert utils.mutually_exclusive(unicode_emoji, custom_emoji_id)
				if this_role_id in remove_roles:
					if unicode_emoji is not None:
						emoji = unicode_emoji
					elif custom_emoji_id is not None:
						# remove_reaction() has isinstance checks, so we can't duck-type our own emoji object.
						# But it accepts strings, and custom emojis can be passed through strings, in name:id format
						# We don't care about the name so we'll just give it this one
						emoji = 'a:{}'.format(custom_emoji_id)

					message = channel.get_partial_message(this_message_id)

					dispatch.run(
						wrapper.client,
						remove_reaction(message, emoji, member),
					)
		else:
			update_role_delta(
				member.id,
				add_roles={role_id},
				channels={channel.id},
				messages={payload.message_id},
				num_reacts=1,
			)
	else:
		update_role_delta(
			member.id,
			remove_roles={role_id},
			channels={channel.id},
			messages={payload.message_id},
			num_unreacts=1,
		)

	if member.id in cooldown:
		now = discord.utils.utcnow()
		if cooldown[member.id] > now:
			if member.id in locked:
				return

			locked.add(member.id)
			await asyncio.sleep((cooldown[member.id] - now).seconds + 1)
			locked.remove(member.id)

		del cooldown[member.id]

	# Calculate reason
	channels_list = []
	for channel_ in queued[member.id].channels:
		channel__ = guild.get_channel(channel_)
		if channel__ is not None:
			channels_list.append(f'#{channel__.name}')
		else:
			channels_list.append('(non-existent channel?)')

	# FIXME: Should be 'A and B' and 'A, B, and C' instead of simple ', '-joining, but whatevs
	channels = ', '.join(channels_list)
	if not channels:
		channels = '(nothing?)'

	if len(queued[member.id].messages) > 1:
		message_noun = 'messages'
	else:
		message_noun = 'a message'

	num_reacts = queued[member.id].num_reacts
	num_unreacts = queued[member.id].num_unreacts

	if num_reacts > 0 and num_unreacts > 0:
		if num_reacts == 1 and num_unreacts == 1:
			reason = f'Member added a reaction to and had one of their reactions removed from {message_noun} with reaction roles in {channels}'
		elif num_reacts == 1:
			reason = f'Member added a reaction to and had some of their reactions removed from {message_noun} with reaction roles in {channels}'
		elif num_unreacts == 1:
			reason = f'Member added reactions to and had one of their reactions removed from {message_noun} with reaction roles in {channels}'
		else:
			reason = f'Member added reactions to and had some of their reactions removed from {message_noun} with reaction roles in {channels}'
	elif num_reacts > 0:
		if num_reacts == 1:
			reason = f'Member added a reaction to {message_noun} with reaction roles in {channels}'
		else:
			reason = f'Member added reactions to {message_noun} with reaction roles in {channels}'
	elif num_unreacts > 0:
		if num_unreacts == 1:
			reason = f'Member’s reaction to {message_noun} with reaction roles was removed in {channels}'
		else:
			reason = f'Member’s reactions to {message_noun} with reaction roles were removed in {channels}'
	else:
		reason = f'Member somehow reacted {num_reacts} times to and had {num_unreacts} reactions of theirs removed from {message_noun} with reaction roles in {channels}?'

	if len(reason) > 500:
		reason = f'{reason[:500]}…'

	# Apply changes
	await utils.givetakeroles(
		member,
		guild,
		list(queued[member.id].add_roles),
		list(queued[member.id].remove_roles),
		reason=reason,
	)

	del queued[member.id]

	cooldown[member.id] = discord.utils.utcnow() + datetime.timedelta(seconds=2)

	await asyncio.sleep(3)

	if member.id in cooldown and cooldown[member.id] < discord.utils.utcnow():
		del cooldown[member.id]

# TODO: This function is unused, group IDs need to be added to it
def add_reaction_role(
	*, channel_id: int, message_id: int, role_id: int, emoji: Union[str, int], max_count: int
) -> bool:
	"""Add a reaction role to a message. `emoji` is either a string for Unicode, or an int of
	the ID of the custom emoji. Returns True if it succeeded, returns False if the entry already
	existed.
	"""
	global cursor
	custom = isinstance(emoji, int)
	unicode = isinstance(emoji, str)
	assert utils.mutually_exclusive(custom, unicode)

	# Check that the message ID doesn't already exist
	result = db_get_messages(channel_id)
	message_ids = [id_ for id_, _ in result]
	if message_id in message_ids:
		return False

	# Add message ID
	cursor.execute("""
			INSERT INTO reactroles_messages
			(message_id, channel_id, max_count)
			VALUES
			(?, ?, ?)
		""",
		(message_id, channel_id, max_count),
	)

	# Check that this entry doesn't already exist
	result = db_get_entries(message_id)
	for _, this_role_id, _, _ in result:
		if this_role_id == role_id:
			return False

	# Add this entry
	if custom:
		emoji_key = 'custom_emoji_id'
	elif unicode:
		emoji_key = 'unicode_emoji'

	cursor.execute("""
			INSERT INTO reactroles_roles
			(message_id, role_id, {})
			VALUES
			(?, ?, ?)
		""".format(emoji_key),
		(message_id, role_id, emoji),
	)

	db_commit()

	return True

def add_reaction_group(
	batch: list[
		tuple[int, int, Union[str, int]]
	],
	*,
	channel_id: int,
	max_count: int,
) -> None:
	"""Add a batch of reaction roles at once. `batch` is a sequence of tuples, each tuple
	containing (in this order) the message ID, role ID, and emoji. The emoji is either a
	string for Unicode, or an int of the ID of the custom emoji. Entries that already exist
	will be silently ignored.
	"""
	global cursor
	register_messages = []
	register_entries = []

	# Just take the ID of the first message
	group_id = batch[0][0]

	for message_id, role_id, emoji in batch:
		# Duplicate entries will be ignored anyway, so don't bother checking them
		register_messages.append(
			(message_id, group_id)
		)
		custom = isinstance(emoji, int)
		unicode = isinstance(emoji, str)
		assert utils.mutually_exclusive(custom, unicode)

		insert_custom = emoji if custom else None
		insert_unicode = emoji if unicode else None

		register_entries.append(
			(message_id, role_id, insert_unicode, insert_custom)
		)

	cursor.execute("""
			INSERT OR IGNORE INTO reactroles_groups
			(group_id, channel_id, max_count)
			VALUES
			(?, ?, ?)
		""",
		(group_id, channel_id, max_count)
	)

	cursor.executemany("""
			INSERT OR IGNORE INTO reactroles_messages
			(message_id, group_id)
			VALUES
			(?, ?)
		""",
		register_messages,
	)
	cursor.executemany("""
			INSERT OR IGNORE INTO reactroles_roles
			(message_id, role_id, unicode_emoji, custom_emoji_id)
			VALUES
			(?, ?, ?, ?)
		""",
		register_entries,
	)
	db_commit()

def remove_reaction_role(*, message_id: int, role_id: int) -> None:
	"""Remove a reaction role from a message."""
	global cursor

	cursor.execute("""
			DELETE FROM reactroles_roles
			WHERE message_id=?
			AND role_id=?
		""",
		(message_id, role_id),
	)

	db_commit()

def remove_message(message_id: int) -> None:
	"""Delete an entire message and its entries."""
	global cursor

	cursor.executescript("""
			DELETE FROM reactroles_messages
			WHERE message_id=?;
			DELETE FROM reactroles_roles
			WHERE message_id=?;
		""",
		(message_id,),
	)

	db_commit()
