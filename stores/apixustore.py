import functools
import pygame
import io
import os
import sys
import json
import time
import datetime
import requests
import utilities
import config
from stores import valuestore
from collections import OrderedDict
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError


def TreeDict(d, *args):
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
		return TreeDict(d[args[0]], *args[1:])


CondFieldMap = {'Time': (int, ('current', 'last_updated_epoch')),
				'Location': (str, ('location', 'name')),
				'Temp': (float, ('current', 'temp_f')),
				'Sky': (str, ('current', 'condition', 'text')),
				'Feels': (float, ('current', 'feelslike_f')),
				'WindDir': (str, ('current', 'wind_dir')),
				'WindMPH': (float, ('current', 'wind_mph')),
				'Humidity': (str, ('current', 'humidity')),
				'Iconurl': (str, ('current', 'condition', 'icon')),
				'Sunrise': (str, ('forecast', 'forecastday', 0, 'astro', 'sunrise')),
				'Sunset': (str, ('forecast', 'forecastday', 0, 'astro', 'sunset')),
				'Moonrise': (str, ('forecast', 'forecastday', 0, 'astro', 'moonrise')),
				'Moonset': (str, ('forecast', 'forecastday', 0, 'astro', 'moonset'))
				}

FcstFieldMap = {'Day': (int, ('date_epoch')),
				'High': (float, ('day', 'maxtemp_f')),
				'Low': (float, ('day', 'mintemp_f')),
				'Sky': (str, ('day', 'condition', 'text')),
				'WindSpd': (str, ('day', 'maxwind_mph')),
				'Iconurl': (str, ('day', 'condition', 'icon'))
				}


class APIXUWeatherSource(object):
	def __init__(self, api, store, location):
		self.baseurl = 'https://api.apixu.com/v1/forecast.json'
		self.args = {'key': api, 'q': location, 'days': '10'}
		self.apikey = api
		self.thisStore = store
		self.location = location

	def GetMap(self, fld):
		pass

	def FetchWeather(self):
		r = requests.get(self.baseurl, params=self.args)
		json = r.json()
		for fn, entry in CondFieldMap.items():
			val = TreeDict(json, *entry[1])
			self.thisStore.SetVal(('Cond', fn), entry[0](val))
		fcstdays = len(json['forecast']['forecastday'])
		for i in range(fcstdays):
			fcst = json['forecast']['forecastday'][i]
			for fn, entry in FcstFieldMap.items():
				val = TreeDict(fcst, *entry[1])
				self.thisStore.SetVal((('Fcst', fn), i), val)
