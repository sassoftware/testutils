import errno
import fcntl
import os
import random
import socket
import time

# this blows - set close-on-exec flag
if hasattr(os, '_urandomfd'):
    fcntl.fcntl(os._urandomfd, fcntl.F_SETFD, 1)

class PortFinder(object):
    __slots__ = []
    _portstart = random.randrange(16000, 30000)

    @classmethod
    def findPorts(cls, num = 1, failOnError=False, closeSockets=True):
        if cls._portstart > 31500:
            # Wrap around, hope for the best
            cls._portstart = random.randrange(16000, 30000)
        ports = []
        sockets = []
        for port in xrange(cls._portstart, cls._portstart + 300):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('localhost', port))
            except socket.error, e:
                if e[0] != errno.EADDRINUSE:
                    raise
            else:
                if closeSockets:
                    s.close()
                else:
                    sockets.append(s)
                ports.append(port)
                if len(ports) == num:
                    cls._portstart = max(ports) + 1
                    if closeSockets:
                        return ports
                    else:
                        return zip(ports, sockets)

        if failOnError:
            raise socket.error, "Cannot find open port to run server on"
        else:
            cls._portstart = random.randrange(16000, 30000)
            return cls.findPorts(num, failOnError=True)

def findPorts(num, failOnError = False, closeSockets = True):
    return PortFinder.findPorts(num, failOnError = failOnError,
        closeSockets = closeSockets)

def tryConnect(host, port, count=100, interval=0.1, logFile=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind to a random port, instead of letting the socket library pick up at
    # connect() time, otherwise there is a chance we stomp on the server's
    # port (connect() will increment the port number each time)
    for _ in range(4):
        _localTryPort, = PortFinder.findPorts(num = 1)
        try:
            sock.bind(('', _localTryPort))
            break
        except socket.error, e:
            if e[0] != errno.EADDRINUSE: # Address already in use
                raise
    else: # for
        # Re-raise the EADDRINUSE
        raise

    for _ in range(count):
        try:
            sock.connect((host, port))
            sock.close()
            return
        except socket.error, e:
            if e.args[0] == errno.ECONNREFUSED:
                time.sleep(interval)
                continue
            raise
    if logFile:
        print 'logFile contents:\n%s' % open(logFile).read()
    # re-raise the last error
    raise
