# Installation
* The system has currently been tested on Raspberry Pi Zero, Pi Zero W, 2, and 3 using an Adafruit 3.5" resistive PiTFT, Official Raspberry Pi 7" Capacitive Touchscreen, Adafruit 2.8" capacitive PiTFT, and a Waveshare 3.5" screen.  Note that some screens support dimming (the Adafruit ones for example) but some don't (the Waveshare).  Some limited testing has been done on Chinese clone screens - no guarantees there as you may have to work on their calibrations.  The current install scripts change the system  to run under Python 3 as distributed with Raspbian.  The code is no longer comatible with Python 2 due to requirements on the libraries it uses.

  To set up a system use one of the following methods:

    * Easiest:  Build your Pi using the a recent Raspbian image from the Foundation.  The system has been tested and run on Jessie and Stretch versions.  (As of 5/1/2018 the current version is a Stretch version.)  Add the **pisetup.sh** script to the /boot partition on the SD card while you have the card in whatever system you use to write the image.  After booting the Pi with this image you may want to configure WiFi from the console if you need that.  Then run as root `bash /boot/pisetup.sh`.  
        * Note: If Raspbian finds a file called "wpa_supplicant.conf" in the boot directory it will copy that to the right spot to enable WiFi.  This file looks like:
          ```
          ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
          update_config=1
          country=US

          network={
              ssid="your wifi ssid"
              psk="your wifi key"
          }
          ```
             Also, if it finds an ssh file (content of no importance) it will enable ssh access.  So I find it easiest when I finish burning the OS image on the SD card, to then copy my wpa file and an empty ssh file to the boot partition (it will be available on your PC).  Then when you first boot the Pi you will be able to immediately log into it over the network via ssh and run the pisetup script with no need to ever use an HDMI cable.  In the same spirit as this, my script looks for a directory called "auth" and copies its contents to ~pi/Console/local so you can create your password stuff once and put it in a file that gets included in your config file.
        * Note: Various subscripts get run by pisetup some of which may ask you to reboot the system.  *DO NOT REBOOT* from these subscripts - none should interactively give you that option in any case.  If you select auto reboots in the initial prompts, you should never have to manually reboot and eventually the system should finish and either open a desktop or if you autorun the console, start the console.  Manual reboot would only be needed if you do not ask for auto reboots during install (see below).  If you answer y to the continue install question then you should have to answer a few questions at the start and then nothing more.

        This script will ask questions needed to configure the console hardware and software:
        * A node name: allows the node to be addressed by name on the network versus only by it's IP address.  Set this and make sure it is unique on your network.  You should be able to address the node later as <nodename>.local.
        * VNC Standard Port: this allows you to move the VNC server and ssh server to non-standard ports if you wish.  If you answer yes a VNC port will be established on 5900 for the console and on 5901 for a virtual console and ssh will run on 22 (note if you use the headless configuration approach noted above, ssh will run on its normal port until after the pisetup script runs even if you move it via the prompt).  If you supply a port number here then the VNC virtual console will appear on that port, the VNC console will appear on that port minus 1, and ssh will appear on that port minus 100.  Don't use this unless you know why you are - one reason might be if you are planning to open a firewall in your router to allow non-local access to the console (often but not always a bad idea).  To access the node via VNC you will probably want to normally use the virtual VNC since the console VNC will have the size and shape of your Pi screen and will only display an interactive terminal if the pi screen is showing one (i.e., the softconsole is not running).
        * Personal: You probably want to answer N to this.  I sometimes run special stable versions of the softconsole at my house to try out things.  Setting this to yes will access such versions which may mean you get something that isn't tested for your situation.
        * Autostart: Normally you'll answer y to this as it sets things up to automatically run the softconsole on the pi screen at boot rather than leaving your pi at an X-window session.
        * Screen type: Enter the type of pi screen you are using from the list of supported ones in the question.  Other screens may well work but you'll need to install them yourself after this script finishes.
        * Whether you want to set up a minimal ISY test. (see below)
        * Continue install: answer yes here to simplify the install process.  The system will automatically reboot and run the second part of the softconsole install. 
 If you don't answer y then when the script finishes you should reboot and then run **installconsole.sh** as root after the reboot.  Before rebooting you may do any other system configuration that you need.  For example, this is where you'd configure a screen type that isn't (yet) supported by the setup script.
   
        * **Note**: There are some long pauses in my experience doing this, and their length depends upon which Pi you have and the specific brand/type microSD card you are using (speeds vary a lot across manufacturers and models).  When you first boot Stretch, e.g., it may seem to give you a prompt and then blank the screen.  It stays blank a long time (3-4 minutes) and then opens a graphical console.  There are also some long downloads and unpacks.  Particularly if you are installing on a Pi0 be patient - that little processor is working as hard as it can!
    * Expert alternative: Configure its networking and expand its file system.  Manually examine the scripts above to perform the specific configurations and installations that make sense for your system.
* Note: I don't suggest setting the personal system flag in the install script.  What it does is force the update function of the console to use the release I am running on my home systems.  Generally this is fine since I don't want my house system broken, but may be a less tested version or have some other quirky behavior that I am looking at.    
* The resultant system should have a consolestable and consolebeta directories populated and a Console directory created.  The configuration file goes in the Console directory.  The default name of config.txt is looked for first, followed by looking for a file of the form config-_systemname_.txt.  The console can be run manually as "sudo python -u console.py" from within the consolestable directory.  The console is also configured as a Linux service using the systemd manager with the name "softconsole".  See the discussion below on starting the console.  The version of the console run by systemd will be the one in consolestable unless "usebeta" file exists in the home directory.  From the maintenance screen in console you can ask to set the beta version and download the current beta.
* Current release notes:
    * Version 2 code made a major overhaul the the fundamental program sequencing structure to allow for alert procedures and alert screens.  Alert procedures are procedures that can be called based on time, the value of an ISY var, or the state of an ISY device.  Alert screens are screens that can be defined to take over control of the display based on the value of an ISY var or an ISY node value, possibly delayed in time by some period.  Alert screens can be deferred by a keytouch or can execute some action that will resolve the alert.  If the alert condition is otherwise cleared within the ISY, the screen will also go away.
    * Version 2.8 made variables first class citizens that appear in "stores" that can be referenced in alerts, alert screens, and weather screens using the format STORENAME:VAR:VAR . . .  All weather stations create a store for all their current conditions and forecasts.  MQTT broker clients create a store for any items they subscribe to.  There is a system store **System** that holds some system wide parameters (currently only the Dim and Bright values).  As of this release ISY variable references that use "StateVar" parameters are deprecated in favor of the general form of variable reference ISY:State:name and ISY:Int:name (or console local variables as LocalVar:Name).  The old forms are supported for now in the config files but will eventually disappear.  This release also add the VARKEY option.
    * Version 3 code made hubs a configurable part of the console which means that console now can support multiple hubs of multiple types.  Currently ISY and Home Assistant hubs are supported.  If multipe hubs are specified a DefaultHub=name directive sets the hub to be used when no other hub is specified.  Within a screen a DefaultHub directive can be given to change the default hub for that screen.  It is always possible to specify the hub for a node using the NODE:nodename syntax like that used for stores.
    * Version 3.1 adds support for weather providers other than Weather Underground and allows multiple such suppliers.  Unfortunately, this requires a small change to the configuration file even if you are continuing to use WU (see below).  The TimeTemp screen type required non-compatible changes to work with the new approach so I have left a TimeTempX screen type that should continue to work with the old approach using the WunderKey to set the api key.  I'll delete this soon since the changes to use the new approach are pretty minimal.  If you want to add another weather provider, it should be pretty easy to write the code using the apixustore.py module as a model.  It mostly handles mapping from the provider specific json response to the one used elsewhere in the console.
    * Version 3.2 adds support for consoles to be aware of other running consoles and coalesce serious error messages to their logs as well as their error in log indicators.  This makes running multiple console around the house much simpler since accessing the log from any of them will let you see Warnings or Errors reported by any of them and will correspondingly clear the other error indicators when it is known that the message has been seen for sure on another consoles log scan.  It also added some mostly hidden diagnostic capabilities and greatly improved handling of errors from the hubs, particularly ISY reported communication errors.  With the demise of WeatherUnderground as an available weather provider, support for accessing their api has been removed (code was moved to deprecated folder in the source).  Their API is changing with no way for me to access the new one given it is no longer free.
    * Note that all the source code for the console is available on github under kevinkahn/softconsole and you are free to examine and/or modify as you like.

# Console Directory and Files
The installation creates a number of diretories and installs many files, all based in the /home/pi directory.  First there 3 directories that hold the actual program and its documentation.  The directory **consolestable** holds the current released code.  If you later update the release via the maintenance screen or via an automatic update procedure the files in this directory get updated.  The directory **consolebeta** holds the current beta release.  Normally you won't care about or run this version since it is test code.  You can select to run this version from the console maintenance screen but I don't suggest you do that unless you are doing because I asked you to.  The directory **consolerem** is empty and is an artifact of my debugging and test environment.  The directory **Console** is the only directory that you should normally have reason to manually change or use.  It holds, by default, the configuration files and the operational log files for the console.  Other files left from the install process are in a directory called **consoleinstallleftovers** which may be deleted under normal situations.  Files earlyprep.log and prep.log document the install and may be useful for diagnosing issues if a problem occurs during system installation.  The python script adafruit-pitft-touch-cal is used during installation to set up the screen calibration.  It is left behind in case any issues arise with that. Finally the file log.txt simply records console code installs and restarts.  The contents of the 2 source directories is simply a clone of the relevant versions of the GitHub repository, although once the console has run python also leaves compiled files here.

The **Console** directory holds the log files from each run of the console.  Most recent is Console.log, previous is Console.log.1, etc.  The number of logs kept is a console parameter.  The setupconsole asks whether to set up a minimal test system.  If you answer 'n' then the Console directory is left empty and you should proceed to create your configuration information manually.  If you are just starting, you should probably answer 'y'.  In this case, a set of example configuration files will be copied from the example directory in consolestable to Console.  By default the console looks for ~/Console/config.txt as its starting configuration file.  I have for neatness used the subdirectory cfglib as a place to place additional configuration files that may be included via directives in config.txt and have conventionally use the cfg extension for these.  Note, there is no difference between the config.txt format and the cfg file formats and were I to do this again I'd probably have made them all names *.cfg.  In my use, I have found that I often what to use the same screen on a number of my consoles and this allows me to create those screen configurations once and copy them to each system.  Se the next section for a suggested way to get started via the minimal configuration file that is in the examples.

# Starting the Console
As of version 2.6 the system has moved to systemd for starting.  If you do a clean install of this version or beyond a service description has been placed in /usr/lib/systemd/system.  To have the console start at boot do "sudo systemctl enable softconsole" and beginning with the next boot it will start automatically.  If you selected this option during install this has already been done for you.  To stop the console from starting automatically use "sudo systemctl disable softconsole".  At any time the console can be started with "sudo systemctl start softconsole" or stopped with "sudo systemctl stop softconsole".  All other interactions via the systemd mechanism are also available and limited console log messages will appear in syslog.  See systemd man pages for more info about service control.

If you upgrade to 2.6 rather than doing a clean install then the systemd mechanisms are set up but are not enabled and the existing start mechanism using rc.local continues to be used.  Because other modifications may have been made to your rc.local I did not try to automate this update.  While the rc.local startup should continue to work, I suggest that you manually edit rc.local to remove the start of the console and then enable systemd startup as above.
# Quick Setup of Minimal Test
To insure that the basic setup of the Console is ok and that you understand the pieces, there is a minimal test configuration that you might want to run.  If you answer 'y' to the question above about creating a minimal ISY test configuration, setup will continue by asking for the IP address of your ISY, your ISY username, and your ISY password.  It will create the file Console/cfglib/auth.cfg using this information.  It will also ask for the ISY name of a single switch that you want to use for the test.  It will use this information to create a single screen with a single button that should turn that switch on and off.  It will also define a clock screen that should appear when the console is idle.  The minimal test configuration is not currently supported for a HA hub.

Now start the console as root by going to the consolestable directory and running python -u console.py.  This should bring up a very simple 1 screen instance of the console that can turn on/off the switch you picked.  If you leave the screen untouched for 15 seconds it should dim and then after another 30 seconds it will switch to display a cover screen - here the clock.  

You can also touch a nav key at the bottom of the screen to move to the next or previous screen in the chain (here there is only one - the clock screen) to get the clock displayed.  As this is a live screen and not a cover screen it will have nav keys.  Now if you don't touch the screen it will dim after 15 seconds, persist as a dim clock for 30 seconds and then change to a dim home screen (here the test screen), persist for 30 seconds as a dim home screen, then switch to a cover screen (here the clock also but with no nav keys).  At any point where the screen is dim touching it will brighten it, and if it is on a cover screen return you to the home screen.

Playing with this test should give a basic idea of the operation when many screens are available.  The times above are all parameters in the config file.  Multiple cover screens can be defined which will then cycle using the times in the idle list times parameter.  When the screen is "bright" touching it 3 times will switch to a Secondary chain of screens (see other example files as not such secondary chain is defined in the  minimal test).  Touching the screen 5 times will get you to the Maintenance screen from which new versions can be downloaded or the console or the Pi restarted or shutdown.
# Basic Operation/Arrangement of the Console
The basic command structure of the console is based on screens.  The program allows a main sequence of screen within which you can move forward and back via the navigation keys at the bottom of the screen.  The program also allows the definition of a secondary chain of screens.  You can move between these chains via 3 quick taps.  The reason for the 2 chains is that I have found that for any console instance it is likely to be convenient for have a few screens that get frequently accessed.  However, you may want to have many more, e.g., to include ones that control all other parts of your house.  It is annoying if these are in the main chain since you then would have to click through them all the time.  One of the screens on the main chain is designated home and this is the screen that the console will return to on its own if left idle for a timeout period.  The console also defines "cover" or idle screens which appear when the console has been idle for a while.  If more than one is defined the console will sequence through these screens based on timers.  Think of these as "covering" the home screen; they allow easy display of things like time or weather (or eventually perhaps other information).  These are passive screens when displayed with no navigation keys.  Touching them simply reverts the console to the home screen.  As a side note 5 taps will take you to a maintenance screen that allows some administrative operations.
# Setting up and Running Softconsole
First I admit in advance that the syntax and parsing of the config files is both a bit arcane and somewhat error prone.  This is larglely due to the configuration parser I use and perhaps someday I can improve this.  You've been warned!  Given an understanding for the minimal test above you can then create real configuration files as you wish:
* Create a main config file, see the files in the "example configs" directory within consolestable for help.  The name of the config file defaults first to **config.txt**.  If no config.txt file is found in the Console directory then the console looks for a file with the name **config-\<nodename\>.txt**.  This is convenient if you are running multiple consoles around your home.  You can create a single directory of all your configs and blindly load it onto each system and the system will select the correct configuration based on its name.  The basic structure of the file is a sequence of sections started with \[section name] where the outermost part of the file is implicitly a section.  Subsections which are currently only used to describe keys are started within a section with \[\[subsection]].  Within any section are parameter assignments of the form name = value.  A complete list of current parameters is found in the params.txt file in this directory.  It lists the global parameters with their type and default value if no assignment is supplied.  It also lists for each module the local parameters of that module as well as any global parameters that can be overridden in that module.  Strings may be written without quotes.
  * While error checking is limited for the config information, the program will log to the Console.log file any parameters that appear in your configuration that are not actually consumed by the console as meaningful.  This helps locate possible typos in the config file.
  * One note of importance: labels are lists of strings and should always be notated as "str1","str2".  A label with a single string must be made a list by appending a trailing comma.  Failure to do this will result in the string itself being viewed as a list of single characters which will result in strange output.
* The parameter MainChain provides the names in order of the screens accessible normally.  The parameter SecondaryChain provides a list of screens that are accessible indirectly (see below).  Any number of screens can be defined.
* Whenever a color needs to be specified you can use any color name from the W3C list at http://www.w3.org/TR/SVG11/types.html#ColorKeywords
* The config file supports an "include = filename" parameter to allow breaking it up conveniently.  This cam be useful if multiple consoles use some of the same screens and you want to have only one version of the description for those shared screens.  It also supports a "cfglib = dirname" as a default place to look for included config files.  Personally I have lots of small config files that I keep in a directory and specialize a single top level config file for each of my consoles.  See the directory "example configs" on github for lots of examples.
* Some responses from weather providers are fairly long phrases that don't display nicely on the weather screens.  There is a file termshortenlist in the Console directory which is a json representation of a Python dictionary that maps phrases to shorter ones for display.  It is self explanatory if you look at the examples that are prepopulated.  You can edit this as you wish to add or change phrases to be shortened.  If the console comes across a phrase that appears too long as it is running it will add create a termshortenlist.new file and add it to it.  This provides an easy way to create a new version of the termshortenlist file by editing the new one.

# Hubs
As of Version 3 the console can support multiple hubs.  Currently it can handle ISY controllers and HomeAssistant controllers.  It can support, in principle, any number of hubs concurrently although testing at this point has only been for a single ISY together with a single HA, where individual screens have had keys that operated devices from each type of hub appearing together.  HA hubs currently support on/off operation for light and switch domains.  They also make available all sensor entities in a store named with the HA Hub name.  Finally, they support a thermostat screen that uses the standard HA climate domain but has only been tested using Nest thermostats.  The old form syntax for specifying the ISY hub via config file elements ISYaddr=, ISYuser=, ISYpasswd= are still supported.  However, the new preferred specification for a hub is to have a section in the config file named for the hub (e.g.,[[MyISY]]) with elements in that section type=, address=, user=, and password=.  An ISY Hub specification might look like:
 
```
        [[MyISY]
        type = ISY
        address = 192.168.1.15
        user = myusername
        password = mysecret
```
Current types are ISY and HASS.  Note that Home Assistant Hubs do not expect a user.  For a HA hub use the password element to specify an access token that you create in your HA hub (HA 0.77 and after).  No user is needed for an HA hub.

A default hub can be set for the configuration with DefaultHub= specifying the name of the default.  Any screen can also provide a DefaultHub= element to override the default hub for that screen.  Finally, key section names can specify explicitly the hub by which their device is controlled via the syntax hubname:nodename.

# Stores and Values
The console has a general notion of stored values that some of the screens and alerts can use.  Stored values are referenced by their store name and value name within the store and can be any single value or an array of values.  For example, each weather station that is referenced from Weather Underground has its recent data stored in a store named by the station name.  As an example for the weather station KPDX one can access the current temperature at Portland Airports as KPDX:Cond:Temp or the forecast low temperature for the day 2 days out as KPDX:Fcst:Low:2.

Stores are created for ISY variables (ISY:State:<varname> and ISY:Int:<varname>), local variables (LocalVar:<varname>), the weather stations, any MQTT brokers (<brokername>:<varname>), and console debug flags (Debug:<flagname>).  There is also a System store (entries of the form System:DimLevel) that holds some global system parameters that may be displayed or changed at runtime (currently mainly the DimLevel and BrightLevel values).  Store values may be referenced on weather and timetemp screens, in alerts, and alert screen actions.  There is also an **assignvar** alert (referenced as AssignVar.Assign) that may be used to assign a literal or another variable value to a store element.  An example of its use is to change the dim level of the screen at certain times of day.

Stores are also used to store all major system and screen parameters.  System parameters are in the **System** store, while screen parameters are in a store named with the name of the screen.  Use the maintenance screen, set flags, dump stores to create a StoresDump file in the Console directory if you want to see all the stores and field names.  Inaddition to the alert and screen references described above there is a general ability to set a store value while the console is running via MQTT.  This is definitely not for the faint of heart - feel free to contact me directly if you need to use this and the discussion below isn't adequate.

# Weather Providers
Screens that display weather need to have a store populated with the current information.  You define a weather provider like you do a hub.  Currently there is support for APIXU.  Define a provider and its key in the config file or an included subfile as:
```
    [APIXU]
    type = WeatherProvider
    apikey = <key>

```
The section names designate the provider and one or both can be used.  Locations for which to get weather are defined like:
```
[PortlandW]
type = APIXU
location = 'Portland, OR'
refresh = 59
[PDX]
type = APIXU
location = '45.586497654,-122.591830966'
```  
The section name will be the name of the store that will hold the weather and can be referenced where ever store references are allowed, most likely on a weather screen or timetemp screen.  Location is the string that the provider will use to return the weather.  Refresh is the optional refresh interval for getting new data in minutes (default 60).  Most providers limit calls per day so this provides some control over the demand you create.

The weather information is available in a store named as above with entries under "Cond" for current conditions, "Fcst" for forecast conditions (these are indexed by day number), as some common fields.  The set of fields available with standard names for screen display purposes are:
 * Current conditions:
```
    Time: time of readings as string
    TimeEpoch: time of readings as Unix epoch
    Location: Location of readings as string
    Temp: Current temperature as float
    Humidity: Current humidity as string
    Sky: Current sky condition as string
    Feels: Current "feels like" temperatire as float
    WindDir: Current wind direction as string
    WindMPH: Current wind speed as float
    WindGust: Current gust value as int
    Sunrise: Daily sunrise time as string
    Sunset: Daily sunset time as string
    Moonrise: Daily moonrise time as string
    Moonset: Daily moonset time as string
    Age: Dynamically computed age of reading as string
    Icon: Pygame surface of weather icon
```
 * Forecast Fields: (these are indexed by day up to the length of available forecast)
 ```
    Day: Name of day forecast is for as string
    High: Forecast high for day as float
    Low: Forecast low for day as float
    Sky: Forecast sky condition for day as string
    WindSpd: Forecast wind as float
    WindDir: Forecast wind direction as string of form "DIr@" since
     some providers do not provide this.  This form allows empty
     string for those to still have display make sense.
    Icon: Pygame surface for weather icon
```
 * Common Fields:
 ```
     FcstDays: Number of forecast days available as int
     FcstEpoch: Time of forecast as Unix epoch
     FcstData: Time of forecast as string
 ```

# MQTT Broker Reference
## MQTT for Information Access
The console can subscribe to an MQTT broker and get variables updated via that route.  To do this create a separate section named as you with for each MQTT broker you wish to subscribe to.  Provide parameters that specify its type as MQTT, its address, password (if needed), and then a sequence of subsections each of which names a variable to be subscribed to.  These sections have parameters Topic, TopicType, and Expires that describe how the value will be stored in the console.  If Expires is left out then values will be valid forever, otherwise they will disappear after the listed number of seconds.

For example, the following might subscribe to a broker running in the house to which local sensors publish the current temperature and humidity on the patio.  One can then reference the current patio temperature on, for example, a timetempscreen, as myBroker:PatioTemp.  If the sensor stops posting for over 2 minutes then the console will show no value.
```
    [myBroker]
            type = MQTT
            address = server.house
            password = foobar
            [[PatioTemp]]
            Topic = Patio/Temp
            TopicType = float
            Expires = 120
            [[PatioHum]]
            Topic = Patio/Hum
            TopicType = float
            Expires = 120
```

## MQTT for Console Management
If the console subscribes to MQTT then additional function is enabled for managing the consoles.  If the console subscribes to multiple MQTT brokers than the first one configured is the default management broker.  You can force a specific MQTT broker to be the management broker by specifying **ReportStatus = True** in the configuration file for that broker.  The rest of this section describes the management related functions enabled by a management broker.

At startup the console registers itself with the broker with a message to **consoles/all/nodes/\<hostname\>** containing information about the version running (version name, github sha, time of download), the time of the registration, the boottime of the pi running the console, the OS version running on the pi, and the hardware version of the pi. The console will then periodically publish to the broker at **consoles/\<hostname\>/status** a status update containing its status, uptime, and the state of the error indicator flag that notes an unseen Warning or Error in the log.  If the console goes down for any reason, the broker will publish a **dead** status. There is a short python program in the download directory called status.py that is an example of how to do a quick check of whatever consoles are running.  A console will also publish to **consoles/all/errors** a message whenever a Warning or Error level message is logged.

The consoles will also coordinate their Warning/Error messages.  A console log will now contain a copy of such messges issued by other consoles.  An attempt is made to coalesce messages when multiple consoles see the same issue at the same time.  If you scan the log from any one console, in addition to clearing its own error indicator, it will also cause the indicators for other consoles to be cleared provided that the log you scanned has been up long enough to have contained all the errors from that other console.  This generally means that scanning the log of a single console will let you see any errors that have occurred elsewhere in the house.

Finally, the consoles will accept commands from MQTT.  A console listens on the topics **consoles/all/set** and **consoles/\<hostname\>/set** for store name and value to be set in a variable (json encoded).  A console also listens on **consoles/all/cmd** and /**consoles/\<hostname\>/cmd** for the following commands:
* restart: restart the console
* getstable: fetch the current stable release
* getbeta: fetch the current beta release
* usestable: set the console to start the stable version at next restart
* usebeta: set the console to start the beta version at the next restart
* status: issue a status message to MQTT
* issueError, issueWarning, issueInfo,hbdump: diagnostic/debug commands

# Currently supported screens
* Keypad: mimics the KPL.  Can support any number of buttons from 1 to 25 and will autoplace/autosize buttons in this range.  Parmetrs KeysPerColumn and KeysPerRow may be used to override the auto placement of the keys.  Keys may be colored as desired.  Key types are:
    * ONOFF: linked to a device or scene and supports On, Off, FastOn, FastOff behaviors
    * RUNPROG: linked to a program to run.  It issues a RunThen on the designated program for ISY hubs. It issues a automation.trigger for the automation for HA hubs.
    * (Deprecated-use RUNPROG with modifiers) ONBLINKRUNTHEN: linked to a program.  Will blink to provide user feedback and will issue RunThen on program
    * ON: will always send an "on" command to the linked device.  This is useful for things like garage doors that use on toggles.
    * OFF: will always send an "off" command to the linked device.
    * SETVAR: set the value of an ISY variable
    * VARKEY: this type can be used passively to construct status displays or also allow stepping through a predefined set of variable values.  Its **Var** parameter specifies a store item to operate on.  It has an **Appearance** parameter that specifies the display appearance of the key for various values of the store item.  This parameter has the form of a list of comma delimited descriptor items.  Each descriptor item is of the form "range color label" (without the quotes).  Range is either a single integer that specifies a store item value or a pair n:m which defines a range within which the store item falls for this descriptor to be used.  Color is the color of the key for this value. Label is the label the key should have for this value using semicolons to separate lines within the label and a $ to be substituted for the store item value if desired.  If the label is left out of the descriptor item the normal key label is used (either the key name or an explicit label parameter). if the store value doesn't match any of the ranges the normal key label is used.  A **ValueSeq** parameter optionally specifies values that should be cyclically assigned to the store item if the key is pressed.  If the current value of the store item is not in the ValueSeq then a press sets the value to the first item in the sequence.  Leaving it out makes the key passive. As an example should help clarify:
       ```
        [[TestKey]]
            type = VARKEY
            label = Error in Value, $
            Var = ISY:State:tEST
            ValueSeq = 0,1,3,6
            KeyCharColorOn = royalblue
            Appearance = 0 green 'All good',1:2 yellow 'Probably; good; $',3:99 99 red 'Not so hot $'
        ```
        This describes a key that will be green and say "All good" if the variable is 0; be yellow and say "Probably good" and show the value on 3 lines if the value is 1 or 2; and be red and say "Not so hot" and the value on a single line for values of 3 to 99.  For any other values the key will display "Error in Value" and the value.  Sequential presses of the key when the value is 0 will set the variable to 1, then 3, then 6, then 0.  If something else has set the variable to, e.g.,4, then pressing it will make the variable 0.
    * Modifier Parameters: The ONOFF, RUNPROG, VARKEY, and SETVAR keytypes support certain parameters that modify the key behavior:
        * Verify = 1: displays a confirmation screen before running the program.  The messages on the confirmation screen can be customized with the GoMsg and/or NoGoMsg parameters.
        * Blink = n: provide visual feedback when when the runthen is issued by blinking the key n times.  (For VARKEY the key will blink if you have not yet seen it with its current value, even if that value had been previously set while another screen was showing on the console.)
        * FastPress = 1: requires a quick double tap to activate the key. (Note not applicable to the ONOFF keys since there a double press corresponds to issuing a fast on or off to the device).
     
    * Note: for scenes ONOFF will choose a device to use as a proxy for the state of the scene for purposes of the appearance of the button.  Generally this will turn out to be some other switch or KPL button that is a controller for the scene.  This can be overridden by supplying a specific device address or name to use as the proxy.
* Clock: displays a clock formatted according to the OutFormat parameter using any of the underlying OS time formatting codes.  The character size for each line can be set individually.  If there are more lines in the format than character sizes the last size is repeated. Python standard formatting is at https://docs.python.org/2/library/time.html.  Linux (RPi) supports a somewhat richer set of codes e.g. http://linux.die.net/man/3/strftime
* Weather: uses a weather provider to display current conditions and forecast.  The location parameter is a location code defined as above.    
* Thermostat: mimics the front panel of the Insteon thermostat and provides full function equivalency.
* ThermostatNest: thermostat screen for HomeAssistant that has been tested with Nest thermostat.  This screen uses an improved update approach for the setpoints.  Touching the setpoint buttons only adjusts the values locally on the console and greys the values to indicate this.  If no additional touch is seen for 2 seconds then the resultant setpoint is pushed to HA and thus the thermostat.  The displayed values remain greyed until an update from the thermostat indicates it has set them or an addition time period passes after which the actual current setpoints are retrieved and displayed normally.  Thus if an error occurs updating the setpoints on the actual thermostat you may see the old setpoint reappear indicating something went wrong.  This is important for the Nest because Nest limits the rate of changes they will accept in an undocumented manner.  So reducing the actual number of Nest updates is important as is accepting that sometimes they simply don't accept the update (thus the console reverting to old values).
* Time/Temp: combined screen, nice as a sleep screen that gives current time and the weather.  Format of the screen is largely controlled by the config.txt file.  The location is displayed unless you set the character size for that line to 0.  An icon can be displayed as part of the current conditions by setting CondIcon = True.  An icon canbe displayed as part of each forecast day by setting FcstIcon = True.  There are a variety of options for the display of the forecast days that can be selected by setting FcstLayout in the config file.  They are:
    * Block: forecast items are left aligned in a block that is centered based on the longest item (1 column) 
    * BlockCentered: forecast items are individually centered but multiline items are left aligned (1 column)
    * LineCentered: forecast items have each individual line centered (1 column)
    * 2ColVert: 2 column layout newspaper style days ordered down the column with a vertical line that visually splits the columns
    * 2ColHoriz: 2 column layout with days ordered across then down
    
    Fields that are referenced in the format descriptions of the config file will use the store corresponding to the location code specified for the screen and the type of field group being specified by default.  E.g., if the location is specified as KPDX then the default for a field, \<field\>, mentioned in the ConditionFields is KPDX:Cond:<field>.  However, any field in any part of the screen can be explicitly notated.  E.g., in the ConditionFields one could specify FOO:Fcst:High:1 to reference the forecast field for the next day high at FOO or MQTT:Humidity to reference some field Humidity that is supplied via an MQTT broker named MQTT.

    There are four regions of the screen each with its own character sizing parameter.  The font size of the clock area is given as **ClockSize**, that of the location as **LocationSize** (where 0 suppresses the location line), the current conditions block as **CondSize**, and the forecast block as **FcstSize**.  Note that for the current conditions and forecast blocks which can be multiline the appropriate size parameter can be a list of sizes which then apply sequentially to the lines.  The old parameter **CharSize** is deprecated.  It works currently but will be removed in the future.

    * Alert: used to display an alarm condition - see below.

# Alerts
Alerts are defined in an "\[Alerts\]" section of the config files.  See cfglib/pdxalerts for some examples.  Currently alerts can be triggered periodically, based on a node state chance, or based on a variable state change.  The effect of the alert can be delayed by some time to avoid alerts for routine events that should clear within some typical window.  Alerts can either invoke an alert screen (see the away and garage alerts in the sample file) or an alert procedure (see the update alert).
## Triggers
The condition that causes an alert is defined within the config section that defines the alert.  It has a **Type** which is currently Periodic, VarChange, or NodeChange.  For the VarChange trigger Var specifies a store element (see stores above), and Test and Value are used to describe how to test it.  For the *node* trigger Node, Test, and Value describe the trigger.  For *periodic* provides two options. You can provide parameter **Interval** which describes a repetition period either as an integer seconds or as an integer followed by "minutes" or "hours".  Alternatively, you can specify a parameter **At** which specifies either a single time of day or comma seperated list of times using standard time format (24 hour or explicit am/pm).  For any of the triggers a Delay parameter may be specified to have the actual triggering delays some time period beyond the condition becoming true.
Triggers cause either an alert screen to be shown or an alert proc to be run.  If the screen or proc in question takes some parameter from the alert the Parameter defines it (see NetworkHealth for example).
## Local Variables
It is possible to define variables local to the console by creating a **\[\[Variables]]** section in the config file and defining one or more **varname = \<value\>** within it.  These may be used like any other store element by being referenced as LocalVars:\<name\>  At the moment they have limited but some use.
## Alert Procedures
Currently the following alerts are available:
* **autoversion:** trigger this either at init time or periodically to check github for a new release.  If a new *currentrelease* is found it is downloaded, installed, and the console rebooted with the new version.  The old version is moved to a directory under the consolestable called *previousversion*.
* **netcmd:** if the ISY has an integer variable defined with a name Command.\<nodename\> then a capability is enabled to issue a command on the console by changing the value of the ISY variable.  (To conform with ISY variable naming rules and '-' characters in the node name are replaced by '.' in the variable name.) To see the available commands that can be remotely issued see the header of the netcmd.py file in the source code.
* **networkhealth** when triggered (typically periodically)check for network connectivity to a specified IP address.  E.g., checking for 8.8.8.8 (the google name servers) will allow creation of an alert if Internet access is lost.  Typically this trigger will be used to invoke an alert screen to display the alarm.  Define the trigger to have Parameter = IPaddress,localvarname and localvarname will be set to 1 if the address is pingable and 0 otherwise.  If the variable changes it triggers any alert based on a "varchange" which can be used to display the alarm.
* **assignvar** When triggered (as *AssignVar.Assign*) it executes the assignments listed in it Parameter option.  The Parameter is of the form var-ref = val where var-ref is a store idenitifier and val is either a number or a store identifier.  E.g., Paramter = ISY:State:tEST = KPDX:Cond:Temp, ISY:Int:TestVar= 5 would assign the current KPDX Temperature to the ISY State variable tEST and assign the value 5 to the ISY Int variable TestVar each time it is fired.  (This replaces the temporary hack alert tempstoisy.)  As an example use, an assign of a value to the variable System:DimLevel using a periodic alert with a specific time parameter might be used to adjust the dim level of a console for late night versus daytime behavior.

## Alert Screens
These are screens that are triggered to appear based on a node or variable state, perhaps with a delay from the time of the state change.  E.g., display alert screen 5 minutes after garage door is opened if it is still open.  They provide a single button that can be linked to resolve the alert condition.  They are triggered by a test in the alert section of the config file defined above. An Alert screen can be deferred for a predefined time after which they will reappear. If the condition causing the alert clears they will disappear.
# Connecting Console Names with ISY Names
* Some names in the config file are used to link console objects to ISY nodes/scenes.  Specifically the section name of a thermostat sceen is used to connect that screen to an ISY thermostat and the subsection names of ONOFF keys are used to link those keys to an ISY device or scene.
* Simple names are looked up as the names of leaf nodes in the ISY node tree.  You can also reference an ISY node via its full name using conventional "/" notation to describe the path from the root by starting the name with a "/".
* When a name is looked up in the ISY for linking preference it always given to finding the name as a scene first.  Thus if a device and a scene have the same name the console will link to the scene.

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
* On the maintenance/log screen single tap the lower part of the screen to see the next page or the upper part to see the previous page.
* On all normal display screens you may see a dim circle displayed in the upper left hand corner of the screen.  This indicates that since the last time you looked at the log from the maintenance screen, a Warning or Error level entry was added.  It clears once you go to the log screen.

# Developers Notes
## Defining New Screens by Coding a Module (updated for version 2)
New screens can be developed/deployed by subclassing screen.ScreenDesc and placing the code in the screens directory.  Screens modules have a single line of code at the module level of the form "config.screentypes[*name*] = *classname*" where *name* is the string to be used in config files to as the type value to create instances and *classname* is the name of the class defined in the module.  A screen class defines the following methods (ScreenDesc provide base level implementations that should be called if overridden):

* __init__: Create a screen object based on an entry in the config file with a type equal to the type string registered in the definition of the screen.
* InitDisplay(nav): code to display the screen.  nav are the navigation keys or None and should be passed through the the underlying InitDisplay of ScreenDesc
* ReInitDisplay: code to redisplay the screen if it has been removed temporarily and assumes nav keys are already set.  Generally not overridden.
* ISYEvent(node,value): A watched ISY *node* has changed to the new *value*
* ExitScreen: code that is called as the screen is being taken off the display

## Defining New Alert Procs
Alert procs are defined as methods in classes stored in the alerts directory.  They have a single module level line of code of the form "config.alertprocs["*classname*"] = *classname*" where *classname* is the name of the class defined in the module.  The class will be instantiated once at console start time.  It may define one or more methods that will be called based on the definition of Alerts in the config file that the console reads.

## Diagnostic Support
Corresponding to each Console.log file in the Console directory there is a hidden directory **.HistoryBuffer that may contain diagnostic information.  When certain errors occur or upon user command the console will dump a recent history of all key events that have occurred over as much as the previous 5 minutes.  This includes very detailed diagnostic information from internal task lists and event queues as well as items that have been received from the hubs.

