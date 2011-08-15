#
# Copyright (c) rPath, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
