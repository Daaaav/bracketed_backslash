# Contributing
Just make sure your code is worth its merit.
## General
Please don't push your changes to the `master` branch, unless you know what you
are doing! Use the `untested` branch instead. Or you can create your own
branch.
## Documentation Style
Make sure each line doesn’t exceed eighty characters, for maintainability.
Markdown will concatenate each “block” of text not separated by a blank line
into one big line, anyways.
## Code Style
- tabs instead of spaces with a tabstop of eight.
- no trailing whitespace
	- this includes lines that are just whitespace
- things that look like `this()` should stay looking like `this()` and not
`this ()`

# Tasks
If you’re willing to let Info Teddy be lazy and do the work that he’s supposed
to do (and he’ll convince you by saying he has homework to do and a life), you
can add all of this.
## v1.0
- [ ] actually cache message attachments
- [ ] make `\info` show when the member was last seen (and do it well)
- [ ] make `\restart` restart the bot in place such that everything is reloaded
but the `Client.messages` cache isnt cleared
- [ ] less hard-written configuration (see im lazy) and/or none at all
- [ ] log more shit
	- [x] member avatar changes
	- [x] member role adds/removes
	- [x] when people are invisible for no reason
		- its done however it can only detect invisible people when
		they send a message
- [ ] actually add moderation/administration commands
	- [x] `\softban`
	- [x] `\nononly`
	- [x] `\nogenmen`
	- [x] `\nocedule`
		- [ ] come up with a better name for this fucking command
	- [x] `\notts`
	- [x] `\nonick`
	- [x] `\rolerst`
- [ ] give roles
	- [x] give roles upon a new member joining
	- [ ] remember roles so members cant circumvent softbans/other
	restrictive roles and ofc give them back upon joining

# Ideas
If you’re willing to be lazy yourself, add ideas and/or requests here so people
who aren’t lazy can actually do them.

If an item is checked, then it means the team is going to do it (hopefully),
and it will be added to the section above.
## v1.0
- [ ] more secret shit
- [ ] ~~maybe if the bot doesnt have a token specified itll just log shit to
an output file~~ i forgot about the part where youd need the token specified anyways
- [ ] maybe one single configuration location like a normal person xd
