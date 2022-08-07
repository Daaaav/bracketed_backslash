# \[\\\]
This is a bot created by Info Teddy, and currently maintained by Info Teddy and
Dav999, written in Python.

This bot is in active development.
# License
All code files in the entirety of this repository are licensed under GPLv3-only.
You cannot automatically "upgrade" the license to a later version of the GPL,
an upgrade has to be a relicensing that will be decided by the project
maintainers.
# Installation Instructions
## Requirements
- Python ≥3.6 is required.
- [`discord.py` rewrite](https://github.com/Rapptz/discord.py/tree/rewrite) is
  required.
- [Pillow](https://github.com/python-pillow/Pillow) is required.

## Downloading
Download the bot first.

With [SSH](https://gitgud.io/help/ssh/README):
```
git clone git@ssh.gitgud.io:infoteddy/bracketed_backslash.git
```
With HTTPS:
```
git clone https://gitgud.io/infoteddy/bracketed_backslash.git
```
With HTTPS, you will be prompted for your [gitgud.io](https://gitgud.io/)
username and password every time, not just when cloning the repository.
## Setup
Make sure to `chmod +x main.py` if you want to make sure the bot can restart
with `\restart`.

After that, you start the bot by doing `./run.sh` (if you did
`chmod +x run.sh`) or `bash run.sh` or `sh run.sh`.
# Configuration
Since this started as a private bot, the variables are pretty much hard-written
into the bot scripts themselves. But all of the hardcode variables are Discord
IDs.

Sometime ago, we added the `\config` command. There should be enough
documentation for it in its `\help` entry.
## Token
The bot token should be only by itself in a file, called `bot_token.conf`, in
the same directory as `main.py`.
## Owner ID
The owner ID should be only by itself in a file, called `ownerid.conf`, in the
same directory as `main.py`.
# Contributing
See [contributing.md](contributing.md).
