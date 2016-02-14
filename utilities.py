import os
import sys
import time
import RPi.GPIO as GPIO
import pygame
import fonts

import config


def interval_str(sec_elapsed):
    d = int(sec_elapsed/(60*60*24))
    h = int((sec_elapsed%(60*60*24))/3600)
    m = int((sec_elapsed%(60*60))/60)
    s = int(sec_elapsed%60)
    return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)


def normalize_label(l):
    return l if not isinstance(l, basestring) else [l]


def ParseParam(param):
    for p in param.__dict__:
        if '__' not in p:
            p2 = p.replace('_', '', 1) if p.startswith('_') else p
            config.__dict__[p2] = type(param.__dict__[p])(config.ParsedConfigFile.get(p2, param.__dict__[p]))
            if not p.startswith('_'):
                config.Logs.Log('Param: ' + p + ": " + str(config.__dict__[p2]))


def signal_handler(sig, frame):
    print "Signal: {}".format(sig)
    print "pid: ", os.getpid()
    time.sleep(1)
    pygame.quit()
    print time.time(), "Console Exiting"
    sys.exit(0)


def daemon_died(sig, frame):
    print "CSignal: {}".format(sig)
    if config.DaemonProcess is None:
        return
    if config.DaemonProcess.is_alive():
        print "Child ok"
    else:
        print time.time(), "Daemon died!"
        pygame.quit()
        sys.exit()


def InitializeEnvironment():
    os.environ['SDL_FBDEV'] = '/dev/fb1'
    os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
    os.environ['SDL_MOUSEDRV'] = 'TSLIB'
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    pygame.display.init()
    config.fonts = fonts.Fonts()
    config.screenwidth, config.screenheight = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    config.screen = pygame.display.set_mode((config.screenwidth, config.screenheight), pygame.FULLSCREEN)
    config.screen.fill((0, 0, 0))  # clear screen
    pygame.display.update()
    pygame.mouse.set_visible(False)
    pygame.fastevent.init()
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT)
    config.backlight = GPIO.PWM(18, 1024)
    config.backlight.start(100)


def LocalizeParams(inst, g, *args):
    print g
    print inst.__dict__
    print inst.__class__.__dict__
    print config.__dict__
    for p in args:
        if p in config.__dict__:
            v = config.__dict__[p]
            t = type(config._dict__[p])
            print ' in', p, v, t
        elif p in g:
            v = g[p]
            t = type(g[p])
            print 'out', p, v, t
        else:
            print "CODE ERROR"
        inst.__dict__[p] = t(config.ParsedConfigFile.get(p, v))
