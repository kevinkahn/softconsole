import time

import config
import debug
from screens import screen
from keyspecs import toucharea
from utils import utilities, fonts, hw
import screens.supportscreens as supportscreens
from utils.utilfuncs import wc, interval_str
import configobj

fixedoverrides = {'CharColor': 'white', 'BackgroundColor': 'royalblue', 'label': ['Maintenance'], 'DimTO': 60,
				  'PersistTO': 90, 'KeyColorOff': 'green'}


class MaintScreenDesc(screen.BaseKeyScreenDesc):
	# noinspection PyDefaultArgument
	def __init__(self, name, keys, overrides=None):
		# keys is a dict of key descriptors the name is the key in the dict and the item is a tuple
		# (label, tapproc, dbltapproc, verify, dispopts, defopts, var)
		# the following works around what looks like a bug - if I just set overrides=fixoverrides
		# above it keeps using last call's overrides
		global fixedoverrides
		ov = configobj.ConfigObj(overrides) if overrides is not None else configobj.ConfigObj(fixedoverrides)
		super().__init__(ov, name)
		debug.debugPrint('Screen', "Build Maintenance Screen")
		self.NavKeysShowing = True
		self.DefaultNavKeysShowing = True
		screen.AddUndefaultedParams(self, None, TitleFontSize=40, SubFontSize=25)
		self.SetScreenTitle(name, self.TitleFontSize, 'white')
		for k, kt in keys.items():
			DN = [kt[0]] if isinstance(kt[0], str) else kt[0]
			DblTap = None if len(kt) < 3 else kt[2]
			verify = False if len(kt) < 4 else kt[3] == 'True'
			dispopts = [] if len(kt) < 5 else kt[4]
			defopt = None if len(kt) < 6 else kt[5]
			V = '' if len(kt) < 7 else kt[6]
			self.Keys[k] = toucharea.ManualKeyDesc(self, k, DN, 'gold', 'black', 'red', KOn='black', KOff='red',
												   Verify=verify, proc=kt[1], procdbl=DblTap, dispopts=dispopts,
												   dispdef=defopt, var=V)
			if verify:
				VerifyScreen = supportscreens.VerifyScreen(self.Keys[k], ('Proceed',), ('Cancel',), kt[1],
														   self, self.Keys[k].KeyColorOff, self.Keys[k].BackgroundColor,
														   self.Keys[k].CharColor,
														   True, self.HubInterestList)
				self.Keys[k].Proc = VerifyScreen.Invoke

		topoff = self.SubFontSize
		self.LayoutKeys(topoff, self.useablevertspace - topoff)
		self.DimTO = 60
		self.PersistTO = 120  # allow long inactivity in Maint screen but not forever
		utilities.register_example("MaintScreenDesc", self)

	def ScreenContentRepaint(self):
		# todo allow 2 line title? turn into a set title
		r = fonts.fonts.Font(self.SubFontSize, '', True, True).render(
			'{} Up: {}'.format(time.strftime("%H:%M:%S", time.localtime(config.sysStore.Time)),
							   interval_str(config.sysStore.UpTime)), 0, wc(self.CharColor))
		rl = (hw.screenwidth - r.get_width()) / 2
		hw.screen.blit(r, (rl, self.TopBorder + self.TitleFontSize))

	def ExitScreen(self, viaPush):
		super().ExitScreen(viaPush)
