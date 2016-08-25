from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
import json

class EdgeProtocol(basic.LineReceiver):
    def lineReceived(self, line):
        deferred = self.factory.parseCommand(line)

        def writeResponse(message):
            self.transport.write(json.dumps({
                'success': True,
                'message': message
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

    def parseCommand(self, line):
        "setColors, getColors, getLock, releaseLock, setMode, getMode"
        try:
            data = json.loads(line)
        except (ValueError):
            return defer.fail()

        return defer.succeed(data)

def main():
    endpoints.serverFromString(reactor, "tcp:1234").listen(EdgeFactory())
    reactor.run()

if __name__ == '__main__':
    main()
