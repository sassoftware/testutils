import fcntl
import itertools
import os
import signal
import sys
import unittest

from testrunner import output
from testrunner import testsuite
from testrunner.loader import Loader


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



class _TestSuiteHandler(object):

    def __init__(self, cfg, resources, sortTestFn=None,
                 suiteClass = ConaryTestSuite):
        self.cfg = cfg
        self.resources = resources
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

    def _getTestsToRun(self, argList=[]):
        topdir = os.path.realpath(self.resources.testPath)
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
        if self.sortTestFn:
            return self.sortTestFn(tets)
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

        runner = output.DebugTestRunner(
                                debug=options.debug,
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
        return parser

    def parseOptions(self, parser, argv):
        return parser.parse_args(argv)

    def main(self, argv):
        parser = self.addOptions()
        options, args = self.parseOptions(parser, argv[1:])
        return self.runTests(options, args)

class CoverageTestSuiteHandler(_TestSuiteHandler):

    def getCoverageExclusions(self, environ):
        return self.cfg.coverageExclusions

    def getCoverageDirs(self, environ):
        if not self.cfg.coverageDirs:
            return [os.path.dirname(sys.modules['testsuite'].__file__)]
        return self.cfg.coverageDirs

    def runCoverage(self, options, argv):
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
        options, args = parser.parse_args(argv)
        if options.coverage or options.patch_coverage or options.patch_file or options.push_coverage:
            if not options.already_covering:
                retval = self.runCoverage(options, argv)
                sys.exit(retval)
        return options, args

TestSuiteHandler = CoverageTestSuiteHandler
