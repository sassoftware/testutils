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
