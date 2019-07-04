import time
import logsupport
from logsupport import ConsoleDetail
import debug
import config
from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, _NormalizeState, RegisterDomain
import screens.__screens as screens
from controlevents import CEvent, PostEvent, ConsoleEvent


class MediaPlayer(HAnode):
	def __init__(self, HAitem, d):
		super(MediaPlayer, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('media_player', self.entity_id, self)

		self.Sonos = False
		if 'sonos_group' in self.attributes:
			self.Sonos = True
			self.internalstate = 255
			self.sonos_group = self.attributes['sonos_group']
			self.source_list = self.attributes['source_list']  # todo should this be conditional like in update?
			self.muted = self.attributes['is_volume_muted']
			self.volume = self.attributes['volume_level']
			self.song = self.attributes['media_title'] if 'media_title' in self.attributes else ''
			self.artist = self.attributes['media_artist'] if 'media_artist' in self.attributes else ''
			self.album = self.attributes['media_album_name'] if 'media_album_name' in self.attributes else ''

	def AddPlayer(self):
		if self.Sonos:
			logsupport.Logs.Log("{}: added new Sonos player {}".format(self.Hub.name, self.name))
			config.SonosScreen = None

	def Update(self, **ns):
		oldst = self.state
		if 'attributes' in ns: self.attributes = ns['attributes']
		self.state = ns['state']
		newst = _NormalizeState(self.state)
		if newst != self.internalstate:
			logsupport.Logs.Log("Mediaplayer state change: ", self.Hub.Entities[self.entity_id].name, ' was ',
								self.internalstate, ' now ', newst, '(', self.state, ')', severity=ConsoleDetail)
			self.internalstate = newst

		if self.Sonos:
			if self.internalstate == -1:  # unavailable
				logsupport.Logs.Log("Sonos room went unavailable: ", self.Hub.Entities[self.entity_id].name)
				return
			else:
				if oldst == -1:
					logsupport.Logs.Log("Sonos room became available: ", self.Hub.Entities[self.entity_id].name)
				self.sonos_group = self.attributes['sonos_group']
				if 'source_list' in self.attributes: self.source_list = self.attributes['source_list']
				self.muted = self.attributes['is_volume_muted'] if 'is_volume_muted' in self.attributes else 'True'
				self.volume = self.attributes['volume_level'] if 'volume_level' in self.attributes else 0
				self.song = self.attributes['media_title'] if 'media_title' in self.attributes else ''
				self.artist = self.attributes['media_artist'] if 'media_artist' in self.attributes else ''
				self.album = self.attributes['media_album_name'] if 'media_album_name' in self.attributes else ''

			if screens.DS.AS is not None:
				if self.Hub.name in screens.DS.AS.HubInterestList:
					if self.entity_id in screens.DS.AS.HubInterestList[self.Hub.name]:
						debug.debugPrint('DaemonCtl', time.time() - config.sysStore.ConsoleStartTime,
										 "HA reports node change(screen): ",
										 "Key: ", self.Hub.Entities[self.entity_id].name)

						# noinspection PyArgumentList
						PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
											   value=self.internalstate))

	def Join(self, master, roomname):
		ha.call_service(self.Hub.api, 'sonos', 'join', {'master': '{}'.format(master),
														'entity_id': '{}'.format(roomname)})

	def UnJoin(self, roomname):
		ha.call_service(self.Hub.api, 'sonos', 'unjoin', {'entity_id': '{}'.format(roomname)})

	def VolumeUpDown(self, roomname, up):
		updown = 'volume_up' if up >= 1 else 'volume_down'
		ha.call_service(self.Hub.api, 'media_player', updown, {'entity_id': '{}'.format(roomname)})
		ha.call_service(self.Hub.api, 'media_player', 'media_play', {'entity_id': '{}'.format(roomname)})

	def Mute(self, roomname, domute):
		ha.call_service(self.Hub.api, 'media_player', 'volume_mute', {'entity_id': '{}'.format(roomname),
																	  'is_volume_muted': domute})
		if not domute:  # implicitly start playing if unmuting in case source was stopped
			ha.call_service(self.Hub.api, 'media_player', 'media_play', {'entity_id': '{}'.format(roomname)})

	# todo add a Media stop to actually stop rather than mute things media_player/media_stop

	def Source(self, roomname, sourcename):
		ha.call_service(self.Hub.api, 'media_player', 'select_source', {'entity_id': '{}'.format(roomname),
																		'source': '{}'.format(sourcename)})


RegisterDomain('media_player', MediaPlayer)

# todo add a Media stop to actually stop rather than mute things media_player/media_stop
# todo split to media and sonos
