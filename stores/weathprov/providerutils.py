import logsupport
import config
import json
from logsupport import ConsoleWarning, ConsoleDetail

WeathProvs = {}

TermShortener = {}

GenericShortener = {
	'moderate': 'mdrt',
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
	'or': '/'
}


def TryShorten(term):
	global TermShortener
	newterm = term
	if term in TermShortener:
		return TermShortener[term]
	elif len(term) > 12 and term[0:4] != 'http':
		phrase = term.split(' ')
		chg = False
		for i, word in enumerate(list(phrase)):
			if word.lower() in GenericShortener:
				chg = True
				phrase[i] = GenericShortener[word.lower()]
				if word[0].isupper(): phrase[i] = phrase[i].capitalize()
		if chg:
			newterm = ' '.join(phrase).replace(' / ','/')
			if len(newterm) > 12:
				logsupport.Logs.Log("Long term: ", term, ' generically shortened to: ', newterm,
									severity=ConsoleWarning)
			else:
				logsupport.Logs.Log("Long term: ", term, ' generically shortened to: ', newterm,
									severity=ConsoleDetail)
		else:
			logsupport.Logs.Log("Long term: " + term, severity=ConsoleWarning)
		TermShortener[term] = newterm  # only report once
		with open(config.homedir + '/Console/termshortenlist.new', 'w') as f:
			json.dump(TermShortener, f, indent=4, separators=(',', ": "))
	return newterm


# noinspection PyBroadException
def SetUpTermShortener():
	global TermShortener
	try:
		with open(config.homedir + '/Console/termshortenlist', 'r') as f:
		# noinspection PyBroadException
			TermShortener = json.load(f)
	except:
		TermShortener = {}
