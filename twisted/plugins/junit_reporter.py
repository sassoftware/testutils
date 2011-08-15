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


from twisted.plugin import IPlugin
from twisted.trial.itrial import IReporter
from zope.interface import implements


class _JUnitReporter(object):
    implements(IPlugin, IReporter)

    name = "JUnit Reporter"
    description = "JUnit XML output for trial"
    module = "testrunner.trial"
    klass = "JUnitReporter"
    longOpt = "junit"
    shortOpt = "j"


JUnitReporter = _JUnitReporter()
