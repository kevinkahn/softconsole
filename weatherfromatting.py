import config
import logsupport
from logsupport import ConsoleWarning, ConsoleDetailHigh
from utilfuncs import wc
from stores import valuestore
import pygame
import string

ICONSPACE = 10


def CreateWeathBlock(Format, Fields, WeathFont, FontSize, WeathColor, icon, centered, day=-1, useicon=True):
	erroronce = False
	rf = []
	fh = 0
	fw = 0
	FS = FontSize[:] if isinstance(FontSize, list) else [FontSize]
	fsize = int(FS.pop(0))
	usefont = config.fonts.Font(fsize, WeathFont)

	fld = ''
	vals = []
	iconref = []
	try:
		for fld in Fields:
			if day == -1:
				t = valuestore.GetVal(fld)
				if callable(t):
					vals.append(t())
				else:
					vals.append(t)
			else:
				fcstdays = valuestore.GetVal((fld[0], 'FcstDays'))
				if day < fcstdays:
					t = valuestore.GetVal(fld + (day,))
					if callable(t):
						vals.append(t())
					else:
						vals.append(t)
				else:
					vals.append(None)
					if not erroronce:
						logsupport.Logs.Log(
							"Attempt to forecast(day " + str(day) + ") beyond " + str(fcstdays) + " returned by WU",
							severity=ConsoleDetailHigh)
						erroronce = True
	except Exception as e:
		logsupport.Logs.Log('Weather Block field access error: '+str(fld)+' Exc: '+str(e))

	try:
		for f in Format:
			rf.append(usefont.render(WFormatter().format(f, d=vals), 0, wc(WeathColor)))
			fh += rf[-1].get_height()
			if rf[-1].get_width() > fw: fw = rf[-1].get_width()
			if FS:
				fsize = int(FS.pop(0))
				usefont = config.fonts.Font(fsize, WeathFont)
	except Exception as e:
		logsupport.Logs.Log('TimeTemp Weather Formatting Error: ', repr(e), severity=ConsoleWarning)
		if isinstance(e, KeyError):
			logsupport.Logs.Log(' No such weather field: ',e.message, severity=ConsoleWarning)
		rf.append(usefont.render('Weather N/A', 0, wc(WeathColor)))
		fh = rf[-1].get_height()*len(Format)  # force the height to always be equal even if error
		if rf[-1].get_width() > fw: fw = rf[-1].get_width()
	if icon is not None:
		totw = fw + fh + ICONSPACE
		hoff = fh + ICONSPACE
		if day == -1:
			iconref = icon[1:]
		else:
			if day < fcstdays:
				iconref = icon[1:] + (day,)
			else:
				iconref = None
				if not erroronce:
					erroronce = True
					logsupport.Logs.Log(
						"Attempt to forecast(day " + str(day) + ") beyond " + str(fcstdays) + " returned by provider",
						severity=ConsoleDetailHigh)
	else:
		iconref = None
		totw = fw
		hoff = 0
	fsfc = pygame.Surface((totw, fh))
	fsfc.set_colorkey(wc('black'))
	v = 0
	# noinspection PyBroadException
	try:
		if iconref is not None:
			tmp = pygame.transform.smoothscale(valuestore.ValueStores[icon[0]].GetVal(iconref), (fh, fh))
			# R = pygame.Rect((0, 0), (tmp.get_height(), tmp.get_width()))
			# pygame.draw.rect(fsfc, (128, 128, 128), R, 3)
			# print('Scale: '+str(tmp.get_height())+ ' ' + str(valuestore.ValueStores[icon[0]].GetVal(iconref)) )
			fsfc.blit(tmp, (0, 0))
	except:
		if useicon:
			logsupport.Logs.Log("Internal error - missing icon for: ", str(icon[0]), str(iconref),
								severity=ConsoleWarning)
	for l in rf:
		if centered:
			fsfc.blit(l,(hoff + (fw-l.get_width())/2,v))
		else:
			fsfc.blit(l,(hoff,v))
		v += l.get_height()
	return fsfc


class WFormatter(string.Formatter):
	def format_field(self, value, format_spec):
		if format_spec.endswith(('f', 'd')) and value is None:
			return 'n/a'
		elif value is None:
			return 'n/a'
		elif value == -9999.0:
			return 'n/a'
		else:
			return super(WFormatter, self).format_field(value, format_spec)


