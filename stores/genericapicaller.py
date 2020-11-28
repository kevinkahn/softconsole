"""
# creation info apikey, baseurl, urlparams (how to structure), frequency of refresh (allow on demand?)
# perhaps a formatting string of some sort?
//a.com/xyz?key={},lat={}
where in the {} go other store items? or items from config file so like for weather where I have city= then that would sub into
{city}

maybe simpler to have a loadable json getter that takes a set of keyword parameter, calls an api, parses the json and returns a dict
would need two types of params - ones that are common across instances and ones that are specific to the store
e.g., for weather api is common, location is specific

in auth:
[Weatherbit]
type = jsonfetcher
apikey = xyz
module = this would need to be either relative to stores/jsonfetchers or absolute to get user provided

this would cause an import module
call to setup which would populate a jsongetter dict, or register a storetype?  would need to be able to instantiate
equivalent of weather locations

register jsonproviders by name,
type = one of these names then create a store for it

[AlphaVantage]
type=jsonprovider
apikey=xxx

[stockpricegp1]
type = AlphaVantage
symbols = MSFT,GOOG
refreshtiming = ondemand, 40 minutes, start,end times ???

proc make store from json:
  load a json and populate a store from it

in the watching thread need to do a PostEvent(ConsoleEvent(CEvent.SchedEvent, **self.kwargs)) with the proc = alert.Invoke
when the file changes, otherwise the watching thread just processes the var changes and goes back to watching


Add a general blank screen
"""
