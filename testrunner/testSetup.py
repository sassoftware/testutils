#!/usr/bin/python
# -*- mode: python -*-
#
# Copyright (c) 2004-2008 rPath, Inc.
#

import os

import testhelp
from testrunner import resources

def setup():
    setupResources()

def setupResources():
    resources.testPath = testhelp.getTestPath("testsuite")
    if 'CONARY_TEST_PATH' in os.environ:
        resources.archivePath = os.environ.get('CONARY_TEST_PATH') + '/archive'
    else:
        resources.archivePath = resources.testPath + '/archive'
    resources.conaryDir = os.environ['CONARY_PATH']
