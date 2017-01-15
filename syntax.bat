@echo off
REM  I guess I could .gitignore this? Ah well, it's probably useful for any developer using Windows and who has Pyflakes.

REM  Unfortunately Pyflakes doesn't understand exec(compile(open().read()))
(
	type main.py
	echo.
	type functions.py
	echo.
	type commands.py
) >concatenatedmain.py

REM  Nor import. But hey, this works.
@echo on
C:\Users\U\AppData\Local\Programs\Python\Python35\Scripts\pyflakes concatenatedmain.py col.py config.py emb.py images.py

@echo off
pause

del concatenatedmain.py
@echo on
