# \[\\\]
[\\] is a bot originally written by Info Teddy and Dav999 in Python utilizing
discord.py, and is now hosted and maintained by Dav999.

This bot is still actively maintained, but new features are mostly only added
when needed.

Having been active since 2016, this bot traditionally had commands starting
with `\` (i.e. `\help`) but the most important commands are now available
as slash commands. If you still need a traditional `\` command, depending on
the instance you may need to add a ping to the message to comply with new
Discord rules, but the bot's status and bio will tell you more in that case.

# License
All code files in the entirety of this repository are licensed under
AGPLv3-only. You cannot automatically "upgrade" the license to a later version
of the AGPL, an upgrade has to be a relicensing that will be decided by the
project maintainers.

# Installation instructions
The below applies if you'd like to run your own instance of this bot, rather
than using an official main instance (hosted by Dav).

It might be a good idea to let me know if you're hosting your own instance in
production - otherwise I might remove features without warning because nobody's
using them on the main instances, or make changes that require one-off manual
configuration migrations, and barely document them if at all, because I'm the
only one needing to do them anyway.

## Requirements
- Python 3 is required.
- Some libraries are required (or in some cases optional, but some features
  won't work). Ensure the following are installed:
  [discord.py](https://github.com/Rapptz/discord.py),
  [Pillow](https://github.com/python-pillow/Pillow), `sqlite3`, `wikipedia`.
  If something's missing here, it'll probably show itself when you run it.

## Configuration
The bot expects a few files to be filled first before startup:

### `op_ids.json`

This file contains IDs for host/operators and the "operating server".
There can be one host, and any number of operators, whose Discord user IDs need
to be filled in. `opguild` contains the ID of the operating server, and
`opguild_chans` contains the IDs of channels in that server.

```json
{
	"host": 111111111111111111,
	"operators": [
		111111111111111111
	],
	"opguild": 2222222222222222222,
	"opguild_chans": {
		"bot_guilds": 3333333333333333333,
		"connections": 4444444444444444444,
		"direct_messages": 5555555555555555555
	}
}
```

### `bot_token.conf`

This should contain the token of the bot, on a single line.

## Running
After that, you start the bot by doing `./run.sh`. It's recommended to do this
in `tmux` or similar.

The slash commands will need to be set up once for a new bot account, and every
time the command signatures change (new command added or removed, arguments or
description changed, etc). To do this, use `\syncslash`. You can replace the
backslash with a ping of the bot here (and you must if the `prefix_must_ping`
config option is enabled)

Speaking of config options, you may want to familiarize yourself with, and set
up, the options in the built-in config command.
