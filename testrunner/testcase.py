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


class TestCase(unittest.TestCase):
    TIMEZONE = 'Pacific/Fiji'

    def __init__(self, methodName):
	unittest.TestCase.__init__(self, methodName)
        self.logFilter = LogFilter()
        self.owner = pwd.getpwuid(os.getuid())[0]
        self.group = grp.getgrgid(os.getgid())[0]
        from testrunner import resources
        self.resources = resources

        self.conaryDir = resources.conaryDir
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

    def tearDown(self):
        from conary.lib import log
        log.setVerbosity(self._logLevel)

    def mock(self, parent, selector, replacement):
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
        while self.mockObjects:
            parent, selector, (oldval, missing) = self.mockObjects.pop()
            if missing:
                delattr(parent, selector)
            else:
                setattr(parent, selector, oldval)

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
        fdPath ='/proc/%s/fd' % os.getpid() 
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

        if (not returnException) and e:
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

        if e:
            return (e, sout + serr)
        else:
            return (ret, sout + serr)

    def discardOutput(self, func, *args, **kwargs):
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

    def failUnlessContains(self, needle, haystack, msg=None):
        """Fail the test unless the needle is in the haystack."""
        if not needle in haystack:
            if not msg:
                msg = "'%s' not in '%s'" %(needle, haystack)
            raise self.failureException, msg

    def failUnlessRaises(self, excClass, callableObj, *args, **kwargs):
        try:
            callableObj(*args, **kwargs)
        except excClass, e:
            return e
        else:
            if hasattr(excClass,'__name__'):
                excName = excClass.__name__
            else:
                excName = str(excClass)
            raise self.failureException, "%s not raised" % excName

    assertRaises = failUnlessRaises


