#!/usr/bin/python

import asyncio
import os
import subprocess
import time

import discord

import config

config.load()

client = discord.Client(
	max_messages=999999999,
	status=discord.Status.dnd,
	activity=discord.Game('Starting...'),
	allowed_mentions=discord.AllowedMentions(
		everyone=False,
		users=False,
		roles=False
	)
) # defines all client.* commands

boottime = time.strftime(config.get_s('timeformat'))
boottimeunix = time.time()

startup_error_codes = {
	'send_connect': 'E01',
	'memberroles': 'E02',
	'rules': 'E03',
	'rolexpires': 'E04',
}

startup_errors = {}
for e in startup_error_codes:
	startup_errors[e] = True

minutemessageedits = {}

messages_deleted_by_bot = []
deleted_messages = []

# Holds IDs because that's the only thing that's needed here, saves a lot of memory
# and has better performance, because the cache can get yuge
owncache = []

votemutes = {} # userid -> dict with `starttime`, `proponents`*, `opponents`*

exptimer = None  # threading.Timer object

current_commit = ''
def set_current_commit():
	global current_commit
	current_commit = subprocess.Popen(
		['git', 'describe', '--always'],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE
	).communicate()[0].decode('utf-8')
set_current_commit()

maineventloop = asyncio.get_event_loop()

hangman_games = {} # channel ID -> HangmanGame (one game per channel)

memberroles = {}
rolexpires = {}
rules = {}
disabledrules = []

latestroled = ''

# on_guild_role_update() variables
# 'pos_ev' -> 'position_event'
pos_ev_diffs = {}
pos_ev_locks = {}

# Invite caching
inv_cache = {}
