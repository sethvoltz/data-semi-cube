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

    def __init__(self):
        self.dispatch = {
            'setColors': self.set_colors,
            'getColors': self.get_colors
        }

    def parse_command(self, line):
        "Parse the incomming command and route to correct handler"

        try:
            data = json.loads(line)
        except:
            return defer.fail(Exception('Unable to parse JSON payload'))

        if 'command' not in data or data['command'] not in self.dispatch:
            return defer.fail(Exception('Unknown or missing command'))

        return self.dispatch[data['command']](data)

    def set_colors(self, command):
        deferred = defer.Deferred()
        deferred.callback({ 'colors': [1, 2, 3, 4, 5, 6] })
        return deferred

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


def main():
    endpoints.serverFromString(reactor, "tcp:1234").listen(EdgeFactory())
    reactor.run()

if __name__ == '__main__':
    main()
