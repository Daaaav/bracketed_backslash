# [\] Discord bot
# Copyright 2021, [\] Developers and Contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""handles dispatching individual tasks for each event"""

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

def repeat_async_forever(client, function, args=None, kwargs=None, *, interval):
	# As of right now, there is no intended way to stop it from repeating forever once it's run
	# Fun side effect to note: it waits for the function to return before doing the delay again
	if args is None:
		args = []
	if kwargs is None:
		kwargs = {}

	async def inner(inner_function, args, kwargs):
		while True:
			await inner_function(*args, **kwargs)
			await asyncio.sleep(interval)

	run(client, inner(function, args, kwargs))
