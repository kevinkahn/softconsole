# Class/Attribute Structure:


#object: [ScreenDesc, TouchPoint, ISY, ISYNode]
The most base type

##ScreenDesc: [TimeTempScreenDesc, WeatherScreenDesc, BaseKeyScreenDesc, ClockScreenDesc, AlertsScreenDesc]

	Basic information about a screen, subclassed by all other screens to handle this information
	
*  AddToHubInterestList
*  BackgroundColor
*  CharColor
*  CmdCharCol
*  CmdKeyCol
*  DefaultHub
*  DimTO
*  ExitScreen
*  HubInterestList
*  InitDisplay
*  Keys
*  KeysPerColumn
*  KeysPerRow
*  LayoutKeys
*  NavKeys
*  NodeEvent
*  PaintBase
*  PaintKeys
*  PersistTO
*  ReInitDisplay
*  ShowScreen
*  SubFontSize
*  TitleFontSize
*  WithNav
*  label

##TimeTempScreenDesc: []

***missing***


##WeatherScreenDesc: []

***missing***

*  CondOrFcst
*  WunderKey
*  condfields
*  condformat
*  currentconditions
*  dayfields
*  dayformat
*  fcstfields
*  fcstformat
*  fmt
*  footfields
*  footformat
*  location
*  scrlabel
*  store

##BaseKeyScreenDesc: [MaintScreenDesc, LogDisplayScreen, VerifyScreen, KeyScreenDesc, ThermostatScreenDesc]

***missing***

*  buttonspercol
*  buttonsperrow

##MaintScreenDesc: []

***missing***


##LogDisplayScreen: []

***missing***

*  NextPage
*  PageStartItem
*  PrevPage
*  item
*  pageno

##VerifyScreen: []

***missing***

*  CallingScreen
*  Invoke

##KeyScreenDesc: []

***missing***


##ThermostatScreenDesc: []

***missing***

*  AdjButSurf
*  AdjButTops
*  BumpMode
*  BumpTemp
*  ISYObj
*  ModeButPos
*  ModesPos
*  SPPos
*  StatePos
*  TempPos
*  TitlePos
*  TitleRen
*  fsize
*  info
*  isy
*  oldinfo

##ClockScreenDesc: []

***missing***


##AlertsScreenDesc: []

***missing***


##TouchPoint: [ManualKeyDesc]

	Represents a touchable rectangle on the screen.
	
*  AddTitle
*  Blink
*  BlinkKey
*  BuildKey
*  ButtonFontSizes
*  Center
*  ControlObj
*  FastPress
*  FindFontSize
*  FinishKey
*  GoMsg
*  KeyCharColorOff
*  KeyCharColorOn
*  KeyColor
*  KeyColorOff
*  KeyColorOn
*  KeyOffImage
*  KeyOffImageBase
*  KeyOffOutlineColor
*  KeyOnImage
*  KeyOnImageBase
*  KeyOnOutlineColor
*  KeyOutlineOffset
*  NoGoMsg
*  PaintKey
*  Proc
*  ScheduleBlinkKey
*  Screen
*  SetKeyImages
*  Size
*  State
*  Verify
*  docodeinit
*  dosectioninit
*  touched

##ManualKeyDesc: [VarKey, RunProgram, OnOffKey, SetVarKey]

	Defines a drawn touchable rectangle on the screen that represents a key (button).  May be called with one of 2
	signatures.  It can be called manually by code to create a key by supplying all the attributes of the key in the
	code explicitly.  It can also be called with a config objects section in which case it will build the key from the
	combination of the defaults for the attributes and the explicit overides found in the config.txt file section
	that is passed in.
	
*  KeyLabelOff
*  KeyLabelOn

##VarKey: []

***missing***


##RunProgram: []

***missing***


##OnOffKey: []

***missing***

*  DisplayObj
*  KeyAction
*  NodeName
*  OnOffKeyPressed
*  SceneProxy
*  VerifyPressAndReturn
*  lastpresstype

##SetVarKey: []

***missing***

*  SetVarKeyPressed
*  Value
*  Var
*  VarName
*  VarType

##ISY: []

	Representation of an ISY system as a whole and provides roots to its structures
	and useful directories to its nodes/programs.  Provides a debug method to dump the constructed graph.
	Note current limitation: assumes non-conflicting names at the leaves.  Qualified name support is a future addition.
	
*  GetCurrentStatus
*  GetNode
*  GetProgram
*  ISYprefix
*  ISYrequestsession
*  NodesByAddr
*  PrintTree
*  SetAlertWatch
*  StatesDump
*  addr
*  alertspeclist
*  password
*  try_ISY_comm
*  user

##ISYNode: [OnOffItem]

***missing***


##OnOffItem: [TreeItem]

	Provides command handling for nodes that can be sent on/off faston/fastoff commands.
	

##TreeItem: [Scene, ProgramFolder, Folder]

	Provides the graph structure for the ISY representation.  Any ISY node can have a parent and children managed by
	this class.  The class also holds identity information, namely name and addr
	
*  Hub
*  RunProgram
*  address
*  children
*  fullname
*  name
*  parent

##Scene: []

	Represents an ISY scene.
	
*  members
*  obj
*  proxy

##ProgramFolder: [Program]

	Represents an ISY program folder (ISY keeps the node and program folders separately)
	
*  status

##Program: []

	Represents an ISY program and provides command support to issue run commands to it.
	

##Folder: [Node]

	Represents and ISY node/scene folder.
	
*  SendOnOffCommand
*  flag
*  parenttype

##Node: []

	Represents and ISY device node.
	
*  devState
*  enabled
*  hasstatus
*  pnode
