#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import fcntl
import inspect
import itertools
import os
import signal
import sys
import types
import unittest

from testrunner import output
from testrunner import pathManager


class Loader(unittest.TestLoader):

    def _filterTests(self, tests):
        if not self.context:
            return
        # Allow for inverted contexts (e.g. "--context='!foo'")
        inverted = self.context.startswith('!')
        context = inverted and self.context[1:] or self.context

        # Check each test method for contexts.
        for testCase in tests._tests[:]:
            # python 2.6 renamed the field to _testMethodName
            testMethodName = getattr(testCase, '_testMethodName', None) or \
                getattr(testCase, '_TestCase__testMethodName')
            method = getattr(testCase, testMethodName, None)

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
            if inverted and context in contexts:
                # inverted mode: we're removing tests that match the context
                tests._tests.remove(testCase)
            elif not inverted and context not in contexts:
                # normal mode: we're removing tests that don't match the context
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
                    print >> sys.stderr, "%s has no attribute %s" % (
                            '.'.join(found), part)
                    sys.stderr.flush()

                    interesting = (lambda x:
                            inspect.ismodule(x)
                            or inspect.isclass(x)
                            or inspect.isfunction(x))

                    if not interesting(obj):
                        sys.exit(3)

                    print >> sys.stderr, "Attributes:"
                    for name, sub in sorted(obj.__dict__.items()):
                        if name.startswith('_'):
                            continue
                        if not interesting(sub):
                            continue
                        print >> sys.stderr, name
                    sys.stderr.flush()
                    sys.exit(3)

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

class TestProgram(unittest.TestProgram):
    def runTests(self):
        if self.testRunner is None:
            self.testRunner = TextTestRunner(verbosity=self.verbosity)
        self.results = self.testRunner.run(self.test)
        return self.results

class _TestSuiteHandler(object):

    def __init__(self, cfg, sortTestFn=None,
                 suiteClass = ConaryTestSuite):
        self.cfg = cfg
        self.suiteClass = suiteClass
        self.sortTestFn = sortTestFn

    def isIndividual(self):
        return self.cfg.isIndividual

    def _outputStats(self, results, outFile):
        outFile.write('''\
    tests run: %s
    skipped:   %s
    failed:    %s
    ''' % (results.testsRun, results.skippedTests,
          (results.erroredTests + results.failedTests)))

    def _getTestsToRun(self, argList=[], split=None):
        topdir = os.path.realpath(pathManager.getPath('TEST_PATH'))
        tests = []
        cwd = os.getcwd()
        argsUsedAsFilter = set()
        for (dirpath, dirnames, filenames) in os.walk(topdir):
            for f in filenames:
                if (f.endswith('test.py') and not f.startswith('.')
                    or (f.startswith('test') and f.endswith('.py')
                        and f != 'testsuite.py' and f != 'testSetup.py'
                        and f != 'testsetup.py')
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

        if split:
            a, b = split.split('/')
            b = int(b)
            a = int(a) % b
            tests.sort()
            tests = tests[a::b]

        return tests

    def sigUsr1Handler(*args, **kw):
        from conary.lib import debugger
        debugger.serve()

    def sortTests(self, tests):
        if self.sortTestFn:
            return self.sortTestFn(tests)
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

        failedpath = os.path.abspath('.failed')
        if options.rerun_failed:
            if os.path.exists(failedpath):
                args += [ x for x in open(failedpath).read().split('\n') if x]
            else:
                raise RuntimeError('Could not find .failed file from previous failing run')
        runner = output.DebugTestRunner(debug=options.debug,
                useCallback=not options.dots,
                oneLine=not (options.verbose or options.dots),
                stream=stream, xml_stream=xml_stream,
                alwaysSucceed=options.always_succeed)

        if self.isIndividual():
            program = TestProgram(testRunner=runner, testLoader=loader,
                                 argv=[sys.argv[0]] + args)
            results = program.results
        else:
            tests = self._getTestsToRun(args, options.split)
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
            failedTests = open(failedpath, 'w')
            print 'Failed tests:'
            for test, tb in itertools.chain(results.errors,
                                            results.failures):
                # python 2.6 renamed the field to _testMethodName
                testMethodName = getattr(test, '_testMethodName', None) or \
                        getattr(test, '_TestCase__testMethodName')
                module =  test.__class__.__module__
                if module == '__main__':
                    module = ''
                else:
                    module += '.'

                testName =  '%s%s.%s' % (module, test.__class__.__name__, testMethodName)
                print testName
                failedTests.write(testName + '\n')
            print '(Rerun w/ --rerun-failed to rerun only failed tests)'

        if options.stat_file:
            outputStats(results, open(statFile, 'w'))

        if options.profile:
            prof.stop()
        return results

    def addOptions(self):
        from conary.lib import options

        parser = options.OptionParser(version='0.1')
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
        parser.add_option('--rerun-failed', action='store_true',
                          dest='rerun_failed',
                          help='rerun those tests that failed')
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
        parser.add_option('--always-succeed', action='store_true',
                help="Return a success exit code even if tests failed")
        parser.add_option('--split', metavar="M/N",
                help="Run only a deterministic fraction of tests.")
        return parser

    def parseOptions(self, parser, argv):
        return parser.parse_args(argv[1:])

    def main(self, argv):
        parser = self.addOptions()
        options, args = self.parseOptions(parser, argv)
        return self.runTests(options, args)

class CoverageTestSuiteHandler(_TestSuiteHandler):

    def getCoverageExclusions(self, environ):
        return self.cfg.coverageExclusions

    def getCoverageDirs(self, environ):
        if not self.cfg.coverageDirs:
            return [os.path.dirname(sys.modules['testsuite'].__file__)]
        return self.cfg.coverageDirs

    def runCoverage(self, options, argv):
        from testrunner import coveragewrapper
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
                                             pathManager.getPath('TEST_PATH') + '/.coverage',
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


    def addOptions(self):
        from conary.lib import options
        parser = _TestSuiteHandler.addOptions(self)
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
        return parser


    def parseOptions(self, parser, argv):
        options, args = parser.parse_args(argv[1:])
        if options.coverage or options.patch_coverage or options.patch_file or options.push_coverage:
            if not options.already_covering:
                retval = self.runCoverage(options, argv)
                sys.exit(retval)
        return options, args

TestSuiteHandler = CoverageTestSuiteHandler
