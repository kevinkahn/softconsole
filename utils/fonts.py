# import py-game
from guicore.screencallmanager import pg

import debug
from utils import hw

monofont = "notomono"  # gets reset to "droidsansmono" if noto not present to support pre Stretch


class Fonts(object):
	def __init__(self):
		global monofont
		pg.font.init()
		f = pg.font.get_fonts()
		if monofont not in f:
			# pre stretch system doesn't have noto mono
			monofont = "droidsansmono"
		self.fontcache = {"": {40: {True: {True: pg.font.SysFont("", hw.scaleH(40), True, True)}}}}

	# cache is tree dir with first key as name, second as size, third as ital, fourth as bold
	# initialize with 1 font for use in early abort messages (40,"",True,True)

	def Font(self, fsize, face="", bold=False, italic=False):
		def gennewfont(gname, gsize, gbold, gitalic):
			return pg.font.SysFont(gname, hw.scaleH(gsize), gbold, gitalic)

		size = int(fsize)
		try:
			return self.fontcache[face][size][italic][bold]
		except KeyError:
			name = face if face != "" else None
			if face not in self.fontcache:
				self.fontcache[face] = {size: {italic: {bold: gennewfont(name, size, bold, italic)}}}
			else:
				if size not in self.fontcache[face]:
					self.fontcache[face][size] = {italic: {bold: gennewfont(name, size, bold, italic)}}
				else:
					if italic not in self.fontcache[face][size]:
						self.fontcache[face][size][italic] = {bold: gennewfont(name, size, bold, italic)}
					else:
						if bold not in self.fontcache[face][size][italic]:
							self.fontcache[face][size][italic][bold] = gennewfont(name, size, bold, italic)
						else:
							pass  # log this - should never get here
			debug.debugPrint('Fonts', 'New font: ', face if face != "" else '-Sys-', ' :', size, (' b', ' B')[bold],
							 (' i', ' I')[italic])
			return self.fontcache[face][size][italic][bold]


fonts = Fonts()
