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


import collections
import errno
import fcntl
import gc
import grp
import re
import sys
import os
import pprint
import pwd
import tempfile
import types
import unittest
from testrunner.output import SkipTestException
from testutils import mock
from testutils import os_utils


try:
    from unittest.util import safe_repr as _safe_repr
    safe_repr = _safe_repr
except ImportError:
    safe_repr = repr


class LogFilter:
    def __init__(self):
        self.records = []
        self.ignorelist = []

    def clear(self):
        from conary.lib import log
        self.records = []
        self.ignorelist = []
        log.logger.removeFilter(self)

    def filter(self, record):
        from conary.lib import log
        text = log.formatter.format(record)
        for regex in self.ignorelist:
            if regex.match(text):
                return False
        self.records.append(text)
        return False

    def ignore(self, regexp):
        self.ignorelist.append(re.compile(regexp))

    def add(self):
        from conary.lib import log
        log.logger.addFilter(self)

    def remove(self):
        from conary.lib import log
        log.logger.removeFilter(self)

    def compareWithOrder(self, records):
        """
        compares stored log messages against a sequence of messages and
        resets the filter
        """
        if self.records == None or self.records == []:
            if records:
                raise AssertionError, "expected log messages, none found"
            return
        if type(records) is str:
            records = (records,)

        if len(records) != len(self.records):
            raise AssertionError, "expected log message count does not match"

        for num, record in enumerate(records):
            if self.records[num] != record:
                raise AssertionError, "expected log messages do not match: '%s' != '%s'" %(self.records[num], record)
        self.records = []

    def _compare(self, desiredList, cmpFn, allowMissing = False,
                 originalRecords = None):
        """
        compares stored log messages against a sequence of messages and
        resets the filter.  order does not matter.
        """
        if self.records == None or self.records == []:
            if desiredList:
                raise AssertionError, "Did not receive any log messages when expecting %s" % (desiredList,)
            return

        if originalRecords is None:
            originalRecords = desiredList

        if not allowMissing and len(desiredList) != len(self.records):
            raise AssertionError, "expected log message count does not match: desired / expected:\n%s\n%s" %(
                pprint.pformat(desiredList, width=1),
                pprint.pformat(self.records, width=1))

        matched = [ False ] * len(self.records)
        for j, desired in enumerate(desiredList):
            match = False
            for i, record in enumerate(self.records):
                if cmpFn(record, desired):
                    match = True
                    matched[i] = True

            if not match:
                raise AssertionError, \
                        "expected log message not found: '%s'; got '%s'" % (originalRecords[j], record)

        if not allowMissing and False in matched:
            record = self.records[matched.index(False)]
            raise AssertionError, "unexpected log message found: '%s'" %record

        self.records = []

    def compare(self, records, allowMissing = False):
        if type(records) is str:
            records = (records,)

        return self._compare(records, lambda actual, desired: actual == desired,
                             allowMissing = allowMissing)

    def regexpCompare(self, records):
        if type(records) is str:
            records = (records,)

        regexps = records
        return self._compare(regexps,
                 lambda actual, regexp: re.match(regexp, actual) is not None,
                 originalRecords = records)

class MockMixIn(object):
    def mock(self, parent, selector, replacement):
        if not hasattr(self, 'mockObjects'):
            self.mockObjects = []
        # Extract the current value
        if not hasattr(parent, selector):
            # No current value
            currval = (None, True)
        elif isinstance(parent, (type, types.ClassType)):
            # If this is a class, we need to be careful when we mock, since we
            # could mock a parent's object
            import inspect
            defClasses = [ (x[2], x[3], x[1])
                for x in inspect.classify_class_attrs(parent)
                if x[0] == selector ]
            # We've just extracted the class that defined the attribute and
            # the real value
            if defClasses[0][2] == 'static method':
                replacement = staticmethod(replacement)
            if defClasses[0][2] == 'class method':
                replacement = classmethod(replacement)
            if defClasses[0][0] != parent:
                # We inherited this object from the parent
                currval = (None, True)
            else:
                currval = (defClasses[0][1], False)
        else:
            currval = (getattr(parent, selector), False)
        self.mockObjects.append((parent, selector, currval))
        setattr(parent, selector, replacement)

    def unmock(self):
        if not hasattr(self, 'mockObjects'):
            return
        while self.mockObjects:
            parent, selector, (oldval, missing) = self.mockObjects.pop()
            if missing:
                delattr(parent, selector)
            else:
                setattr(parent, selector, oldval)

class TestCase(unittest.TestCase, MockMixIn):
    TIMEZONE = 'Pacific/Fiji'

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        self.logFilter = LogFilter()
        self.owner = os_utils.effectiveUser
        self.group = os_utils.effectiveGroup

        import testrunner.pathManager
        self.mockObjects = []
        self.openFds = set()

    def setUp(self):
        from conary.lib import log
        self._logLevel = log.getVerbosity()

        # Set the timezone to something consistent
        os.environ['TZ'] = self.TIMEZONE
        import time; time.tzset()
        import _strptime
        # Reset strptime's internal cache too
        try:
            _strptime._cache_lock.acquire()
            _strptime._TimeRE_cache.__init__(_strptime.LocaleTime())
        finally:
            _strptime._cache_lock.release()

        # save the original stdio fds for later
        self.savedStdin = sys.stdin
        self.savedStdout = sys.stdout
        self.savedStderr = sys.stderr

    def tearDown(self):
        from conary.lib import log
        log.setVerbosity(self._logLevel)

        # reattached the original stdio fds after the test has completed
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass
        sys.stdin = self.savedStdin
        sys.stdout = self.savedStdout
        sys.stderr = self.savedStderr


    def _expectedFdLeak(self, fd):
        if not hasattr(self, 'openFds'):
            self.openFds = set()

        contents = os.readlink('/proc/%d/fd/%d' % (os.getpid(), fd))
        self.openFds.add((fd, contents))

    @staticmethod
    def _openFdSet():
        fdPath ='/proc/%s/fd' % os.getpid()
        s = set()
        for fd in os.listdir(fdPath):
            try:
                contents = os.readlink(fdPath + '/' + fd)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    # listdir on /proc/*/fd finds the directory
                    # for the directory itself and reports it, but
                    # listdir cleans that up itself
                    contents = None
                else:
                    contents = 'unknown'

            if contents:
                s.add((fd, contents))

        return s

    def run(self, *args, **kw):
        from conary.lib import util
        fdCount = util.countOpenFileDescriptors()
        if fdCount != len(self.openFds):
            self.openFds = self._openFdSet()

        prePid = os.getpid()

        try:
            unittest.TestCase.run(self, *args, **kw)
        finally:
            # Make sure some test didn't accidentally fork the
            # testsuite.
            postPid = os.getpid()
            if prePid != postPid:
                sys.stderr.write("\n*** CHILD RE-ENTERED TESTSUITE ***\n")
                sys.stderr.write("A forked process was allowed to return to "
                    "the testsuite handler, probably due\nto an exception. "
                    "Find it and kill it!\n")
                sys.stderr.write("PID was: %d  now: %d\n" % (prePid, postPid))
                os._exit(2)

            self.unmock()
            mock.unmockAll()

            # ask gc to run to see if we can avoid "leaked -1 file descriptors"
            gc.collect()
            fdCount = util.countOpenFileDescriptors()
            if False and fdCount != len(self.openFds):
                try:
                    methodName = self.__testMethodName
                except AttributeError:
                    methodName = self._testMethodName
                sys.stderr.write("\nTest %s.%s leaked %s file descriptors\n"
                    % (self.__module__, methodName,
                        fdCount - len(self.openFds)))
                newOpenFds = self._openFdSet()
                for (fd, contents) in newOpenFds - self.openFds:
                    if contents and ((fd, contents) not in self.openFds):
                        print '%s: %s' % (fd, contents)
                self.openFds = newOpenFds

    def writeFile(self, path, contents, mode = None):
        if os.path.exists(path):
            mtime = os.stat(path).st_mtime
        else:
            mtime = None

        f = open(path, "w")
        f.write(contents)
        f.close()

        if mtime:
            os.utime(path, (mtime, mtime))

        if mode is not None:
            os.chmod(path, mode)

    def compareFileContents(self, path1, path2):
        f1 = open(path1)
        f2 = open(path2)
        while 1:
            buf1 = f1.read(1024 * 128)
            buf2 = f2.read(1024 * 128)
            if not buf1 and not buf2:
                return True
            if buf1 != buf2:
                return False

    def compareFileModes(self, path1, path2):
        sb1 = os.lstat(path1)
        sb2 = os.lstat(path2)
        return sb1.st_mode == sb2.st_mode

    def captureOutput(self, func, *args, **kwargs):
        returnException = kwargs.pop('_returnException', False)
        printOnError = kwargs.pop('_printOnError', False)
        removeBrokenPipeErrors = kwargs.pop('_removeBokenPipeErrors', False)
        if os.getenv('NO_CAPTURE'):
            return func(*args, **kwargs), ''

        sys.stdout.flush()
        sys.stderr.flush()
        (outfd, outfn) = tempfile.mkstemp()
        os.unlink(outfn)
        (errfd, errfn) = tempfile.mkstemp()
        os.unlink(errfn)
        stdout = os.dup(sys.stdout.fileno())
        stderr = os.dup(sys.stderr.fileno())
        os.dup2(outfd, sys.stdout.fileno())
        os.dup2(errfd, sys.stderr.fileno())
        fcntl.fcntl(stdout, fcntl.F_SETFD, 1)
        fcntl.fcntl(stderr, fcntl.F_SETFD, 1)
        e = None
        try:
            try:
                ret = func(*args, **kwargs)
            except Exception, e:
                exc_info = sys.exc_info()
                pass
        finally:
            sys.stderr.flush()
            sys.stdout.flush()
            os.dup2(stdout, sys.stdout.fileno())
            os.close(stdout)
            os.dup2(stderr, sys.stderr.fileno())
            os.close(stderr)

        if e and not returnException and not printOnError:
            os.close(outfd)
            os.close(errfd)
            raise exc_info[0], exc_info[1], exc_info[2]

        # rewind and read in what was captured
        os.lseek(outfd, 0, 0)
        f = os.fdopen(outfd, 'r')
        sout = f.read()
        # this closes the underlying fd
        f.close()
        # no do stderr
        os.lseek(errfd, 0, 0)
        f = os.fdopen(errfd, 'r')
        serr = f.read()
        f.close()

        if e and printOnError:
            print
            print 'BEGIN STDOUT'
            sys.stdout.write(sout)
            print
            print 'BEGIN STDERR'
            sys.stderr.write(serr)
            print
            raise exc_info[0], exc_info[1], exc_info[2]

        if removeBrokenPipeErrors:
            sout = '\n'.join([x for x in sout.split('\n') if x !=
                           'error: [Errno 32] Broken pipe'])
            serr = '\n'.join([x for x in serr.split('\n') if x !=
                           'error: [Errno 32] Broken pipe'])

        if e:
            return (e, sout + serr)
        else:
            return (ret, sout + serr)

    def discardOutput(self, func, *args, **kwargs):
        if os.getenv('NO_CAPTURE'):
            return func(*args, **kwargs)

        sys.stdout.flush()
        stdout = os.dup(sys.stdout.fileno())
        stderr = os.dup(sys.stderr.fileno())
        null = os.open('/dev/null', os.W_OK)
        os.dup2(null, sys.stdout.fileno())
        os.dup2(null, sys.stderr.fileno())
        os.close(null)
        try:
            ret = func(*args, **kwargs)
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os.dup2(stdout, sys.stdout.fileno())
            os.close(stdout)
            os.dup2(stderr, sys.stderr.fileno())
            os.close(stderr)

        return ret

    def logCheck2(self, records, fn, *args, **kwargs):
        from conary.lib import log
        regExp = kwargs.pop('logRegExp', False)
        verbosity = kwargs.pop('verbosity', log.WARNING)
        return self.logCheck(fn, args, records, kwargs, regExp=regExp,
                             verbosity = verbosity)

    def logCheck(self, fn, args, records, kwargs={}, regExp = False,
                 verbosity = None):
        from conary.lib import log
        self.logFilter.add()
        if verbosity != None:
            log.setVerbosity(verbosity)
        rc = fn(*args, **kwargs)
        try:
            if regExp:
                self.logFilter.regexpCompare(records)
            else:
                self.logFilter.compare(records)
        finally:
            self.logFilter.remove()
        return rc

    def mimicRoot(self):
        from conary.lib import util

        self.oldgetuid = os.getuid
        self.oldmknod = os.mknod
        self.oldlchown = os.lchown
        self.oldchown = os.chown
        self.oldchmod = os.chmod
        self.oldchroot = os.chroot
        self.oldexecl = os.execl
        self.oldexecve = os.execve
        self.oldMassCloseFDs = util.massCloseFileDescriptors
        self.oldutime = os.utime
        os.getuid = lambda : 0
        os.mknod = self.ourMknod
        os.lchown = self.ourChown
        os.chown = self.ourChown
        os.chmod = self.ourChmod
        os.chroot = self.ourChroot
        os.execl = self.ourExecl
        os.execve = self.ourExecve
        util.massCloseFileDescriptors = lambda x, y: 0
        os.utime = lambda x, y: 0
        self.thisRoot = ''
        self.chownLog = []
        self.chmodLog = []
        self.mknodLog = []

    def ourChroot(self, *args):
        self.thisRoot = os.sep.join((self.thisRoot, args[0]))

    def ourExecl(self, *args):
        args = list(args)
        args[0:1] = [os.sep.join((self.thisRoot, args[0]))]
        self.oldexecl(*args)

    def ourExecve(self, *args):
        args = list(args)
        args[0:1] = [os.sep.join((self.thisRoot, args[0]))]
        self.oldexecve(*args)

    def ourChown(self, *args):
        self.chownLog.append(args)

    def ourMknod(self, *args):
        self.mknodLog.append(args)

    def ourChmod(self, *args):
        # we cannot chmod a file that doesn't exist (like a device node)
        # try the chmod for files that do exist
        self.chmodLog.append(args)
        try:
            self.oldchmod(*args)
        except:
            pass

    def realRoot(self):
        from conary.lib import util

        os.getuid = self.oldgetuid
        os.mknod = self.oldmknod
        os.lchown = self.oldlchown
        os.chown = self.oldchown
        os.chmod = self.oldchmod
        os.chroot = self.oldchroot
        os.execl = self.oldexecl
        os.execve = self.oldexecve
        os.utime = self.oldutime
        util.massCloseFileDescriptors = self.oldMassCloseFDs
        self.chownLog = []

    def findUnknownIds(self):
        uid = 0
        for x in range(600, 65535, 2):
            try:
                pwd.getpwuid(x)
            except KeyError:
                uid = x
                break
        if uid == 0:
            raise RuntimeError('Unable to find unused uid')
        gid = 0
        for x in range(601, 65535, 2):
            try:
                grp.getgrgid(x)
            except KeyError:
                gid = x
                break
        if gid == 0:
            raise RuntimeError('Unable to find unused gid')
        return uid, gid

    if hasattr(unittest.TestCase, 'assertIn'):
        failUnlessContains = unittest.TestCase.assertIn
    else:
        def assertIn(self, member, container, msg=None):
            """Just like self.assertTrue(a in b), but with a nicer default message."""
            if member not in container:
                standardMsg = '%s not found in %s' % (safe_repr(member),
                                                      safe_repr(container))
                self.fail(msg or standardMsg)
        failUnlessContains = assertIn

        def assertNotIn(self, member, container, msg=None):
            """Just like self.assertTrue(a not in b), but with a nicer default message."""
            if member in container:
                standardMsg = '%s unexpectedly found in %s' % (safe_repr(member),
                                                            safe_repr(container))
                self.fail(msg or standardMsg)

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        # Override so that the exception is returned. But also try to pass
        # through the context manager feature added in Python 2.7
        if callableObj is None:
            return unittest.TestCase.assertRaises(self, excClass, callableObj,
                    *args, **kwargs)
        try:
            callableObj(*args, **kwargs)
        except excClass, err:
            return err
        else:
            try:
                exc_name = excClass.__name__
            except AttributeError:
                exc_name = str(excClass)
            raise self.failureException("%s not raised" % exc_name)
    failUnlessRaises = assertRaises

    def assertRaisesRegexp(self, expected_exception, expected_regexp,
            callable_obj=None, *args, **kwargs):
        if callable_obj is None:
            return unittest.TestCase.assertRaisesRegexp(self,
                    expected_exception, expected_regexp, callable_obj, *args,
                    **kwargs)
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        exc_value = self.assertRaises(expected_exception, callable_obj, *args,
                **kwargs)
        if not expected_regexp.search(str(exc_value)):
            raise self.failureException('"%s" does not match "%s"' %
                    (expected_regexp.pattern, str(exc_value)))

    @classmethod
    def _strip(cls, data):
        if data is None:
            return None
        # Convert empty string to None
        return data.strip() or None

    @classmethod
    def _nodecmp(cls, node1, node2):
        if node1.attrib != node2.attrib:
            return False
        if node1.nsmap != node2.nsmap:
            return False
        children1 = node1.getchildren()
        children2 = node2.getchildren()

        if children1 or children2:
            # Compare text in nodes that have children (mixed content).
            # We shouldn't have mixed content, but we need to be flexible.
            if cls._strip(node1.text) != cls._strip(node2.text):
                return False
            if len(children1) != len(children2):
                return False
            for ch1, ch2 in zip(children1, children2):
                if not cls._nodecmp(ch1, ch2):
                    return False
            return True
        # No children, compare the text
        return node1.text == node2.text

    @classmethod
    def _removeTail(self, node):
        stack = collections.deque([ node ])
        while stack:
            n = stack.pop()
            n.tail = None
            children = n.getchildren()
            if children:
                # We don't accept mixed content
                n.text = None
            stack.extend(n.getchildren())
        return node

    def assertXMLEquals(self, first, second):
        from lxml import etree
        tree0 = self._removeTail(etree.fromstring(first.strip()))
        tree1 = self._removeTail(etree.fromstring(second.strip()))
        if not self._nodecmp(tree0, tree1):
            data0 = etree.tostring(tree0, pretty_print=True, with_tail=False)
            data1 = etree.tostring(tree1, pretty_print=True, with_tail=False)
            import difflib
            diff = '\n'.join(list(difflib.unified_diff(data0.splitlines(),
                    data1.splitlines()))[2:])
            self.fail(diff)

class TestCaseWithWorkDir(TestCase):
    testDirName = 'testcase-'

    @classmethod
    def isIndividual(cls):
        import testsuite
        individual = getattr(testsuite, '_individual', None)
        if individual is None:
            individual = getattr(testsuite, 'Suite').individual
        return bool(individual)

    def setUp(self):
        TestCase.setUp(self)
        if self.isIndividual():
            self.workDir = "/tmp/%s%s" % (self.testDirName, os_utils.effectiveUser)
        else:
            from testrunner import testhelp
            self.workDir = testhelp.getTempDir(self.testDirName)
        from conary.lib import util
        util.rmtree(self.workDir, ignore_errors = True)
        util.mkdirChain(self.workDir)

    def tearDown(self):
        from conary.lib import util
        TestCase.tearDown(self)
        if not self.isIndividual():
            util.rmtree(self.workDir, ignore_errors = True)


def todo(reason, whichException=None):
    """Decorate a test that is expected to fail.

    @todo("See #1234")
    def mytest(self):
        self.assertEquals(2 + 2, 5)
    """
    def decorate(func):
        def wrapper(self, *args, **kwargs):
            if whichException is None:
                toCatch = self.failureException
            else:
                toCatch = whichException
            try:
                func(self, *args, **kwargs)
            except toCatch:
                raise SkipTestException("TODO: " + reason)
            else:
                raise self.failureException(
                        'Test passed when it was expected to fail (%s)' %
                        (reason,))
        wrapper.func_name = func.func_name
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorate
