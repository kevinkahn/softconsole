import json

import config
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail

WeathProvs = {}

TermShortener = {}

StillLong = {}

GenericShortener = {
	'moderate': 'mdrt',
	'thunder': 'thndr',
	'patchy': 'pchy',
	'chance': 'chc',
	'freezing': 'frzing',
	'light': 'lt',
	'heavy': 'hvy',
	'shower': 'shwr',
	'showers': 'shwrs',
	'drizzle': 'drzl',
	'rain': 'rn',
	'snow': 'snw',
	'or': '/',
	'with': 'w/',
	'until': 'til',
	'evening': 'evng',
	'possible': 'psbl',
	'morning': 'mrng',
	'the': ''
}


def TryShorten(term):
	global TermShortener, StillLong
	maxlength = 12
	newterm = term.replace(' throughout the day', '')  # todo def a noise list also del trailing, leading spaces etc
	newterm = newterm.replace('.', '')

	if newterm in TermShortener:
		return TermShortener[newterm]
	elif len(newterm) > maxlength and newterm[0:4] != 'http':
		phrase = newterm.split(' ')
		chg = False
		for i, word in enumerate(list(phrase)):
			if word.lower() in GenericShortener:
				chg = True
				phrase[i] = GenericShortener[word.lower()]
				if word[0].isupper(): phrase[i] = phrase[i].capitalize()
		if chg:  # todo clean up reporting
			newterm = ' '.join(phrase).replace(' /', '/').replace('/ ', '/').replace('.', '')
			if len(newterm) > maxlength and term not in StillLong:
				logsupport.Logs.Log("Long term: ", term, ' generically shortened to: ', newterm,
									severity=ConsoleWarning)
				StillLong[term] = newterm
			elif term not in StillLong:
				logsupport.Logs.Log("Long term: ", term, ' generically shortened to: ', newterm,
									severity=ConsoleDetail)
		else:
			logsupport.Logs.Log("Long term: " + term, severity=ConsoleWarning)
		TermShortener[term] = newterm  # only report once
		with open('{}/Console/termshortenlist.new'.format(config.sysStore.HomeDir), 'w') as f: # todo move to async?
			json.dump(TermShortener, f, indent=4, separators=(',', ": "))
		with open('{}/Console/problemterms.new'.format(config.sysStore.HomeDir), 'w') as f: # todo move to async?
			json.dump(TermShortener, f, indent=4, separators=(',', ": "))
			json.dump(StillLong, f, indent=4, separators=(',', ": "))
	return newterm


# noinspection PyBroadException
def SetUpTermShortener():
	global TermShortener
	try:
		with open('{}/Console/termshortenlist'.format(config.sysStore.HomeDir), 'r') as f:
			# noinspection PyBroadException
			TermShortener = json.load(f)
	except:
		TermShortener = {}
