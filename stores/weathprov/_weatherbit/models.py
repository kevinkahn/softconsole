from .utils import UnicodeMixin, LocalizeDateTime, _get_date_from_timestamp
import datetime

class TimeSeries(UnicodeMixin):
    def __init__(self, data, response, headers):
        self.response = response
        self.http_headers = headers
        self.json = data
        self.points = []
        self._load(self.json)


    def _load(self, response):
        self.city_name = response['city_name']
        self.lat = response['lat']
        self.lon = response['lon']
        self.country_code = response['country_code']
        self.state_code = response['state_code']
        self._load_from_points(response['data'])

    def _load_from_points(self, points):
        for point in points:
            self.points.append(Point(point))
        # Sort by datetime.
        self.points.sort(key=lambda p: p.datetime)

    def get_series(self, api_vars):
        """""
        Accepts either a list of variables, or a string (single var)
        Returns a list (sorted by datetime) of objects with the variables
        requested, and their corresponding dates.
        """""
        series = []

        if type(api_vars) == str:
            api_vars = [api_vars]

        for p in self.points:
            series_point = {}
            for var in api_vars:
                try:
                    series_point[var] = getattr(p, var)
                except AttributeError as e:
                    raise e
            series_point['datetime'] = p.datetime
            series.append(series_point)

        # Sort by datetime.
        series.sort(key=lambda p: p['datetime'])
        return series

class SingleTime(UnicodeMixin):
    def __init__(self, data, response, headers):
        self.response = response
        self.http_headers = headers
        self.json = data
        self.points = []
        self._load(self.json)

            
    def _load(self, response):
        self.count = int(response['count'])
        self._load_from_points(response['data'])

    def _load_from_points(self, points):
        for point in points:
            self.points.append(SingleTimePoint(point))
        # Sort by datetime.
        self.points.sort(key=lambda p: p.datetime)


class Point(UnicodeMixin):
    def __init__(self, point):
        self.pres = point.get('pres')
        self.slp = point.get('slp')
        self.weather = point.get('weather')
        self.rh = point.get('rh')
        self.dewpt = point.get('dewpt')
        self.temp = point.get('temp')
        self.app_temp = point.get('app_temp')
        self.max_temp = point.get('max_temp')
        self.min_temp = point.get('min_temp')
        self.precip = point.get('precip')
        self.snow = point.get('snow')
        self.snow_depth = point.get('snow_depth')
        self.ghi = point.get('ghi')
        self.dni = point.get('dni')
        self.dhi = point.get('dhi')
        self.pod = point.get('pod')
        self.uv  = point.get('uv')
        self.max_uv = point.get('max_uv')
        self.precip_gpm = point.get('precip_gpm')
        self.wind_gust_spd = point.get('wind_gust_spd')
        self.max_wind_ts = point.get('max_wind_ts')
        self.wind_spd = point.get('wind_spd')
        self.wind_dir = point.get('wind_dir')
        self.max_wind_spd = point.get('max_wind_spd')
        self.max_wind_dir = point.get('max_wind_dir')
        self.datetime = _get_date_from_timestamp(point.get('datetime'))
        self.clouds = point.get('clouds')
        self.ts = point.get('ts')
        self.valid_date = point.get('valid_date')


class SingleTimePoint(UnicodeMixin):
    def __init__(self, point):
        self.city_name = point.get('city_name')
        self.lat = point.get('lat')
        self.lon = point.get('lon')
        self.country_code = point.get('country_code')
        self.state_code = point.get('state_code')

        self.snow = point.get('snow')
        self.wind_dir = point.get('wind_dir')
        self.weather = point.get('weather')
        self.wind_spd = point.get('wind_spd')
        self.rh = point.get('rh')
        self.slp = point.get('slp')
        self.temp = point.get('temp')
        self.app_temp = point.get('app_temp')
        self.precip = point.get('precip')
        self.visibility = point.get('visibility')
        self.station = point.get('station')
        self.datetime = _get_date_from_timestamp(point.get('ob_time'))
        self._sunrise = _get_date_from_timestamp(point.get('sunrise'), True)
        self._sunset = _get_date_from_timestamp(point.get('sunset'), True)
        now = datetime.datetime.now()
        self.sunrise =  LocalizeDateTime(self._sunrise)
        self.sunset = LocalizeDateTime(self._sunset)
        self.ghi = point.get('ghi')
        self.dni = point.get('dni')
        self.dhi = point.get('dhi')
        self.clouds = point.get('clouds')


class Forecast(TimeSeries):
    """""
    The Forecast API Response class, extends TimeSeries.
    """""
    pass

class History(TimeSeries):
    """""
    The History API Response class, extends TimeSeries.
    """""
    pass

class Current(SingleTime):
    """""
    The Current API Response class, extends SingleTime.
    """""
    pass