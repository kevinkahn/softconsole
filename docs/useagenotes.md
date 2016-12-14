# Installation
* The system has currently been tested on Raspberry Pi Zero, 2, and 3 using an Adafruit 3.5" resistive PiTFT and Adafruit 2.8" capacitive PiTFT.  To set up a system load the current best version of the Jessie release of Raspbian.  Then use one of these options to install things:
    * Easiest: before booting the Pi add the file earlyprep.sh to the /boot partition on whatever system you built the SD card on.  Then after booting run as root "bash /boot/earlyprep.sh" which will prompt you to configure WiFi if needed, expand the file system, and set the WiFi country.  Reboot when the script exits and after the reboot run the piprep script as root (bash ./piprep.sh).  This script takes no parameters but asks a series of questions to decide on the configuration details.    After the prep script completes it may leave a TODO file in the pi home directory of additional configuration things that are needed.
    * Expert alternative: Configure its networking and expand its file system.  Manually examine the consoleprep.sh script to perform the specific configurations and installations that make sense for your system.
    
* The resultant system should have a consolestable and consolebeta directories populated and a Console directory created.  The config.txt goes in the Console directory.  Run the console as "sudo python -u console.py" from within the consolestable directory.  I also arrange to run the console automatically at boot.  An example of this is in the rc.local file in the scripts directory. My script will run the stable version unless a "usebeta" file and a "cleanexit" file exist in the home directory.  From the maintenance screen in console you can ask to set the beta version and download the current beta.  If you set the beta version and you shutdown the console cleanly the beta will run else it will fall back to the stable version.
* Current release notes:
    * The latest release moved to using the Pi hardware PWM to control screen brightness which gets rid of periodic brightness glitches.  This requires installing wiringpi and python-dev modules.  Consoleprep now does this but if you have an existing installation you can manually issue the commands (see the consoleprep script for them).  If for some reason you don't wish to use hw PWM the hwa.py has the soft PWM version and can be renamed to hw.py to use it rather than the hw.py that is there by default.
    * Version 2 code made a major overhaul the the fundamental program sequencing structure to allow for alert procedures and alert screens.  Alert procedures are procedures that can be called based on time, the value of an ISY var, or the state of an ISY device.  Alert screens are screens that can be defined to take over control of the display based on the value of an ISY var or an ISY node value, possibly delayed in time by some period.  Alert screens can be deferred by a keytouch or can execute some action that will resolve the alert.  If the alert condition is otherwise cleared within the ISY, the screen will also go away.
    * Note that all the source code for the console is available on github under kevinkahn/softconsole and you are free to examine and/or modify as you like.

# Setting up and Running Softconsole
* Create a config.txt file, see the exampleconfig.txt file for help.  The basic structure of the file is a sequence of sections started with \[section name] where the outermost part of the file is implicitly a section.  Subsections which are currently only used to describe keys are started within a section with \[\[subsection]].  Within any section are parameter assignments of the form name = value.  A complete list of current parameters is found in the params.txt file in this directory.  It lists the global parameters with their type and default value if no assignment is supplied.  It also lists for each module the local parameters of that module as well as any global parameters that can be overridden in that module.  Strings may be written without quotes.  
  * One note of importance: labels are lists of strings and should always be notated as "str1","str2".  A label with a single string must be made a list by appending a trailing comma.  Failure to do this will result in the string itself being viewed as a list of single characters which will result in strange output.
* The parameter MainChain provides the names in order of the screens accessible normally.  The parameter SecondaryChain provides a list of screens that are accessible indirectly (see below).  Any number of screens can be defined.
* Whenever a color needs to be specified you can use any color name from the W3C list at http://www.w3.org/TR/SVG11/types.html#ColorKeywords
* The config.txt file supports an "include = filename" parameter to allow breaking it up conveniently.  This cam be useful if multiple consoles use some of the same screens and you want to have only one version of the description for those shared screens.  It also supports a "cfglib = dirname" as a default place to look for included config files.  Personally I have lots of small config files that I keep in a directory and specialize a single top level config file for each of my consoles.  See the directory "example configs" on github for lots of examples.
* Some responses from weatherunderground are fairly long phrases that don't display nicely on the weather screens.  There is a file termshorten list which is a json representation of a Python dictionary that maps phrases to shorter ones for display.  It is self explanatory if you look at the examples that are prepopulated.  You can edit this as you wish to add or change phrases to be shortened.

# Currently supported screens
* Keypad: mimics the KPL.  Can support any number of buttons from 1 to 25 and will autoplace/autosize buttons in this range.  Buttons may be colored as desired.  Key types are:
    * ONOFF: linked to a device or scene and supports On, Off, FastOn, FastOff behaviors
    * ONBLINKRUNTHEN: linked to a program.  Will blink to provide user feedback and will issue RunThen on program
    * ON: will always send an "on" command to the linked device.  This is useful for things like garage doors that use on toggles.
    * SETVAR: set the value of an ISY variable
    * Note: for scenes ONOFF will choose a device to use as a proxy for the state of the scene for purposes of the appearance of the button.  Generally this will turn out to be some other switch or KPL button that is a controller for the scene.  This can be overridden by supplying a specific device address or name to use as the proxy.
* Clock: displays a clock formatted according to the OutFormat parameter using any of the underlying OS time formatting codes.  The character size for each line can be set individually.  If there are more lines in the format than character sizes the last size is repeated. Python standard formatting is at https://docs.python.org/2/library/time.html.  Linux (RPi) supports a somewhat richer set of codes e.g. http://linux.die.net/man/3/strftime
* Weather: uses Weather Underground to display current conditions and forecast.  The location parameter is a WU location code - see their site for codes.  To use this screen you must have a WU key which can be gotten for free for low volume use.  
* Thermostat: mimics the front panel of the Insteon thermostat and provides full function equivalency.
* Time/Temp: combined screen, nice as a sleep screen that gives current time and the weather at a single location.  Format of the screen is largely controlled by the config.txt file.
* Alert: these are screens that are triggered to appear based on a node or variable state, perhaps with a delay from the time of the state change.  E.g., display alert screen 5 minutes after garage door is opened if it is still open.  They provide a single button that can be linked to resolve the alert condition.  They are triggered by an test in the alert section of the config file. Alert screen can be deferred for a predefined time after which they will reappear. If the condition causing the alert clears they will disappear.

# Alerts
Alerts are defined in an "\[Alerts\]" section of the config files.  See cfglib/pdxalerts for some examples.  Currently alerts can be triggered periodically, based on a node state chance, or based on a variable state change.  The effect of the alert can be delayed by some time to avoid alerts for routine events that should clear within some typical window.  Alerts can either invoke an alert screen (see the away and garage alerts in the sample file) or an alert procedure (see the update alert).  

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
    * The original version had only a single idle screen named by the DimHomeScreenCoverName parameter.  This parameter is deprecated but will still work if you don't opt for the new multi-idle screen ability.  You can designate a sequence of idle screens with DimIdleListNames and corresponding linger times per screen with DimIdleListTimes.  Once the console is idle it will cycle through these screens until tapped.  This got added to make a wall unit a nicer info display when not otherwise being used.
* On the maintenance/log screen single tap to see the next page

# Developers Notes
## Defining New Screens by Coding a Module (updated for version 2)
New screens can be developed/deployed by subclassing screen.ScreenDesc and placing the code in the screens directory.  Screens modules have a single line of code at the module level of the form "config.screentypes[*name*] = *classname*" where *name* is the string to be used in config files to as the type value to create instances and *classname* is the name of the class defined in the module.  A screen class defines the following methods (ScreenDesc provide base level implementations that should be called if overridden):

* __init__: Create a screen object based on an entry in the config file with a type equal to the type string registered in the definition of the screen.
* EnterScreen: code to be performed just before the screen is gets displayed.  Most typically sets any ISY nodes to be watched while the screen is up.
* InitDisplay(nav): code to display the screen.  nav are the navigation keys or None and should be passed through the the underlying InitDisplay of ScreenDesc
* ReInitDisplay: code to redisplay the screen if it has been removed temporarily and assumes nav keys are already set.  Generally not overridden.
* ISYEvent(node,value): A watched ISY *node* has changed to the new *value*
* ExitScreen: code that is called as the screen is being taken off the display

## Defining New Alert Procs
Alert procs are defined as methods in classes stored in the alerts directory.  They have a single module level line of code of the form "config.alertprocs["*classname*"] = *classname*" where *classname* is the name of the class defined in the module.  The class will be instantiated once at console start time.  It may define one or more methods that will be called based on the definition of Alerts in the config file that the console reads.

## Attribute Use and Classes
The file classstruct.txt in docs provides an automatically generated list of Classes, their subclasses, and the attributes defined at each level of the class structure.  This may be a useful aid if a new screen is being written or new types of keys need to be created.

