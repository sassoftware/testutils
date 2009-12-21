#!/usr/bin/python
#
# Copyright (c) 2009 rPath, Inc.  All Rights Reserved.
#

import os
import sys
import unittest

class TestSuite(object):
    individual = False
    pathManager = None
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
        if self.pathManager is None:
            from testrunner import pathManager
            self.__class__.pathManager = pathManager

        self.setupTestDir()
        self.setupDefaultVars()
        self.setupPaths()
        self.setupModules()
        self.setupCoverageHooks()
        self.setupSpecific()

        self.setupDone = True

    def setupDefaultVars(self):
        for varname in self.execPathVarNames:
            self.pathManager.addExecPath(varname)
        for varname in self.resourceVarNames:
            self.pathManager.addResourcePath(varname)

    def setupTestDir(self):
        testPath = self.getTestTopDir()
        self.pathManager.addExecPath('TEST_PATH', testPath)

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

    def main(self, argv = None, individual = True):
        self.__class__.individual = individual
        self.setup()
        from testrunner import testhelp

        testPath = os.getenv('TEST_PATH')

        class Handler(testhelp.TestSuiteHandler):
            suiteClass = self.__class__.suiteClass
            def getCoverageDirs(slf, environ):
                if hasattr(self, 'getCoverageDirs'):
                    return self.getCoverageDirs(slf, environ)
                return [ os.path.dirname(self.testsuite_module.__file__) ]

            def getCoverageExclusions(slf, environ):
                if hasattr(self, 'getCoverageExclusions'):
                    return self.getCoverageExclusions(slf, environ)
                return testhelp.TestSuiteHandler.getCoverageExclusions(slf, environ)
            def sortTests(slf, tests):
                return self.sortTests(tests)

        handler = Handler(individual=individual)

        if argv is None:
            argv = list(sys.argv)
        results = handler.main(argv)
        return results.getExitCode()

    def run(self):
        sys.exit(self.main(sys.argv, individual = False))
