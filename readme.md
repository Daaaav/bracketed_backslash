# \[\\\]
This is a bot created by Info Teddy, and currently maintained by Info Teddy and
Dav999, written in Python for use on the
[tOLP Discord server](https://discord.gg/0r76El7PzkPMhSBF).

This bot is in active development.
# Installation Instructions
## Requirements
- Python ≥3.5 is required.
- [`discord.py`](https://github.com/Rapptz/discord.py) is required.

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

After that, you start the bot by doing `./intro.sh` (if you did
`chmod +x intro.sh`) or `bash intro.sh` or `sh intro.sh`.
# Configuration
Since this is a private bot, the variables are pretty much hard-written into
the bot script itself. But all of the user-specific variables (except for the
token) are Discord IDs.
## Token
The bot token should be only by itself in a file, called `bot_token.conf`, in
the same directory as `intro.sh`.
# Contributing
See [contributing.md](contributing.md).
