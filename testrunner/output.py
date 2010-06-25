import bdb
import cPickle
import fcntl
import os
import re
import sys
import time
import traceback
import inspect
import unittest

class TestTimer(object):
    def __init__(self, file, testSuite):
        self.startAll = time.time()
        if os.path.exists(file):
            try:
                self.times = cPickle.load(open(file))
            except Exception, msg:
                print "error loading test times:", msg
                self.times = {}
        else:
            self.times = {}
        self.file = os.path.abspath(file)

        self.toRun = set()
        testSuites = [testSuite]
        while testSuites:
            testSuite = testSuites.pop()
            if not isinstance(testSuite, unittest.TestCase):
                testSuites.extend(x for x in testSuite) 
            else:
                self.toRun.add(testSuite.id())

    def printTimes(self):
        times = list(sorted(self.times.iteritems(), key=lambda x: x[1][0]))
        maxLen = max(len(x[0]) for x in times)
        for testName, (time, numRuns) in times:
            if testName.split('.', 1)[0] == '__main__':
                continue
            time = '%.2fs' % time
            print "%-*s%-10s(%s runs)"  % (maxLen, testName, time, numRuns)

    def startTest(self, test):
        self.testStart = time.time()
        self.testId = test.id()

    def stopTest(self, test):
        id = self.testId
        self.toRun.discard(id)

    def testPassed(self):
        id = self.testId
        thisTime = time.time() - self.testStart
        avg, times = self.times.get(id, [0, 0])
        avg = ((avg * times) + thisTime) / (times + 1.0)
        times = min(times+1, 3)
        self.times[id] = [avg, times]
        self.store(self.file)

    def estimate(self):
        left =  sum(max(0, self.times.get(x, [1])[0]) for x in self.toRun)
        passed = time.time() - self.startAll
        return  passed, passed + left

    def store(self, file):
        cPickle.dump(self.times, open(file, 'w'))


class TestCallback:

    def _message(self, msg):
        if self.oneLine:
            self.out.write("\r")
            self.out.write(msg)
            if len(msg) < self.last:
                i = self.last - len(msg)
                self.out.write(" " * i + "\b" * i)
            self.out.flush()
            self.last = len(msg)
        else:
            self.out.write(msg)
            self.out.write('\n')
            self.out.flush()

    def __del__(self):
        if self.last and self.oneLine:
            self._message("")
            print "\r",
            self.out.flush()

    def clear(self):
        if self.oneLine:
            self._message("")
            print "\r",

    def __init__(self, f = sys.stdout, oneLine = True):
        self.oneLine = oneLine
        self.last = 0
        self.out = f

    def totals(self, run, passed, failed, errored, skipped, total, 
               timePassed, estTotal, test=None):
        totals = (failed +  errored, skipped, timePassed / 60, 
                  timePassed % 60, estTotal / 60, estTotal % 60, run, total)
        msg = 'Fail: %s Skip: %s - %0d:%02d/%0d:%02d - %s/%s' % totals

        if test:
            # append end of test to message
            id = test.id()
            if self.oneLine:
                cutoff = max((len(id) + len(msg)) - 76, 0)
            else:
                cutoff = 0
            msg = msg + ' - ' + id[cutoff:]

        if test or self.oneLine:
            self._message(msg)

class SkipTestException(Exception):
    def __init__(self, msg=''):
        self.msg = msg

class SkipTestResultMixin:
    def __init__(self):
        self.skipped = []

    def checkForSkipException(self, test, err):
        # because of the reloading of modules that occurs when
        # running multiple tests, no guarantee about the relation of
        # this SkipTestException class to the one run in the 
        # actual test can be made, so just check names
        if err[0].__name__ == 'SkipTestException':
            self.addSkipped(test, err)
            return True

    def addSkipped(self, test, err):
        self.skipped.append(test)

    def __repr__(self):
        return ("<%s run=%i errors=%i failures=%i skipped=%i>" %
                (unittest._strclass(self.__class__), self.testsRun,
                 len(self.errors), len(self.failures),
                 len(self.skipped)))



class SkipTestTextResult(unittest._TextTestResult, SkipTestResultMixin):

    def __init__(self, *args, **kw):
        self.passedTests = 0
        self.failedTests = 0
        self.erroredTests = 0
        self.skippedTests = 0

        self.alwaysSucceed = kw.pop('alwaysSucceed', False)
        self.debug = kw.pop('debug', False)
        self.useCallback = kw.pop('useCallback', True)
        self.xml_stream = kw.pop('xml_stream', None)

        test = kw.pop('test')
        self.total = test.countTestCases()

        oneLine = kw.pop('oneLine', False)
        self.callback = TestCallback(oneLine=oneLine)

        unittest._TextTestResult.__init__(self, *args, **kw)
        SkipTestResultMixin.__init__(self)

        self.timer = TestTimer('.times', test)
        self.stderr = os.fdopen(os.dup(sys.stderr.fileno()), 'w', 0)
        fcntl.fcntl(self.stderr.fileno(), fcntl.F_SETFD, 1)

    def post_mortem(self, err):
        from conary.lib import debugger
        debugger.post_mortem(err[2], err[1], err[0])

    def addSkipped(self, test, err):
        self.skippedTests += 1
        SkipTestResultMixin.addSkipped(self, test, err)
        if self.useCallback:
            self.callback.clear()
            if err[1].msg:
                msg = '(%s)' % (err[1].msg, )
            else:
                msg = ''
            print 'SKIPPED:', test.id(), msg

        self.doXmlOutput('skip', test, err)

    def addError(self, test, err):
        if isinstance(err[1], bdb.BdbQuit):
            raise KeyboardInterrupt

        if self.checkForSkipException(test, err):
            return

        unittest.TestResult.addError(self, test, err)
        if self.useCallback:
            self.callback.clear()
        else:
            print
        desc = self._exc_info_to_string(err, test)
        self.printErrorList('ERROR', [(test, desc)])

        if self.debug:
            self.post_mortem(err)

        self.erroredTests += 1

        self.doXmlOutput('error', test, err)

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if self.useCallback:
            self.callback.clear()
        else:
            print
        desc = self._exc_info_to_string(err, test)
        self.printErrorList('FAILURE', [(test, desc)])

        if self.debug:
            self.post_mortem(err)

        self.failedTests += 1

        self.doXmlOutput('failure', test, err)

    def addSuccess(self, test):
        self.timer.testPassed()
        self.passedTests += 1

        if not self.useCallback:
            unittest._TextTestResult.addSuccess(self, test)

        self.doXmlOutput('success', test)

    def startTest(self, test):
        unittest._TextTestResult.startTest(self, test)
        self.timer.startTest(test)
        self.printTotals(test)

    def stopTest(self, test):
        unittest._TextTestResult.stopTest(self, test)
        self.timer.stopTest(test)
        self.printTotals()

    def printTotals(self, test=None):
        if self.useCallback:
            timePassed, totalTime = self.timer.estimate()
            self.callback.totals(self.testsRun, self.passedTests,
                                 self.failedTests,
                                 self.erroredTests, self.skippedTests, 
                                 self.total, timePassed, totalTime, test)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stderr.write(self.separator1)
            self.stderr.write('\n')
            self.stderr.write("%s: %s" % (flavour,self.getDescription(test)))
            self.stderr.write('\n')
            self.stderr.write(self.separator2)
            self.stderr.write('\n')
            self.stderr.write(str(err))
            self.stderr.write('\n')

    def doXmlOutput(self, flavor, test, err=None):
        if not self.xml_stream:
            return

        className, testName = test.id().rsplit('.', 1)
        className = className.replace('__main__.', '')

        if self.xml_stream['prefix']:
            className = self.xml_stream['prefix'] + '.' + className

        if err:
            ferr = err[0]
            if inspect.isclass(ferr):
                exceptionName = ferr.__name__
            else:
                exceptionName = ferr
        else:
            exceptionName = ''

        if flavor == 'success':
            print >>self.xml_stream['file'], \
                '  <testcase classname="%s" name="%s" time="%.03f" />' \
                % (className, testName, time.time() - self.timer.testStart)
        elif flavor == 'skip':
            if err[1].msg:
                msg = str(err[1].msg)
            else:
                msg = ''

            msg = re.sub('-+', '-', msg)

            print >>self.xml_stream['file'], \
                '  <!-- SKIPPED: %s (%s) -->' % (test.id(), msg)
        else:
            tb = ''.join(traceback.format_exception(*err))
            # Separate right closing brackets since this will break CDATA
            tb = re.sub(r'\](?=\])', '] ', tb)

            self.xml_stream['file'].write( '''
  <testcase classname="%(className)s" name="%(testName)s" time="%(time).03f">
    <%(flavor)s type="%(exceptionName)s" message="">
      <![CDATA[%(traceback)s]]>
    </%(flavor)s>
  </testcase>
''' % dict(className=className, testName=testName, exceptionName=exceptionName,
                time=(time.time() - self.timer.testStart), flavor=flavor,
                traceback=tb))

        self.xml_stream['file'].flush()

    def getExitCode(self):
        if self.alwaysSucceed or self.wasSuccessful():
            return 0
        else:
            return 16


class DebugTestRunner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        self.debug = kwargs.pop('debug', False)
        self.useCallback = kwargs.pop('useCallback', False)
        self.oneLine = kwargs.pop('oneLine', True)
        self.xml_stream = kwargs.pop('xml_stream', None)
        self.alwaysSucceed = kwargs.pop('alwaysSucceed')
        if self.oneLine or self.useCallback:
            kwargs['verbosity'] = 0
        else:
            kwargs['verbosity'] = 1
        unittest.TextTestRunner.__init__(self, *args, **kwargs)

    def getTimes(self, test):
        self.test = test
        result = self._makeResult()
        return result.timer

    def run(self, test):
        self.test = test
        result = self._makeResult()

        if self.xml_stream:
            print >>self.xml_stream['file'], '<testsuite>'

        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime

        self.stream.writeln('\n' + result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run != 1 and "s" or "", timeTaken))

        if self.xml_stream:
            print >>self.xml_stream['file'], '</testsuite>'

        return result

    def _makeResult(self):
        return SkipTestTextResult(self.stream, self.descriptions,
                self.verbosity, test=self.test, debug=self.debug,
                useCallback=self.useCallback, oneLine=self.oneLine,
                xml_stream=self.xml_stream, alwaysSucceed=self.alwaysSucceed)
