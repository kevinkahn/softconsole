import config

from utilfuncs import wc
import pygame



def fitFont(font, s, FitLine):
	if not FitLine: return s
	s2 = s
	starg = config.fonts.Font(s2, font).get_linesize()
	while starg > s:
		s2 = s / starg * s2
		starg = config.fonts.Font(s2, font).get_linesize()
	return s2


def CreateTextBlock(textlines, fontsizes, color, center, font=config.monofont, FitLine=False, MaxWidth=1000000):
	lines = textlines[:] if isinstance(textlines, list) else [textlines]
	sizes = fontsizes[:] if isinstance(fontsizes, list) else [fontsizes]
	h = 0
	w = 0
	t = len(sizes)
	if len(lines) > t:
		for i in range(len(lines) - t):
			sizes.append(sizes[-1])
	rl = []
	for l, s in zip(lines, sizes):
		for trys in [s, int(.75 * s), int(.625 * s)]:
			usesz = fitFont(font, trys, FitLine)
			line = config.fonts.Font(usesz, font).render(l, 0, wc(color))
			if line.get_width() < MaxWidth: break
		if line.get_width() > MaxWidth:
			usesz = fitFont(font, s // 2, FitLine)
			mid = len(l) // 2 + 1
			breaks = [i for i, ltr in enumerate(l) if ltr == ' '] + [len(l) - 1]
			for indx, val in enumerate(breaks):
				if config.fonts.Font(usesz, font).size(l[:breaks[indx]])[0] > MaxWidth:
					break
			lleft = l[:breaks[indx - 1]]
			lright = '  ' + l[breaks[indx - 1]:]
			usesz = fitFont(font, s // 2, FitLine)
			line1 = config.fonts.Font(usesz, font).render(lleft, 0, wc(color))
			line2 = config.fonts.Font(usesz, font).render(lright, 0, wc(color))
			rl.append(line1)
			rl.append(line2)
			h += (rl[-1].get_height() + rl[-2].get_height())
			w = max(w, rl[-1].get_width(), rl[-2].get_width())
		else:
			rl.append(line)
			h += rl[-1].get_height()
			w = max(w, rl[-1].get_width())
	blk = pygame.Surface((w, h))
	blk.set_colorkey(wc('black'))
	v = 0
	for l in rl:
		if center:
			blk.blit(l, ((w - l.get_width()) / 2, v))
		else:
			blk.blit(l, (0, v))
		v += l.get_height()

	return blk, blk.get_height(), blk.get_width()
