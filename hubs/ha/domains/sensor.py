import time

from hubs.ha.hasshub import HAnode, RegisterDomain, stringtonumeric
from utils.utilfuncs import safeprint
import logsupport


class Sensor(HAnode):  # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Sensor, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('sensor', self.entity_id, self)
		logsupport.Logs.Log(
			'Initialize attr store for sensor {} as {}'.format(self.entity_id, stringtonumeric(self.state)),
			severity=logsupport.ConsoleDetail)
		self.Hub.attrstore.SetVal(self.entity_id, stringtonumeric(self.state))
		self.missinglast = 'Explicit' if self.state in (
		'Xunknown', 'Xunavailable') else 'No'  # if unknown assume really not there (like pool stuff) options:
		if self.missinglast == 'Explicit': safeprint('Unavailable: {}'.format(self.entity_id))
		# 'No', 'Explicit', 'Implied', 'ExplictOnly':only set unavail on explicit report
		self.gone = 0

	def SetSensorAlert(self, p):
		self.Hub.attrstore.AddAlert(self.entity_id, p)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		if 'attributes' in ns: self.attributes = ns['attributes']
		try:
			if 'state' in ns:
				try:
					device = self.Hub.EntToDev[self.entity_id]
				except Exception as E:
					safeprint('Device lookup error {} {} {}'.format(self.entity_id, ns, E))
					device = None
				if ns['state'] in ('', 'unknown', 'None', 'unavailable'):
					if self.missinglast in ('No', 'No-ExplicitOnly'):  # don't keep reporting same outage

						self.Hub.NoteDeviceGone(device)
						if self.Hub.DevGoneCount(device) == 3:
							safeprint(
								'    Set intermittent device {}  {}'.format(device, self.Hub.DevGoneCount(device)))
							logsupport.Logs.Log(
								'Sensor data missing intermittent device {}; future outages not  logged'.format(
									device))
						elif self.Hub.DevGoneCount(device) > 3:
							pass  # safeprint('    Intermittent device {}  {}'.format(device, self.Hub.DevGoneCount(device)))
						else:
							safeprint(
								'    Gone from Hub: {} {} from {} {}'.format(self.Hub.name, self.entity_id, device, ns))
							logsupport.Logs.Log(
								'Sensor data missing for {} value: {}, Device {} offline'.format(ns['entity_id'],
																								 ns['state'], device))
						for ent in self.Hub.DeviceToEnt[device]:
							nd = self.Hub.GetNode(ent)[0]
							if hasattr(nd, 'missinglast'):
								if nd.missinglast == 'No':
									nd.missinglast = 'Implied'
									if self.Hub.DevGoneCount(device) > 2:
										pass  # safeprint('    Intermittent device {} {} {}'.format(device, ent,
									#											self.Hub.DevGoneCount(
									#												device)))
									else:
										safeprint('    Imply {} from {}'.format(ent, device))

						self.missinglast = 'Explicit' if self.missinglast == 'No' else 'ExplicitOnly'
						self.gone = time.time()
					elif self.missinglast == 'Implied':
						self.missinglast = 'Explicit'
					else:
						# safeprint('Still gone {}'.format(ns))
						logsupport.Logs.Log('Sensor data missing for {} value: {}'.format(ns['entity_id'], ns['state']),
											severity=logsupport.ConsoleDetail)
					stval = None
				else:
					if self.missinglast == 'Implied':
						self.missinglast = 'No-ExplicitOnly'
						safeprint(
							'Not whole device {} Ent: {} {}'.format(self.Hub.EntToDev[self.entity_id], self.entity_id,
																	ns))
					elif self.missinglast in ('Explicit', 'ExplicitOnly'):
						if self.Hub.DevGoneCount(device) < 3:
							logsupport.Logs.Log(
								'Sensor data now available for {} value: {}, Device {}'.format(ns['entity_id'],
																							   ns['state'],
																							   self.Hub.EntToDev[
																								   self.entity_id]))
							safeprint('Back: {} after {} Device {} {}'.format(self.entity_id, time.time() - self.gone,
																			  self.Hub.EntToDev[self.entity_id], ns))
						self.missinglast = 'No' if self.missinglast == 'Explicit' else 'No-ExplicitOnly'
					elif self.missinglast == 'No-ExplicitOnly':
						# safeprint('Odd item {} state {} {}'.format(self.entity_id,self.missinglast, ns))
						pass
					# noinspection PyBroadException
					try:
						# convert to numeric if a number
						stval = stringtonumeric(ns['state'])
					except Exception:
						# otherwise, leave as string
						stval = ns['state']
				self.Hub.attrstore.SetVal(self.entity_id, stval)
		except Exception as E:
			logsupport.Logs.Log('Sensor {} update error: State: {}  Exc:{}'.format(self.name, repr(ns), repr(E)))
			self.Hub.attrstore.SetVal(self.entity_id, None)


RegisterDomain('sensor', Sensor)
