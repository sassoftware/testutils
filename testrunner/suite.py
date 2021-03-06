#!/usr/bin/python
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


import inspect
import os
import sys
import unittest

class TestSuite(object):
    individual = False
    testsuite_module = None
    # Number of directories to strip off from testsuite.py's filename in order
    # to get to the testsuite's top level
    topLevelStrip = 0
    catchSIGUSR1 = True

    suiteClass = unittest.TestSuite

    setupDone = False

    execPathVarNames = []
    resourceVarNames = []

    def setup(self):
        if self.setupDone:
            return
        self.setupTestDir()
        self.setupDefaultVars()
        self.setupPaths()
        self.setupModules()
        self.setupCoverageHooks()
        self.setupSpecific()

        self.setupDone = True

    def setupDefaultVars(self):
        pass

    def setupTestDir(self):
        self.testPath = self.getTestTopDir()
        os.environ['TEST_PATH'] = self.testPath

    def setupModules(self):
        from testrunner.testhelp import context, TestCase, findPorts, SkipTestException
        self.testsuite_module.context = context
        self.testsuite_module.TestCase = TestCase
        self.testsuite_module.findPorts = findPorts
        self.testsuite_module.SkipTestException = SkipTestException

    def setupCoverageHooks(self):
        from conary.lib import util
        sys.excepthook = util.genExcepthook(True,
            catchSIGUSR1 = self.catchSIGUSR1)

        # Coverage hooks
        from conary.lib import coveragehook

    def setupPaths(self):
        pass

    def setupSpecific(self):
        pass

    def getTestTopDir(self):
        dname = os.path.realpath(os.path.dirname(self.testsuite_module.__file__))
        if self.topLevelStrip:
            return os.sep.join(dname.split(os.sep)[:-self.topLevelStrip])
        else:
            return dname

    def sortTests(self, tests):
        return tests

    def sortTestsByType(self, tests, bucketOrder = None):
        if bucketOrder is None:
            bucketOrder = [ 'smoketest', 'unit_test', 'functionaltest' ]
        else:
            bucketOrder = bucketOrder[:]
        # Everything else
        bucketOrder.append(None) 
        buckets = dict((x, []) for x in bucketOrder)

        for test in tests:
            # Try to extract the bucket name
            bucketName = test.split('.')[1 - self.topLevelStrip]
            l = buckets.get(bucketName, buckets[None])
            l.append(test)
        tests = []
        for bucketName in bucketOrder:
            tests.extend(sorted(buckets[bucketName]))
        return tests

    def getCoverageDirs(self, handler, environ):
        return [self.testsuite_module]

    def getCoverageExclusions(self, handler, environ):
        return None

    def main(self, argv = None, individual = True):
        self.__class__.individual = individual
        self.setup()
        from testrunner import testhelp

        class Handler(testhelp.TestSuiteHandler):
            suiteClass = self.__class__.suiteClass
            def getCoverageDirs(slf, environ):
                dirs = self.getCoverageDirs(slf, environ)
                for n, dirname in enumerate(dirs):
                    if inspect.ismodule(dirname):
                        dirname = os.path.dirname(dirname.__file__)
                    dirs[n] = os.path.abspath(dirname)
                return dirs

            def getCoverageExclusions(slf, environ):
                excl = self.getCoverageExclusions(slf, environ)
                if excl is None:
                    excl = testhelp.TestSuiteHandler.getCoverageExclusions(slf,
                            environ)
                return excl

            def sortTests(slf, tests):
                return self.sortTests(tests)

        handler = Handler(individual=individual, testPath=self.testPath)

        if argv is None:
            argv = list(sys.argv)
        results = handler.main(argv)
        return results.getExitCode()

    def run(self):
        sys.exit(self.main(sys.argv, individual = False))
