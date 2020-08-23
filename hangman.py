alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def validletter(ltr):
	if findletter(ltr) == -1:
		return False
	return True

def findletter(ltr):
	return alphabet.find(ltr.upper())

class HangmanGame:
	"""One instance of hangman.
	This class is designed not to depend on [\] code.
	"""

	def __init__(self, word, starter, maxmistakes=10):
		self.word = word
		self.starter = starter
		self.maxmistakes = maxmistakes
		self.mistakes = 0
		self.active = True
		self.guessedletters = [False]*26

	def alreadyguessed(self, ltr):
		"""Returns True if the letter was already guessed"""
		if self.guessedletters[findletter(ltr)]:
			return True
		return False

	def guess(self, ltr):
		"""Sets a letter as guessed, and updates game state
		depending on whether the letter occurs in the word.
		Returns whether guess was successful.
		"""
		self.guessedletters[findletter(ltr)] = True
		if self.word.upper().find(ltr.upper()) != -1:
			# Hit
			if self.fullyguessed():
				self.stop()
			return True
		# No hit
		self.miss()
		return False

	def fullwordguess(self, word):
		if word.lower() == self.word.lower():
			# Hit
			self.stop()
			return True
		# No hit
		self.miss()
		return False

	def correctlength(self, word):
		"""Returns True if word is the same length as the real word"""
		return len(word) == len(self.word)

	def fullyguessed(self):
		for i in range(0, len(self.word)):
			if not self.alreadyguessed(self.word[i]):
				return False
		return True

	def miss(self):
		"""Increments the number of mistakes, and
		marks game inactive if max mistakes reached
		"""
		self.mistakes += 1
		if self.isgameover():
			self.stop()

	def stop(self):
		self.active = False

	def isgameover(self):
		return self.mistakes >= self.maxmistakes

	def attemptsleft(self):
		return self.maxmistakes - self.mistakes

	def isstarter(self, member):
		return member == self.starter

	def worddisp(self):
		theoutput = ''

		for i in range(0, len(self.word)):
			if self.alreadyguessed(self.word[i]):
				theoutput += '__**`{}`**__ '.format(self.word[i])
			else:
				theoutput += '`_` '

		# Now display already guessed letters.
		theoutput += '    (used: '

		notnone = False

		for l in alphabet:
			if self.alreadyguessed(l):
				notnone = True
				theoutput += l

		if not notnone:
			theoutput += 'none'

		theoutput += ')'

		return theoutput
