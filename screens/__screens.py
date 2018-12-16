HomeScreen = None
HomeScreen2 = None
DimIdleList = []
DimIdleTimes = []
MainDict = {}  # map: name:screen
SecondaryDict = {}
ExtraDict = {}  # todo both extras could be local to configobjects
ExtraChain = []

screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module
