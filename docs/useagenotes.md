# Running Softconsole
* Clone to a directory on the RPi
* Create a directory to hold the config.txt file and logs (defaults to ~pi/Console)
* Create a config.txt file, see the exampleconfig.txt file for help.  The basic structure of the file is a sequence of sections started with \[section name] where the outermost part of the file is implicitly a section.  Subsections which are currently only used to describe keys are started within a section with \[\[subsection]].  Within any section are parameter assignments of the form name = value.  A complete list of current parameters is found in the params.txt file in this directory.  It lists the global parameters with their type and default value if no assignment is supplied.  It also lists for each module the local parameters of that module as well as any global parameters that can be overridden in that module.  Strings may be written without quotes.  
  * One note of importance: labels are lists of strings and should always be notated as "str1","str2".  A label with a single string must be made a list by appending a trailing comma.  Failure to do this will result in the string itself being viewed as a list of single characters which will result in strange output.
* The parameter MainChain provides the names in order of the screens accessible normally.  The parameter SecondaryChain provides a list of screens that are accessible indirectly (see below).  Any number of screens can be defined.
* Whenever a color needs to be specified you can use any color name from the W3C list at http://www.w3.org/TR/SVG11/types.html#ColorKeywords

# Currently supported screens
* Keypad: mimics the KPL.  Can support any number of buttons from 1 to 25 and will autoplace/autosize buttons in this range.  Buttons may be colored as desired.  Key types are:
    * ONOFF: linked to a device or scene and supports On, Off, FastOn, FastOff behaviors
    * ONBLINKRUNTHEN: linked to a program.  Will blink to provide user feedback and will issue RunThen on program
    * Note: for scenes ONOFF will choose a device to use as a proxy for the state of the scene for purposes of the appearance of the button.  Generally this will turn out to be some other switch or KPL button that is a controller for the scene.  This can be overridden by supplying a specific device address or name to use as the proxy.
* Clock: displays a clock formatted according to the OutFormat parameter using any of the underlying OS time formatting codes.  The character size for each line can be set individually.  If there are more lines in the format than character sizes the last size is repeated. Python standard formatting is at https://docs.python.org/2/library/time.html.  Linux (RPi) supports a somewhat richer set of codes e.g. http://linux.die.net/man/3/strftime
* Weather: uses Weather Underground to display current conditions and forecast.  The location parameter is a WU location code - see their site for codes.  To use this screen you must have a WU key which can be gotten for free for low volume use.  
* Thermostat: mimics the front panel of the Insteon thermostat and provides full function equivalency.

# Connecting Console Names with ISY Names
* Some names in the config file are used to link console objects to ISY nodes/scenes.  Specifically the section name of a thermostat sceen is used to connect that screen to an ISY thermostat and the subsection names of ONOFF keys are used to link those keys to an ISY device or scene.
* When a name is looked up in the ISY for linking preference it always given to finding the name as a scene first.  Thus if a device and a scene have the same name the console will link to the scene.
* A current limitation of the console is that names of scenes or devices in the ISY are assumed to be unique.  I.e. names qualified with folder paths are not used.  This limit may be removed in the future.

# Operating Softconsole
* Single tap on an On/Off key to actuate it
* Double tap on a program key to actuate it.  This is done to lessen accidental running of programs from random screen taps.
* Change screens via the command buttons at the bottom of the screen
* Triple tap to access the secondary chain of screens 
* 5-tap to access a maintenance screen
* After the designated time screen will dim
* After the designated time screen will automatically return to the home screen (except from the maintenance screen)
* From the home screen after the dim time out the screen will go to a "sleep" screen if designated - any tap will awaken it
* On the maintenance/log screen single tap to see the next page

# Developers Notes
## Defining New Screens by Coding a Module
New screens can be developed/deployed by subclassing screen.ScreenDesc and placing the code in the screens directory.  A new screen needs to define and __init__ method that takes a section object from the config file and a screen name and uses those to build a new object.  That object must define a HandleScreen method that takes one optional parameter that indicated whether the console driver thinks the screen needs to be painted afresh.  HandleScreen must ultimately call NewWaitPress passing itself.  It may optionally also pass a callback procedure and a callback interval  and a callback count in which case this will be called periodically as specified.  (An example use is that the current clock screen uses this to update the seconds every second even when no touches are happening.)  NewWaitPress will return when a single or double tap has occurred or s command key had been pressed.  Return values are a tuple (reason, info).  Reason may be:

* WAITEXIT in which case the screen object should itself return with the info as its return value
* WAITNORMALBUTTON, WAITNORMALBUTTONFAST: if keys have been defined on the screen info contains the key number that was pressed.
* WAITEXTRACONTROLBUTTON: if the screen specified extra control button(s) info is the index of the one pressed
* WAITISYCHANGE: a notification of a change of state for a device being monitored in the ISY event stream occurred. Info is s tuple  (address, state) of the device.

## Attribute Use and Classes
The file classstruct.txt in docs provides an automatically generated list of Classes, their subclasses, and the attributes defined at each level of the class structure.  This may be a useful aid if a new screen is being written or new types of keys need to be created.

