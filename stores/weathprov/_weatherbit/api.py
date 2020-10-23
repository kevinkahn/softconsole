import requests

class Api(object):
    def __init__(self, key, https=True):
        self.key = key
        self.version = 'v2.0'
        self.forecast_granularity = 'daily'
        self.https = https
        self.api_domain = "api.weatherbit.io"

    def _get_base_url(self):
        if self.https:
            base_url = "https://"
        else:
            base_url = "http://"
        return base_url + self.api_domain + "/" + self.version + "/"

    def _get_forecast_url(self, granularity):
        return self._get_base_url() + "forecast/" + granularity + "?key=" + self.key

    def _get_current_url(self):
        return self._get_base_url() + "current/" + "?key=" + self.key

    def get_forecast_url(self, **kwargs):
        base_url = self._get_forecast_url(kwargs['granularity'])

        # Build root geo-lookup.
        if 'lat' in kwargs and 'lon' in kwargs:
            arg_url_str = "&lat=%(lat)s&lon=%(lon)s"
        elif 'city' in kwargs:
            arg_url_str = "&city=%(city)s"
        elif 'city_id' in kwargs:
            arg_url_str = "&city_id=%(city_id)s"

        # Add on additional parameters.
        if 'state' in kwargs:
            arg_url_str = arg_url_str + "&state=%(state)s"
        if 'country' in kwargs:
            arg_url_str = arg_url_str + "&country=%(country)s"
        if 'days' in kwargs:
            arg_url_str = arg_url_str + "&days=%(days)s"
        if 'units' in kwargs:
            arg_url_str = arg_url_str + "&units=%(units)s"

        return base_url + (arg_url_str % kwargs)


    def get_current_url(self, **kwargs):
        base_url = self._get_current_url()

        # Build root geo-lookup.
        if 'lat' in kwargs and 'lon' in kwargs:
            arg_url_str = "&lat=%(lat)s&lon=%(lon)s"
        elif 'city' in kwargs:
            arg_url_str = "&city=%(city)s"
        elif 'city_id' in kwargs:
            arg_url_str = "&city_id=%(city_id)s"

        # Add on additional parameters.
        if 'state' in kwargs:
            arg_url_str = arg_url_str + "&state=%(state)s"
        if 'country' in kwargs:
            arg_url_str = arg_url_str + "&country=%(country)s"
        if 'units' in kwargs:
            arg_url_str = arg_url_str + "&units=%(units)s"

        return base_url + (arg_url_str % kwargs)



    def get_forecast(self, **kwargs):

        if kwargs is None:
            raise Exception('Arguments Required.')

        kwargs['granularity'] = self.forecast_granularity
        url = self.get_forecast_url(**kwargs)
        weatherbitio_reponse = requests.get(url)
        weatherbitio_reponse.raise_for_status()
        json = weatherbitio_reponse.json()
        headers = weatherbitio_reponse.headers
        return json

    def get_current(self, **kwargs):
        
        if kwargs is None:
            raise Exception('Arguments Required.')

        url = self.get_current_url(**kwargs)
        weatherbitio_reponse = requests.get(url)
        weatherbitio_reponse.raise_for_status()
        json = weatherbitio_reponse.json()
        headers = weatherbitio_reponse.headers
        return json
