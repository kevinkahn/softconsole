import sys

import datetime
from datetime import timezone
from dateutil.tz import tzlocal
import logsupport

class UnicodeMixin(object):

	"""Mixin class to handle defining the proper __str__/__unicode__
	methods in Python 2 or 3."""

	if sys.version_info[0] >= 3:  # Python 3
		def __str__(self):
			return self.__unicode__()
	else:  # Python 2
		def __str__(self):
			return self.__unicode__().encode('utf8')


class PropertyUnavailable(AttributeError):
	pass

def LocalizeDateTime(t):
	now = datetime.datetime.now()
	return t.replace(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc).astimezone(tzlocal())

def _get_date_from_timestamp(datestamp, minsec=False):
	for fmt in ('%Y-%m-%d:%H:%M', '%Y-%m-%d:%H', '%Y-%m-%d %H:%M', '%Y-%m-%d', "%H:%M"):
		try:
			t = datetime.datetime.strptime(datestamp, fmt)
			#print('Matched {} with {} as {}'.format(fmt, datestamp, t))
			return t
		except ValueError:
			pass
	logsupport.Logs.Log('Bad date/time {} from Weatherbit'.format(datestamp), severity=logsupport.ConsoleWarning)
	raise ValueError('No valid date format found in Weatherbit response for {}'.format(datestamp))