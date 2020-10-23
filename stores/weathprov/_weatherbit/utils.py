import datetime
from datetime import timezone
from dateutil.tz import tzlocal
import logsupport


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