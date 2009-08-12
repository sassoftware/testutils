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
