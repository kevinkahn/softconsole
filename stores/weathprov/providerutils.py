import logsupport
import config
import json
from logsupport import ConsoleWarning

TermShortener = {}


def TryShorten(term):
	global TermShortener
	if term in TermShortener:
		return TermShortener[term]
	elif len(term) > 12 and term[0:4] != 'http':
		logsupport.Logs.Log("Long term: " + term, severity=ConsoleWarning)
		TermShortener[term] = term  # only report once
		with open(config.homedir + '/Console/termshortenlist.new', 'w') as f:
			json.dump(TermShortener, f, indent=4, separators=(',', ": "))
	return term


def SetUpTermShortener():
	global TermShortener
	try:
		with open(config.homedir + '/Console/termshortenlist', 'r') as f:
		# noinspection PyBroadException
			TermShortener = json.load(f)
	except:
		TermShortener = {}
