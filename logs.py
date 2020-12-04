"""Contains the functions that send mod log messages."""

import datetime
import os
import time
from typing import List, Sequence, Union

import discord

import bot
import config
import utils
import wrapper

async def log_deleted_message(log_channel: discord.TextChannel, message: discord.Message) -> None:
	"""Log a deleted message. Reuploads its attachments if the message had any."""

	if message.type is not discord.MessageType.default:
		content = message.system_content
	else:
		content = message.content

	embed = discord.Embed(
		title=(
			'\N{NO ENTRY SIGN}{system}MESSAGE {withatch}DELETED (SENT {reltime} IN #{chan})'
		).format(
			system='SYSTEM ' if message.type is not discord.MessageType.default else '',
			withatch='WITH ATTACHMENT ' if message.attachments != [] else '',
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			chan=utils.mdspecialchars(message.channel.name),
		),
		description=content,
		colour=message.author.colour,
		timestamp=datetime.datetime.now(),
	)

	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.avatar_url,
	)

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(
			utils.id_summary(uid=message.author.id, mid=message.id, cid=message.channel.id),
		)
	)

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
				'_\N{PAPERCLIP}The attachment for message {0.id} is attached._'
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
			'\N{PUSHPIN}MESSAGE PINNED (SENT {reltime} IN #{chan})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			chan=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=message.author.colour,
	)
	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.avatar_url,
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
			'\N{PUSHPIN}MESSAGE UNPINNED (SENT {reltime} IN #{chan})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			chan=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=message.author.colour,
	)
	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.avatar_url,
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
			'\N{MEMO}EMBED REMOVED FROM MESSAGE (SENT {reltime} IN #{chan})'
		).format(
			reltime=utils.reltime(
				time.mktime(
					message.created_at.timetuple(),
				),
			),
			chan=utils.mdspecialchars(message.channel.name),
		),
		colour=message.author.colour,
		timestamp=edited_at,
	)
	embed.set_author(
		name=message.author.display_name,
		icon_url=message.author.avatar_url,
	)

	if message.content:
		embed.add_field(name='Message Content', value=message.content[:1024], inline=False)
	else:
		embed.add_field(name='No Message Content', value='_(none)_', inline=False)
	if len(message.content) > 1024:
		embed.add_field(name='[continued]', value=message.content[1024:], inline=False)

	embed.add_field(
		name='\u200b',
		value=utils.get_jump_link(message) + '\n' + utils.mdspecialchars(
			utils.id_summary(uid=message.author.id, mid=message.id, cid=message.channel.id),
		),
	)
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
			'\N{MEMO}MESSAGE{withattach} EDITED (SENT {reltime} IN #{chan})'
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
		timestamp=edited_at,
	)
	embed.set_author(
		name=new.author.display_name,
		icon_url=new.author.avatar_url,
	)

	if old.content:
		embed.add_field(name='Older Content', value=old.content[:1024], inline=False)
	else:
		embed.add_field(name='No Older Content', value='_(none)_', inline=False)
	if len(old.content) > 1024:
		embed.add_field(name='[continued]', value=old.content[1024:], inline=False)

	if new.content:
		embed.add_field(name='Newer Content', value=new.content[:1024], inline=False)
	else:
		embed.add_field(name='No Newer Content', value='_(none)_', inline=False)
	if len(new.content) > 1024:
		embed.add_field(name='[continued]', value=new.content[1024:], inline=False)

	embed.add_field(
		name='\u200b',
		value=utils.get_jump_link(new) + '\n' + utils.mdspecialchars(
			utils.id_summary(uid=new.author.id, mid=new.id, cid=new.channel.id),
		),
	)
	await log_channel.send(embed=embed)

async def log_changed_nickname(
	log_channel: discord.TextChannel, old: discord.Member, new: discord.Member,
) -> None:
	"""Log that a member's nickname was changed."""

	embed = discord.Embed(
		title='\N{REGIONAL INDICATOR SYMBOL LETTER N}\N{PAGER}CHANGED NICKNAME',
		colour=new.colour,
		timestamp=datetime.datetime.now(),
	)

	embed.set_author(name=new.name, icon_url=new.avatar_url)

	if old.nick is None:
		embed.add_field(name='No Older Nickname', value='\u200b')
	else:
		embed.add_field(
			name='Older Nickname',
			value=utils.mdspecialchars(old.nick),
		)

	if new.nick is None:
		embed.add_field(name='No Newer Nickname', value='\u200b')
	else:
		embed.add_field(
			name='Newer Nickname',
			value=utils.mdspecialchars(new.nick),
		)

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(
			utils.id_summary(uid=new.id),
		),
		inline=False,
	)

	await log_channel.send(embed=embed)

async def log_updated_roles(
	log_channel: discord.TextChannel, old: discord.Member, new: discord.Member,
) -> None:
	"""Log that a member had role(s) added or removed from them.
	If the role is the special Nitro Booster role, also log it as boosting or unboosting the server.
	"""

	addedroles = list(set(new.roles) - set(old.roles))
	removedroles = list(set(old.roles) - set(new.roles))

	nitroboosterid = config.get_s('nitrobooster', new.guild.id)
	if nitroboosterid != 0:
		boosteradd = any(r.id == nitroboosterid for r in addedroles)
		boosterrem = any(r.id == nitroboosterid for r in removedroles)
	else:
		boosteradd = False
		boosterrem = False

	if boosteradd:
		nitrobooster = next(r for r in addedroles if r.id == nitroboosterid)
		if len(addedroles) == 1:
			addedroles = []
	if boosterrem:
		nitrobooster = next(r for r in removedroles if r.id == nitroboosterid)
		if len(removedroles) == 1:
			removedroles = []

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
			icon_url=new.avatar_url,
		)
		embed.add_field(
			name=('Added role' if boosteradd else 'Removed role'),
			value=utils.mdspecialchars(nitrobooster.name),
		)
		embed.set_footer(text=utils.id_summary(uid=new.id, rid=nitrobooster.id))
		await log_channel.send(embed=embed)
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
			title = '\N{TWISTED RIGHTWARDS ARROWS}ROLES CHANGED FOR USER'
		elif addedroles:
			if addedplural:
				title = 'ROLES ADDED TO USER'
				desc = addedroles_list
			else:
				title = 'ROLE ADDED TO USER'
				desc = '**{}**'.format(utils.mdspecialchars(addedroles[0].name))
				roleid = addedroles[0].id
				color = addedroles[0].colour
			title = '\N{INBOX TRAY}{}'.format(title)
		elif removedroles:
			if removedplural:
				title = 'ROLES REMOVED FROM USER'
				desc = removedroles_list
			else:
				title = 'ROLE REMOVED FROM USER'
				desc = '**{}**'.format(utils.mdspecialchars(removedroles[0].name))
				roleid = removedroles[0].id
				color = removedroles[0].colour
			title = '\N{OUTBOX TRAY}{}'.format(title)

		title = '\N{KEY}{}'.format(title)

		embed = discord.Embed(title=title, description=desc, colour=color)
		utils.paginate_description(embed, max_length=2048)

		embed.set_author(
			name=new.display_name,
			icon_url=new.avatar_url,
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
						value=addedroles_list,
						inline=False,
					)

			parse_plural(embed, addedplural, 'Added role', 'Added roles', addedroles_list)
			parse_plural(embed, removedplural, 'Removed role', 'Removed roles', removedroles_list)

		await log_channel.send(embed=embed)

async def log_changed_tag(
	log_channel: discord.TextChannel, old: discord.User, new: discord.User,
) -> None:
	"""Log that a user's username changed.
	If their discriminator changed as well, then log that too.
	"""

	title = '\N{REGIONAL INDICATOR SYMBOL LETTER U}\N{PAGER}CHANGED USERNAME'
	if old.discriminator != new.discriminator:
		title += ' AND DISCRIMINATOR \N{SMALL ORANGE DIAMOND}'

	embed = discord.Embed(
		title=title,
		colour=new.colour, # FIXME: Outside guilds, users don't have a color!
		timestamp=datetime.datetime.now(),
	)

	embed.set_author(
		name=new.display_name,
		icon_url=new.avatar_url,
	)

	embed.add_field(name='Older Username', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer Username', value=utils.mdspecialchars(new.name))

	if old.discriminator != new.discriminator:
		embed.add_field(name='\u200b', value='\u200b', inline=False)

		embed.add_field(
			name='Older Discriminator',
			value='#' + old.discriminator,
		)

		embed.add_field(name='Newer Discriminator', value='#' + new.discriminator)

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(utils.id_summary(uid=new.id)),
		inline=False,
	)

	await log_channel.send(embed=embed)

async def log_changed_avatar(
	log_channel: discord.TextChannel, old: discord.User, new: discord.User,
) -> None:
	"""Log that a user's avatar changed."""

	if not old.avatar and new.avatar:
		title='\N{BUSTS IN SILHOUETTE}\N{UPWARDS BLACK ARROW}ADDED AVATAR'
		desc=new.avatar
	elif old.avatar and not new.avatar:
		title='\N{BUSTS IN SILHOUETTE}\N{NO ENTRY SIGN}REMOVED AVATAR'
		desc=old.avatar
	else:
		title=(
			'\N{BUSTS IN SILHOUETTE}'
			'\N{BLACK RIGHTWARDS ARROW}'
			'\N{BUSTS IN SILHOUETTE}'
			'CHANGED AVATAR'
		)
		desc=''

	embed = discord.Embed(
		title=title,
		description=desc,
		colour=new.colour, # FIXME: Outside guilds, users don't have a color!
		timestamp=datetime.datetime.now(),
	)

	embed.set_author(name=new.display_name, icon_url=new.avatar_url)

	if not old.avatar and new.avatar:
		embed.set_image(url=new.avatar_url)
	elif old.avatar and not new.avatar:
		embed.set_image(url=old.avatar_url)
	else:
		embed.add_field(name='Older Avatar Hash (Thumbnail)', value=old.avatar)
		embed.add_field(
			name='Newer Avatar Hash (Inset Image)',
			value=new.avatar,
			inline=False,
		)

		embed.set_thumbnail(url=old.avatar_url)
		embed.set_image(url=new.avatar_url)

	# This is not standard procedure, but only because we can't place the ID summary
	# field after an inset image
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
		all_invites = utils.invite_diff(wrapper.inv_cache[guild.id], all_invites)

		if len(all_invites) == 1:
			invite = all_invites[0]
		else:
			invite = None

	embed = discord.Embed(
		title=(
			'\N{BLACK RIGHTWARDS ARROW}JOINED SERVER'
			if not member.bot else
			'\N{BLACK RIGHTWARDS ARROW}\N{ROBOT FACE}BOT ADDED TO SERVER'
		),
		color=utils.colorize(member),
		timestamp=datetime.datetime.now(),
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

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(utils.id_summary(uid=member.id)),
		inline=False,
	)

	embed.set_author(name=member.display_name, icon_url=member.avatar_url)
	embed.set_thumbnail(url=member.avatar_url)
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
		bot_ = '\N{ROBOT FACE}BOT '
	else:
		bot_ = ''

	if action is discord.AuditLogAction.kick:
		title = '\N{MANS SHOE}\N{DOOR}{bot}KICKED FROM SERVER'.format(bot=bot_)
	elif action is discord.AuditLogAction.ban:
		# TODO: Implement, taking care of on_member_ban() in the process
		pass
	else:
		title = '\N{DOOR}{bot}REMOVED FROM SERVER'.format(bot=bot_)

	embed = discord.Embed(
		title=title,
		color=utils.colorize(member),
		timestamp=datetime.datetime.now(),
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

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(utils.id_summary(uid=member.id)),
		inline=False,
	)

	embed.set_author(name=member.display_name, icon_url=member.avatar_url)
	embed.set_thumbnail(url=member.avatar_url)

	await log_channel.send(embed=embed)

async def log_banned_member(
	log_channel: discord.TextChannel,
	guild: discord.Guild,
	user: Union[discord.User, discord.Member],
) -> None:
	"""Log that a user was banned from the guild."""

	# TODO: Modernize this log
	message = '**`>`**👞🚪⛔`user` **``{}``**`#{}` `({}) banned from server {} ({})`'.format(
		utils.wrapbackticks(user.name), user.discriminator, user.id, guild.name, guild.id,
	)
	await log_channel.send(message)

async def log_unbanned_member(
	log_channel: discord.TextChannel, guild: discord.Guild, user: discord.User,
) -> None:
	"""Log that a user has been unbanned from the guild."""

	# TODO: Modernize this log
	message = (
		'**`>`**\N{BABY ANGEL}`user` **``{}``**`#{}` `({})'
		' unbanned from server {} ({})`'
	).format(
		utils.wrapbackticks(user.name), user.discriminator, user.id, guild.name, guild.id,
	)
	await log_channel.send(message)

async def log_created_role(
	log_channel: discord.TextChannel, role: discord.Role, nitro_booster: bool,
) -> None:
	"""Log a created role. Also if it's the Nitro Booster role, add a special message."""

	embed = discord.Embed(
		title='ROLE ADD AT {time}'.format(time=str(role.created_at)),
		description=utils.mdspecialchars(role.name),
		colour=role.colour,
	)

	if nitro_booster:
		embed.set_footer(text='This is *the* booster role, right? Congrats!')

	await log_channel.send(embed=embed)

async def log_deleted_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log a deleted role."""

	embed = discord.Embed(
		title='ROLE REMOVE',
		description=utils.mdspecialchars(role.name),
		colour=role.colour,
	)
	embed.add_field(name='Original Creation Time', value=str(role.created_at))
	await log_channel.send(embed=embed)

async def log_renamed_role(
	log_channel: discord.TextChannel, old: discord.Role, new: discord.Role,
) -> None:
	"""Log a renamed role."""

	embed = discord.Embed(
		title='ROLE NAME CHANGE',
		description=utils.mdspecialchars(new.name),
		colour=new.colour,
	)
	embed.add_field(name='Older Name', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer Name', value=utils.mdspecialchars(new.name))
	await log_channel.send(embed=embed)

async def log_hoisted_role(log_channel: discord.TextChannel, role: discord.Role) -> None:
	"""Log a hoisted role."""

	embed = discord.Embed(
		title='ROLE HOIST',
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
		title='ROLE UNHOIST',
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
			name=utils.mdspecialchars(ev_new.name),
			id=ev_new.id,
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
		timestamp=datetime.datetime.now(),
		colour=colour,
	)
	embed.add_field(
		name='Older Hierarchy',
		value='{}{}{}'.format(trun_indic_top, old_log, trun_indic_bottom),
	)
	embed.add_field(
		name='Newer Hierarchy',
		value='{}{}{}'.format(trun_indic_top, new_log, trun_indic_bottom),
	)

	await log_channel.send(embed=embed)

async def log_changed_role_color(
	log_channel: discord.TextChannel, old: discord.Role, new: discord.Role,
) -> None:
	"""Log a changed role color."""

	embed = discord.Embed(
		title='ROLE COLOR CHANGE',
		description=utils.mdspecialchars(new.name),
		colour=new.colour,
	)
	embed.add_field(
		name='Older Color',
		value='(default)' if old.colour.value == 0 else str(old.colour).upper(),
	)
	embed.add_field(
		name='Newer Color',
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
		title='ROLE PERMISSIONS CHANGE',
		description=utils.obj_info(new),
		colour=new.colour,
	)
	embed.add_field(name='Permission Updated', value=diff[0][0])
	embed.add_field(
		name='Older Permission',
		value=str(dict(old.permissions)[diff[0][0]]),
	)
	embed.add_field(
		name='Newer Permission',
		value=str(dict(new.permissions)[diff[0][0]]),
	)
	await log_channel.send(embed=embed)

async def log_added_reaction(
	log_channel: discord.TextChannel,
	reaction: discord.Reaction,
	user: Union[discord.Member, discord.User],
) -> None:
	"Log an added reaction."""

	message = reaction.message
	is_custom_emoji = hasattr(reaction.emoji, 'name')

	embed = discord.Embed(
		title=(
			'\N{WHITE SMILING FACE}\N{UPWARDS BLACK ARROW}'
			'REACTION ADDED TO MESSAGE (SENT {reltime} IN #{name})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			name=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=user.colour,
		timestamp=datetime.datetime.now(),
	)

	embed.set_author(
		name=user.display_name,
		icon_url=user.avatar_url,
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
		value=utils.get_jump_link(message) + '\n' + utils.mdspecialchars(
			utils.id_summary(
				uid=user.id,
				mid=message.id,
				eid=reaction.emoji.id if is_custom_emoji else '',
				character='\n' if is_custom_emoji else ' ',
			),
		),
		inline=False,
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
			'\N{WHITE SMILING FACE}\N{NO ENTRY SIGN}'
			'REACTION REMOVED FROM MESSAGE (SENT {reltime} IN #{name})'
		).format(
			reltime=utils.reltime(time.mktime(message.created_at.timetuple())),
			name=utils.mdspecialchars(message.channel.name),
		),
		description=message.content,
		colour=user.colour,
		timestamp=datetime.datetime.now(),
	)

	embed.set_author(name=user.display_name, icon_url=user.avatar_url)

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
		value=utils.get_jump_link(message) + '\n' + utils.mdspecialchars(utils.id_summary(
			uid=user.id,
			mid=message.id,
			eid=reaction.emoji.id if is_custom_emoji else '',
			character='\n' if is_custom_emoji else ' ',
		)),
		inline=False,
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

	embed = discord.Embed(description='Server changed icon')
	embed.set_thumbnail(url=old.icon_url)
	embed.add_field(
		name='Older Icon URL: None' if old.icon_url == '' else 'Older Icon URL (Thumbnail)',
		value='No Older Icon URL' if old.icon_url == '' else old.icon_url,
	)
	embed.add_field(
		name='Newer Icon URL: None' if new.icon_url == '' else 'Newer Icon URL (Inset Image)',
		value='No Newer Icon URL' if new.icon_url == '' else new.icon_url,
	)
	embed.set_image(url=new.icon_url)
	await log_channel.send(embed=embed)

async def log_renamed_guild(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a renamed guild."""

	embed = discord.Embed(description='Server changed name')
	embed.set_thumbnail(url=new.icon_url)
	embed.add_field(name='Older Name', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer Name', value=utils.mdspecialchars(new.name))
	await log_channel.send(embed=embed)

async def log_changed_guild_voice_region(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed guild voice region."""

	embed = discord.Embed(description='VOICE REGION CHANGE')
	embed.set_thumbnail(url=new.icon_url)
	embed.add_field(name='Older Region', value=str(old.region))
	embed.add_field(name='Newer Region', value=str(new.region))
	await log_channel.send(embed=embed)

async def log_changed_guild_afk_timeout(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed AFK timeout."""

	b_m, b_s = divmod(old.afk_timeout, 60)
	b_h, b_m = divmod(b_m, 60)
	a_m, a_s = divmod(new.afk_timeout, 60)
	a_h, a_s = divmod(a_m, 60)
	embed = discord.Embed(description='AFK TIMEOUT CHANGE')
	embed.set_thumbnail(url=new.icon_url)
	embed.add_field(
		name='Older Timeout',
		value='{h}h {m}m {s}s'.format(h=b_h, m=b_m, s=b_s),
	)
	embed.add_field(
		name='Newer Timeout',
		value='{h}h {m}m {s}s'.format(h=a_h, m=a_m, s=a_s),
	)
	await log_channel.send(embed=embed)

async def log_changed_guild_afk_channel(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed AFK channel."""

	embed = discord.Embed(description='AFK CHANNEL CHANGE')
	embed.set_thumbnail(url=new.icon_url)
	embed.add_field(
		name='Older Channel: None' if old.afk_channel is None else 'Older Channel',
		value='No Older Channel' if old.afk_channel is None else utils.obj_info(old.afk_channel),
	)
	embed.add_field(
		name='Newer Channel: None' if new.afk_channel is None else 'Newer Channel',
		value='No Newer Channel' if new.afk_channel is None else utils.obj_info(new.afk_channel),
	)
	await log_channel.send(embed=embed)

async def log_changed_guild_verification_level(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log a changed verification level."""

	embed = discord.Embed(description='VERIFICATION LEVEL CHANGE')
	embed.set_thumbnail(url=new.icon_url)
	embed.add_field(
		name='Older Level',
		value=str(old.verification_level).title(),
	)
	embed.add_field(
		name='Newer Level',
		value=str(new.verification_level).title(),
	)
	await log_channel.send(embed=embed)

async def log_changed_guild_mfa_level(
	log_channel: discord.TextChannel, old: discord.Guild, new: discord.Guild,
) -> None:
	"""Log two-factor authentication being turned on or off."""

	if old.mfa_level == 0 and new.mfa_level == 1:
		embed=discord.Embed(description='SERVER 2FA ENABLED')
	elif old.mfa_level == 1 and new.mfa_level == 0:
		embed=discord.Embed(description='SERVER 2FA DISABLED')
	await log_channel.send(embed=embed)

async def log_changed_guild_emotes(
	log_channel: discord.TextChannel,
	old: Sequence[discord.Emoji],
	new: Sequence[discord.Emoji],
) -> None:
	"""Log emotes being added or removed from a guild."""

	diff = list(set(old).symmetric_difference(set(new)))
	emote_list = ''
	for emote in diff:
		emote_list += '{str} – {0}\n'.format(utils.obj_info(emote), str=str(emote))
	if len(old) > len(new):
		desc = 'EMOTE REMOVE'
	elif len(old) < len(new):
		desc = 'EMOTE ADD'
	else:
		# Emote name change, get the emote in question
		for old_emote in old:
			for new_emote in new:
				if old_emote.id == new_emote.id and old_emote.name != new_emote.name:
					changed_old_emote = old_emote
					changed_new_emote = new_emote

		embed = discord.Embed(
			title='EMOTE NAME CHANGE',
			description=str(changed_new_emote),
		)
		embed.add_field(name='Older Name', value=changed_old_emote.name)
		embed.add_field(name='Newer Name', value=changed_new_emote.name)
		await log_channel.send(embed=embed)
		return
	embed = discord.Embed(description=desc)
	embed.add_field(name='Emotes', value=emote_list)
	await log_channel.send(embed=embed)

async def log_created_guild_channel(
	log_channel: discord.TextChannel, channel: discord.abc.GuildChannel,
) -> None:
	"""Log a created channel."""

	embed = discord.Embed(
		title='{emoji}\N{BLACK RIGHTWARDS ARROW}{name} CREATED'.format(
			emoji=utils.get_channel_type_emoji(channel),
			name=utils.get_channel_type_name(channel).upper(),
		),
		description='**{name}**'.format(name=utils.mdspecialchars(channel.name)),
		colour=utils.colorize(channel.id),
		timestamp=channel.created_at,
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
			name='No Slowmode' if channel.slowmode_delay == 0 else 'Slowmode',
			value='_(none)_' if channel.slowmode_delay == 0 else '{} seconds'.format(
				channel.slowmode_delay,
			), # TODO: Account for hours/minutes/etc. Should be a utils.py function
		)

	if hasattr(channel, 'topic'):
		embed.add_field(
			name='No Topic' if channel.topic is None else 'Topic',
			value='_(none)_' if channel.topic is None else channel.topic,
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
			name='No User Limit' if channel.user_limit == 0 else 'User Limit',
			value='_(none)_' if channel.user_limit == 0 else '{} users'.format(
				channel.user_limit,
			),
		)

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(utils.id_summary(cid=channel.id)),
		inline=False,
	)

	await log_channel.send(embed=embed)

async def log_deleted_guild_channel(
	log_channel: discord.TextChannel, channel: discord.abc.GuildChannel,
) -> None:
	"""Log a deleted channel."""

	embed = discord.Embed(
		title='{emoji}\N{NO ENTRY SIGN}{name} DELETED'.format(
			emoji=utils.get_channel_type_emoji(channel),
			name=utils.get_channel_type_name(channel).upper(),
		),
		description='**{name}**'.format(name=utils.mdspecialchars(channel.name)),
		colour=utils.colorize(channel.id),
		timestamp=datetime.datetime.now(),
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

	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(utils.id_summary(cid=channel.id)),
		inline=False,
	)

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
		title='\N{RADIOACTIVE SIGN}{amount} MESSAGES PURGED IN #{channel.name}'.format(
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
		timestamp=datetime.datetime.now(),
	)
	embed.add_field(
		name='\u200b',
		value=utils.mdspecialchars(
			utils.id_summary(cid=channel.id),
		)
	)
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

	author = channel.guild.get_member(int(payload.data['author']['id']))
	embed = discord.Embed(
		title=(
			'UNCACHED MESSAGE UPDATED (SENT {reltime}'
			' IN #{0.name}).'
			' NEWER CONTENT AND PROPERTIES:'
		).format(
			channel,
			reltime=utils.reltime(
				time.mktime(
					discord.utils.parse_time(payload.data['timestamp']).timetuple(),
				)
			),
		),
		description=payload.data['content'],
		colour=author.colour,
	)
	embed.set_author(
		name=author.display_name,
		icon_url=author.avatar_url,
	)
	embed.add_field(
		name='Pinned',
		value='Yes' if payload.data['pinned'] else 'No',
	)
	embed.add_field(
		name='TTS',
		value='Yes' if payload.data['tts'] else 'No',
	)
	embed.add_field(
		name='Rich Embed',
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
	embed.set_footer(text=utils.id_summary(uid=author.id, mid=payload.data['id']))
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.data['id'])
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
		icon_url=author.avatar_url,
	)
	embed.add_field(
		name='Member of Reaction',
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
	embed.set_footer(text=utils.id_summary(uid=author.id, cid=channel.id, mid=payload.message_id))
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.message_id)
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
		icon_url=author.avatar_url,
	)
	embed.add_field(
		name='Member of Reaction',
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
	embed.set_footer(text=utils.id_summary(uid=author.id, cid=channel.id, mid=payload.message_id))
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.message_id)
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
	embed.set_footer(text=utils.id_summary(cid=channel.id, mid=payload.message_id))
	utils.embed_manual_jump_link(embed, gid=channel.guild.id, cid=channel.id, mid=payload.message_id)
	await log_channel.send(embed=embed)

async def log_renamed_guild_channel(
	log_channel: discord.TextChannel,
	old: discord.abc.GuildChannel,
	new: discord.abc.GuildChannel,
) -> None:
	"""Log a renamed channel."""

	embed = discord.Embed(
		title='{emoji}\N{TWISTED RIGHTWARDS ARROWS}{name} UPDATE'.format(
			emoji=utils.get_channel_type_emoji(new),
			name=utils.get_channel_type_name(new).upper(),
		),
		description=utils.obj_info(new),
		colour=new.guild.me.colour,
	)
	embed.add_field(name='Older Name', value=utils.mdspecialchars(old.name))
	embed.add_field(name='Newer Name', value=utils.mdspecialchars(new.name))
	await log_channel.send(embed=embed)
