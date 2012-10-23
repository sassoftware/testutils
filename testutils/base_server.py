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


from testrunner import testhelp

class BaseServer(object):
    "Base server class. Responsible with setting up the ports etc."
    # We only want standalone repositories to have SSL support added via
    # useSSL
    sslEnabled = False

    def start(self, resetDir = True):
        raise NotImplementedError

    def cleanup(self):
        pass

    def stop(self):
        raise NotImplementedError

    def reset(self):
        pass

    def isStarted(self):
        raise NotImplementedError

    def initPort(self):
        ports = testhelp.findPorts(num = 1, closeSockets=False)[0]
        self.port = ports[0]
        self.socket = ports[1]

    def __del__(self):
        if self.isStarted():
            print 'warning: %r was not stopped before freeing' % self
            try:
                self.stop()
            except:
                print 'warning: could not stop %r in __del__' % self
