# Installation
* The system has currently been tested on Raspberry Pi Zero, 2, and 3 using an Adafruit 3.5" resistive PiTFT and Adafruit 2.8" capacitive PiTFT.  To set up a system load the current best version of the Jessie release of Raspbian.  Then use one of these options to install things:
    * Easiest: before booting the Pi add the file earlyprep.sh to the /boot partition on whatever system you built the SD card on.  Then after booting run as root "bash /boot/earlyprep.sh" which will prompt you to configure WiFi if needed, expand the file system, and set the WiFi country.  Reboot when the script exits and after the reboot run the piprep script as root (bash ./piprep.sh).  This script takes no parameters but asks a series of questions to decide on the configuration details.    After the prep script completes it may leave a TODO file in the pi home directory of additional configuration things that are needed.
    * Reasonable alternative: Configure its networking and expand its file system.  Then download the script consoleprep.sh or consoleprep2.sh (wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/consoleprep[2].sh) and give it execution rights (chnmod +x consoleprep.sh).  Reboot to actually get the expanded file system and run the script as root specifying the type of display to be used (35r, 28r, 28c) (e.g., sudo consoleprep.sh -t 35r).  The script asks various questions to set timezone, provide a password for the tightvncserver installed as a convenience for headless operation, etc.  It may ask for permission to use more file space at various points - answer y to these.  I answer n to the use of the display as console.  After the script completes reboot.  The difference between the 2 versions of the script is that the original one uses the Adafruit install scripts to add the drivers and other stuff needed for the PiTFT.  As of the switch in Raspbian (Debian) to use device tree stuff which happened in March 16 the Adafruit scripts stopped working.  The "2" version of the script uses a different set of install programs that works with the more recent versions.  So you can either use the March 16 version of Raspbian and the original script or (recommended) use the most current version of Raspbian and the "2" script.  I think the new version of the script is also a bit cleaner and asks fewer questions.
    
* The resultant system should have a consolestable and consolebeta directories populated and a Console directory created.  The config.txt goes in the Console directory.  Run the console as "sudo python -u console.py" from within the consolestable directory.  I also arrange to run the console automatically at boot.  An example of this is in the rc.local file in the scripts directory (which also shows running the echo emulator).  My script will run the stable version unless a "usebeta" file and a "cleanexit" file exist in the home directory.  From the maintenance screen in console you can ask to set the beta version and download the current beta.  If you set the beta version and you shutdown the console cleanly the beta will run else it will fall back to the stable version.
* Current release notes:
    * This has been tested at this point with the 3.5 resistive PiTFT on a Pi2 and Pi3 and with a 2.8 capacitive PiTFT on a Pi Zero.  It should work with other combinations since this is a pretty broad sample but YMMV.
    * The latest release moved to using the Pi hardware PWM to control screen brightness which gets rid of periodic brightness glitches.  This requires installing wiringpi and python-dev modules.  Consoleprep now does this but if you have an existing installation you can manually issue the commands (see the consoleprep script for them).  If for some reason you don't wish to use hw PWM the hwa.py has the soft PWM version and can be renamed to hw.py to use it rather than the hw.py that is there by default.

# Manually Installing Softconsole
* Insure all necessary libraries for python needed by the console are installed
    * One way to do this is to just install the console and try running it and when it crashes see why and load the library.  Better is probably to look at the current version of the prep script noted above which should load all the needed stuff.
* Fetch setupconsole.py from github/kevinkahn/softconsole and run it

# Setting up and Running Softconsole
* Create a config.txt file, see the exampleconfig.txt file for help.  The basic structure of the file is a sequence of sections started with \[section name] where the outermost part of the file is implicitly a section.  Subsections which are currently only used to describe keys are started within a section with \[\[subsection]].  Within any section are parameter assignments of the form name = value.  A complete list of current parameters is found in the params.txt file in this directory.  It lists the global parameters with their type and default value if no assignment is supplied.  It also lists for each module the local parameters of that module as well as any global parameters that can be overridden in that module.  Strings may be written without quotes.  
  * One note of importance: labels are lists of strings and should always be notated as "str1","str2".  A label with a single string must be made a list by appending a trailing comma.  Failure to do this will result in the string itself being viewed as a list of single characters which will result in strange output.
* The parameter MainChain provides the names in order of the screens accessible normally.  The parameter SecondaryChain provides a list of screens that are accessible indirectly (see below).  Any number of screens can be defined.
* Whenever a color needs to be specified you can use any color name from the W3C list at http://www.w3.org/TR/SVG11/types.html#ColorKeywords
* The config.txt file supports an "include = filename" parameter to allow breaking it up conveniently.  This cam be useful if multiple consoles use some of the same screens and you want to have only one version of the description for those shared screens.
* Some responses from weatherunderground are fairly long phrases that don't display nicely on the weather screens.  There is a file termshorten list which is a json representation of a Python dictionary that maps phrases to shorter ones for display.  It is self explanatory if you look at the examples that are prepopulated.  You can edit this as you wish to add or change phrases to be shortened.

# Currently supported screens
* Keypad: mimics the KPL.  Can support any number of buttons from 1 to 25 and will autoplace/autosize buttons in this range.  Buttons may be colored as desired.  Key types are:
    * ONOFF: linked to a device or scene and supports On, Off, FastOn, FastOff behaviors
    * ONBLINKRUNTHEN: linked to a program.  Will blink to provide user feedback and will issue RunThen on program
    * Note: for scenes ONOFF will choose a device to use as a proxy for the state of the scene for purposes of the appearance of the button.  Generally this will turn out to be some other switch or KPL button that is a controller for the scene.  This can be overridden by supplying a specific device address or name to use as the proxy.
* Clock: displays a clock formatted according to the OutFormat parameter using any of the underlying OS time formatting codes.  The character size for each line can be set individually.  If there are more lines in the format than character sizes the last size is repeated. Python standard formatting is at https://docs.python.org/2/library/time.html.  Linux (RPi) supports a somewhat richer set of codes e.g. http://linux.die.net/man/3/strftime
* Weather: uses Weather Underground to display current conditions and forecast.  The location parameter is a WU location code - see their site for codes.  To use this screen you must have a WU key which can be gotten for free for low volume use.  
* Thermostat: mimics the front panel of the Insteon thermostat and provides full function equivalency.
* Time/Temp: combined screen, nice as a sleep screen that gives current time and the weather at a single location.  Format of the screen is largely controlled by the config.txt file.

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
## Defining New Screens by Coding a Module
New screens can be developed/deployed by subclassing screen.ScreenDesc and placing the code in the screens directory.  A new screen needs to define and __init__ method that takes a section object from the config file and a screen name and uses those to build a new object.  That object must define a HandleScreen method that takes one optional parameter that indicated whether the console driver thinks the screen needs to be painted afresh.  HandleScreen must ultimately call NewWaitPress passing itself.  It may optionally also pass a callback procedure and a callback interval  and a callback count in which case this will be called periodically as specified.  (An example use is that the current clock screen uses this to update the seconds every second even when no touches are happening.)  NewWaitPress will return when a single or double tap has occurred or s command key had been pressed.  Return values are a tuple (reason, info).  Reason may be:

* WAITEXIT in which case the screen object should itself return with the info as its return value
* WAITNORMALBUTTON, WAITNORMALBUTTONFAST: if keys have been defined on the screen info contains the key number that was pressed.
* WAITEXTRACONTROLBUTTON: if the screen specified extra control button(s) info is the index of the one pressed
* WAITISYCHANGE: a notification of a change of state for a device being monitored in the ISY event stream occurred. Info is s tuple  (address, state) of the device.

## Attribute Use and Classes
The file classstruct.txt in docs provides an automatically generated list of Classes, their subclasses, and the attributes defined at each level of the class structure.  This may be a useful aid if a new screen is being written or new types of keys need to be created.

