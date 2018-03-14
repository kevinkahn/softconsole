import config
import logsupport
from logsupport import ConsoleWarning
from utilities import wc
from stores import valuestore
import pygame
import string

ICONSPACE = 10

def CreateWeathBlock(Format, Fields, WeathFont, FontSize, WeathColor, icon, centered, day=-1):
	rf = []
	fh = 0
	fw = 0
	FS = [FontSize] if isinstance(FontSize, basestring) else FontSize[:]
	fsize = int(FS.pop(0))
	usefont = config.fonts.Font(fsize, WeathFont)

	try:
		vals = []
		for fld in Fields:
			if day == -1:
				vals.append(valuestore.GetVal(fld))
			else:
				vals.append(valuestore.GetVal(fld + (day,)))
	except Exception as e:
		logsupport.Logs.Log('Weather Block field access error: '+str(fld))

	try:
		for f in Format:

			rf.append(usefont.render(WFormatter().format(f, d=vals), 0, wc(WeathColor)))
			fh += rf[-1].get_height()
			if rf[-1].get_width() > fw: fw = rf[-1].get_width()
			if FS != []:
				fsize = int(FS.pop(0))
				usefont = config.fonts.Font(fsize, WeathFont)
	except Exception as e:
		logsupport.Logs.Log('TimeTemp Weather Formatting Error', severity=ConsoleWarning)
		if isinstance(e, KeyError):
			logsupport.Logs.Log(' No such weather field: ',e.message, severity=ConsoleWarning)
		rf.append(usefont.render('Weather N/A', 0, wc(WeathColor)))
		fh = rf[-1].get_height()*len(Format)  # force the height to always be equal even if error
		if rf[-1].get_width() > fw: fw = rf[-1].get_width()
	if icon is not None:
		totw = fw + fh + ICONSPACE
		hoff = fh + ICONSPACE
		iconref = icon[1:] if day == -1 else icon[1:] + (day,)
	else:
		totw = fw
		hoff = 0
	fsfc = pygame.Surface((totw, fh))
	fsfc.set_colorkey(wc('black'))
	v = 0
	try:
		if icon is not None: fsfc.blit(pygame.transform.smoothscale(valuestore.ValueStores[icon[0]].GetVal(iconref), (fh, fh)), (0, 0))
	except:
		logsupport.Logs.Log("Missing icon for: ",str(iconref),severity=ConsoleWarning)
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








class WeatherInfoActual(object):

	def __init__(self, WunderKey, location):
		# Put the Block Refresh here to test it TODO
#		T = WeatherVals(location,WunderKey)
#		valuestore.ValueStores[location] = T
#		T.BlockRefresh()
		return
		self.keyok = True
		self.nextwebreq = 0  # time of next call out to wunderground
		self.webreqinterval = 60*30  # 30 minutes
		self.url = 'http://api.wunderground.com/api/' + WunderKey + '/conditions/forecast10day/astronomy/q/' \
				   + location + '.json'
		self.ConditionVals = {}
		self.ForecastVals = []
		self.location = location
		self.returnval = 0
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile = open(os.path.dirname(config.configfile) + '/' + location + 'wv.log', 'w')
			self.weathjsonfile = open(os.path.dirname(config.configfile) + '/' + location + 'wj.log', 'w')
			self.weathvalfile.write(location + ' \n==================\n')
			self.weathvalfile.flush()
			self.weathjsonfile.write(location + '\n==================\n')
			self.weathjsonfile.flush()

	def dumpweatherresp(self, val, json, tag, param):
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(val) + '\n=================')
			self.weathjsonfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(json) + '\n=================')
			self.weathvalfile.flush()
			self.weathjsonfile.flush()
