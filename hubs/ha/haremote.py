"""
Copied/shortened from the homeassisant git when this package was deprecated by them.  It provides a convenient call interface
to getting various info via the req url interface.  Could be cleaned up to just use the url interface if I thought that
were to be stable


Support for an interface to work with a remote instance of Home Assistant.

If a connection error occurs while communicating with the API a
HomeAssistantError will be raised.

For more details about the Python API, please refer to the documentation at
https://home-assistant.io/developers/python_api/
"""
import enum
import json
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from aiohttp.hdrs import METH_GET, METH_POST, CONTENT_TYPE
from types import MappingProxyType
import datetime
import threading
from utils.utilfuncs import safeprint
import logsupport

URL_API = '/api/'
URL_API_CONFIG = '/api/config'
URL_API_STATES = '/api/states'
URL_API_SERVICES = '/api/services'
CONTENT_TYPE_JSON = 'application/json'
HTTP_HEADER_HA_AUTH = 'X-HA-access'
URL_API_STATES_ENTITY = '/api/states/{}'
URL_API_SERVICES_SERVICE = '/api/services/{}/{}'


class HomeAssistantError(Exception):
	pass

def split_entity_id(entity_id: str):
	"""Split a state entity_id into domain, object_id."""
	return entity_id.split(".", 1)


'''
This is a standin for the actual HomeAssistant State class to allow accessing without importing all of the homeassistan
module
'''

class HAState(object):
	"""Object to represent a state within the state machine.

    entity_id: the entity that is represented.
    state: the state of the entity
    attributes: extra information on entity and state
    last_changed: last time the state was changed, not the attributes.
    last_updated: last time this object was updated.
    """

	def __init__(self, entity_id, state, attributes=None, last_changed=None,
                 last_updated=None):
		"""Initialize a new state."""

		self.entity_id = entity_id.lower()
		self.state = state
		self.attributes = MappingProxyType(attributes or {})
		self.last_updated = last_updated
		self.last_changed = last_changed or self.last_updated

	@property
	def domain(self):
		"""Domain of this state."""
		return split_entity_id(self.entity_id)[0]

	@property
	def object_id(self):
		"""Object id of this state."""
		return split_entity_id(self.entity_id)[1]

	@property
	def name(self):
		"""Name of this state."""
		return (
			self.attributes.get('friendly_name') or
			self.object_id.replace('_', ' '))

	def as_dict(self):
		"""Return a dict representation of the State.

		Async friendly.

        To be used for JSON serialization.
        Ensures: state == State.from_dict(state.as_dict())
        """
		return {'entity_id': self.entity_id,
                'state': self.state,
                'attributes': dict(self.attributes),
                'last_changed': self.last_changed,
                'last_updated': self.last_updated}

	@classmethod
	def from_dict(cls, json_dict):
		"""Initialize a state from a dict.

        Async friendly.

        Ensures: state == State.from_json_dict(state.to_json_dict())
        """
		if not (json_dict and 'entity_id' in json_dict and
                'state' in json_dict):
			return None

		last_changed = json_dict.get('last_changed')

		last_updated = json_dict.get('last_updated')

		return cls(json_dict['entity_id'], json_dict['state'],
                   json_dict.get('attributes'), last_changed, last_updated)

	def __eq__(self, other):
		"""Return the comparison of the state."""
		return (self.__class__ == other.__class__ and
				self.entity_id == other.entity_id and
				self.state == other.state and
				self.attributes == other.attributes)

	def __repr__(self):
		"""Return the representation of the states."""

		return "<HAstate {}={} attributes: {} @ {}>".format(
            self.entity_id, self.state, self.attributes,
            self.last_changed)



class APIStatus(enum.Enum):
	"""Representation of an API status."""

	OK = "ok"
	INVALID_PASSWORD = "invalid_password"
	CANNOT_CONNECT = "cannot_connect"
	UNKNOWN = "unknown"

	def __str__(self) -> str:
		"""Return the state."""
		return self.value  # type: ignore


class API:
	"""Object to pass around Home Assistant API location and credentials."""

	def __init__(self, host: str, prefix, api_password: Optional[str] = None,
				 port: Optional[int] = 8123,
				 use_ssl: bool = False) -> None:
		"""Init the API."""
		self.host = host
		self.port = port
		self.api_password = api_password
		self.base_url = prefix + host + ':' + str(port)

		#	self.base_url += ':{}'.format(port)

		self.status = None  # type: Optional[APIStatus]
		self._headers = {CONTENT_TYPE: CONTENT_TYPE_JSON}

		if api_password is not None:
			# self._headers[HTTP_HEADER_HA_AUTH] = api_password
			self._headers['Authorization'] = 'Bearer ' + api_password

		self.MainSession = requests.session()
		self.MainSession.headers = self._headers
		self.AsyncSession = requests.session()
		self.AsyncSession.headers = self._headers

	def validate_api(self, force_validate: bool = False) -> bool:
		"""Test if we can communicate with the API."""
		if self.status is None or force_validate:
			self.status = validate_api(self)

		return self.status == APIStatus.OK

	def __call__(self, method: str, path: str, data: Dict = None,
				 timeout: int = 5) -> requests.Response:
		"""Make a call to the Home Assistant API."""
		if data is None:
			data_str = None
		else:
			data_str = json.dumps(data, cls=JSONEncoder)

		url = urllib.parse.urljoin(self.base_url, path)

		try:
			if method == METH_GET:
				return requests.get(
					url, params=data_str, timeout=timeout,
					headers=self._headers)

			return self.MainSession.request(method, url, data=data_str, timeout=timeout)
		# return requests.request(
		#	method, url, data=data_str, timeout=timeout,
		#	headers=self._headers)

		except requests.exceptions.ConnectionError:
			raise HomeAssistantError("Error connecting to server")

		except requests.exceptions.Timeout:
			error = "Timeout when talking to {}".format(self.host)
			raise HomeAssistantError(error)

	def asyncpost(self, path, data, timeout=10):
		if data is None:
			data_str = None
		else:
			data_str = json.dumps(data, cls=JSONEncoder)

		url = urllib.parse.urljoin(self.base_url, path)
		try:
			return self.AsyncSession.post(url, data=data_str, timeout=timeout)
		except requests.exceptions.ConnectionError:
			raise HomeAssistantError("Error connecting to server")

		except requests.exceptions.Timeout:
			error = "Timeout when talking to {} {} {}".format(self.host, path, data)
			raise HomeAssistantError(error)

	def __repr__(self) -> str:
		"""Return the representation of the API."""
		return "<API({}, password: {})>".format(
			self.base_url, 'yes' if self.api_password is not None else 'no')


class JSONEncoder(json.JSONEncoder):
	"""JSONEncoder that supports Home Assistant objects."""

	# pylint: disable=method-hidden
	def default(self, o: Any) -> Any:
		"""Convert Home Assistant objects.

		Hand other objects to the original method.
		"""
		if isinstance(o, datetime):
			return o.isoformat()
		if isinstance(o, set):
			return list(o)
		if hasattr(o, 'as_dict'):
			return o.as_dict()

		return json.JSONEncoder.default(self, o)


def validate_api(api: API) -> APIStatus:
	"""Make a call to validate API."""
	try:
		req = api(METH_GET, URL_API)

		if req.status_code == 200:
			return APIStatus.OK

		if req.status_code == 401:
			return APIStatus.INVALID_PASSWORD

		return APIStatus.UNKNOWN

	except HomeAssistantError:
		return APIStatus.CANNOT_CONNECT


def get_state(api: API, entity_id: str):
	"""Query given API for state of entity_id."""
	try:
		req = api(METH_GET, URL_API_STATES_ENTITY.format(entity_id))
		#logsupport.DevPrint('JSON: {}'.format((req.json())))
		#logsupport.DevPrint('STAT: {}'.format(HAState.from_dict(req.json())))

		return HAState.from_dict(req.json()) \
			if req.status_code == 200 else None

	except (HomeAssistantError, ValueError):
		# ValueError if req.json() can't parse the json
		logsupport.Logs.Log("Error fetching state", severity=logsupport.ConsoleWarning)

		return None


def get_states(api: API):
	"""Query given API for all states."""
	try:
		req = api(METH_GET,
				  URL_API_STATES)

		return [HAState.from_dict(item) for
				item in req.json()]

	except (HomeAssistantError, ValueError, AttributeError):
		# ValueError if req.json() can't parse the json
		# _LOGGER.exception("Error fetching states")
		logsupport.Logs.Log("Error fetching states in get_states", severity=logsupport.ConsoleWarning)

		return []


def get_services(api: API) -> Dict:
	"""Return a list of dicts.

	Each dict has a string "domain" and a list of strings "services".
	"""
	try:
		req = api(METH_GET, URL_API_SERVICES)

		return req.json() if req.status_code == 200 else {}  # type: ignore

	except (HomeAssistantError, ValueError):
		# ValueError if req.json() can't parse the json
		logsupport.Logs.Log("HA Got unexpected services result")
		return {}

def safe_call_service(api: API, domain: str, service: str,
					  service_data: Dict = None,
					  timeout: int = 5) -> None:
	try:
		call_service(api, domain, service, service_data, timeout)
	except Exception as E:
		safeprint('Exc: {}'.format(E))

def call_service(api: API, domain: str, service: str,
				 service_data: Dict = None,
				 timeout: int = 5) -> None:
	"""Call a service at the remote API."""
	# print('Call svc {} {} {}'.format(domain,service,service_data))
	for tryit in ('first try', 'retry'):
		try:
			req = api(METH_POST,
					  URL_API_SERVICES_SERVICE.format(domain, service),
					  service_data, timeout=timeout)

			if req.status_code != 200:
				logsupport.Logs.Log(
					"HA Error calling service ({}) {} - {} Request: domain: {} service: {} data: {}".format(tryit,
																											req.status_code,
																											req.text,
																											domain,
																											service,
																											service_data))
			else:
				if tryit == 'retry':
					logsupport.Logs.Log('Retry worked ({}.{})'.format(domain, service))
				return

		except HomeAssistantError as e:
			logsupport.Logs.Log("HA service call failed ({}) timeout: {} exc: {}".format(tryit, timeout, repr(e)),
								severity=logsupport.ConsoleWarning if tryit == 'retry' else logsupport.ConsoleInfo)
			if tryit == 'retry':
				raise
			else:
				timeout = 2 * timeout

def async_caller(api, domain, service, service_data, timeout):
	n = threading.current_thread().name
	# print('Async caller {} {} {} {} {} {}'.format(n, repr(api), domain, service, service_data, timeout))
	try:
		req = api.asyncpost(URL_API_SERVICES_SERVICE.format(domain, service),
							service_data, timeout=timeout)

		if req.status_code != 200:
			logsupport.Logs.Log(
				"HA Error calling service {} - {} Request: domain: {} service: {} data: {}".format(req.status_code,
																								   req.text, domain,
																								   service,
																								   service_data))
	# call_service(api, domain, service, service_data, timeout)
	except Exception as E:
		logsupport.Logs.Log(
			'Comm error in async call of {} {} {} Exc: {}'.format(domain, service, service_data, repr(E)))
		safeprint('Async exc: {} {}'.format(n, repr(E)))


def call_service_async(api: API, domain: str, service: str, service_data: Dict = None, timeout: int = 5) -> None:
	t = threading.Thread(name='HA-' + service, target=async_caller, daemon=True,
						 args=(api, domain, service, service_data, timeout))
	t.start()

def get_config(api: API) -> Dict:
	"""Return configuration."""
	req = "*empty*"
	try:
		req = api(METH_GET, URL_API_CONFIG)

		if req.status_code != 200:
			return {}

		result = req.json()
		if 'components' in result:
			result['components'] = set(result['components'])
		return result  # type: ignore

	except ValueError as E:
		# ValueError if req.json() can't parse the JSON
		logsupport.Logs.Log("Got unexpected configuration results from HA:{}".format(repr(E)),
							severity=logsupport.ConsoleWarning, hb=True)
		logsupport.Logs.Log("Result: " + repr(req))
		return {}
	except HomeAssistantError as E:
		# probably lost network to hub
		logsupport.Logs.Log("Got unexpected configuration results from HA:{}".format(repr(E)),
							severity=logsupport.ConsoleDetail)
		return {}
