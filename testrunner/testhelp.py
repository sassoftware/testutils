import gc
import errno
import fcntl
import gc
import grp
import itertools
import sys
import os
import os.path
import pprint
import pwd
import signal
import socket
import random
import re
import tempfile
import types
import unittest

from testrunner import resources
from testrunner.decorators import context
from testrunner import testhandler
ConaryTestSuite = testhandler.ConaryTestSuite

from testcase import TestCase
from testrunner.output import SkipTestException, DebugTestRunner

from testrunner.testhandler import Loader

global _handler
_handler = None
global _conaryDir
_conaryDir = None

portstart = random.randrange(16000, 30000)
# this blows
if hasattr(os, '_urandomfd'):
    fcntl.fcntl(os._urandomfd, fcntl.F_SETFD, 1)

def findPorts(num = 1, failOnError=False, closeSockets=True):
    global portstart
    if portstart > 31500:
        # Wrap around, hope for the best
        portstart = random.randrange(16000, 30000)
    ports = []
    sockets = []
    for port in xrange(portstart, portstart + 300):
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
                portstart = max(ports) + 1
                if closeSockets:
                    return ports
                else:
                    return zip(ports, sockets)

    if failOnError:
        raise socket.error, "Cannot find open port to run server on"
    else:
        portstart = random.randrange(16000, 30000)
        return findPorts(num, failOnError=True)

# gets a temporary directory that is made only of lowercase letters
# for MySQL's benefit
def getTempDir(prefix):
    while True:
        d = tempfile.mkdtemp(prefix=prefix)
        dl = d.lower()
        try:
            os.mkdir(dl, 0700)
        except OSError, e:
            if e.errno == errno.EEXIST:
                continue # try again
        else:
            os.rmdir(d)
            break
    return dl

def getPath(envName, default=None):
    if envName in os.environ:
        return os.path.realpath(os.environ[envName])
    elif default is None:
        print "please set %s" % envName
        sys.exit(1)
    else:
        os.environ[envName] = default
        return default

def insertPath(path, updatePythonPath=False):
    if path not in sys.path:
        sys.path.insert(0, path)
    if 'PYTHONPATH' in os.environ:
        os.environ['PYTHONPATH'] = os.pathsep.join((path,
                                                   os.environ['PYTHONPATH']))
    else:
        os.environ['PYTHONPATH'] = path

def getConaryDir():
    global _conaryDir
    return _conaryDir

def getTestPath(testsuiteModule = None):
    # By default, use the standard setup
    if testsuiteModule is None:
        testsuiteModule = 'testsuite'
    invokedAs = sys.argv[0]
    if invokedAs.find("/") != -1:
        if invokedAs[0] != "/":
            invokedAs = os.getcwd() + "/" + invokedAs
        path = os.path.dirname(invokedAs)
    else:
        path = os.getcwd()

    testPath = os.path.realpath(path)
    # find the top of the test directory in the full path - this
    # sets the right test path even when testsuite.setup() is called
    # from a testcase in a subdirectory of the testPath
    if sys.modules.has_key(testsuiteModule):
        testPath = os.path.join(testPath, 
                        os.path.dirname(sys.modules[testsuiteModule].__file__))
    return testPath

def getArchivePath(testDir):
    for path in (testDir, os.path.dirname(__file__)):
        path_maybe = os.path.join(path, 'archive')
        if os.path.isdir(path_maybe):
            return path_maybe

    return None


# backwards compatible code
def getHandlerClass(suiteClass_, getCoverageDirsFn, getExcludeDirsFn=None,
                    sortTestsFn=None):
    class GeneratedHandlerClass(TestSuiteHandler):
        suiteClass = suiteClass_
        def sortTests(self, tests):
            if sortTestsFn:
                return sortTestsFn(tests)
            return tests

        def getCoverageDirs(self, environ):
            return getCoverageDirsFn(self, environ)

        def getCoverageExclusions(self, environ):
	    if getExcludeDirsFn:
                return getExcludeDirsFn(self, environ)
	    return []

    return GeneratedHandlerClass


# Backwards compatible testsuite handler.  We should get rid of this.
from testrunner import testhandler
class TestSuiteHandler(testhandler.TestSuiteHandler):

    suiteClass = unittest.TestSuite

    def __init__(self, individual, topdir, conaryDir, testPath):
        global _handler
        global _conaryDir
        _handler = self
        _conaryDir = conaryDir
        cfg = resources.cfg
        cfg.isIndividual = individual
        cfg.cleanTestDirs = not individual
        resources.testPath = testPath
        resources.conaryDir = conaryDir
        testhandler.TestSuiteHandler.__init__(self, cfg, resources, None, self.suiteClass)

    def getCoverageExclusions(self, environ):
        return []

    def getCoverageDirs(self, environ):
        return [os.path.dirname(sys.modules['testsuite'].__file__)]

def main(argv=[], individual=True, handlerClass=TestSuiteHandler):
    from conary.lib import util
    sys.excepthook = util.genExcepthook(True, catchSIGUSR1=False)
    handler = handlerClass(individual=individual, topdir=getTestPath(),
                           testPath=getTestPath(), conaryDir=getConaryDir())
    print "This process PID:", os.getpid()
    results = handler.main(argv)
    if results is None:
        sys.exit(0)
    sys.exit(not results.wasSuccessful())

