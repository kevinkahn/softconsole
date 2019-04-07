"""
This file holds utility functions that have no dependencies on other console code.
Avoids import loops
"""
import webcolors


def wc(clr, factor=0.0, layercolor=(255, 255, 255)):
	lc = webcolors.name_to_rgb(layercolor) if isinstance(layercolor, str) else layercolor
	if isinstance(clr, str):
		try:
			v = webcolors.name_to_rgb(clr)
		except ValueError:
			# logsupport.Logs.Log('Bad color name: ' + str(clr), severity=ConsoleWarning)
			v = webcolors.name_to_rgb('black')
	else:
		v = clr

	return v[0] + (lc[0] - v[0]) * factor, v[1] + (lc[1] - v[1]) * factor, v[2] + (lc[2] - v[2]) * factor


def interval_str(sec_elapsed):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	if d != 0:
		return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)
	elif h != 0:
		return "{:>02d}hrs {:>02d}mn {:>02d}sec".format(h, m, s)
	else:
		return "{:>02d}mn {:>02d}sec".format(m, s)


def tint(clr, tint_factor=.25):
	# tint_factor = .25
	r, g, b = wc(clr)
	return r + (255 - r) * tint_factor, g + (255 - g) * tint_factor, b + (255 - b) * tint_factor


def TreeDict(d, args):
	# Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
	if len(args) == 1:
		temp = d[args[0]]
		if isinstance(temp, str) and temp.isdigit():
			temp = int(temp)
		else:
			try:
				temp = float(temp)
			except (ValueError, TypeError):
				pass
		return temp
	else:
		return TreeDict(d[args[0]], args[1:])
