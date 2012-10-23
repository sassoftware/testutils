#!/usr/bin/python
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
