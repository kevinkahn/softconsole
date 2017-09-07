# Class/Attribute Structure):


#object: [ISY, TouchPoint, OnOffItem, ScreenDesc]
The most base type

##ISY: []

	Singleton object (1 per console) that represents the ISY system as a whole and provides roots to its structures
	and useful directories to its nodes/programs.  Provides a debug method to dump the constructed graph.
	Note current limitation: assumes non-conflicting names at the leaves.  Qualified name support is a future addition.
	
*  FoldersByAddr
*  FoldersByName
*  LinkChildrenParents
*  NodeRoot
*  NodesByAddr
*  NodesByName
*  PrintTree
*  ProgRoot
*  ProgramFoldersByAddr
*  ProgramFoldersByName
*  ProgramsByAddr
*  ProgramsByName
*  ScenesByAddr
*  ScenesByName
*  varsInt
*  varsIntInv
*  varsState
*  varsStateInv

##TouchPoint: [ManualKeyDesc]

	Represents a touchable rectangle on the screen.
	
*  AddTitle
*  BlinkKey
*  ButtonFontSizes
*  Center
*  FeedbackKey
*  FindFontSize
*  FinishKey
*  PaintKey
*  Proc
*  Screen
*  Size
*  docodeinit
*  dosectioninit
*  touched

##ManualKeyDesc: [OnOffKey]

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

##OnOffKey: []

***missing***

*  MonitorObj
*  NodeName
*  OnKey
*  OnOff
*  SceneProxy

##OnOffItem: [TreeItem]

	Provides command handling for nodes that can be sent on/off faston/fastoff commands.
	

##TreeItem: [Folder, Scene, ProgramFolder]

	Provides the graph structure for the ISY representation.  Any ISY node can have a parent and children managed by
	this class.  The class also holds identity information, namely name and addr
	
*  address
*  children
*  name
*  parent
*  runThen

##Folder: [Node]

	Represents and ISY node/scene folder.
	
*  SendCommand
*  flag
*  parenttype

##Node: []

	Represents and ISY device node.
	
*  devState
*  enabled
*  hasstatus
*  pnode

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
	

##ScreenDesc: [BaseKeyScreenDesc, ClockScreenDesc]

	Basic information about a screen, subclassed by all other screens to handle this information
	
*  BackgroundColor
*  BrightLevel
*  CharColor
*  CmdCharCol
*  CmdKeyCol
*  DimLevel
*  DimTO
*  EnterScreen
*  ExitScreen
*  ISYEvent
*  InitDisplay
*  Keys
*  LayoutKeys
*  NavKeys
*  NodeWatch
*  PaintBase
*  PaintKeys
*  PersistTO
*  ReInitDisplay
*  ShowScreen
*  Subscreens
*  WithNav
*  label

##BaseKeyScreenDesc: [ThermostatScreenDesc, MaintScreenDesc, LogDisplayScreen, KeyScreenDesc]

***missing***

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

*  SubFontSize
*  TitleFontSize

##LogDisplayScreen: []

***missing***

*  NextPage

##KeyScreenDesc: []

***missing***

*  subscriptionlist

##ClockScreenDesc: []

***missing***

