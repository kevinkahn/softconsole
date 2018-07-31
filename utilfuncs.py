"""
This file holds utility functions that have no dependencies on other console code.
Avoids import loops
"""
import webcolors


def wc(clr, factor=0.0, layercolor=(255, 255, 255)):  # todo move this and interval str to a dependencyless file
	try:
		v = webcolors.name_to_rgb(clr)
	except ValueError:
		#logsupport.Logs.Log('Bad color name: ' + str(clr), severity=ConsoleWarning)
		v = webcolors.name_to_rgb('black')

	return v[0] + (layercolor[0] - v[0]) * factor, v[1] + (layercolor[1] - v[1]) * factor, v[2] + (
				layercolor[2] - v[2]) * factor


def interval_str(sec_elapsed):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)

def tint(clr):
	tint_factor = .25
	r, g, b = wc(clr)
	return r + (255 - r) * tint_factor, g + (255 - g) * tint_factor, b + (255 - b) * tint_factor