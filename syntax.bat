@echo off
REM  I guess I could .gitignore this? Ah well, it's probably useful for any developer using Windows and who has Pyflakes.

echo ----

REM  Unfortunately Pyflakes doesn't understand exec(compile(open().read()))
(
	type main.py
	echo.
	type functions.py
	echo.
	type commands.py
) >concatenatedmain.py

REM  Nor import. But hey, this works.
forfiles /m *.py /c "cmd /c if not @file==\"main.py\" if not @file==\"functions.py\" if not @file==\"commands.py\" (C:\Users\U\AppData\Local\Programs\Python\Python35\Scripts\pyflakes @file)"

echo ----
pause

del concatenatedmain.py
@echo on
