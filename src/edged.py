#!/usr/bin/python

from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
from itertools import chain, repeat
import sys
import json
import uuid
import os

DEBUG = False
if os.environ.get('DEBUG', False) == 'yes':
    DEBUG = True

if not DEBUG:
    from neopixel import *

# Local modules
from cube import CubeMode

# =------------------------------------------------------------------------------= Configuration =--=
# LED strip configuration:
LED_COUNT      = 6       # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (must support PWM!)
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest

# =--------------------------------------------------------------------------= Network Protocol =--=
class EdgeProtocol(basic.LineReceiver):
    def lineReceived(self, line):
        if not line.strip():
            self.transport.loseConnection()
            return

        deferred = self.factory.parse_command(line)

        def writeResponse(data):
            self.transport.write(json.dumps({
                'success': True,
                'data': data
                }) + "\r\n")
        deferred.addCallback(writeResponse)

        def onError(err):
            self.transport.write(json.dumps({
                'success': False,
                'message': err.getErrorMessage(),
                'trace': str(err)
                }) + "\r\n")
        deferred.addErrback(onError)


class EdgeFactory(protocol.Factory):
    protocol = EdgeProtocol

    def __init__(self, light_controller):
        self.light_controller = light_controller
        self.active_locks = [ None ] * 6
        self.lock_map = {}
        self.mode = CubeMode.normal
        self.last_set_mode = None

        self.dispatch = {
            'setColors':   self.set_colors,
            'getColors':   self.get_colors,
            'requestLock': self.request_lock,
            'releaseLock': self.release_lock,
            'setMode':     self.set_mode,
            'getMode':     self.get_mode
        }

    def parse_command(self, line):
        """Parse the incomming command and route to correct handler"""

        try:
            data = json.loads(line)
        except:
            return defer.fail(Exception('Unable to parse JSON payload'))

        if 'command' not in data or data['command'] not in self.dispatch:
            return defer.fail(Exception('Unknown or missing command'))

        return self.dispatch[data['command']](data)

    # Protocol Commands

    def set_colors(self, command):
        """
        Set the active color unless a lock is currently in place

        colors - A set of colors equal in length to the device requirements
                 null values may be used to not set that light
        mode - The minimum mode required to show these colors
        """

        if 'colors' not in command:
            return defer.fail(Exception('No colors parameter was specified'))

        if 'mode' not in command:
            command['mode'] = 'normal'

        mode = CubeMode.lookup[command['mode']]
        if mode < self.mode:
            return defer.fail(Exception('Specified mode is less than current device mode'))

        try:
            if 'lock' in command:
                if command['lock'] not in self.active_locks:
                    return defer.fail(Exception('Lock code unknown or expired'))

                else:
                    locked_colors = [ color
                        if self.active_locks[index] == command['lock']
                        else None
                        for index, color
                        in enumerate(command['colors']) ]
                    self.light_controller.set(locked_colors, save=False)

            else:
                locked_colors = [ color
                    if self.active_locks[index]
                    else None
                    for index, color
                    in enumerate(command['colors']) ]
                active_colors = [ color
                    if not self.active_locks[index]
                    else None
                    for index, color
                    in enumerate(command['colors']) ]
                self.light_controller.set(locked_colors, show=False)
                self.light_controller.set(active_colors)

                self.last_set_mode = mode

            return defer.succeed({ 'colors': self.light_controller.get() })
        except:
            return defer.fail()

    def get_colors(self, command):
        try:
            colors = self.light_controller.get()
            return defer.succeed({ 'colors': colors })
        except:
            return defer.fail()

    def request_lock(self, command):
        """
        duration - max millis to hold lock
        lights - which lights to lock, array of indices (0..5)
        """

        if 'duration' not in command:
            return defer.fail(Exception('No lock duration specified'))

        if 'lights' not in command or len(command['lights']) < 1:
            return defer.fail(Exception('No light lock set specified'))

        if 'mode' not in command:
            command['mode'] = 'normal'

        if CubeMode.lookup[command['mode']] < self.mode:
            return defer.fail(Exception('Specified mode is less than current device mode'))

        if len([ light for light in command['lights'] if self.active_locks[light] ]) > 0:
            return defer.fail(Exception('One or more requested lights already locked'))

        # Conditions met, let's award a lock
        lock_code = str(uuid.uuid4())
        for light in command['lights']:
            self.active_locks[light] = lock_code

        self.lock_map[lock_code] = [
            command['mode'],
            reactor.callLater(
                command['duration'] / 1000.0,
                self.clear_lock,
                lock_code
            ),
        ]

        return defer.succeed({
            'lock': lock_code,
            'lights': command['lights'],
            'duration': command['duration']
        })

    def release_lock(self, command):
        """
        lock - the lock code to release
        """

        if 'lock' not in command:
            return defer.fail(Exception('No lock code specified'))

        if len([ code for code in self.active_locks if code == command['lock'] ]) < 1:
            return defer.fail(Exception('Requested lock code does not exist'))

        self.clear_lock(command['lock'])
        return defer.succeed({ 'lock': command['lock'] })

    def set_mode(self, command):
        """
        Most services will want to push individual colors (weather, stock, etc)
        as "ambient" priority while animations will generally use "normal"
        level. Information such as alerts, emergency notifications, etc, may use
        the "critical" level.

        mode - The mode to set the device to
        """

        if 'mode' not in command:
            return defer.fail(Exception('No mode specified'))

        mode = CubeMode.lookup[command['mode']]
        if mode == None:
            return defer.fail(Exception('Unknown mode specified'))

        if self.mode is not mode:
            print "Updating device mode to", command['mode']
            self.mode = mode

            # clear all locks less than current mode
            for key in self.lock_map.keys():
                if self.lock_map[key][0] < self.mode:
                    self.clear_lock(key)

            # reset the lights if set by lower mode
            try:
                if self.last_set_mode < self.mode:
                    self.light_controller.reset()
            except:
                pass

        return defer.succeed({ 'mode': CubeMode.name[self.mode] })

    def get_mode(self, command):
        return defer.succeed({ 'mode': CubeMode.name[self.mode] })

    # Helper Functions

    def clear_lock(self, lock_code):
        [lock_mode, call_id] = self.lock_map.pop(lock_code, None)
        if call_id and call_id.active():
            call_id.cancel()

        colors = self.light_controller.get()
        locked_colors = [ color
            if self.active_locks[index] == lock_code
            else None
            for index, color
            in enumerate(colors) ]

        for index, code in enumerate(self.active_locks):
            if code == lock_code:
                self.active_locks[index] = None

        try:
            self.light_controller.set(locked_colors, save=False)
        except:
            pass # eat error


# =--------------------------------------------------------------------= Dummy Light Controller =--=
class DummyLightController:
    """Fake light controller for testing"""

    def __init__(self, config):
        self.current_colors = [0] * config['led_count']
        self.config = config
        self.reset()

    def clean_color(self, value):
        if value == None: return None
        if isinstance(value, int): return value
        if isinstance(value, basestring): return self.hex_to_rgb(value)
        return None # fallback, unknown value type

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def reset(self):
        print 'Resetting colors to off'
        self.set([0] * self.config['led_count'])

    def set(self, colors, save=True, show=True):
        if len(colors) < self.config['led_count']:
            raise Exception('Insufficient colors specified')

        color_set = map(self.clean_color, colors[0:self.config['led_count']])

        for i in range(self.config['led_count']):
            if color_set[i] is not None:
                if save: self.current_colors[i] = color_set[i]

        print 'Current Colors: ' + json.dumps(self.current_colors)
        return self.current_colors

    def get(self):
        return self.current_colors


# =--------------------------------------------------------------------------= Light Controller =--=
class LightController:
    """Run the lights themselves"""

    def __init__(self, config):
        self.current_colors = [0] * config['led_count']
        self.config = config

        # Create NeoPixel object with appropriate configuration.
        self.strip = Adafruit_NeoPixel(
            config['led_count'],
            config['led_pin'],
            config['frequency'],
            config['dma_channel'],
            False, # invert signal
            config['brightness'],
            0, # channel (default 0)
            ws.WS2811_STRIP_GRB)

        # Intialize the library (must be called once before other functions).
        self.strip.begin()
        self.reset()

    def clean_color(self, value):
        if value == None: return None
        if isinstance(value, int): return value
        if isinstance(value, basestring): return self.hex_to_rgb(value)
        return None # fallback, unknown value type

    def hex_to_rgb(self, value):
        value = value.lstrip('#')
        lv = len(value)
        return Color(*(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)))

    def reset(self):
        self.set([0] * self.config['led_count'])
        print 'Edge colors reset to off'

    def set(self, colors, save=True, show=True):
        if len(colors) < self.strip.numPixels():
            raise Exception('Insufficient colors specified')

        color_set = map(self.clean_color, colors[0:self.strip.numPixels()])

        for i in range(self.strip.numPixels()):
            if color_set[i] is not None:
                if show: self.strip.setPixelColor(i, color_set[i])
                if save: self.current_colors[i] = color_set[i]

        self.strip.show()

        return self.current_colors

    def get(self):
        return self.current_colors


# =--------------------------------------------------------------------------------------= Main =--=
def main():
    print 'Starting Data Semi Cube Edge Service...'
    if DEBUG:
        light_controller = DummyLightController({ 'led_count': LED_COUNT })

    else:
        light_controller = LightController({
            'led_count': LED_COUNT,
            'led_pin': LED_PIN,
            'frequency': LED_FREQ_HZ,
            'dma_channel': LED_DMA,
            'brightness': LED_BRIGHTNESS
        })

    endpoints.serverFromString(reactor, "tcp:8300").listen(EdgeFactory(light_controller))
    reactor.run()
    print 'Edge Service Started'

if __name__ == '__main__':
    main()
