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


import grp
import os
import pwd
import subprocess
import sys

# Running user
effectiveUser = os.getuid()
effectiveGroup = os.getgid()
try:
    effectiveUser = pwd.getpwuid(effectiveUser)[0]
    effectiveGroup = grp.getgrgid(effectiveGroup)[0]
except KeyError:
    effectiveUser = str(effectiveUser)
    effectiveGroup = str(effectiveGroup)

def listSemaphores():
    p = subprocess.Popen(["/usr/bin/ipcs", "-s", "-c"],
                         stdout = subprocess.PIPE)
    semIds = set()
    for line in p.stdout:
        line = [x for x in line.split() if x]
        if not line or not line[0].isdigit():
            continue
        if line[2] != effectiveUser:
            continue
        semIds.add(line[0])
    return semIds

# catch subprocess exec errors and be more informative about them
def osExec(args):
    try:
        os.execv(args[0], args)
        os._exit(1)
    except OSError:
        sys.stderr.write("\nERROR:\nCould not exec: %s\n" % (args,))
    # if we reach here, it's an error anyway
    os._exit(-1)
