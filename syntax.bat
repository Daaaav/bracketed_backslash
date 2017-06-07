@echo off
REM  I guess I could .gitignore this? Ah well, it's probably useful for any developer using Windows and who has Pyflakes.

echo ----

REM  Unfortunately Pyflakes doesn't understand import. But hey, this works.
forfiles /m *.py /c "cmd /c C:\Users\U\AppData\Local\Programs\Python\Python35\Scripts\pyflakes @file"

echo ----
pause

@echo on
