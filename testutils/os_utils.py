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
