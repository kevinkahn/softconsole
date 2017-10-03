# softconsole
Uses a Raspberry Pi and a 3.5" Adafruit PiTFT to create a soft touch controller for ISY-994 home automation.  In its
simplest from you can think of it as a soft replacement for using an 8 key Insteon Keypad Link to turn scenes on/off.
However, it allows defining an arbitrary number of screens of a variety of types.  A Key screen provides a screen with
a number of keys between 1 and 25 that can be linked to ISY supported devices, scenes, or programs.  The layout of
the keys self adjust for the number of keys.  The keys change color to reflect state of the controlled devices.  A
Weather screen provides current conditions and forecast using Weather Underground for any location based on its code.
(A free Weather Underground key is needed to support this.)  A clock screen provides a user configurable date/day
display.  A thermostat screen controls a thermostat via the ISY (heat/cool setpoint, current temp, etc.).  The screen
can automatically dim after a period of no touching, return to a home screen, or switch to a "cover" screen over the
home screen.  All is configurable via a config.txt file (with sensible defaults).  New types of screens could be added
by coding a screen class (see existing code for examples) which can be linked to the existing program with only a
single change to the existing code.

For detailed documentation see the [useage notes](docs/useagenotes.md).
