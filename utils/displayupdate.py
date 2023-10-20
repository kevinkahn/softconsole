from guicore.screencallmanager import pg

from utils import hw

rotationangle = (0, 270, 180, 90, 0)
touchmodifier = ('', 'cc90', 'flip', 'cc270', '')
softrotate = 0
actualtouchmodifier = ''
updatedisplay = pg.display.update


def softdisplayupdate(rect=None):
	if rect is not None:
		hw.screen.blit()
	t = pg.transform.rotate(hw.screen, rotationangle[softrotate])
	hw.realscreen.blit(t, (0, 0))
	# del t
	pg.display.update()


def initdisplayupdate(sr):
	global updatedisplay, softrotate
	softrotate = sr
	if softrotate != 0:
		updatedisplay = softdisplayupdate


portrait = True
