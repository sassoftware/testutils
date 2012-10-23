#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


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
                if error.args[0] != errno.EADDRINUSE:
                    raise
                # Collision - reseed so we get as far away from the
                # other process as possible.
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


def findPorts(num=1, closeSockets=True):
    return _portFinder.findPorts(num, closeSockets=closeSockets)


def tryConnect(host, port, count=100, interval=0.1, logFile=None,
               backoff=0.05, maxInterval=1):
    addrs = socket.getaddrinfo(host, port)
    family, socktype, proto, _, sockaddr = addrs[0]
    sock = socket.socket(family, socktype)
    # Setting SO_REUSEADDR lets the kernel recycle dead ports
    # immediately, which is polite since we're making so many connections.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    for n in range(count):
        try:
            sock.connect(sockaddr)
            sock.close()
            return
        except socket.error, error:
            if error.args[0] == errno.ECONNREFUSED:
                i = min(interval + n * backoff,maxInterval)
                time.sleep(i)
                continue
            raise
    if logFile:
        if os.path.exists(logFile):
            print 'logFile contents:\n%s' % open(logFile).read()
        else:
            print 'log file is missing'
    # re-raise the last error
    raise


def getLocalhostIP():
    """
    Return the first IP that 'localhost' resolves to.

    Hopefully that's either 127.0.0.1 or ::1.
    """
    return socket.getaddrinfo('localhost', 0)[0][4][0]
