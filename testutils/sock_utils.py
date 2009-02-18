import errno
import fcntl
import os
import random
import socket
import time

# this blows - set close-on-exec flag
if hasattr(os, '_urandomfd'):
    #pylint: disable-msg=E1101,W0212
    fcntl.fcntl(os._urandomfd, fcntl.F_SETFD, 1)


class PortFinder(object):
    LOWER_BOUND = 16000
    UPPER_BOUND = 30000

    def __init__(self):
        self._port = None
        self.reseed()

    def reseed(self):
        random.seed()
        self._port = random.randrange(self.LOWER_BOUND, self.UPPER_BOUND)

    def findPorts(self, num=1, closeSockets=True):
        """
        Find C{num} random ports that aren't in use.

        If C{closeSockets} is C{True} (the default), returns a list
        of port numbers. If C{False}, returns a list of C{(port, socket)}
        tuples.
        """
        print 'Finding %d ports' % num # XXX
        ports = []
        sockets = []
        while len(ports) < num:
            if self._port > self.UPPER_BOUND:
                # Wrap around
                self._port = self.LOWER_BOUND

            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # Try to bind the IPv6 "any" address to make sure the
                # port isn't in use with TCPv4 or TCPv6 on any interface.
                sock.bind(('::', self._port))
            except socket.error, error:
                if error.errno != errno.EADDRINUSE:
                    raise
                # Collision - reseed so we get as far away from the
                # other process as possible.
                print 'collision!' # XXX
                self.reseed()
                time.sleep(random.uniform(0.1, 0.7))
                continue
            else:
                # Open port
                if closeSockets:
                    sock.close()
                else:
                    sockets.append(sock)

                ports.append(self._port)
                self._port += 1

        if closeSockets:
            return ports
        else:
            return zip(ports, sockets)


_portFinder = PortFinder()


def findPorts(num, closeSockets=True):
    return _portFinder.findPorts(num, closeSockets=closeSockets)


def tryConnect(host, port, count=100, interval=0.1, logFile=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Setting SO_REUSEADDR lets the kernel recycle dead ports
    # immediately, which is polite since we're making so many connections.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    for _ in range(count):
        try:
            sock.connect((host, port))
            sock.close()
            return
        except socket.error, error:
            if error.errno == errno.ECONNREFUSED:
                time.sleep(interval)
                continue
            raise
    if logFile:
        if os.path.exists(logFile):
            print 'logFile contents:\n%s' % open(logFile).read()
        else:
            print 'log file is missing'
    # re-raise the last error
    raise
