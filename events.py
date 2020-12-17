# [\] Discord bot
# Copyright 2020, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import asyncio
import copy
import datetime
import logging
import json
import os
import sys
import threading
import time
import traceback

import discord

import bot
import checks
import config
import commands
import customcommands
import dispatch
import emb
import logs
import op_ids
import reaction_roles
import starboard
import utils
import wrapper

# pylint: disable=missing-function-docstring

async def on_ready():
	for e in wrapper.startup_errors:
		# Like all the warning lights in a car
		wrapper.startup_errors[e] = True

	client = wrapper.client
	user = client.user

	try:
		# Just send a connection message in the operating server
		# If this fails, well, we won't know when the bot connects.
		# But it might be a sign of op_ids being missing (or Discord just has an outage on that server)
		logging.info(
			'Logged in to Discord.\n'
			'\tID: %s\n'
			'\tUsername: %s\n'
			'\tDiscriminator: %s\n'
			'\tGuilds: %s\n',
			user.id,
			user.name,
			user.discriminator,
			len(client.guilds),
		)
		await bot.bot_connected_message(
			client.get_channel(int(op_ids.ids['opguild_chans']['connections'])),
			color=discord.utils.find(
				lambda s: s.id == op_ids.ids['opguild'], client.guilds,
			).me.colour,
			startup_time=wrapper.boottimeunix,
		)
		wrapper.startup_errors['send_connect'] = False
	except Exception as e:
		logging.error('\x1b[41mStartup error when sending connect message\x1b[0m')
		traceback.print_exc()

	try:
		# Load the role cache and check if we didn't miss changes to roles during downtime
		# If this fails, we can't give users back their roles when they rejoin the server
		try:
			with open('memberroles.json', 'r') as infile:
				wrapper.memberroles = utils.convert_id_keys_to_int(json.load(infile))

			# Now look what I've woken up to.
			for gld in wrapper.memberroles:
				if config.get_s('rolecachemode', gld) == 0:
					continue
				if wrapper.client.get_guild(gld) is None:
					logging.info('Guild {} seems to not be accessible anymore but is in role cache'.format(gld))
					continue
				rcwarnings = ''
				for mem in wrapper.client.get_guild(gld).members:
					if not mem.id in wrapper.memberroles[gld]:
						if len(mem.roles) >= 2:
							rcwarnings += (
								'\n{mem.mention} is not in the cache! '
								'(They’re suddenly in the server.) '
								'Adding their roles to the cache now.'
							).format(mem=mem)

							# Possibly redundant list() tbh, just making sure
							# since I can't test and I don't know python well
							# enough to know whether it's redundant
							wrapper.memberroles[gld][mem.id] = \
							list(utils.rolelist(mem.roles))

						continue
					if set(wrapper.memberroles[gld][mem.id]) != \
					set(utils.rolelist(mem.roles)):
						rcwarnings += (
							'\n'
							'{} has different roles than in the cache! Maybe you want to correct things.\n'
							'    **`Cached:`** {}\n'
							'    **`Seen:`** {}'
						).format(
							mem.mention,
							utils.listroles_id(wrapper.memberroles[gld][mem.id]),
							utils.listroles(mem.roles),
						)
				if rcwarnings:
					logging.warning(
						'Role cache warnings for server %s: %s',
						gld,
						rcwarnings,
					)
					rcwarnings = (
						'**User role cache warning.**\n'
						'Full warning output has been sent to the terminal.\n'
						+ rcwarnings
					)
					await utils.getspecialchannel(
							discord.utils.get(wrapper.client.guilds, id=gld)
					).send(rcwarnings[:1900])

		except FileNotFoundError:
			logging.info('memberroles file does not exist yet so creating it now')

			with open('memberroles.json', 'w') as outfile:
				json.dump(wrapper.memberroles, outfile)

		wrapper.startup_errors['memberroles'] = False
	except Exception as e:
		logging.error('\x1b[41mStartup error when loading role cache\x1b[0m')
		traceback.print_exc()

	try:
		# Load rules.
		# If this fails, the rules system doesn't work.
		try:
			with open('rules.json', 'r') as infile:
				wrapper.rules = utils.convert_id_keys_to_int(json.load(infile))
		except FileNotFoundError:
			logging.info('rules file does not exist yet so creating it now')

			with open('rules.json', 'w') as outfile:
				json.dump(wrapper.rules, outfile)
		try:
			with open('disabledrules.json', 'r') as infile:
				wrapper.disabledrules = [int(i) for i in json.load(infile)]
		except FileNotFoundError:
			logging.info('disabledrules file does not exist yet so creating it now')

			with open('disabledrules.json', 'w') as outfile:
				json.dump(wrapper.disabledrules, outfile)
		wrapper.startup_errors['rules'] = False
	except Exception as e:
		logging.error('\x1b[41mStartup error when loading rules\x1b[0m')
		traceback.print_exc()

	try:
		# Load role expiry.
		# If this fails, existing expiry times won't work until next boot and new roles will never expire
		try:
			with open('rolexpires.json', 'r') as infile:
				wrapper.rolexpires = utils.convert_id_keys_to_int(json.load(infile))
		except FileNotFoundError:
			logging.info('rolexpires file does not exist yet so creating it now')

			with open('rolexpires.json', 'w') as outfile:
				json.dump(wrapper.rolexpires, outfile)

		await utils.handleExpiryTimer()

		wrapper.startup_errors['rolexpires'] = False
	except Exception as e:
		logging.error('\x1b[41mStartup error when loading rolexpires\x1b[0m')
		traceback.print_exc()

	errcodes = []
	for e in wrapper.startup_errors:
		if wrapper.startup_errors[e]:
			errcodes.append(wrapper.startup_error_codes[e])
	if errcodes:
		# None of these errors are currently really "slam on the brakes" serious
		await wrapper.client.change_presence(
			status=discord.Status.online,
			activity=discord.Game(','.join(errcodes))
		)
	else:
		await wrapper.client.change_presence(
			status=discord.Status.online,
			activity=discord.Game(name=config.get_s('gamestatus'))
		)

	# Essentials are out of the way now!

	for chan in wrapper.client.get_all_channels():
		if isinstance(chan, discord.TextChannel):
			msgs = chan.history()
			try:
				async for m in msgs:
					wrapper.client._connection._messages.append(m)
			except discord.errors.Forbidden:
				logging.info(
					'Failed to retrieve message history for'
					' %s (%s)#%s (%s).',
					chan.guild.name, chan.guild.id, chan.name, chan.id,
				)

	# Now set up our own cache, that Discord.py won't remove messages from before telling us!
	for m in wrapper.client.cached_messages:
		wrapper.owncache.append(m.id)

	for guild in wrapper.client.guilds:
		try:
			wrapper.inv_cache[guild.id] = await guild.invites()
		except discord.Forbidden:
			logging.info('Failed to retrieve guild invites for %s (%s).', guild.name, guild.id)
		else:
			audit_log_entries = guild.audit_logs(action=discord.AuditLogAction.invite_create)
			try:
				async for entry in audit_log_entries:
					if entry.target not in wrapper.inv_cache[guild.id]:
						wrapper.inv_cache[guild.id].append(entry.target)
			except discord.Forbidden:
				logging.info('Failed to retrieve audit log invites for %s (%s).', guild.name, guild.id)

	dispatch.repeat_async_forever(
		wrapper.client,
		bot.sync_invite_cache,
		[wrapper.client, wrapper.inv_cache],
		interval=30,
	)

async def on_message(m):
	wrapper.owncache.append(m.id)

	if m.author == wrapper.client.user or m.author.bot:
		return

	if isinstance(m.channel, discord.abc.PrivateChannel):
		e = discord.Embed(
			description=m.content,
			timestamp=m.created_at,
			colour=wrapper.client.get_guild(op_ids.ids['opguild']).me.colour,
		)
		e.set_author(name=m.author.name, icon_url=m.author.avatar_url)
		e.set_footer(text=utils.id_summary(uid=m.author.id, mid=m.id, cid=m.channel.id))
		await wrapper.client.get_channel(op_ids.ids['opguild_chans']['direct_messages']).send(
			embed=e,
		)

	schan = utils.getspecialchannel_reply(m)
	priv = utils.isprivatemessage(m.guild)

	if not priv and m.tts and not utils.logdisabled('message_tts', m.guild) and \
	not utils.channelnotlogged(m.channel, m.guild):
		e = discord.Embed(
			title=(
				':microphone2:Message {0.id} was sent with TTS'
				' in #{0.channel.name}'
			).format(m),
			description=m.content,
			colour=m.author.colour,
			timestamp=m.created_at,
		)
		e.set_author(
			name=m.author.display_name,
			icon_url=m.author.avatar_url
		)
		e.add_field(
			name='Message author',
			value='<@!{id}> ({id})'.format(id=m.author.id)
		)
		await schan.send(embed=e)

	if not priv and m.attachments and not utils.logdisabled('message_delete', m.guild) and \
	not utils.channelnotlogged(m.channel, m.guild) and \
	not utils.usernotlogged(m.author, m.guild):
		a = await utils.fetch(m.attachments[0].url)
		fn = (
			'{atchcche}/{id}_{fn}'
		).format(
			atchcche=bot.attachcache,
			id=m.attachments[0].id,
			fn=m.attachments[0].filename,
		)
		with open(fn, 'wb') as f:
			f.write(a)
			f.close()

	if not priv and m.embeds != []:
		for n, e in enumerate(m.embeds):
			if e.type == 'image':
				# get the filename from the url
				# i.e. the part after the last forward slash
				fn = e.url.split('/')[-1]

				# fetch the embed preview discord fetches
				img = await utils.fetch(e.thumbnail.proxy_url)

				# cache the image
				dfn = '{embedcache}/{m.id}_{n}_{fn}'.format(
					embedcache=bot.embedcache,
					m=m,
					n=n,
					fn=fn,
				)
				with open(dfn, 'wb') as f:
					f.write(img)
					f.close()

	if not priv and m.author.id in config.get_s('blacklist', m.guild.id):
		return

	if priv and m.author.id in config.get_s('blacklist'):
		return

	if priv:
		invokesymbol = '@'
	elif checks.is_mod(m.author):
		invokesymbol = '#'
	else:
		invokesymbol = '$'

	is_join_channel = (not priv) and \
	config.get_s('rolecachemode', m.guild.id) == 2 and \
	m.channel.id == config.get_s('joinchannel', m.guild.id)

	if is_join_channel:
		await m.delete()
		wrapper.messages_deleted_by_bot.append(m)

	prefixes = config.get_s('prefixes')[:]

	if not priv and config.is_detached('prefixes', m.guild.id):
		prefixes.extend(config.get_s('prefixes', m.guild.id))

	for prefix in prefixes:
		if m.content.startswith(prefix):
			command = m.content.split(prefix, 1)[1]
			clean_command_with_args = m.clean_content.split(prefix, 1)[1]
			break
	else:
		return

	try:
		arguments = command.split(' ', 1)[1]
		clean_arguments = clean_command_with_args.split(' ', 1)[1]
	except IndexError:
		arguments = None
		clean_arguments = None
	command = command.split(' ', 1)[0]
	clean_command = clean_command_with_args.split(' ', 1)[0]

	# Prevent access to those who aren't supposed to send messages
	if not priv and \
	not checks.is_mod(m.author) and \
	not config.get_s('alloweverywhere', m.guild.id) and \
	not m.channel.id in config.get_s('allowedchannels', m.guild.id) and \
	not command in config.get_s('globalcommands', m.guild.id):
		return
	if not priv and command in config.get_s('disabledcommands', m.guild.id):
		e = emb.error('This command is currently disabled{onthisguild}.'.format(
			onthisguild=(
				' on this server'
				if config.is_detached('disabledcommands', m.guild.id) else
				'')
			)
		)
		await bot.reply(m, emb=e)
		return

	if priv and command in config.get_s('disabledcommands'):
		e = emb.error('This command is currently disabled.')
		await bot.reply(m, emb=e)
		return

	if command in commands.commands:
		func = commands.commands[command]
	elif customcommands.exists(m.guild, command):
		try:
			await customcommands.run(
				m.guild, command, m, arguments, clean_arguments, invokesymbol
			)
		except discord.errors.Forbidden:
			e = emb.error(bot.t['no_permission'])
			await bot.reply(m, emb=e)
			raise
		except Exception:
			e = emb.error(bot.t['generic_error'])
			await bot.reply(m, emb=e)
			raise
		return
	else:
		# Check if it's an alias
		for c, p in commands.commands.items():
			if p[2] is not None and command in p[2]:
				func = commands.commands[c]
				break
		else:
			if (not is_join_channel) and \
			(not priv and config.get_s('notify_invalidcmd', m.guild.id)) or \
			(priv and config.get_s('notify_invalidcmd')):
				e = emb.warning(
					(
						'Invalid command. Input `\help` for'
						' a list of valid commands.'
					)
				)
				await bot.reply(m, emb=e)
			return

	if isinstance(m.channel, discord.abc.PrivateChannel) and (func[3] or func[4]):
		e = emb.error(bot.t['noprivate'])
		await bot.reply(m, emb=e)
		return

	if func[5] and not is_join_channel:
		embed = emb.error('What an odd place to be using this command!')
		await bot.reply(m, emb=embed)
		return
	elif not func[5] and is_join_channel:
		return

	if func[4] and \
	('active' not in config.get_s('tntgb', m.guild.id)
	or not config.get_s('tntgb', m.guild.id)['active']):
		e = emb.error(bot.t['tntgb_only'])
		await bot.reply(m, emb=e)
		return
	if func[1] is not None and not func[1](m.author):
		e = emb.error(bot.t['you_no_permission'])
		utils.logfailedcommand(command, arguments, m)
		await bot.reply(m, emb=e)
		return
	kwargs = {
		'command': command,
		'arguments': arguments,
		'clean_arguments': clean_arguments,
		'clean_command_with_args': clean_command_with_args,
		'invokesymbol': invokesymbol,
		'sudo': False,
	}
	try:
		await func[0](wrapper.client, m, **kwargs)
	except discord.errors.Forbidden:
		e = emb.error(bot.t['no_permission'])
		await bot.reply(m, emb=e)
		raise
	except Exception:
		e = emb.error(bot.t['generic_error'])
		await bot.reply(m, emb=e)
		logging.info('\x1b[41mFault did occur in command {}\x1b[0m'.format(command))
		raise

async def on_message_delete(msg):
	wrapper.deleted_messages.append(msg)
	if utils.isprivatemessage(msg.guild):
		return
	if msg.author == wrapper.client.user:
		logging.info(
			'bot message %s by user %s#%s (%s)'
			' in channel %s (%s) at %s utc deleted,'
			' original content is\n%s',
			msg.id, msg.author.name, msg.author.discriminator, msg.author.id,
			msg.channel.id, msg.channel.name, msg.created_at,
			msg.content,
		)
		return

	if utils.logdisabled('message_delete', msg.guild):
		return
	if utils.channelnotlogged(msg.channel, msg.guild):
		return
	if utils.usernotlogged(msg.author, msg.guild):
		return
	schan = utils.getspecialchannel_reply(msg)
	await logs.log_deleted_message(schan, msg)

	if msg in wrapper.messages_deleted_by_bot:
		wrapper.messages_deleted_by_bot.remove(msg)
		return
	dthreshold = datetime.timedelta(
		seconds=config.get_s('deleted_message_resend_timer', msg.guild.id),
	)
	if (datetime.datetime.now() - msg.created_at) < dthreshold and \
	not msg.author.bot:
		if config.get_s('deleted_message_resend_content', msg.guild.id):
			em = discord.Embed(
				title='UNDELETED MESSAGE',
				description=msg.content,
				colour=msg.author.colour,
			)
			em.set_footer(
				text='This message was resent as it was deleted too recently.',
			)
		else:
			em = discord.Embed(title='Message was deleted', colour=msg.author.colour)
			em.set_footer(
				text=(
					'This notification was sent because a message by this'
					' user was deleted too recently.'
				),
			)
		em.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
		await msg.channel.send(embed=em)

async def on_message_edit(old, new):
	if utils.isprivatemessage(old.guild):
		return
	if utils.channelnotlogged(new.channel, new.guild):
		return
	if utils.usernotlogged(new.author, new.guild):
		return
	edited_at = new.edited_at
	if edited_at is None:
		edited_at = datetime.datetime.now()
	schan = utils.getspecialchannel_reply(new)
	if not old.pinned and new.pinned and not utils.logdisabled('message_pin', new.guild):
		await logs.log_pinned_message(schan, new)
	if old.pinned and not new.pinned and not utils.logdisabled('message_unpin', new.guild):
		await logs.log_unpinned_message(schan, new)

	if not utils.logdisabled('message_deleteembed', new.guild) \
	and len(old.embeds) > len(new.embeds) and old.content == new.content:
		await logs.log_deleted_embed(schan, new, edited_at)

	# Preliminary checkings
	if old.content == new.content:
		# Must be the message being pinned and/or embed(s) displaying
		# Actually, TTS and rich embeds could also have changed,
		# but this is just a refactor
		return

	if not utils.logdisabled('message_edit', new.guild):
		await logs.log_edited_message(schan, old, new, edited_at)

	# Turning off this logging also turns off the feature
	if not utils.logdisabled('message_overedit', new.guild):
		# Delete a message if it has been edited more than 5 times in 30 seconds
		await utils.handle_minute_message_edits(new, schan)

	# Message edited too heavily?
	delta_threshold = datetime.timedelta(
		config.get_s('edited_message_resend_timer', new.guild.id)
	)
	if ((edited_at - new.created_at) < delta_threshold and
	utils.diff(old.content, new.content) >
	config.get_s('edited_message_resend_threshold', new.guild.id)):
		embed = discord.Embed(title='UNEDITED MESSAGE', colour=new.author.colour)

		embed.add_field(name='Older Content', value=old.content[:1024], inline=False)
		if len(old.content) > 1024:
			embed.add_field(name='[continued]', value=old.content[1024:], inline=False)

		embed.add_field(name='Newer Content', value=new.content[:1024], inline=False)
		if len(new.content) > 1024:
			embed.add_field(name='[continued]', value=new.content[1024:], inline=False)

		embed.set_author(name=new.author.display_name, icon_url=new.author.avatar_url)
		embed.set_footer(text='These contents were resent as this message was edited too heavily.')

		await new.channel.send(embed=embed)

async def on_member_update(before, after):
	specialchannel = utils.getspecialchannel(after.guild)

	if before.nick != after.nick and not utils.logdisabled('member_nickname', after.guild):
		await logs.log_changed_nickname(specialchannel, before, after)
	if before.roles != after.roles:
		await logs.log_updated_roles(specialchannel, before, after)

		if config.get_s('rolecachemode', after.guild.id) != 0:
			utils.updaterolecache(after)
			utils.rolecachesave()

	if before.name != after.name and not utils.logdisabled('member_username', after.guild):
		# FIXME: This doesn't log solo discrim changes, only name+discrim changes!
		# FIXME: This hasn't fired since a certain Discord/discord.py refactor!
		await logs.log_changed_tag(specialchannel, before, after)

	if before.avatar != after.avatar and \
	(not utils.logdisabled('member_botavatar', after.guild) \
	if checks.is_bot(after) \
	else not utils.logdisabled('member_avatar', after.guild)):
		# FIXME: This hasn't fired since a certain Discord/discord.py refactor!
		await logs.log_changed_avatar(specialchannel, before, after)

async def on_member_join(member):
	guild = member.guild

	invite = None

	try:
		guild_invites = await guild.invites()
	except discord.Forbidden:
		guild_invites = []
		has_guild_invites = False
	else:
		has_guild_invites = True

	audit_entries = guild.audit_logs(action=discord.AuditLogAction.invite_create)
	audit_invites = []
	try:
		async for entry in audit_entries:
			audit_invites.append(entry.target)
	except discord.Forbidden:
		has_audit_invites = False
	else:
		has_audit_invites = True

	all_invites = []
	all_invites.extend(guild_invites)
	# We filter() out any audit invites we already have, or it will mess up the number of uses
	# because audit invites aren't real invites
	all_invites.extend(filter(lambda i: i not in guild_invites, audit_invites))

	specialchannel = utils.getspecialchannel(guild)
	if not utils.logdisabled('member_join', guild):

		await logs.log_joined_member(
			specialchannel,
			member,
			guild,
			has_guild_invites,
			has_audit_invites,
			guild_invites,
			all_invites,
		)

	if has_guild_invites:
		# Let's cache the invites
		# We can't simply use list.extend because it won't record the updated number of uses
		# Stupid piece of shit
		for invite in all_invites:
			cached_invite = discord.utils.find(lambda i: i.code == invite.code, wrapper.inv_cache[guild.id])
			if cached_invite is not None:
				cached_invite.uses = invite.uses
			else:
				# Holy shit we have a fresh new invite
				wrapper.inv_cache[guild.id].append(invite)

		# Remove duplicates
		wrapper.inv_cache[guild.id] = list(set(wrapper.inv_cache[guild.id]))

	await utils.newmemberroles(member, specialchannel, False)

async def on_member_remove(member):
	guild = member.guild
	specialchannel = utils.getspecialchannel(guild)
	moderator = None
	action = None
	reason = ''

	try:
		async for entry in guild.audit_logs(
			# Apparently this parameter is fucked on Discord's end currently
			#after=datetime.datetime.now() - datetime.timedelta(seconds=2),
			oldest_first=False,
		).filter(
			# Can't grab more than one type of action when making the request
			# so we'll have to filter it ourselves
			lambda e: e.action in (
				discord.AuditLogAction.kick, # TODO: discord.AuditLogAction.ban
			),
		):
			# Can't filter out entries AFTER a certain point in time
			# because the endpoint is fucked
			# so we'll have to, hurr durr, filter it ourselves
			if discord.utils.snowflake_time(entry.id) > \
			datetime.datetime.now() - datetime.timedelta(seconds=2) and \
			entry.target.id == member.id:
				moderator = entry.user
				action = entry.action
				reason = entry.reason
				break
	except discord.Forbidden:
		pass

	if not utils.logdisabled('member_remove', guild):
		await logs.log_removed_member(specialchannel, member, moderator, action, reason)

async def on_member_ban(guild, user):
	if not utils.logdisabled('member_ban', guild):
		specialchannel = utils.getspecialchannel(guild)

		await logs.log_banned_member(specialchannel, guild, user)

	if config.get_s('banlog_logchannel', guild.id) != 0 and \
	config.get_s('banlog_modchannel', guild.id) != 0:
		modchannel = discord.utils.find(
			lambda c: c.id == config.get_s('banlog_modchannel', guild.id),
			guild.channels
		)

		# Get the ban on this user
		reason = '(cannot be determined)'
		try:
			bans = await guild.bans()
		except discord.errors.Forbidden:
			pass
		else:
			for b in bans:
				if b.user == user:
					reason = b.reason
					break

		logmessage = (
			'**Ban on user**: {}#{} ({})\n'
			'**Reason**: {}\n'
			#'Responsible moderator: {}'
		).format(
			user.name, user.discriminator, user.mention,
			reason
		)
		emb = discord.Embed(title='Preview', description=logmessage + '(responsible moderator?)')
		question_msg = await modchannel.send(
			(
				#'{} has just been banned. For the responsible moderator '
				#'to publish a log message in <#{}>, please react to this message '
				#'with 🙋. If this ban was placed after discussion and agreement '
				#'between the moderators, please react to this message with 👍.'
				'{} has just been banned. To publish a log message in <#{}>, please react '
				'to this message with either:\n'
				'🙋 if you placed this ban at your sole discretion\n'
				'👍 if the ban was placed after discussion and agreement between the '
				'moderators'
			).format(
				user.mention, config.get_s('banlog_logchannel', guild.id)
			), embed=emb
		)

		def react_check(reaction, user):
			if reaction.message.id != question_msg.id:
				return False
			e = str(reaction.emoji)
			return e.startswith(('🙋', '👍'))

		reaction, user = await wrapper.client.wait_for('reaction_add', check=react_check)

		if str(reaction.emoji).startswith('🙋'):
			logmessage += '**Responsible moderator**: {}'.format(user)
		else:
			logmessage += 'This ban was placed after discussion and agreement by moderators.'

		await discord.utils.find(
			lambda c: c.id == config.get_s('banlog_logchannel', guild.id),
			guild.channels
		).send(logmessage)

async def on_member_unban(guild, user):
	if utils.logdisabled('member_unban', guild):
		return
	specialchannel = utils.getspecialchannel(guild)
	await logs.log_unbanned_member(specialchannel, guild, user)

async def on_guild_role_create(r):
	schan = utils.getspecialchannel(r.guild)
	nitro_booster = r.name == 'Server Booster' and r.managed

	if nitro_booster:
		config.detach('nitrobooster', r.guild.id)
		config.set_s('nitrobooster', r.id, r.guild.id)
		config.saveconfig()

	if utils.logdisabled('role_create', r.guild):
		return

	await logs.log_created_role(schan, r, nitro_booster)

async def on_guild_role_delete(r):
	if utils.logdisabled('role_delete', r.guild):
		return
	schan = utils.getspecialchannel(r.guild)
	await logs.log_deleted_role(schan, r)

async def on_guild_role_update(before, after):
	guild = after.guild

	# We might have gotten MANAGE_GUILD
	if after.guild.me.guild_permissions.manage_guild:
		try:
			wrapper.inv_cache[after.guild.id] = await after.guild.invites()
		except discord.Forbidden:
			pass
	# Or VIEW_AUDIT_LOG
	if after.guild.me.guild_permissions.view_audit_log:
		audit_log_entries = guild.audit_logs(action=discord.AuditLogAction.invite_create)
		try:
			async for entry in audit_log_entries:
				if entry.target not in wrapper.inv_cache[guild.id]:
					wrapper.inv_cache[guild.id].append(entry.target)
		except discord.Forbidden:
			pass

	specialchannel = utils.getspecialchannel(before.guild)
	# If the name changed
	if before.name != after.name and not utils.logdisabled('role_rename', before.guild):
		await logs.log_renamed_role(specialchannel, before, after)
	# If "display online members separately" changed
	if before.hoist != after.hoist:
		# If the role has been hoisted
		if before.hoist == 0 and after.hoist == 1 and not utils.logdisabled(
			'role_hoist', before.guild
		):
			await logs.log_hoisted_role(specialchannel, after)
		# If the role has been lowered
		if before.hoist == 1 and after.hoist == 0 and not utils.logdisabled(
			'role_unhoist', before.guild
		):
			await logs.log_unhoisted_role(specialchannel, after)
	# If "allow everyone to mention this role" changed
	if before.mentionable != after.mentionable:
		# If the role is now mentionable
		if before.mentionable == 0 and after.mentionable == 1 and not utils.logdisabled(
			'role_mentionable', before.guild
		):
			await logs.log_mentionable_role(specialchannel, after)
		# If the role is no longer mentionable
		if before.mentionable == 1 and after.mentionable == 0 and not utils.logdisabled(
			'role_unmentionable', before.guild
		):
			await logs.log_unmentionable_role(specialchannel, after)

	# If the role has been moved up or down in the hierarchy
	if before.position != after.position and not utils.logdisabled('role_hierarchy', before.guild):
		# Discord is terrible with role update events and sends multiple of them
		#
		# We need a lock, so we don't have multiple calls of this function sending multiple
		# messages and spamming log channels

		# Initialization of the lock
		if after.guild.id not in wrapper.pos_ev_locks:
			wrapper.pos_ev_locks[after.guild.id] = False

		# Initialization of the diff
		if after.guild.id not in wrapper.pos_ev_diffs:
			wrapper.pos_ev_diffs[after.guild.id] = []

		# Anyways, we've received an event: collect it
		wrapper.pos_ev_diffs[after.guild.id].append((before, after))

		# See if we're locked
		if not wrapper.pos_ev_locks[after.guild.id]:
			# We're not locked, so let's lock it
			wrapper.pos_ev_locks[after.guild.id] = True

			# Let's wait for all the events to be collected
			await asyncio.sleep(1)

			# Unlock
			wrapper.pos_ev_locks[after.guild.id] = False

			# Make log message

			# These are set()s to remove any redundant elements that might happen
			# because events are received in a weird order or something
			before_list = set()
			after_list = set()

			for ev_before, ev_after in wrapper.pos_ev_diffs[after.guild.id]:
				before_list.add(ev_before)
				after_list.add(ev_after)

			before_list = list(before_list)
			after_list = list(after_list)

			# Cleanup
			del wrapper.pos_ev_locks[after.guild.id]
			del wrapper.pos_ev_diffs[after.guild.id]

			await logs.log_updated_role_hierarchy(
				specialchannel,
				before_list,
				after_list,
			)

	# If the role color has changed
	if before.colour != after.colour and not utils.logdisabled('role_color', before.guild):
		await logs.log_changed_role_color(specialchannel, before, after)
	# If any of the permissions has changed
	if before.permissions != after.permissions and not utils.logdisabled(
		'role_permissions', before.guild
	):
		await logs.log_changed_role_permissions(specialchannel, before, after)

async def on_reaction_add(reaction, user):
	message = reaction.message

	if utils.isprivatemessage(message.guild) \
	or utils.logdisabled('reaction_add', message.guild) \
	or utils.channelnotlogged(message.channel, message.guild):
		return

	specialchannel = utils.getspecialchannel(message.guild)

	await logs.log_added_reaction(specialchannel, reaction, user)

async def on_reaction_remove(reaction, user):
	message = reaction.message

	if utils.isprivatemessage(message.guild) \
	or utils.logdisabled('reaction_remove', message.guild) \
	or utils.channelnotlogged(message.channel, message.guild):
		return

	specialchannel = utils.getspecialchannel(message.guild)

	await logs.log_removed_reaction(specialchannel, reaction, user)

async def on_reaction_clear(m, rs):
	if utils.isprivatemessage(m.guild) or utils.logdisabled('reaction_clear', m.guild) \
	or utils.channelnotlogged(m.channel, m.guild):
		return
	schan = utils.getspecialchannel(m.guild)
	await logs.log_cleared_reactions(schan, m, rs)

async def on_guild_update(before, after):
	specialchannel = utils.getspecialchannel(after)
	if before.icon != after.icon and not utils.logdisabled('guild_icon', after):
		await logs.log_changed_guild_icon(specialchannel, before, after)
	if before.name != after.name and not utils.logdisabled('guild_rename', after):
		await logs.log_renamed_guild(specialchannel, before, after)
	if before.region != after.region and not utils.logdisabled('guild_region', after):
		await logs.log_changed_guild_voice_region(specialchannel, before, after)
	if before.afk_timeout != after.afk_timeout and \
	not utils.logdisabled('guild_afktimeout', after):
		await logs.log_changed_guild_afk_timeout(specialchannel, before, after)
	if before.afk_channel != after.afk_channel and \
	not utils.logdisabled('guild_afkchannel', after):
		await logs.log_changed_guild_afk_channel(specialchannel, before, after)
	if before.verification_level != after.verification_level and not utils.logdisabled(
		'guild_verificationlevel', after
	):
		await logs.log_changed_guild_verification_level(specialchannel, before, after)
	if before.mfa_level != after.mfa_level and not utils.logdisabled('guild_2fa', after):
		await logs.log_changed_guild_mfa_level(specialchannel, before, after)

async def on_guild_emojis_update(guild, b, a):
	if utils.logdisabled('guild_emotes', guild):
		# We could split this into separate emotes_* log types
		return
	schan = utils.getspecialchannel(guild)
	await logs.log_changed_guild_emotes(schan, b, a)

async def on_voice_state_update(member, old, new):
	if old.channel == new.channel:
		return

	vtcs = [
		member.guild.get_channel(i) for i in config.get_s(
			'voicechat_channel_text', member.guild.id,
		)
	]
	vvcs = [
		member.guild.get_channel(i) for i in config.get_s(
			'voicechat_channel_voice', member.guild.id,
		)
	]

	for vtc, vvc in zip(vtcs, vvcs):
		if new.channel is not None and new.channel == vvc:
			# Joined the voice channel
			ow = discord.PermissionOverwrite(read_messages=True)
			await vtc.set_permissions(member, overwrite=ow)
			break

		if old.channel is not None and old.channel == vvc:
			# Left the voice channel
			await vtc.set_permissions(member, overwrite=None)
			break

async def on_guild_channel_create(channel):
	if utils.logdisabled('channel_add', channel.guild):
		return

	schan = utils.getspecialchannel(channel.guild)

	await logs.log_created_guild_channel(schan, channel)

async def on_guild_channel_delete(channel):
	if utils.logdisabled('channel_remove', channel.guild):
		return

	schan = utils.getspecialchannel(channel.guild)

	await logs.log_deleted_guild_channel(schan, channel)

async def on_raw_bulk_message_delete(payload):
	# We must first know what channel it is
	mchan = wrapper.client.get_channel(payload.channel_id)

	unhandled_message_ids = copy.deepcopy(payload.message_ids)
	# Can't we just handle this with normal message deletion events?
	if len(payload.cached_messages) <= 10:
		for m in payload.cached_messages:
			# Technically on_raw_message_delete always fires in case of normal deletes,
			# and the starboard may remove deleted messages based on that.
			# But this is classified as a purge anyway, and deleting messages from the
			# starboard is not that important.
			await on_message_delete(m)
			unhandled_message_ids.remove(m.id)

	if not unhandled_message_ids:
		# That wasn't much of a purge.
		return

	if isinstance(mchan, discord.abc.PrivateChannel) \
	or utils.channelnotlogged(mchan, mchan.guild):
		return
	if utils.logdisabled('message_delete', mchan.guild) and \
	utils.logdisabled('message_deleteuncached', mchan.guild):
		return

	# Okay, we're not sending like 50 "deleted message" notifications.
	schan = utils.getspecialchannel(mchan.guild)
	await logs.log_bulk_deleted_messages(schan, mchan, payload)

async def on_raw_message_delete(payload):
	# We must first know what channel it is
	mchan = wrapper.client.get_channel(payload.channel_id)

	await starboard.remove_message(payload, mchan)

	if not isinstance(mchan, discord.abc.PrivateChannel) and \
	not utils.logdisabled('message_deleteuncached', mchan.guild) and \
	not utils.channelnotlogged(mchan, mchan.guild):
		# Check if on_message_delete() was already called by this message
		# If it was, then return
		if discord.utils.find(
			lambda m: m.id == payload.message_id, wrapper.client.cached_messages,
		) is not None:
			# If the message lingers in deleted_messages, it doesn't really matter for now
			return
		if payload.message_id in wrapper.owncache:
			# Already removed from the cache, but we still haven't run on_message_delete
			# This happens all the time.
			wrapper.owncache.remove(payload.message_id)
			return
		for m in wrapper.deleted_messages:
			if m.id == payload.message_id:
				# on_message_delete was faster
				wrapper.deleted_messages.remove(m)
				return

		schan = utils.getspecialchannel(mchan.guild)
		await logs.log_deleted_uncached_message(schan, mchan, payload)

async def on_raw_message_edit(payload):
	# We must first know what channel it is
	mchan = wrapper.client.get_channel(int(payload.data['channel_id']))

	if isinstance(mchan, discord.abc.PrivateChannel) or \
	utils.logdisabled('message_updateuncached', mchan.guild) or \
	utils.channelnotlogged(mchan, mchan.guild):
		return
	# Check if the message is in the cache and return if it is
	if discord.utils.find(
		lambda m: m.id == payload.message_id, wrapper.client.cached_messages,
	) is not None:
		return

	schan = utils.getspecialchannel(mchan.guild)
	await logs.log_updated_uncached_message(schan, mchan, payload)

async def on_raw_reaction_add(payload):
	# We must first know what channel it is
	mchan = wrapper.client.get_channel(payload.channel_id)

	# FIXME: The starboard check blocks the rest of the function if it sends a message,
	# then the reaction roles if it adds a role
	await starboard.check_message(payload, mchan, True)
	await reaction_roles.check_message(payload, mchan, True)

	if not isinstance(mchan, discord.abc.PrivateChannel) and \
	not utils.logdisabled('reaction_adduncached', mchan.guild) and \
	not utils.channelnotlogged(mchan, mchan.guild):
		# Check if the message is in the cache and return if it is
		if discord.utils.find(
			lambda m: m.id == payload.message_id, wrapper.client.cached_messages,
		) is not None:
			return

		schan = utils.getspecialchannel(mchan.guild)
		await logs.log_added_uncached_reaction(schan, mchan, payload)

async def on_raw_reaction_remove(payload):
	# We must first know what channel it is
	mchan = wrapper.client.get_channel(payload.channel_id)

	# FIXME: Blocking function (see on_raw_reaction_add())
	await starboard.check_message(payload, mchan, False)
	await reaction_roles.check_message(payload, mchan, False)

	if not isinstance(mchan, discord.abc.PrivateChannel) and \
	not utils.logdisabled('reaction_removeuncached', mchan.guild) and \
	not utils.channelnotlogged(mchan, mchan.guild):
		# Check if the message is in the cache and return if it is
		if discord.utils.find(
			lambda m: m.id == payload.message_id, wrapper.client.cached_messages,
		) is not None:
			return

		schan = utils.getspecialchannel(mchan.guild)
		await logs.log_removed_uncached_reaction(schan, mchan, payload)

async def on_raw_reaction_clear(payload):
	# We must first know what channel it is
	mchan = wrapper.client.get_channel(payload.channel_id)

	await starboard.remove_message(payload, mchan)
	# TODO: Automatically remove message from reaction roles system?

	if not isinstance(mchan, discord.abc.PrivateChannel) and \
	not utils.logdisabled('reaction_clearuncached', mchan.guild) and \
	not utils.channelnotlogged(mchan, mchan.guild):
		# Check if the message is in the cache and return if it is
		if discord.utils.find(
			lambda m: m.id == payload.message_id, wrapper.client.cached_messages,
		) is not None:
			return

		schan = utils.getspecialchannel(mchan.guild)
		await logs.log_cleared_uncached_reactions(schan, mchan, payload)

# TODO: Implement on_reaction_clear_emoji() and on_raw_reaction_clear_emoji()

async def on_guild_channel_update(b, a):
	if utils.logdisabled('channel_rename', a.guild):
		return
	schan = utils.getspecialchannel(a.guild)
	if b.name != a.name:
		await logs.log_renamed_guild_channel(schan, b, a)

async def on_guild_join(guild):
	em = discord.Embed(
		title='BOT ADDED TO SERVER',
		description=utils.obj_info(guild),
		colour=wrapper.client.get_guild(op_ids.ids['opguild']).me.colour,
	)
	em.set_image(url=guild.icon_url)
	await wrapper.client.get_channel(op_ids.ids['opguild_chans']['bot_guilds']).send(embed=em)

async def on_guild_remove(guild):
	em = discord.Embed(
		title='BOT REMOVED FROM SERVER',
		description=utils.obj_info(guild),
		colour=wrapper.client.get_guild(op_ids.ids['opguild']).me.colour,
	)
	em.set_image(url=guild.icon_url)
	await wrapper.client.get_channel(op_ids.ids['opguild_chans']['bot_guilds']).send(embed=em)

async def on_error(event_name, *args, **kwargs):
	# See discord.py's client.py for the default implementation
	now = datetime.datetime.now()
	print('\x1b[41m[{}] Exception in event {}\x1b[0m'.format(now, event_name), file=sys.stderr)
	traceback.print_exc()

	wrapper.runtime_exceptions.append( (now, event_name, sys.exc_info()) )
