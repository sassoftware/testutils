#
# Copyright (c) 2010 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

import sys
from twisted.python import reflect
from twisted.python import usage
from twisted.scripts import trial
from twisted.trial import reporter
try:
    from xml.etree import ElementTree as ET
except ImportError:
    from elementtree import ElementTree as ET


def skipTest(reason):
    def decorate(func):
        func.skip = reason
        return func
    return decorate


def todoTest(reason):
    def decorate(func):
        func.todo = reason
        return func
    return decorate


class JUnitReporter(reporter.VerboseTextReporter):

    def __init__(self, *args, **kwargs):
        super(JUnitReporter, self).__init__(*args, **kwargs)
        self.xmlstream = open('junit.xml', 'w')
        print >> self.xmlstream, '<testsuite>'

    def startTest(self, test):
        super(JUnitReporter, self).startTest(test)

        if '.' in test.id():
            classname, testname = test.id().rsplit('.', 1)
        else:
            classname, testname = '', test.id()
        self.et = ET.Element('testcase', {
            'classname': classname,
            'name': testname,
            })
        self.suppress = False

    def stopTest(self, test):
        super(JUnitReporter, self).stopTest(test)

        if not self.suppress:
            self.et.set('time', str(self._lastTime))
        self.xmlstream.write('  ')
        ET.ElementTree(self.et).write(self.xmlstream)
        self.xmlstream.write('\n')

        self.et = None

    def _addTraceback(self, kind, failure):
        ET.SubElement(self.et, kind, {
            'type': reflect.qual(failure.type),
            'message': '',
            }).text = failure.getTraceback()

    def addError(self, test, result):
        super(JUnitReporter, self).addError(test, result)
        self._addTraceback('error', result)

    def addFailure(self, test, result):
        super(JUnitReporter, self).addFailure(test, result)
        self._addTraceback('failure', result)

    def addSkip(self, test, result):
        super(JUnitReporter, self).addSkip(test, result)

        self.suppress = True
        self.et = ET.Comment("%s skipped: %s" % (test.id(), result))

    def addExpectedFailure(self, test, result, todo):
        super(JUnitReporter, self).addExpectedFailure(test, result, todo)

        self.suppress = True
        self.et = ET.Comment("%s expected failure: %s" % (test.id(),
            todo.reason))

    def addUnexpectedSuccess(self, test, result):
        super(JUnitReporter, self).addUnexpectedSuccess(test, result)

        ET.SubElement(self.et, 'failure', {
            'type': 'todo',
            'message': '',
            }).text = (
                    "Unexpected test success\n"
                    "Test is marked as TODO, but succeeded!\n"
                    )

    def _printSummary(self):
        print >> self.xmlstream, '</testsuite>'


def main():
    always_succeed = '--always-succeed' in sys.argv
    if always_succeed:
        sys.argv.remove('--always-succeed')

    # Copypasta from twisted.scripts.trial.run, to tweak the return values
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    config = trial.Options()
    try:
        config.parseOptions()
    except usage.error, ue:
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)
    trial._initialDebugSetup(config)
    trialRunner = trial._makeRunner(config)
    suite = trial._getSuite(config)
    if config['until-failure']:
        test_result = trialRunner.runUntilFailure(suite)
    else:
        test_result = trialRunner.run(suite)
    if config.tracer:
        sys.settrace(None)
        results = config.tracer.results()
        results.write_results(show_missing=1, summary=False,
                              coverdir=config.coverdir)
    # Copypasta ends here
    if always_succeed or test_result.wasSuccessful():
        return 0
    else:
        return 2
