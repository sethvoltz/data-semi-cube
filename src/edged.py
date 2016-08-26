from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
import json

class EdgeProtocol(basic.LineReceiver):
    def lineReceived(self, line):
        deferred = self.factory.parse_command(line)

        def writeResponse(data):
            self.transport.write(json.dumps({
                'success': True,
                'data': data
                }) + "\r\n")
            self.transport.loseConnection()
        deferred.addCallback(writeResponse)

        def onError(err):
            self.transport.write(json.dumps({
                'success': False,
                'message': err.getErrorMessage()
                }) + "\r\n")
            self.transport.loseConnection()
        deferred.addErrback(onError)


class EdgeFactory(protocol.Factory):
    protocol = EdgeProtocol

    def __init__(self, light_controller):
        self.light_controller = light_controller
        self.dispatch = {
            'setColors': self.set_colors,
            'getColors': self.get_colors
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
            return defer.fail(Exception('Unable to set colors due to unknown error'))

    def get_colors(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred

    def request_lock(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred

    def release_lock(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred

    def set_mode(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred

    def get_mode(self, command):
        deferred = defer.Deferred()
        deferred.errback(Exception('Not Implemented'))
        return deferred


class LightController:
    """Run the lights themselves"""

    def __init__(self):
        pass

    def set(self, colors):
        return colors


def main():
    light_controller = LightController()
    endpoints.serverFromString(reactor, "tcp:1234").listen(EdgeFactory(light_controller))
    reactor.run()

if __name__ == '__main__':
    main()
