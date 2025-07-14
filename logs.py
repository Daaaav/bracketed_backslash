# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Contains the functions that send mod log messages."""

import datetime
import logging
import os
import time
from typing import List, Sequence, Union

import discord

import bot
import utils
import wrapper

async def log_deleted_message(log_channel: discord.TextChannel, message: discord.Message) -> None:
	"""Log a deleted message. Reuploads its attachments if the message had any."""

	if message.is_system():
		content = message.system_content
	else:
		content = message.content

	embed = discord.Embed(
		title=(
			'\N{NO ENTRY SIGN} {system}MESSAGE {withatch}DELETED (SENT {reltime} IN #{chan})'
		).format(
			system='SYSTEM ' if message.is_system() else '',
			withatch='WITH ATTACHMENT ' if message.attachments != [] else '',
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			chan=utils.mdspecialchars(message.channel.name),
		),
		description=content,
		colour=message.author.colour,
	)

	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.display_avatar.url,
	)

	embed.set_footer(text=utils.id_summary(uid=message.author.id, mid=message.id, cid=message.channel.id))
	await log_channel.send(embed=embed)

	if message.attachments != []:
		# FIXME: This only does one attachment!
		filepath = (
				'{atchcche}/{id}_{fn}'
		).format(
			atchcche=bot.attachcache,
			id=message.attachments[0].id,
			fn=message.attachments[0].filename,
		)
		if os.path.isfile(filepath):
			con = (
				'_\N{PAPERCLIP} The attachment for message {0.id} is attached._'
			).format(message)
			try:
				await log_channel.send(
					con,
					file=discord.File(
						filepath,
						filename=message.attachments[0].filename,
					),
				)
			except discord.HTTPException:
				con = (
					'_Failed to upload the attachment for message {0.id}._'
				).format(message)
				await log_channel.send(con)
		else:
			con = (
				'_The attachment for message {0.id} was not found'
				' in the message attachments cache._'
			).format(message)
			await log_channel.send(con)

async def log_pinned_message(log_channel: discord.TextChannel, message: discord.Message) -> None:
	"""Log a pinned message."""

	embed = discord.Embed(
		title=(
			'\N{PUSHPIN} MESSAGE PINNED (SENT {reltime} IN #{chan})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			chan=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=message.author.colour,
	)
	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.display_avatar.url,
	)
	embed.set_footer(
		text=utils.id_summary(uid=message.author.id, mid=message.id, cid=message.channel.id),
	)
	utils.embed_add_jump_link(embed, message)
	await log_channel.send(embed=embed)

async def log_unpinned_message(log_channel: discord.TextChannel, message: discord.Message) -> None:
	"""Log an unpinned message."""

	embed = discord.Embed(
		title=(
			'\N{PUSHPIN} MESSAGE UNPINNED (SENT {reltime} IN #{chan})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			chan=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=message.author.colour,
	)
	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.display_avatar.url,
	)
	embed.set_footer(
		text=utils.id_summary(uid=message.author.id, mid=message.id, cid=message.channel.id),
	)
	utils.embed_add_jump_link(embed, message)
	await log_channel.send(embed=embed)

async def log_deleted_embed(
	log_channel: discord.TextChannel, message: discord.Message, edited_at: datetime.datetime,
) -> None:
	"""Log that an embed was removed from a message. Does not send embed contents or anything."""

	embed = discord.Embed(
		title=(
			'\N{MEMO} EMBED REMOVED FROM MESSAGE (SENT {reltime} IN #{chan})'
		).format(
			reltime=utils.reltime(
				time.mktime(
					message.created_at.timetuple(),
				),
			),
			chan=utils.mdspecialchars(message.channel.name),
		),
		colour=message.author.colour,
	)
	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.display_avatar.url,
	)

	if message.content:
		embed.add_field(name='Message content', value=message.content[:1024], inline=False)
	else:
		embed.add_field(name='No message content', value='\u200b', inline=False)
	if len(message.content) > 1024:
		embed.add_field(name='[continued]', value=message.content[1024:], inline=False)

	embed.add_field(
		name='\u200b',
		value=utils.get_jump_link(message),
	)

	embed.set_footer(text=utils.id_summary(uid=message.author.id, mid=message.id, cid=message.channel.id))
	await log_channel.send(embed=embed)

async def log_edited_message(
	log_channel: discord.TextChannel,
	old: discord.Message,
	new: discord.Message,
	edited_at: datetime.datetime,
) -> None:
	"""Log an edited message."""

	embed = discord.Embed(
		title=(
			'\N{MEMO} MESSAGE{withattach} EDITED (SENT {reltime} IN #{chan})'
		).format(
			withattach=' WITH ATTACHMENT' if new.attachments else '',
			reltime=utils.reltime(
				time.mktime(
					new.created_at.timetuple(),
				),
			),
			chan=utils.mdspecialchars(new.channel.name),
		),
		colour=new.author.colour,
	)
	embed.set_author(
		name=new.author.display_name,
		icon_url=new.author.display_avatar.url,
	)

	if old.content:
		embed.add_field(name='Older content', value=old.content[:1024], inline=False)
	else:
		embed.add_field(name='No older content', value='\u200b', inline=False)
	if len(old.content) > 1024:
		embed.add_field(name='[continued]', value=old.content[1024:], inline=False)

	if new.content:
		embed.add_field(name='Newer content', value=new.content[:1024], inline=False)
	else:
		embed.add_field(name='No newer content', value='\u200b', inline=False)
	if len(new.content) > 1024:
		embed.add_field(name='[continued]', value=new.content[1024:], inline=False)

	embed.add_field(
		name='\u200b',
		value=utils.get_jump_link(new),
	)

	embed.set_footer(text=utils.id_summary(uid=new.author.id, mid=new.id, cid=new.channel.id))
	await log_channel.send(embed=embed)

async def log_changed_nickname(
	log_channel: discord.TextChannel, old: discord.Member, new: discord.Member,
) -> None:
	"""Log that a member's nickname was changed."""

	embed = discord.Embed(
		title='\N{PAGER} CHANGED NICKNAME',
		colour=new.colour,
	)

	embed.set_author(name=new.name, icon_url=new.display_avatar.url)

	if old.nick is None:
		embed.add_field(name='No older nickname', value='\u200b')
	else:
		embed.add_field(
			name='Older nickname',
			value=utils.mdspecialchars(old.nick),
		)

	if new.nick is None:
		embed.add_field(name='No newer nickname', value='\u200b')
	else:
		embed.add_field(
			name='Newer nickname',
			value=utils.mdspecialchars(new.nick),
		)

	embed.set_footer(text=utils.id_summary(uid=new.id))
	await log_channel.send(embed=embed)

async def log_updated_roles(
	log_channel: discord.TextChannel, old: discord.Member, new: discord.Member,
) -> None:
	"""Log that a member had role(s) added or removed from them.
	If the role is the special Nitro Booster role, also log it as boosting or unboosting the server.
	"""

	addedroles = list(set(new.roles) - set(old.roles))
	removedroles = list(set(old.roles) - set(new.roles))

	nitrobooster = new.guild.premium_subscriber_role
	if nitrobooster is not None:
		boosteradd = any(role == nitrobooster for role in addedroles)
		boosterrem = any(role == nitrobooster for role in removedroles)
	else:
		boosteradd = False
		boosterrem = False

	if utils.logdisabled('member_roleadd', new.guild):
		addedroles = []
	if utils.logdisabled('member_roleremove', new.guild):
		removedroles = []

	if (boosteradd and not utils.logdisabled('member_boost', new.guild)) \
	or (boosterrem and not utils.logdisabled('member_unboost', new.guild)):
		embed = discord.Embed(
			title=('BOOSTED SERVER' if boosteradd else 'UNBOOSTED SERVER'),
			colour=nitrobooster.colour
		)
		embed.set_author(
			name=new.display_name,
			icon_url=new.display_avatar.url,
		)
		embed.add_field(
			name=('Added role' if boosteradd else 'Removed role'),
			value=utils.mdspecialchars(nitrobooster.name),
		)
		embed.set_footer(text=utils.id_summary(uid=new.id, rid=nitrobooster.id))
		await log_channel.send(embed=embed)

		if len(addedroles) + len(removedroles) <= 1:
			# Boost role is the only role that was changed, so no need to
			# give another embed that only says "1 role added/removed"...
			return

	if addedroles or removedroles:
		title = ''
		desc = ''
		mixed = addedroles and removedroles
		addedplural = len(addedroles) != 1
		removedplural = len(removedroles) != 1
		roleid = None
		color = utils.colorize(new.id)

		# To not copy-paste code
		def rolelist(roles):
			return '\n'.join(utils.obj_info(role) for role in roles)
		addedroles_list = rolelist(addedroles)
		removedroles_list = rolelist(removedroles)

		if mixed:
			title = '\N{TWISTED RIGHTWARDS ARROWS} ROLES CHANGED FOR USER'
		elif addedroles:
			if addedplural:
				title = 'ROLES ADDED TO USER'
				desc = addedroles_list
			else:
				title = 'ROLE ADDED TO USER'
				desc = '**{}**'.format(utils.mdspecialchars(addedroles[0].name))
				roleid = addedroles[0].id
				color = addedroles[0].colour
			title = '\N{INBOX TRAY} {}'.format(title)
		elif removedroles:
			if removedplural:
				title = 'ROLES REMOVED FROM USER'
				desc = removedroles_list
			else:
				title = 'ROLE REMOVED FROM USER'
				desc = '**{}**'.format(utils.mdspecialchars(removedroles[0].name))
				roleid = removedroles[0].id
				color = removedroles[0].colour
			title = '\N{OUTBOX TRAY} {}'.format(title)

		title = '\N{KEY}{}'.format(title)

		embed = discord.Embed(title=title, description=desc, colour=color)
		utils.paginate_description(embed, max_length=2048)

		embed.set_author(
			name=new.display_name,
			icon_url=new.display_avatar.url,
		)
		embed.set_footer(text=utils.id_summary(uid=new.id, rid=roleid))

		if mixed:
			# To not copy-paste code
			def parse_plural(embed_, plural, text_singular, text_plural, roles_list):
				if plural:
					utils.paginate_field(embed_, max_length=1024,
						name=text_plural,
						value=roles_list,
						inline=False,
					)
				else:
					embed_.add_field(
						name=text_singular,
						value=roles_list,
						inline=False,
					)

			parse_plural(embed, addedplural, 'Added role', 'Added roles', addedroles_list)
			parse_plural(embed, removedplural, 'Removed role', 'Removed roles', removedroles_list)

		await log_channel.send(embed=embed)

async def log_changed_timeout(
	log_channel: discord.TextChannel, old: discord.Member, new: discord.Member,
) -> None:
	"""Log that a member's timed_out_until was changed."""

	if new.timed_out_until is None:
		embed = discord.Embed(
			title='\N{STOPWATCH} TIMEOUT LIFTED',
			colour=new.colour,
		)
	else:
		embed = discord.Embed(
			title='\N{STOPWATCH} TIMEOUT GIVEN',
			colour=new.colour,
		)

		until = new.timed_out_until.timestamp()

		# Round to nearest 10 seconds. That way, someone isn't timed out for "59m58s" or so
		duration = round(until - time.time(), -1)

		embed.add_field(
			name='Duration',
			value=utils.reltime(duration, False, True, True)
		)
		embed.add_field(
			name='Expires',
			value='<t:{ts}:d> <t:{ts}:t>'.format(ts=int(new.timed_out_until.timestamp()))
		)

	embed.set_author(name=new.display_name, icon_url=new.display_avatar.url)

	# Let's also see if we can manage to get the reason...
	try:
		reason = None
		async for entry in new.guild.audit_logs(
			oldest_first=False,
			action=discord.AuditLogAction.member_update
		):
			if entry.target == new and hasattr(entry.changes.after, 'timed_out_until') \
			and entry.changes.before.timed_out_until == old.timed_out_until \
			and entry.changes.after.timed_out_until == new.timed_out_until:
				reason = entry.reason
				break

		if reason is not None:
			embed.add_field(
				name='Reason',
				value=reason,
				inline=False
			)
	except discord.HTTPException:
		pass

	embed.set_footer(text=utils.id_summary(uid=new.id))
	await log_channel.send(embed=embed)

async def log_joined_member(
	log_channel: discord.TextChannel,
	member: discord.Member,
	guild: discord.Guild,
	has_guild_invites: bool,
	has_audit_invites: bool,
	guild_invites: List[discord.Invite],
	all_invites: List[discord.Invite],
) -> None:
	"""Log a member joining a guild."""

	# Figure out which invite the member joined with
	if has_guild_invites:
		if guild.id not in wrapper.inv_cache:
			wrapper.inv_cache[guild.id] = []

		all_invites = utils.invite_diff(wrapper.inv_cache[guild.id], all_invites)
		all_invites = list(filter(lambda i: i.uses is not None and i.uses > 0, all_invites))

		if len(all_invites) == 1:
			invite = all_invites[0]
		else:
			invite = None

	embed = discord.Embed(
		title=(
			'\N{BLACK RIGHTWARDS ARROW} JOINED SERVER'
			if not member.bot else
			'\N{BLACK RIGHTWARDS ARROW}\N{ROBOT FACE} BOT ADDED TO SERVER'
		),
		color=utils.colorize(member),
	)
	embed.add_field(
		name='This server now has',
		value=str(guild.member_count) + ' members',
	)
	embed.add_field(
		name=(
			'Member joined Discord'
			if not member.bot else
			'Bot created'
		),
		value=utils.reltime(time.mktime(member.created_at.timetuple())),
	)

	if not member.bot and has_guild_invites:
		if invite is not None:
			invite_status = (
				'`{invite.code}` by {inviter}'
			).format(
				invite=invite,
				inviter=utils.obj_info(invite.inviter),
			)
		elif not has_audit_invites:
			invite_status = 'I’m not allowed to search the audit log, but here’s the possible invites: {}'.format(
				', '.join('`{invite.code}`'.format(invite=invite) for invite in guild_invites)
			)
		else:
			invite_status = 'Possible invites: {}'.format(
				', '.join('`{invite.code}`'.format(invite=invite) for invite in all_invites)
			)

		embed.add_field(name='Joined with invite', value=invite_status)

	embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
	embed.set_thumbnail(url=member.display_avatar.url)
	embed.set_footer(text=utils.id_summary(uid=member.id))
	await log_channel.send(embed=embed)

async def log_removed_member(
	log_channel: discord.TextChannel,
	member: discord.Member,
	moderator: discord.abc.User,
	action: discord.AuditLogAction,
	reason: str,
) -> None:
	"""Log that a member has been removed from the server.
	This is either because they left on their own, they got kicked, or they got banned.
	"""

	if member.bot:
		bot_ = '\N{ROBOT FACE} BOT'
	else:
		bot_ = ''

	if action is discord.AuditLogAction.kick:
		title = '\N{MANS SHOE}\N{DOOR}{bot} KICKED FROM SERVER'.format(bot=bot_)
	elif action is discord.AuditLogAction.ban:
		# TODO: Implement, taking care of on_member_ban() in the process
		pass
	else:
		title = '\N{DOOR}{bot} REMOVED FROM SERVER'.format(bot=bot_)

	embed = discord.Embed(
		title=title,
		color=utils.colorize(member),
	)

	embed.add_field(
		name='Originally joined server',
		value=utils.reltime(time.mktime(member.joined_at.timetuple())),
	)

	embed.add_field(
		name='This server now has',
		value=str(member.guild.member_count) + ' members',
	)

	if moderator is not None:
		embed.add_field(
			name='Responsible moderator',
			value=utils.obj_info(moderator),
		)
		embed.add_field(
			name='Reason' if reason else 'No reason given',
			value=reason if reason else '\u200b',
		)

	embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
	embed.set_thumbnail(url=member.display_avatar.url)

	embed.set_footer(text=utils.id_summary(uid=member.id))
	await log_channel.send(embed=embed)

async def log_banned_member(
	log_channel: discord.TextChannel,
	guild: discord.Guild,
	user: Union[discord.User, discord.Member],
) -> None:
	"""Log that a user was banned from the guild."""

	# TODO: Modernize this log
	message = '**`>`**👞🚪⛔`user` **``{}``** `({}) banned from server`'.format(
		utils.wrapbackticks(user.name), user.id,
	)
	await log_channel.send(message)

async def log_unbanned_member(
	log_channel: discord.TextChannel, guild: discord.Guild, user: discord.User,
) -> None:
	"""Log that a user has been unbanned from the guild."""

	# TODO: Modernize this log
	message = (
		'**`>`**\N{BABY ANGEL}`user` **``{}``** `({}) unbanned from server`'
	).format(
		utils.wrapbackticks(user.name), user.id,
	)
	await log_channel.send(message)

async def log_created_role(
	log_channel: discord.TextChannel, role: discord.Role, nitro_booster: bool,
) -> None:
	"""Log a created role. Also if it's the Nitro Booster role, add a special message."""

	embed = discord.Embed(
		title='ROLE ADDED',
		description=utils.mdspecialchars(role.name),
		colour=role.colour,
	)

	if nitro_booster:
		embed.set_footer(text='Congrats!')

	await log_channel.send(embed=embed)

async def log_deleted_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log a deleted role."""

	embed = discord.Embed(
		title='ROLE REMOVED',
		description=utils.mdspecialchars(role.name),
		colour=role.colour,
	)
	embed.add_field(name='Original creation time', value=str(role.created_at))
	await log_channel.send(embed=embed)

async def log_renamed_role(
	log_channel: discord.TextChannel, old: discord.Role, new: discord.Role,
) -> None:
	"""Log a renamed role."""

	embed = discord.Embed(
		title='ROLE NAME CHANGED',
		description=utils.mdspecialchars(new.name),
		colour=new.colour,
	)
	embed.add_field(name='Older name', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer name', value=utils.mdspecialchars(new.name))
	await log_channel.send(embed=embed)

async def log_hoisted_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log a hoisted role."""

	embed = discord.Embed(
		title='ROLE HOISTED',
		description='{name}\nID: {id}'.format(
			name=utils.mdspecialchars(role.name),
			id=role.id,
		),
		colour=role.colour,
	)
	await log_channel.send(embed=embed)

async def log_unhoisted_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log an unhoisted role."""

	embed = discord.Embed(
		title='ROLE UNHOISTED',
		description='{name}\nID: {id}'.format(
			name=utils.mdspecialchars(role.name),
			id=role.id,
		),
		colour=role.colour,
	)
	await log_channel.send(embed=embed)

async def log_mentionable_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log that a role is now mentionable by everyone."""

	# TODO: Modernize this log
	message = '**`>`**`role` **``{}``** `({}) is now mentionable`'.format(
		utils.wrapbackticks(role.name), role.id,
	)
	await log_channel.send(message)

async def log_unmentionable_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log that a role is no longer mentionable by everyone."""

	# TODO: Modernize this log
	message = '**`>`**`role` **``{}``** `({}) is no longer mentionable`'.format(
		utils.wrapbackticks(role.name), role.id,
	)
	await log_channel.send(message)

async def log_updated_role_hierarchy(
	log_channel: discord.TextChannel,
	old_list: List[discord.Role],
	new_list: List[discord.Role],
) -> None:
	"""Log an updated role hierarchy."""

	guild = log_channel.guild

	old_list.sort(key=lambda r: r.position, reverse=True)
	new_list.sort(key=lambda r: r.position, reverse=True)

	old_log = ''
	new_log = ''
	generation_string = '{info} {trailing_space}\n'

	for ev_old, ev_new in zip(old_list, new_list):
		old_log += generation_string.format(
			info=utils.obj_info(ev_old),
			trailing_space = '\xa0' * 3,
		)

		tmp_delta = ''
		tmp_old = discord.utils.find(
			# Shut up pylint, discord.utils.find() gets called immediately so it doesn't matter
			lambda r: r.id == ev_new.id, # pylint: disable=cell-var-from-loop
			old_list,
		)
		if tmp_old.position < ev_new.position:
			# Role has been moved up
			tmp_delta = '**\N{UPWARDS ARROW}{}**'.format(
				str(ev_new.position - tmp_old.position)
			)
		if tmp_old.position > ev_new.position:
			# Role has been moved down
			tmp_delta = '**\N{DOWNWARDS ARROW}{}**'.format(
				str(tmp_old.position - ev_new.position)
			)

		new_log += generation_string.format(
			info=utils.obj_info(ev_new),
			trailing_space=tmp_delta,
		)

	# Just for fun, let's generate the embed color by mixing all of the roles'
	# colors together
	colour = int(sum(role.colour.value for role in new_list) / len(new_list))

	# Truncate indicators
	roles = guild.roles
	roles.sort(key=lambda r: r.position)
	if roles[-1].position == new_list[0].position:
		trun_indic_top = ''
	else:
		tmp_num = roles[-1].position - new_list[0].position
		trun_indic_top = '_[{} more role{s} above]_\n'.format(
			tmp_num, s='s' if tmp_num != 1 else '',
		)
	if new_list[-1].position <= 1 or old_list[-1].position <= 1:
		trun_indic_bottom = ''
	else:
		tmp_num = new_list[-1].position - 1
		trun_indic_bottom = '_[{} more role{s} below]_\n'.format(
			tmp_num, s='s' if tmp_num != 1 else '',
		)

	embed = discord.Embed(
		title='\N{KEY}\N{TWISTED RIGHTWARDS ARROWS} ROLE HIERARCHY UPDATED',
		colour=colour,
	)
	embed.add_field(
		name='Older hierarchy',
		value='{}{}{}'.format(trun_indic_top, old_log, trun_indic_bottom),
	)
	embed.add_field(
		name='Newer hierarchy',
		value='{}{}{}'.format(trun_indic_top, new_log, trun_indic_bottom),
	)

	await log_channel.send(embed=embed)

async def log_changed_role_color(
	log_channel: discord.TextChannel, old: discord.Role, new: discord.Role,
) -> None:
	"""Log a changed role color."""

	embed = discord.Embed(
		title='ROLE COLOR CHANGED',
		description=utils.mdspecialchars(new.name),
		colour=new.colour,
	)
	embed.add_field(
		name='Older color',
		value='(default)' if old.colour.value == 0 else str(old.colour).upper(),
	)
	embed.add_field(
		name='Newer color',
		value='(default)' if new.colour.value == 0 else str(new.colour).upper(),
	)
	await log_channel.send(embed=embed)

async def log_changed_role_permissions(
	log_channel: discord.TextChannel, old: discord.Role, new: discord.Role,
) -> None:
	"""Log the changed permissions of a role."""

	# FIXME: This only does one permission!
	diff = list(set(old.permissions).symmetric_difference(set(new.permissions)))
	embed = discord.Embed(
		title='ROLE PERMISSIONS CHANGED',
		description=utils.obj_info(new),
		colour=new.colour,
	)
	embed.add_field(name='Permission updated', value=diff[0][0])
	embed.add_field(
		name='Older permission',
		value=str(dict(old.permissions)[diff[0][0]]),
	)
	embed.add_field(
		name='Newer permission',
		value=str(dict(new.permissions)[diff[0][0]]),
	)
	await log_channel.send(embed=embed)

async def log_added_reaction(
	log_channel: discord.TextChannel,
	reaction: discord.Reaction,
	user: Union[discord.Member, discord.User],
) -> None:
	"""Log an added reaction."""

	message = reaction.message
	is_custom_emoji = hasattr(reaction.emoji, 'name')

	embed = discord.Embed(
		title=(
			'\N{WHITE SMILING FACE}\N{UPWARDS BLACK ARROW} '
			'REACTION ADDED TO MESSAGE (SENT {reltime} IN #{name})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			name=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=user.colour,
	)

	embed.set_author(
		name=user.display_name,
		icon_url=user.display_avatar.url,
	)

	embed.add_field(
		name='Reaction',
		value=utils.mdspecialchars(':{}:'.format(reaction.emoji.name))
		if is_custom_emoji else reaction.emoji,
	)

	if is_custom_emoji:
		embed.set_thumbnail(
			url=discord.Emoji.url.__get__( # pylint: disable=no-member
				reaction.emoji,
			),
		)

	embed.add_field(
		name='\u200b',
		value=utils.get_jump_link(message),
		inline=False,
	)

	embed.set_footer(
		text=utils.id_summary(
			uid=user.id,
			mid=message.id,
			eid=reaction.emoji.id if is_custom_emoji else '',
			character='\n' if is_custom_emoji else ' ',
		)
	)
	await log_channel.send(embed=embed)

async def log_removed_reaction(
	log_channel: discord.TextChannel,
	reaction: discord.Reaction,
	user: Union[discord.Member, discord.User],
) -> None:
	"""Log a removed reaction."""

	message = reaction.message

	is_custom_emoji = hasattr(reaction.emoji, 'name')

	embed = discord.Embed(
		title=(
			'\N{WHITE SMILING FACE}\N{NO ENTRY SIGN} '
			'REACTION REMOVED FROM MESSAGE (SENT {reltime} IN #{name})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			name=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=user.colour,
	)

	embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

	embed.add_field(
		name='Reaction',
		value=utils.mdspecialchars(':{}:'.format(reaction.emoji.name))
		if is_custom_emoji else reaction.emoji,
	)

	if is_custom_emoji:
		embed.set_thumbnail(
			url=discord.Emoji.url.__get__( # pylint: disable=no-member
				reaction.emoji,
			),
		)

	embed.add_field(
		name='\u200b',
		value=utils.get_jump_link(message),
		inline=False,
	)

	embed.set_footer(
		text=utils.id_summary(
			uid=user.id,
			mid=message.id,
			eid=reaction.emoji.id if is_custom_emoji else '',
			character='\n' if is_custom_emoji else ' ',
		)
	)
	await log_channel.send(embed=embed)

async def log_cleared_reactions(
	log_channel: discord.TextChannel,
	message: discord.Message,
	reactions: List[discord.Reaction],
) -> None:
	"""Log a message that has been cleared of reactions."""

	reaction_list = ''
	for reaction in reactions:
		try:
			name = reaction.emoji.name
			custom_emote = True
		except AttributeError:
			name = reaction.emoji
			custom_emote = False
		reaction_list += str(reaction.count) + ' '
		if custom_emote:
			reaction_list += '{name} ({id})\n'.format(
					name=str(reaction.emoji),
					id=reaction.emoji.id,
				)
		else:
			reaction_list += name + '\n'
	embed = discord.Embed(
		title='REACTIONS CLEARED FROM MESSAGE (SENT {reltime} IN #{channel.name})'.format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			channel=message.channel,
		),
		description=message.content,
		colour=message.author.colour,
	)
	embed.add_field(name='Reactions', value=reaction_list)
	utils.embed_add_jump_link(embed, message)
	embed.set_footer(text=utils.id_summary(cid=message.channel.id, mid=message.id))
	await log_channel.send(embed=embed)

async def log_changed_guild_icon(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed guild icon."""

	embed = discord.Embed(title='SERVER CHANGED ICON')
	if old.icon is not None:
		embed.set_thumbnail(url=old.icon.url)
	embed.add_field(
		name='No older icon' if old.icon is None else 'Older icon URL (thumbnail)',
		value='\u200b' if old.icon is None else old.icon.url,
	)
	embed.add_field(
		name='No newer icon' if new.icon is None else 'Newer icon URL (inset image)',
		value='\u200b' if new.icon is None else new.icon.url,
	)
	if new.icon is not None:
		embed.set_image(url=new.icon.url)
	await log_channel.send(embed=embed)

async def log_renamed_guild(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a renamed guild."""

	embed = discord.Embed(title='SERVER CHANGED NAME')
	if new.icon is not None:
		embed.set_thumbnail(url=new.icon.url)
	embed.add_field(name='Older name', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer name', value=utils.mdspecialchars(new.name))
	await log_channel.send(embed=embed)

async def log_changed_guild_afk_timeout(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed AFK timeout."""

	b_m, b_s = divmod(old.afk_timeout, 60)
	b_h, b_m = divmod(b_m, 60)
	a_m, a_s = divmod(new.afk_timeout, 60)
	a_h, a_s = divmod(a_m, 60)
	embed = discord.Embed(title='AFK TIMEOUT CHANGED')
	if new.icon is not None:
		embed.set_thumbnail(url=new.icon.url)
	embed.add_field(
		name='Older timeout',
		value='{h}h {m}m {s}s'.format(h=b_h, m=b_m, s=b_s),
	)
	embed.add_field(
		name='Newer timeout',
		value='{h}h {m}m {s}s'.format(h=a_h, m=a_m, s=a_s),
	)
	await log_channel.send(embed=embed)

async def log_changed_guild_afk_channel(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed AFK channel."""

	embed = discord.Embed(title='AFK CHANNEL CHANGED')
	if new.icon is not None:
		embed.set_thumbnail(url=new.icon.url)
	embed.add_field(
		name='No older channel' if old.afk_channel is None else 'Older channel',
		value='\u200b' if old.afk_channel is None else utils.obj_info(old.afk_channel),
	)
	embed.add_field(
		name='No newer channel' if new.afk_channel is None else 'Newer channel',
		value='\u200b' if new.afk_channel is None else utils.obj_info(new.afk_channel),
	)
	await log_channel.send(embed=embed)

async def log_changed_guild_verification_level(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed verification level."""

	embed = discord.Embed(title='VERIFICATION LEVEL CHANGED')
	if new.icon is not None:
		embed.set_thumbnail(url=new.icon.url)
	embed.add_field(
		name='Older level',
		value=str(old.verification_level).title(),
	)
	embed.add_field(
		name='Newer level',
		value=str(new.verification_level).title(),
	)
	await log_channel.send(embed=embed)

async def log_changed_guild_mfa_level(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log two-factor authentication being turned on or off."""

	if old.mfa_level == discord.MFALevel.disabled and new.mfa_level == discord.MFALevel.require_2fa:
		embed=discord.Embed(title='SERVER 2FA ENABLED')
	elif old.mfa_level == discord.MFALevel.require_2fa and new.mfa_level == discord.MFALevel.disabled:
		embed=discord.Embed(title='SERVER 2FA DISABLED')
	await log_channel.send(embed=embed)

async def log_changed_guild_emotes_or_stickers(
	log_channel: discord.TextChannel,
	old: Sequence[Union[discord.Emoji, discord.Sticker]],
	new: Sequence[Union[discord.Emoji, discord.Sticker]],
	is_sticker: bool
) -> None:
	"""Log emotes or stickers being added or removed from a guild, or edited.
	These are also called "expressions" so that's what we'll call them here.
	(Actually, there's also soundboard sounds, but I don't think there's events for those...)
	"""

	diff = list(set(old).symmetric_difference(set(new)))
	expr_list = ''
	for expr in diff:
		expr_list += '{str} – {0}\n'.format(utils.obj_info(expr), str=str(expr))
	if len(old) > len(new):
		title = 'STICKER REMOVED' if is_sticker else 'EMOTE REMOVED'
	elif len(old) < len(new):
		title = 'STICKER ADDED' if is_sticker else 'EMOTE ADDED'
	else:
		# Attribute change, get the emote/sticker in question
		for old_expr in old:
			for new_expr in new:
				if old_expr.id == new_expr.id:
					if old_expr.name != new_expr.name \
					or (hasattr(old_expr, 'emoji') and old_expr.emoji != new_expr.emoji) \
					or (hasattr(old_expr, 'description') and old_expr.description != new_expr.description):
						changed_old_expr = old_expr
						changed_new_expr = new_expr
						break

		if changed_new_expr is None:
			return

		embed = discord.Embed(
			title='STICKER EDITED' if is_sticker else 'EMOTE EDITED',
			description=str(changed_new_expr),
		)
		embed.add_field(name='Older name', value=changed_old_expr.name)
		embed.add_field(name='Newer name', value=changed_new_expr.name)
		await log_channel.send(embed=embed)
		return
	embed = discord.Embed(title=title)
	embed.add_field(name='Stickers' if is_sticker else 'Emotes', value=expr_list)
	await log_channel.send(embed=embed)

async def log_created_guild_channel(
	log_channel: discord.TextChannel, channel: discord.abc.GuildChannel,
) -> None:
	"""Log a created channel."""

	embed = discord.Embed(
		title='{emoji}\N{BLACK RIGHTWARDS ARROW} {name} CREATED'.format(
			emoji=utils.get_channel_type_emoji(channel),
			name=utils.get_channel_type_name(channel).upper(),
		),
		description='**{name}**'.format(name=utils.mdspecialchars(channel.name)),
		colour=utils.colorize(channel.id),
	)

	if channel.type is not discord.ChannelType.category:
		embed.add_field(
			name='Uncategorized' if channel.category is None else 'Category',
			value='\u200b' if channel.category is None
			else utils.obj_info(channel.category),
		)

	# Text-specific properties

	if hasattr(channel, 'slowmode_delay'):
		embed.add_field(
			name='No slowmode' if channel.slowmode_delay == 0 else 'Slowmode',
			value='\u200b' if channel.slowmode_delay == 0 else '{} seconds'.format(
				channel.slowmode_delay,
			), # TODO: Account for hours/minutes/etc. Should be a utils.py function
		)

	if hasattr(channel, 'topic'):
		embed.add_field(
			name='No topic' if channel.topic is None else 'Topic',
			value='\u200b' if channel.topic is None else channel.topic,
			inline=False,
		)

	# Voice-specific properties

	if hasattr(channel, 'bitrate'):
		embed.add_field(
			name='Bitrate',
			value=utils.get_kbps(channel.bitrate),
		)

	if hasattr(channel, 'user_limit'):
		embed.add_field(
			name='No user limit' if channel.user_limit == 0 else 'User limit',
			value='\u200b' if channel.user_limit == 0 else '{} users'.format(
				channel.user_limit,
			),
		)

	embed.set_footer(text=utils.id_summary(cid=channel.id))
	await log_channel.send(embed=embed)

async def log_deleted_guild_channel(
	log_channel: discord.TextChannel, channel: discord.abc.GuildChannel,
) -> None:
	"""Log a deleted channel."""

	embed = discord.Embed(
		title='{emoji}\N{NO ENTRY SIGN} {name} DELETED'.format(
			emoji=utils.get_channel_type_emoji(channel),
			name=utils.get_channel_type_name(channel).upper(),
		),
		description='**{name}**'.format(name=utils.mdspecialchars(channel.name)),
		colour=utils.colorize(channel.id),
	)

	if channel.type is not discord.ChannelType.category:
		embed.add_field(
			name='Uncategorized' if channel.category is None else 'Category',
			value='\u200b' if channel.category is None
			else utils.obj_info(channel.category),
		)

	embed.add_field(
		name='Originally created',
		value=utils.reltime(time.mktime(channel.created_at.timetuple())),
	)

	embed.set_footer(text=utils.id_summary(cid=channel.id))
	await log_channel.send(embed=embed)

async def log_bulk_deleted_messages(
	log_channel: discord.TextChannel,
	channel: discord.TextChannel,
	payload: discord.RawBulkMessageDeleteEvent,
) -> None:
	"""Log a bulk message deletion event."""

	oldest_id = next(iter(payload.message_ids))
	newest_id = oldest_id
	for mid in payload.message_ids:
		if mid < oldest_id:
			oldest_id = mid
		if mid > newest_id:
			newest_id = mid

	oldest_time = ((oldest_id >> 22) + 1420070400000)/1000
	newest_time = ((newest_id >> 22) + 1420070400000)/1000

	embed = discord.Embed(
		title='\N{RADIOACTIVE SIGN} {amount} MESSAGES PURGED IN #{channel.name}'.format(
			amount=len(payload.message_ids), channel=channel
		),
		description=(
			'Oldest deleted message: {oi} (sent {ot})\n'
			'Newest deleted message: {ni} (sent {nt})'
		).format(
			oi=oldest_id, ot=utils.reltime(oldest_time),
			ni=newest_id, nt=utils.reltime(newest_time)
		),
		colour=0xFF0000,
	)

	embed.set_footer(text=utils.id_summary(cid=channel.id))
	await log_channel.send(embed=embed)

async def log_deleted_uncached_message(
	log_channel: discord.TextChannel,
	channel: discord.TextChannel,
	payload: discord.RawMessageDeleteEvent,
) -> None:
	"""Log a deleted uncached message."""

	embed = discord.Embed(
		title='UNCACHED MESSAGE DELETED IN #{0.name}'.format(channel),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID and its channel.'
		),
		colour=channel.guild.me.colour,
	)
	embed.set_footer(text=utils.id_summary(mid=payload.message_id, cid=channel.id))
	await log_channel.send(embed=embed)

async def log_updated_uncached_message(
	log_channel: discord.TextChannel,
	channel: discord.TextChannel,
	payload: discord.RawMessageUpdateEvent,
) -> None:
	"""Log an updated uncached message."""

	if 'edited_timestamp' in payload.data:
		edited_iso = payload.data['edited_timestamp']
		if edited_iso is None \
		or datetime.datetime.fromisoformat(edited_iso) < discord.utils.utcnow() - datetime.timedelta(days=1):
			logging.info(
				'Suppressing raw message edit event for {} because it was last edited {}'.format(
					payload.data['id'], edited_iso
				)
			)
			return

	author = None
	author_id = None
	embed_colour = None
	if 'author' in payload.data:
		author = channel.guild.get_member(int(payload.data['author']['id']))
		if author is not None:
			author_id = author.id
			embed_colour = author.colour

	if 'content' in payload.data:
		content = payload.data['content']
	else:
		content = '_(unknown content)_'

	embed = discord.Embed(
		title=(
			'UNCACHED MESSAGE UPDATED (SENT {reltime}'
			' IN #{0.name}).'
			' NEWER CONTENT AND PROPERTIES:'
		).format(
			channel,
			reltime=utils.reltime(
				time.mktime(
					discord.utils.snowflake_time(int(payload.data['id'])).timetuple(),
				)
			),
		),
		description=content,
		colour=embed_colour,
	)
	if author is not None:
		embed.set_author(
			name=author.display_name,
			icon_url=author.display_avatar.url,
		)
	if 'pinned' in payload.data:
		embed.add_field(
			name='Pinned',
			value='Yes' if payload.data['pinned'] else 'No',
		)
	if 'tts' in payload.data:
		embed.add_field(
			name='TTS',
			value='Yes' if payload.data['tts'] else 'No',
		)
	if 'embeds' in payload.data:
		embed.add_field(
			name='Rich embed',
			value=(
				'``{}``'.format(utils.wrapbackticks(str(payload.data['embeds']['rich'])))
				if 'rich' in payload.data['embeds']
				else '(none)'
			),
		)
	embed.add_field(
		name='\u200b',
		value=(
			'Since this message is uncached,'
			' I can’t give you its older properties.'
		)
	)
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.data['id'])
	embed.set_footer(text=utils.id_summary(uid=author_id, mid=payload.data['id']))
	await log_channel.send(embed=embed)

async def log_added_uncached_reaction(
	log_channel: discord.TextChannel,
	channel: discord.TextChannel,
	payload: discord.RawReactionActionEvent,
) -> None:
	"""Log an added reaction to an uncached message."""

	author = channel.guild.get_member(payload.user_id)
	embed = discord.Embed(
		title='REACTION ADDED TO UNCACHED MESSAGE IN #{0.name}'.format(channel),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID, author, and channel.'
		),
		colour=channel.guild.me.colour,
	)
	embed.set_author(
		name=author.display_name,
		icon_url=author.display_avatar.url,
	)
	embed.add_field(
		name='Reacting member',
		value=author.mention,
	)
	embed.add_field(
		name='Reaction',
		value=(
			'<:{name}:{id}>'
		).format(
			name=payload.emoji.name,
			id=payload.emoji.id,
		) if payload.emoji.id is not None else payload.emoji.name,
	)
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.message_id)
	embed.set_footer(text=utils.id_summary(uid=author.id, cid=channel.id, mid=payload.message_id))
	await log_channel.send(embed=embed)

async def log_removed_uncached_reaction(
	log_channel: discord.TextChannel,
	channel: discord.TextChannel,
	payload: discord.RawReactionActionEvent,
) -> None:
	"""Log a removed reaction from an uncached message."""

	author = channel.guild.get_member(payload.user_id)
	embed = discord.Embed(
		title='REACTION REMOVED FROM UNCACHED MESSAGE IN #{0.name}'.format(channel),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID, author, and channel.'
		),
		colour=channel.guild.me.colour,
	)
	embed.set_author(
		name=author.display_name,
		icon_url=author.display_avatar.url,
	)
	embed.add_field(
		name='Reacting member',
		value=author.mention,
	)
	embed.add_field(
		name='Reaction',
		value=(
			'<:{name}:{id}>'
		).format(
			name=payload.emoji.name,
			id=payload.emoji.id,
		) if payload.emoji.id is not None else payload.emoji.name,
	)
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.message_id)
	embed.set_footer(text=utils.id_summary(uid=author.id, cid=channel.id, mid=payload.message_id))
	await log_channel.send(embed=embed)

async def log_cleared_uncached_reactions(
	log_channel: discord.TextChannel,
	channel: discord.TextChannel,
	payload: discord.RawReactionClearEvent,
) -> None:
	"""Log an uncached message that has been cleared of its reactions."""

	embed = discord.Embed(
		title=(
			'REACTIONS CLEARED FROM UNCACHED MESSAGE'
			' IN #{0.name}'
		).format(channel),
		description=(
			'Since this message is uncached, I can’t give you'
			' any more information than its ID and its channel.'
		),
		colour=channel.guild.me.colour,
	)
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.message_id)
	embed.set_footer(text=utils.id_summary(cid=channel.id, mid=payload.message_id))
	await log_channel.send(embed=embed)

async def log_renamed_guild_channel(
	log_channel: discord.TextChannel,
	old: discord.abc.GuildChannel,
	new: discord.abc.GuildChannel,
) -> None:
	"""Log a renamed channel."""

	embed = discord.Embed(
		title='{emoji}\N{TWISTED RIGHTWARDS ARROWS} {name} RENAMED'.format(
			emoji=utils.get_channel_type_emoji(new),
			name=utils.get_channel_type_name(new).upper(),
		),
		description=utils.obj_info(new),
		colour=new.guild.me.colour,
	)
	embed.add_field(name='Older name', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer name', value=utils.mdspecialchars(new.name))
	await log_channel.send(embed=embed)

async def log_created_thread(
	log_channel: discord.TextChannel, thread: discord.Thread
) -> None:
	"""Log a created thread."""

	embed = discord.Embed(
		title='{emoji}\N{BLACK RIGHTWARDS ARROW} {name} CREATED'.format(
			emoji=utils.get_channel_type_emoji(thread),
			name=utils.get_channel_type_name(thread).upper(),
		),
		description='**{name}**'.format(name=utils.mdspecialchars(thread.name)),
		colour=utils.colorize(thread.id),
	)

	parent_id = None
	if thread.parent is not None:
		# It can be None, but that would probably be very bad
		embed.add_field(
			name='Parent channel',
			value='#{name}'.format(name=utils.mdspecialchars(thread.parent.name)),
		)
		parent_id = thread.parent.id

	embed.set_footer(text=utils.id_summary(tid=thread.id, cid=parent_id))
	await log_channel.send(embed=embed)

async def log_deleted_thread(
	log_channel: discord.TextChannel,
	parent_channel: Union[discord.ForumChannel, discord.TextChannel],
	payload: discord.RawThreadDeleteEvent
) -> None:
	"""Log a deleted thread."""

	description = None
	if payload.thread is not None:
		description = '**{name}**'.format(name=utils.mdspecialchars(payload.thread.name))

	embed = discord.Embed(
		title='{emoji}\N{NO ENTRY SIGN} {name} DELETED'.format(
			emoji=utils.get_channel_type_emoji(channel=None, channeltype=payload.thread_type),
			name=utils.get_channel_type_name(channel=None, channeltype=payload.thread_type).upper(),
		),
		description=description,
		colour=utils.colorize(payload.thread_id),
	)

	embed.add_field(
		name='Originally created',
		value=utils.reltime(time.mktime(discord.utils.snowflake_time(payload.thread_id).timetuple())),
	)

	embed.set_footer(text=utils.id_summary(tid=payload.thread_id, cid=payload.parent_id))

	await log_channel.send(embed=embed)
