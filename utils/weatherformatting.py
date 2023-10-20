# import py-game
from guicore.screencallmanager import pg

from utils import fonts
import logsupport
from logsupport import ConsoleWarning, ConsoleDetailHigh
from stores import valuestore
from utils.utilfuncs import wc, fmt
from stores.weathprov.providerutils import MissingIcon

ICONSPACE = 10


def CreateWeathBlock(Format, Fields, WeathFont, FontSize, WeathColor, icon, centered, day=-1, useicon=True,
					 maxiconsize=0, maxhorizwidth=1000):
	rf = []
	fh = 0
	fw = 0
	FS = FontSize[:] if isinstance(FontSize, list) else [FontSize]
	tFS = FontSize[:] if isinstance(FontSize, list) else [FontSize]
	fsize = int(FS.pop(0))
	tfsize = int(tFS.pop(0))
	usefont = fonts.fonts.Font(fsize, WeathFont)
	tusefont = fonts.fonts.Font(tfsize, WeathFont)
	fcstdays = 0

	fld = ''
	vals = []
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
					logsupport.Logs.Log(
						"Attempt to forecast(day " + str(day) + ") beyond " + str(fcstdays) + " returned",
						severity=ConsoleDetailHigh)
	except Exception as e:
		logsupport.Logs.Log('Weather Block field access error: ' + str(fld) + ' Exc: ' + str(e))

	iconsize = 0
	try:
		for _ in Format:
			iconsize += tusefont.render('W', 0, wc(WeathColor)).get_height()
			if tFS:
				tfsize = int(tFS.pop(0))
				tusefont = fonts.fonts.Font(tfsize, WeathFont)
		if maxiconsize != 0: iconsize = min(iconsize, maxiconsize)
		if icon is None: iconsize = 0

		for f in Format:
			linetorender = fmt.format(f, d=vals)
			renderedline = usefont.render(linetorender, 0, wc(WeathColor))
			if renderedline.get_width() > maxhorizwidth - iconsize:  # todo make work for > 2 lines
				l1 = linetorender.split(' ')
				l2 = []
				while usefont.render(' '.join(l1), 0, wc(WeathColor)).get_width() > maxhorizwidth - iconsize:
					l2.insert(0, l1[-1])
					del l1[-1]
				rf.append(usefont.render(' '.join(l1), 0, wc(WeathColor)))
				rf.append(usefont.render('  ' + ' '.join(l2), 0, wc(WeathColor)))  # indent extra lines
			else:
				rf.append(usefont.render(linetorender, 0, wc(WeathColor)))
			if FS:
				fsize = int(FS.pop(0))
				usefont = fonts.fonts.Font(fsize, WeathFont)
		for l in rf:
			fh += l.get_height()
			if l.get_width() > fw: fw = l.get_width()

	except Exception as e:
		logsupport.Logs.Log('Weather Formatting Error: ', repr(e), severity=ConsoleWarning)
		if isinstance(e, KeyError):
			logsupport.Logs.Log(' No such weather field: ', e.args, severity=ConsoleWarning)
		rf.append(usefont.render('Weather N/A', 0, wc(WeathColor)))
		fh = rf[-1].get_height() * len(Format)  # force the height to always be equal even if error
		if rf[-1].get_width() > fw: fw = rf[-1].get_width()
	if icon is not None:
		totw = fw + iconsize + ICONSPACE
		hoff = iconsize + ICONSPACE
		if day == -1:
			iconref = icon[1:]
		else:
			if day < fcstdays:
				iconref = icon[1:] + (day,)
			else:
				iconref = None
				logsupport.Logs.Log(
					"Attempt to forecast(day " + str(day) + ") beyond " + str(fcstdays) + " returned by provider",
					severity=ConsoleDetailHigh)
	else:
		iconref = None
		iconsize = 0
		totw = fw
		hoff = 0
	fsfc = pg.Surface((totw, fh))
	fsfc.set_colorkey(wc('black'))
	v = 0
	# noinspection PyBroadException
	try:
		if iconref is not None and valuestore.ValueStores[icon[0]].GetVal(iconref) != MissingIcon:
			tmp = pg.transform.smoothscale(valuestore.ValueStores[icon[0]].GetVal(iconref), (iconsize, iconsize))
			fsfc.blit(tmp, (0, (fh - iconsize) // 2))
	except Exception as E:
		if useicon:
			logsupport.Logs.Log("Internal error - missing icon for: ", str(icon[0]), str(iconref), repr(E),
								severity=ConsoleWarning)
	# logsupport.Logs.Log("Temp msg: ", valuestore.ValueStores([icon[0], ('Cond', 'IconURL')]))
	for l in rf:
		if centered:
			fsfc.blit(l, (hoff + (fw - l.get_width()) / 2, v))
		else:
			fsfc.blit(l, (hoff, v))
		v += l.get_height()
	return fsfc

