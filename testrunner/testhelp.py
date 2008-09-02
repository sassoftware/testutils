import gc
import errno
import fcntl
import gc
import grp
import itertools
import sys
import os
import os.path
import pprint
import pwd
import signal
import socket
import random
import re
import tempfile
import types
import unittest


#FIXME: should make these imports specific
from testrunner.output import *

global _handler
_handler = None
global _conaryDir
_conaryDir = None

portstart = random.randrange(16000, 30000)
# this blows
if hasattr(os, '_urandomfd'):
    fcntl.fcntl(os._urandomfd, fcntl.F_SETFD, 1)

def findPorts(num = 1, failOnError=False, closeSockets=True):
    global portstart
    if portstart > 31500:
        # Wrap around, hope for the best
        portstart = random.randrange(16000, 30000)
    ports = []
    sockets = []
    for port in xrange(portstart, portstart + 300):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('localhost', port))
        except socket.error, e:
            if e[0] != errno.EADDRINUSE:
                raise
        else:
            if closeSockets:
                s.close()
            else:
                sockets.append(s)
            ports.append(port)
            if len(ports) == num:
                portstart = max(ports) + 1
                if closeSockets:
                    return ports
                else:
                    return zip(ports, sockets)

    if failOnError:
        raise socket.error, "Cannot find open port to run server on"
    else:
        portstart = random.randrange(16000, 30000)
        return findPorts(num, failOnError=True)

# gets a temporary directory that is made only of lowercase letters
# for MySQL's benefit
def getTempDir(prefix):
    while True:
        d = tempfile.mkdtemp(prefix=prefix)
        dl = d.lower()
        try:
            os.mkdir(dl, 0700)
        except OSError, e:
            if e.errno == errno.EEXIST:
                continue # try again
        else:
            os.rmdir(d)
            break
    return dl
    
def context(*contexts):
    def deco(func):
        # no wrapper is needed, nor usable.
        if '_contexts' in func.__dict__:
            func._contexts.extend(contexts)
        else:
            func._contexts = list(contexts)
        return func
    return deco

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

class Loader(unittest.TestLoader):

    def _filterTests(self, tests):
        if not self.context:
            return
        # Allow for inverted contexts (e.g. "--context='!foo'")
        inverted = self.context.startswith('!')
        context = inverted and self.context[1:] or self.context

        # Check each test method for contexts.
        for testCase in tests._tests[:]:
            method = getattr(testCase,
                testCase._TestCase__testMethodName, None)

            if method:
                contexts = getattr(method, '_contexts', [])

                # Check to see if the class has a 'contexts'
                # attribute and add those contexts.
                if hasattr(method, 'im_class') and \
                  hasattr(method.im_class, 'contexts'):
                    classContexts = method.im_class.contexts
                    if not isinstance(classContexts, (tuple, list)):
                        classContexts = [classContexts]
                    contexts.extend(classContexts)
            else:
                contexts = []

            # Filter testcases
            if context in contexts:
                tests._tests.remove(testCase)

    def loadTestsFromModule(self, module):
        """Return a suite of all tests cases contained in the given module"""
        tests = []
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, (type, types.ClassType)) and
                issubclass(obj, unittest.TestCase)):
                loadedTests = self.loadTestsFromTestCase(obj)
                self._filterTests(loadedTests)
                tests.append(loadedTests)
            if (isinstance(obj, unittest.TestSuite)):
                tests.append(obj)
        return self.suiteClass(tests)

    @staticmethod
    def _try_import(name):
        try:
            root = __import__(name)
        except ImportError:
            # ImportError might have been caused directly by us trying
            # to import something that does not exist, or it could have
            # been raised by something we tried to import. In the
            # former case, we should return None; in the latter case,
            # we should re-raise the error.

            # Get the frame where the ImportError originated
            e_tb = sys.exc_info()[2]
            while e_tb.tb_next:
                e_tb = e_tb.tb_next
            e_frame = e_tb.tb_frame

            # Compare to the current frame.
            this_frame = sys._getframe(0)
            if this_frame == e_frame:
                # "name" was not found
                return None
            else:
                # Something failed *within* "name"
                raise

        parts = name.split('.')
        module = root
        for part in parts[1:]:
            module = getattr(module, part)

        return module

    def loadModule(self, name):
        if self._try_import(name):
            return None, name

        moduleName = None
        for i in range(0, name.count('.')):
            parts = name.rsplit('.', i + 1)
            moduleName = parts[0]
            objectName = parts[1]
            testName = '.'.join(parts[1:])

            module = self._try_import(moduleName)

            if module:
                # Make sure the module really has the given test in it
                obj = module
                found = [moduleName]
                try:
                    for part in parts[1:]:
                        obj = getattr(obj, part)
                        found.append(part)
                except AttributeError:
                    raise AttributeError("Module or class %s has no "
                        "attribute '%s'" % ('.'.join(found), part))

                return module, testName

        moduleName = name.split('.')[0]
        raise NameError("Module %s does not exist" % moduleName)

    def loadTestsFromName(self, name, module=None):
        # test to make sure we can load what we're trying to load
        # since we can generate a better error message up front.
        if not module:
            try:
                module, name = self.loadModule(name)
            except ImportError, e:
                print 'unable to import module %s: %s' %(name, e)
                raise
        try:
            f = unittest.TestLoader.loadTestsFromName(self, name,
                                                      module=module)
            if isinstance(f, unittest.TestSuite) and not f._tests:
                return f
            return f
        except AttributeError:
            # We need to handle the case where module is None
            if module is None:
                raise

            # try to find a method of a test suite class that matches
            # the thing given.  If we can't find anything, we should
            # raise the original exception, so we'll save it now.
            excinfo = sys.exc_info()
            for objname in dir(module):
                try:
                    newname = '.'.join((objname, name.split('.')[-1]))
                    # context shouldn't apply. test cases were named directly
                    return unittest.TestLoader.loadTestsFromName(self, newname,
                                                                 module=module)
                except Exception, e:
                    pass
            raise excinfo[0], excinfo[1], excinfo[2]
        except ImportError, e:
            print 'unable to import tests from %s: %s' %(name, e)
            raise
        raise AttributeError

    def __init__(self, context = None, suiteClass=unittest.TestSuite):
        self.suiteClass = suiteClass
        unittest.TestLoader.__init__(self)
        self.context = context

class TestCase(unittest.TestCase):

    def __init__(self, methodName):
	unittest.TestCase.__init__(self, methodName)
        self.logFilter = LogFilter()
        self.owner = pwd.getpwuid(os.getuid())[0]
        self.group = grp.getgrgid(os.getgid())[0]

        global _conaryDir
        self.conaryDir = _conaryDir
        self.mockObjects = []
        self.openFds = set()

    def setUp(self):
        from conary.lib import log
        self._logLevel = log.getVerbosity()

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

        try:
            unittest.TestCase.run(self, *args, **kw)
        finally:
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

class ConaryTestSuite(unittest.TestSuite):
    def __init__(self, *args, **kw):
        unittest.TestSuite.__init__(self, *args, **kw)
        self.topLevel = True

    def addTest(self, test):
        unittest.TestSuite.addTest(self, test)
        test.topLevel = False

    def run(self, result):
        try:
            return unittest.TestSuite.run(self, result)
        finally:
            if 'rephelp' in sys.modules and self.topLevel:
                import rephelp
                rephelp._cleanUp()

def getHandlerClass(suiteClass_, getCoverageDirsFn, getExcludeDirsFn=None,
                    sortTestsFn=None):
    class GeneratedHandlerClass(TestSuiteHandler):
        suiteClass = suiteClass_
        def sortTests(self, tests):
            if sortTestsFn:
                return sortTestsFn(tests)
            return tests

        def getCoverageDirs(self, environ):
            return getCoverageDirsFn(self, environ)

        def getCoverageExclusions(self, environ):
	    if getExcludeDirsFn:
                return getExcludeDirsFn(self, environ)
	    return []

    return GeneratedHandlerClass

class TestSuiteHandler(object):

    suiteClass = unittest.TestSuite

    def __init__(self, individual, topdir, conaryDir, testPath):
        global _handler
        global _conaryDir
        _handler = self
        _conaryDir = conaryDir
        self._individual = individual
        self._topdir = topdir
        self.testPath = testPath
        self.conaryDir = conaryDir

    def isIndividual(self):
        return self._individual

    def getCoverageExclusions(self, environ):
        return []

    def getCoverageDirs(self, environ):
        return [os.path.dirname(sys.modules['testsuite'].__file__)]

    def runCoverage(self, options, argv):
        import coveragewrapper
        environ = coveragewrapper.getEnviron()

        stateFile = options.stat_file
        if options.patch_coverage:
            filesToCover = options.patch_coverage
        elif options.push_coverage:
            filesToCover = options.push_coverage
        else:
            filesToCover = options.coverage
        if filesToCover in (True, None):
            filesToCover = []
        else:
            filesToCover = filesToCover.split(',')

        baseDirs = self.getCoverageDirs(environ)
	excludePaths = self.getCoverageExclusions(environ)
        if isinstance(baseDirs, str):
            baseDirs = [baseDirs]

        if options.patch_file:
            files, notExists = coveragewrapper.getFilesToAnnotateFromPatchFile(options.patch_file,
        baseDirs, excludePaths)
        elif options.push_coverage:
            files, notExists = coveragewrapper.getFilesToAnnotateFromHgOut(baseDirs, excludePaths)
        elif options.patch_coverage:
            files, notExists = coveragewrapper.getFilesToAnnotateFromHg(baseDirs, excludePaths)
        else:
            files, notExists = coveragewrapper.getFilesToAnnotate(baseDirs,
                                                                  filesToCover,
                                                                  excludePaths)
        if filesToCover and isinstance(filesToCover, list) and isinstance(files, dict):
            matchingFiles = []
            for path in files.keys():
                for fileToCover in filesToCover:
                    if re.match('.*' + fileToCover, path):
                        matchingFiles.append(path)
                        break
                else:
                    del files[path]
            if not files:
                raise RuntimeError('No files match coverage limiter %s - cannot run coverage' % ','.join(filesToCover))

        if notExists:
            raise RuntimeError, 'no such file(s): %s' % ' '.join(notExists)

        cw = coveragewrapper.CoverageWrapper(environ['coverage'],
                                             self.testPath + '/.coverage',
                                             os.getcwd() + '/annotate',
                                             baseDirs)
        if not options.resume:
            cw.reset()
        argv.append('--already-covering')
        retval = cw.execute(argv)
        # collapse (potentially) 1000s of coverage data files down to 1
        cw.compress()
        if options.report:
            cw.displayReport(files)
        if options.annotate:
            cw.writeAnnotatedFiles(files)

        if options.stat_file:
            print 'Writing coverage stats (this could take a while)...'
            open(options.stat_file, 'a').write('''\
    lines:   %s
    covered: %s
    percent covered: %s
    ''' % cw.getTotals(files))
        return retval


    def _outputStats(self, results, outFile):
        outFile.write('''\
    tests run: %s
    skipped:   %s
    failed:    %s
    ''' % (results.testsRun, results.skippedTests, 
          (results.erroredTests + results.failedTests)))

    def _getTestsToRun(self, argList=[]):
        topdir = os.path.realpath(self._topdir)
        tests = []
        cwd = os.getcwd()
        argsUsedAsFilter = set()
        for (dirpath, dirnames, filenames) in os.walk(topdir):
            for f in filenames:
                if (f.endswith('test.py') and not f.startswith('.')
                    or (f.startswith('test') and f.endswith('.py')
                        and f != 'testsuite.py' and f != 'testSetup.py')
                    # if it is foo/tests/__init__.py, add foo.tests to
                    # our list
                    or (f == '__init__.py'
                        and os.path.basename(dirpath) == 'tests')):
                    # turn any subdir into a dotted module string
                    d = dirpath[len(topdir) + 1:].replace('/', '.')
                    if f == '__init__.py':
                        # foo/tests/__init__.py -> foo.tests
                        testmodule = d
                    else:
                        if d:
                            # if there's a subdir, add a . to delineate
                            d += '.'
                        # strip off .py
                        testmodule = d + f[:-3]
                    if '-' in testmodule:
                        # - is not a valid python module name
                        continue
                    if not argList:
                        tests.append(testmodule)
                    else:
                        for arg in argList:
                            if testmodule.startswith(arg):
                                argsUsedAsFilter.add(arg)
                                tests.append(testmodule)
        # for any argument that wasn't used as a filter
        # transform it into a module name and append it.
        # this lets you do ./testsuite.py footest.FooTest.testCase
        for s in argList:
            if s in argsUsedAsFilter:
                continue
            # strip the .py and change it into a module name
            if s.endswith('.py'):
                s = s[:-3]
                s = os.path.realpath(s)
                s = s[len(topdir) + 1:].replace('/', '.')
            tests.append(s)

        return tests

    def sigUsr1Handler(*args, **kw):
        import epdb
        epdb.serve()

    def sortTests(self, tests):
        return tests

    def runTests(self, options, args):
        if options.profile:
            import hotshot
            prof = hotshot.Profile('conary.prof')
            prof.start()
        signal.signal(signal.SIGUSR1, self.sigUsr1Handler)
        suite = self.suiteClass()
        loader = Loader(context = options.context, 
                        suiteClass=self.suiteClass)

        # output to stdout, not stderr.  reopen because we do some mucking
        # with sys.stdout. Run unbuffered for immediate output.
        stream = os.fdopen(os.dup(sys.stdout.fileno()), 'w', 0)
        fcntl.fcntl(stream.fileno(), fcntl.F_SETFD, 1)
        if options.dots:
            kw = {'verbosity' : 1 }
        else:
            kw = {}

        # open a stream for XML output
        xml_stream = None
        if options.xml_dir:
            # name it after the module that was called, place it in
            # the named directory
            top_name = os.path.basename(sys.argv[0]).rsplit('.', 1)[0]
            file_name = os.path.join(options.xml_dir, top_name + '.xml')
            xml_stream = dict()
            try:
                xml_stream['file'] = open(file_name, 'w')
            except:
                print 'Failed to open %s: %s' % (file_name, \
                    sys.exc_info()[1].strerror)
                sys.exit(1)
            xml_stream['prefix'] = options.xml_prefix

        runner = DebugTestRunner(debug=options.debug, 
                                 useCallback=not options.dots,
                                 oneLine=not (options.verbose or options.dots),
                                 stream=stream, xml_stream=xml_stream)
        if self.isIndividual():
            results = unittest.main(testRunner=runner, testLoader=loader, 
                                    argv=[sys.argv[0]] + args)
        else:
            tests = self._getTestsToRun(args)
            tests = self.sortTests(tests)
            for test in tests:
                try:
                    testcase = loader.loadTestsFromName(test)
                except RuntimeError, e:
                    # buncha __init__ files have no tests
                    print str(e)
                    continue
                suite.addTest(testcase)
            suite.topLevel = True
            args = []
            if options.timing:
                runner.getTimes(suite).printTimes()
                return

            results = runner.run(suite)
            if results.erroredTests or results.failedTests:
                print 'Failed tests:'
                for test, tb in itertools.chain(results.errors,
                                                results.failures):
                    name = test._TestCase__testMethodName
                    print '%s.%s.%s' % (test.__class__.__module__,
                                        test.__class__.__name__, name)

            if options.stat_file:
                outputStats(results, open(statFile, 'w'))

        if options.profile:
            prof.stop()
        return results

    def parseOptions(self, argv):
        from conary.lib import options

        parser = options.OptionParser(version='0.1')
        parser.add_option('--coverage',
                         help='get code coverage numbers',
                         action='callback', nargs=0,
                         callback=options.strictOptParamCallback,
                         dest='coverage')
        parser.add_option('--patch-file',
                         help='get code coverage numbers for a patch.  Assumes --patch-coverage',
                         action='store', dest='patch_file')
        parser.add_option('--push-coverage',
                         help='get code coverage numbers for committed but unpushed code.',
                         action='callback', nargs=0,
                         callback=options.strictOptParamCallback,
                         dest='push_coverage')
        parser.add_option('--already-covering', action='store_true',
                          help='internally used to mark when coverage'
                               ' is already running')
        parser.add_option('--resume',
                         help='resume earlier coverage run',
                         action='store_true')
        parser.add_option('--patch-coverage',
                         help='get code coverage numbers for uncommitted patch',
                         action='callback', nargs=0,
                         callback=options.strictOptParamCallback,
                         dest='patch_coverage')
        parser.add_option('--stat-file', dest='stat_file',
                         help='output test passing information to FILE',
                         metavar='FILE')
        parser.add_option('--debug', action='store_true',
                          help='start debugger when test(s) fail')
        parser.add_option('-v', action='store_true', dest='verbose',
                          help='display one test per line')
        parser.add_option('--dots', action='store_true', dest='dots',
                          help='display dots instead of time output')
        parser.add_option('--profile', action='store_true', dest='profile',
                          help='profile test performance')
        parser.add_option('--timing', action='store_true', dest='timing',
                          help='output timing information')
        parser.add_option('--context', action='store', dest='context',
                          help='limit tests to tests in context CONTEXT',
                          metavar='CONTEXT')
        parser.add_option('--no-report', action='store_false', dest='report',
                          default=True,
                          help='Do not generate report after running coverage')
        parser.add_option('--no-annotate', action='store_false', 
                          dest='annotate', default=True,
                          help='Do not generate report after running coverage')
        parser.add_option('--xml-dir', dest='xml_dir',
                          help='output JUnit-like test results to DIR',
                          metavar='DIR')
        parser.add_option('--xml-prefix', dest='xml_prefix',
                          help='prefix all classes with PREFIX in JUnit output',
                          metavar='PREFIX')


        options, args = parser.parse_args()

        if options.coverage or options.patch_coverage or options.patch_file or options.push_coverage:
            if not options.already_covering:
                retval = self.runCoverage(options, argv)
                sys.exit(retval)

        return options, args

    def main(self, argv):
        options, args = self.parseOptions(argv)
        return self.runTests(options, args)

def getPath(envName, default=None):
    if envName in os.environ:
        return os.path.realpath(os.environ[envName])
    elif default is None:
        print "please set %s" % envName
        sys.exit(1)
    else:
        os.environ[envName] = default
        return default

def insertPath(path, updatePythonPath=False):
    if path not in sys.path:
        sys.path.insert(0, path)
    if 'PYTHONPATH' in os.environ:
        os.environ['PYTHONPATH'] = os.pathsep.join((path,
                                                   os.environ['PYTHONPATH']))
    else:
        os.environ['PYTHONPATH'] = path

def getConaryDir():
    global _conaryDir
    return _conaryDir

def getTestPath(testsuiteModule = None):
    # By default, use the standard setup
    if testsuiteModule is None:
        testsuiteModule = 'testsuite'
    invokedAs = sys.argv[0]
    if invokedAs.find("/") != -1:
        if invokedAs[0] != "/":
            invokedAs = os.getcwd() + "/" + invokedAs
        path = os.path.dirname(invokedAs)
    else:
        path = os.getcwd()

    testPath = os.path.realpath(path)
    # find the top of the test directory in the full path - this
    # sets the right test path even when testsuite.setup() is called
    # from a testcase in a subdirectory of the testPath
    if sys.modules.has_key(testsuiteModule):
        testPath = os.path.join(testPath, 
                        os.path.dirname(sys.modules[testsuiteModule].__file__))
    return testPath

def getArchivePath(testDir):
    for path in (testDir, os.path.dirname(__file__)):
        path_maybe = os.path.join(path, 'archive')
        if os.path.isdir(path_maybe):
            return path_maybe

    return None

def main(argv=[], individual=True, handlerClass=TestSuiteHandler):
    from conary.lib import util
    sys.excepthook = util.genExcepthook(True, catchSIGUSR1=False)
    handler = handlerClass(individual=individual, topdir=getTestPath(),
                           testPath=getTestPath(), conaryDir=getConaryDir())
    print "This process PID:", os.getpid()
    results = handler.main(argv)
    if results is None:
        sys.exit(0)
    sys.exit(not results.wasSuccessful())
