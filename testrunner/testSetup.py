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
    resources.archivePath = os.path.join(resources.testPath, "archive")
    resources.conaryDir = os.environ['CONARY_PATH']
