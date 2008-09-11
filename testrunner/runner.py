#!/usr/bin/python
# -*- mode: python -*-
#
# Copyright (c) 2004-2008 rPath, Inc.
#
import os
import sys
import unittest

import testhelp
from testhelp import context, TestCase, findPorts, SkipTestException


archivePath = None
testPath = None

#from pychecker import checker

conaryDir = None
_setupPath = None
_individual = False

def isIndividual():
    global _individual
    return _individual
testhelp.isIndividual = isIndividual

def setup():
    """
    Setup initializes variables must be initialized before the testsuite
    can be run.  Generally this means setting up and determining paths.
    """
    global _setupPath
    if _setupPath:
        return _setupPath
    pythonSitePackages = os.path.join(
        os.path.dirname(sys.modules['os'].__file__), 'site-packages')

    policyPath = testhelp.getPath('CONARY_POLICY_PATH',
                                  '/usr/lib/conary/policy').split(':')
    for path in policyPath:
        if not os.path.isdir(path):
            print 'CONARY_POLICY_PATH %s does not exist' %path
            sys.exit(1)

    testhelp.insertPath(testhelp.getPath('CONARY_PATH', pythonSitePackages),
                        updatePythonPath=True)

    if isIndividual():
        serverDir = '/tmp/conary-server'
        if os.path.exists(serverDir) and not os.path.access(serverDir, os.W_OK):
            serverDir = serverDir + '-' + pwd.getpwuid(os.getuid())[0]
        os.environ['SERVER_FILE_PATH'] = serverDir

    global testPath
    global archivePath
    global conaryDir
    from testrunner import resources
    resources.testPath = testPath = testhelp.getTestPath()
    resources.conaryDir = conaryDir = os.environ['CONARY_PATH']
    resources.archivePath = archivePath = testhelp.getArchivePath(
                                            os.environ['CONARY_TEST_PATH'])
    if archivePath is None:
        resources.archivePath = archivePath = testhelp.getArchivePath(testPath)

    from conary.lib import util
    sys.excepthook = util.genExcepthook(True, catchSIGUSR1=False)

    testhelp._conaryDir = conaryDir
    _setupPath = path
    return path

def getCoverageDirs(self, environ):
    conaryPath = environ['conary']
    if (conaryPath.endswith('site-packages')
        or conaryPath.endswith('site-packages/')):
        conaryPath = os.path.join(conaryPath, 'conary')
    return conaryPath, environ['policy']

def getCoverageExclusions(self, environ):
    return ['scripts/.*', 'epdb.py', 'stackutil.py']


ConaryTestSuiteHandler = testhelp.getHandlerClass(testhelp.ConaryTestSuite,
                                                  getCoverageDirs,
                                                  getCoverageExclusions)

def main(argv=None, individual=True, handlerClass=ConaryTestSuiteHandler,
         handlerKw={}):
    global _handler
    global _individual
    _individual = individual
    if argv is None:
        argv = list(sys.argv)
    topdir = testhelp.getTestPath()
    if topdir not in sys.path:
        sys.path.insert(0, topdir)
    cwd = os.getcwd()
    if cwd != topdir and cwd not in sys.path:
        sys.path.insert(0, cwd)

    setup()
    from conary.lib import util
    from conary.lib import coveragehook
    sys.excepthook = util.genExcepthook(True, catchSIGUSR1=False)
    kw = dict(individual=individual, topdir=topdir,
              testPath=testPath, conaryDir=conaryDir)
    kw.update(handlerKw)
    handler = handlerClass(**kw)
    print "This process PID:", os.getpid()
    _handler = handler
    results = handler.main(argv)
    if results is None:
        sys.exit(0)
    sys.exit(not results.wasSuccessful())

if __name__ == '__main__':
    main(sys.argv, individual=False)
