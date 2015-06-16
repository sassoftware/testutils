#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import gc
import errno
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
import re
import tempfile
import types
import unittest

from testrunner.decorators import context
from testrunner import testhandler

ConaryTestSuite = testhandler.ConaryTestSuite

from testcase import TestCase, todo
from testrunner.output import SkipTestException, DebugTestRunner

from testrunner.testhandler import Loader
from testutils import sock_utils

# Every module uses findPorts from here
findPorts = sock_utils.findPorts

global _handler
_handler = None
global _conaryDir
_conaryDir = None

# gets a temporary directory that is made only of lowercase letters
# for MySQL's benefit
def getTempDir(prefix, dir=None):
    while True:
        oldPath = tempfile.mkdtemp(prefix=prefix, dir=dir)
        oldDir, oldName = os.path.split(oldPath)
        newName = oldName.lower()
        newPath = os.path.join(oldDir, newName)
        try:
            os.rename(oldPath, newPath)
        except OSError, err:
            if err.args[0] == errno.EEXIST:
                # try again
                os.rmdir(oldPath)
                continue
            raise
        else:
            return newPath

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


class TestSuiteHandler(testhandler.TestSuiteHandler):

    suiteClass = unittest.TestSuite

    def __init__(self, individual, testPath=None,
            # DEPRECATED:
            topdir=None, conaryDir=None):

        global _handler
        _handler = self
        class CFG:
            pass
        cfg = CFG()
        cfg.isIndividual = individual
        cfg.cleanTestDirs = not individual
        cfg.testPath = testPath
        testhandler.TestSuiteHandler.__init__(self, cfg, None, self.suiteClass)

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
