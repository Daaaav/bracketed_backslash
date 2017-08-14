#!/usr/bin/python

import asyncio
import os
import time

import discord

import config

config.load()

client = discord.Client(max_messages=999999999) # defines all client.* commands

boottime = time.strftime(config.get_s('timeformat'))
boottimeunix = time.time()

minutemessageedits = {}

messages_deleted_by_bot = []
deleted_messages = []

# Holds IDs because that's the only thing that's needed here, saves a lot of memory
# and has better performance, because the cache can get yuge
owncache = []

votemutes = {} # userid -> dict with `starttime`, `proponents`*, `opponents`*

exptimer = None  # threading.Timer object

modificationtimes = [os.path.getmtime(x) for x in os.listdir() if x.endswith('.py')]
modificationtimecache = time.strftime(config.get_s('timeformat'), time.gmtime(max(modificationtimes)))

maineventloop = asyncio.get_event_loop()

hangman_games = {} # channel ID -> HangmanGame (one game per channel)

memberroles = {}
rolexpires = {}
rules = {}
disabledrules = []

latestroled = ''
