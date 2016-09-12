#!/usr/bin/python

from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
from neopixel import *
from itertools import chain, repeat
import sys
import json
import uuid

# LED strip configuration:
LED_COUNT      = 6       # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (must support PWM!)
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest

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
        self.active_locks = [ None, None, None ]
        self.lock_map = {}
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

    def set_colors(self, command):
        """Set the active color unless a lock is currently in place"""

        if 'colors' not in command:
            return defer.fail(Exception('No colors parameter was specified'))

        try:
            colors = self.light_controller.set(command['colors'])
            return defer.succeed({ 'colors': colors })
        except:
            return defer.fail()
            # return defer.fail(Exception('Unable to set colors due to unknown error'))

    def get_colors(self, command):
        try:
            colors = self.light_controller.get()
            return defer.succeed({ 'colors': colors })
        except:
            return defer.fail()

    def request_lock(self, command):
        # duration - max millis to hold lock
        # bars - which bars to lock, array of indices (0, 1, 2)

        if 'duration' not in command:
            return defer.fail(Exception('No lock duration specified'))

        if 'bars' not in command or len(command['bars']) < 1:
            return defer.fail(Exception('No bar lock set specified'))

        if len([ bar for bar in command['bars'] if self.active_locks[bar] ]) > 0:
            return defer.fail(Exception('One or more requested bars already locked'))

        # Conditions met, let's award a lock
        lock_code = str(uuid.uuid4())
        for bar in command['bars']:
            self.active_locks[bar] = lock_code

        self.lock_map[lock_code] = reactor.callLater(
            command['duration'] / 1000,
            self.clear_lock,
            lock_code
        )

        return defer.succeed({
            'lock': lock_code,
            'bars': command['bars'],
            'duration': command['duration']
        })

    def release_lock(self, command):
        if 'lock' not in command:
            return defer.fail(Exception('No lock code specified'))

        if len([ code for code in self.active_locks if code == command['lock'] ]) < 1:
            return defer.fail(Exception('Requested lock code does not exist'))

        self.clear_lock(command['lock'])
        return defer.succeed({ 'lock': command['lock'] })

    def set_mode(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred

    def get_mode(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred

    def clear_lock(self, lock_code):
        call_id = self.lock_map.pop(lock_code, None)
        if call_id and call_id.active():
            call_id.cancel()

        for index, code in enumerate(self.active_locks):
            if code == lock_code:
                self.active_locks[index] = None


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

    def set(self, colors):
        if len(colors) < self.strip.numPixels():
            raise Exception('Insufficient colors specified')

        color_set = map(self.clean_color, colors[0:self.strip.numPixels()])

        for i in range(self.strip.numPixels()):
            if color_set[i] is not None:
                self.strip.setPixelColor(i, color_set[i])
                self.current_colors[i] = color_set[i]

        self.strip.show()

        return self.current_colors

    def get(self):
        return self.current_colors


def main():
    print 'Starting Data Semi Cube Edge Service...'
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
