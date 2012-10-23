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
from testrunner.output import SkipTestException

# Marker decorators
def tests(*issues):
    '''
    Marks a function as testing one or more issues.
    If the referenced issue is a feature, the test verifies that the
    implementation is valid.
    If the issue is a bug, the test confirms that the fix is complete. The
    test should fail against the previous code, and pass with the new code.
    Note that this decorator doesn't actually do anything useful yet, it's
    just a marker.

    Example:
    @testsuite.tests('FOO-123', 'BAR-456')
    def testPonies(self):
        ...
    '''
    def decorate(func):
        func.meta_tests = issues
        return func
    return decorate

def context(*contexts):
    def deco(func):
        # no wrapper is needed, nor usable.
        if '_contexts' in func.__dict__:
            func._contexts.extend(contexts)
        else:
            func._contexts = list(contexts)
        return func
    return deco

def requireBinary(name):
    def deco(f):
        def testfunc(*args):
            # testsuite shouldn't import conary.lib.util/checkPath()
            # so we kind of duplicate here
            for path in os.environ.get("PATH", "").split(os.pathsep):
                if os.access(os.path.join(path, name), os.X_OK):
                    return f(*args)
            raise SkipTestException("could not find binary %s" %name)
        testfunc.__name__ = f.__name__
        return testfunc
    return deco
