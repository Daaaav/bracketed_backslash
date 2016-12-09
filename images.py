# encoding=utf-8

from PIL import Image

barim = Image.open('img/bar.png')
greenbarim = Image.open('img/greenbar.png')
yellowbarim = Image.open('img/yellowbar.png')
redbarim = Image.open('img/redbar.png')
thresholdim = Image.open('img/threshold.png')

def progressbar(percentage):
	tempimg = Image.new("RGBA", (102,12))
	tempimg.paste(barim, (0,0,102,12))

	if percentage >= 95:
		barcolor = redbarim
	elif percentage >= 80:
		barcolor = yellowbarim
	else:
		barcolor = greenbarim
	tempimg.paste(barcolor.crop((0,0,percentage,10)), (1,1,percentage+1,11))
	tempimg.save("img/temp.png") # Maybe we can write to and return a file-like object instead of writing anything to disk?

	return "img/temp.png"

def votebar(percentagepro, percentageopp, threshold):
	tempimg = Image.new('RGBA', (102,12))
	tempimg.paste(barim, (0,0,102,12))

	tempimg.paste(thresholdim, (threshold+1,1,threshold+2, 11))

	tempimg.paste(greenbarim.crop((0,0,int(percentagepro),10)), (1,1,int(percentagepro)+1,11))
	tempimg.paste(redbarim.crop((100-int(percentageopp),0,100,10)), (101-int(percentageopp),1,101,10))
	tempimg.save('img/temp.png')

	return 'img/temp.png'
