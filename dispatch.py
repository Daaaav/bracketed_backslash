"""
dispatch.py - handles dispatching individual tasks for each event
Copyright (C) 2017  Info Teddy

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import asyncio

def run(client, coro):
	# Use this function for event creation because it requires less verbosity and there is less
	# noise.
	client.loop.create_task(dispatch(client, coro))

async def dispatch(client, coro):
	# You can use this one but you'll have to create your own task for it, which is more verbose
	# and creates more noise.
	try:
		await coro
	except asyncio.CancelledError:
		pass
	except Exception:  # pylint: disable=broad-except
		try:
			await client.on_error('bot_dispatch')
		except asyncio.CancelledError:
			pass
