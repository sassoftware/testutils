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
