#!/usr/bin/python
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
