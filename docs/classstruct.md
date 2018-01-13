# Class/Attribute Structure:


#object: [TouchPoint, TreeItem, ScreenDesc]
The most base type

##TouchPoint: [ManualKeyDesc]

	Represents a touchable rectangle on the screen.
	
*  AddTitle
*  BlinkKey
*  ButtonFontSizes
*  Center
*  FindFontSize
*  FinishKey
*  PaintKey
*  Proc
*  Screen
*  SetKeyImages
*  Size
*  docodeinit
*  dosectioninit
*  proc
*  touched

##ManualKeyDesc: [SetVarKey, RunProgram, SetVarValueKey, OnOffKey]

	Defines a drawn touchable rectangle on the screen that represents a key (button).  May be called with one of 2
	signatures.  It can be called manually by code to create a key by supplying all the attributes of the key in the
	code explicitly.  It can also be called with a config objects section in which case it will build the key from the
	combination of the defaults for the attributes and the explicit overides found in the config.txt file section
	that is passed in.
	
*  ISYObj
*  KeyCharColorOff
*  KeyCharColorOn
*  KeyColor
*  KeyColorOff
*  KeyColorOn
*  KeyLabelOff
*  KeyLabelOn
*  KeyOffOutlineColor
*  KeyOnOutlineColor
*  KeyOutlineOffset
*  State

##SetVarKey: []

***missing***

*  Blink
*  FastPress
*  SetVar
*  Value
*  Var
*  VarID
*  VarType
*  Verify

##RunProgram: []

***missing***


##SetVarValueKey: []

***missing***

*  SetVarValue

##OnOffKey: []

***missing***

*  KeyAction
*  MonitorObj
*  NodeName
*  OnOffKeyPressed
*  SceneProxy
*  VerifyPressAndReturn

##TreeItem: [Folder]

	Provides the graph structure for the ISY representation.  Any ISY node can have a parent and children managed by
	this class.  The class also holds identity information, namely name and addr
	
*  address
*  children
*  name
*  parent

##Folder: []

	Represents and ISY node/scene folder.
	
*  flag
*  parenttype

##ScreenDesc: [HouseStatusScreenDesc, TimeTempScreenDesc, BaseKeyScreenDesc, WeatherScreenDesc, AlertsScreenDesc, ClockScreenDesc]

	Basic information about a screen, subclassed by all other screens to handle this information
	
*  BackgroundColor
*  BrightLevel
*  CharColor
*  CmdCharCol
*  CmdKeyCol
*  DimLevel
*  DimTO
*  ExitScreen
*  ISYEvent
*  InitDisplay
*  Keys
*  LayoutKeys
*  NavKeys
*  NodeList
*  PaintBase
*  PaintKeys
*  PersistTO
*  ReInitDisplay
*  ShowScreen
*  Subscreens
*  VarsList
*  WithNav
*  label

##HouseStatusScreenDesc: []

***missing***

*  HandleScreen
*  NormalOff
*  NormalOn
*  SetUp

##TimeTempScreenDesc: []

***missing***


##BaseKeyScreenDesc: [ThermostatScreenDesc, MaintScreenDesc, VerifyScreen, LogDisplayScreen, KeyScreenDesc]

***missing***

*  KeysPerColumn
*  KeysPerRow
*  buttonspercol
*  buttonsperrow

##ThermostatScreenDesc: []

***missing***

*  AdjButSurf
*  AdjButTops
*  BumpMode
*  BumpTemp
*  ModeButPos
*  ModesPos
*  SPPos
*  StatePos
*  TempPos
*  TitlePos
*  TitleRen
*  fsize
*  info

##MaintScreenDesc: []

***missing***


##VerifyScreen: []

***missing***

*  CallingScreen
*  Invoke
*  SubFontSize
*  TitleFontSize

##LogDisplayScreen: []

***missing***

*  NextPage
*  PrevPage

##KeyScreenDesc: []

***missing***


##WeatherScreenDesc: []

***missing***

*  CondOrFcst
*  Info
*  RenderScreenLines
*  WunderKey
*  conditions
*  currentconditions
*  errormsg
*  fmt
*  forecast
*  location
*  scrlabel

##AlertsScreenDesc: []

***missing***


##ClockScreenDesc: []

***missing***

