# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

import logging

class BlackHoleChannel:
	"""The sole purpose of this class is to be a stand-in for deleted specialchannels that our
	code will naively assume can never have been deleted. If you send it a message, nobody
	cares that it didn't actually get send anywhere (apart from the console), and having a
	message not be sent and actually running code to completion is always better than getting
	random exceptions.

	Eventually this kind of bug should probably be fixed and all our code should have dedicated
	handling for getting None values, but this is a stopgap to prevent trouble from forgetting
	that getting a channel from Discord can fail.
	"""
	id: int

	def __init__(self, cid):
		self.id = cid

	async def send(self, content=None, *, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None, allowed_mentions=None, reference=None, mention_author=None):
		logging.warning('Attempted to send a message to black hole (deleted stand-in) channel {}.\nContent:\n{}'.format(self.id, content))

