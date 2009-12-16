#!/usr/bin/python
#
#             Perforce Defect Tracking Integration Project
#              <http://www.ravenbrook.com/project/p4dti/>
#
#                   COVERAGE.PY -- COVERAGE TESTING
#
#             Gareth Rees, Ravenbrook Limited, 2001-12-04
#                     Ned Batchelder, 2004-12-12
#         http://nedbatchelder.com/code/modules/coverage.html
#
#
# 1. INTRODUCTION
#
# This module provides coverage testing for Python code.
#
# The intended readership is all Python developers.
#
# This document is not confidential.
#
# See [GDR 2001-12-04a] for the command-line interface, programmatic
# interface and limitations.  See [GDR 2001-12-04b] for requirements and
# design.
#
# Portions (C) 2009 rPath, Inc. Those portions are licensed under the Python
# Software Foundation license agreement, which can be found at www.python.org.
#

"""Usage:

coverage.py -x MODULE.py [ARG1 ARG2 ...]
    Execute module, passing the given command-line arguments, collecting
    coverage data.

coverage.py -e
    Erase collected coverage data.

coverage.py -r [-m] FILE1 FILE2 ...
    Report on the statement coverage for the given files.  With the -m
    option, show line numbers of the statements that weren't executed.

coverage.py -a [-d dir] FILE1 FILE2 ...
    Make annotated copies of the given files, marking statements that
    are executed with > and statements that are missed with !.  With
    the -d option, make the copies in that directory.  Without the -d
    option, make each copy in the same directory as the original.

Coverage data is saved in the file .coverage by default.  Set the
COVERAGE_FILE environment variable to save it somewhere else."""

__version__ = "2.1.20041214"    # see detailed history at the end of this file.

import compiler
import compiler.visitor
import errno
import os
import re
import string
import sys
import types

# import _coverage ourselves, due to wacky coveragewrapper stuff
# and not having this directory in the path
import imp
info = imp.find_module('_coverage', [os.path.dirname(__file__)])
_coverage = imp.load_module('_coverage', *info)

# 2. IMPLEMENTATION
#
# This uses the "singleton" pattern.
#
# The word "morf" means a module object (from which the source file can
# be deduced by suitable manipulation of the __file__ attribute) or a
# filename.
#
# When we generate a coverage report we have to canonicalize every
# filename in the coverage dictionary just in case it refers to the
# module we are reporting on.  It seems a shame to throw away this
# information so the data in the coverage dictionary is transferred to
# the 'cexecuted' dictionary under the canonical filenames.
#
# The coverage dictionary is called "c" and the trace function "t".  The
# reason for these short names is that Python looks up variables by name
# at runtime and so execution time depends on the length of variables!
# In the bottleneck of this application it's appropriate to abbreviate
# names to increase speed.

# A coverage collection object
c = _coverage.Collector()

class StatementFindingAstVisitor(compiler.visitor.ASTVisitor):
    def __init__(self, statements, excluded, suite_spots):
        compiler.visitor.ASTVisitor.__init__(self)
        self.statements = statements
        self.excluded = excluded
        self.suite_spots = suite_spots
        self.excluding_suite = 0
        
    def doRecursive(self, node):
        self.recordNodeLine(node)
        for n in node.getChildNodes():
            self.dispatch(n)

    visitStmt = visitModule = doRecursive
    
    def doCode(self, node):
        if hasattr(node, 'decorators') and node.decorators:
            self.dispatch(node.decorators)
            self.recordAndDispatch(node.code)
        else:
            self.doSuite(node, node.code)

    visitFunction = visitClass = doCode

    def getFirstLine(self, node):
        # Find the first line in the tree node.
        lineno = node.lineno
        for n in node.getChildNodes():
            f = self.getFirstLine(n)
            if lineno and f:
                lineno = min(lineno, f)
            else:
                lineno = lineno or f
        return lineno

    def getLastLine(self, node):
        # Find the first line in the tree node.
        lineno = node.lineno
        for n in node.getChildNodes():
            lineno = max(lineno, self.getLastLine(n))
        return lineno
    
    def doStatement(self, node):
        self.recordLine(self.getFirstLine(node))

    visitAssert = visitAssign = visitAssTuple = visitDiscard = visitPrint = \
                visitPrintnl = visitRaise = visitSubscript = \
                visitDecorators = \
                doStatement
    
    def recordNodeLine(self, node):
        return self.recordLine(node.lineno)
    
    def recordLine(self, lineno):
        # Returns a bool, whether the line is included or excluded.
        if lineno:
            # Multi-line tests introducing suites have to get charged to their
            # keyword.
            if lineno in self.suite_spots:
                lineno = self.suite_spots[lineno][0]
            # If we're inside an exluded suite, record that this line was
            # excluded.
            if self.excluding_suite:
                self.excluded[lineno] = 1
                return 0
            # If this line is excluded, or suite_spots maps this line to
            # another line that is exlcuded, then we're excluded.
            elif self.excluded.has_key(lineno) or \
                 self.suite_spots.has_key(lineno) and \
                 self.excluded.has_key(self.suite_spots[lineno][1]):
                return 0
            # Otherwise, this is an executable line.
            else:
                self.statements[lineno] = 1
                return 1
        return 0
    
    default = recordNodeLine
    
    def recordAndDispatch(self, node):
        self.recordNodeLine(node)
        self.dispatch(node)

    def doSuite(self, intro, body, exclude=0):
        exsuite = self.excluding_suite
        if exclude or (intro and not self.recordNodeLine(intro)):
            self.excluding_suite = 1
        self.recordAndDispatch(body)
        self.excluding_suite = exsuite
        
    def doPlainWordSuite(self, prevsuite, suite):
        # Finding the exclude lines for else's is tricky, because they aren't
        # present in the compiler parse tree.  Look at the previous suite,
        # and find its last line.  If any line between there and the else's
        # first line are excluded, then we exclude the else.
        lastprev = self.getLastLine(prevsuite)
        firstelse = self.getFirstLine(suite)
        for l in range(lastprev+1, firstelse):
            if self.suite_spots.has_key(l):
                self.doSuite(None, suite, exclude=self.excluded.has_key(l))
                break
        else:
            self.doSuite(None, suite)
        
    def doElse(self, prevsuite, node):
        if node.else_:
            self.doPlainWordSuite(prevsuite, node.else_)
    
    def visitFor(self, node):
        self.doSuite(node, node.body)
        self.doElse(node.body, node)

    def visitIf(self, node):
        # The first test has to be handled separately from the rest.
        # The first test is credited to the line with the "if", but the others
        # are credited to the line with the test for the elif.
        self.doSuite(node, node.tests[0][1])
        for t, n in node.tests[1:]:
            self.doSuite(t, n)
        self.doElse(node.tests[-1][1], node)

    def visitWhile(self, node):
        self.doSuite(node, node.body)
        self.doElse(node.body, node)

    def visitTryExcept(self, node):
        self.doSuite(node, node.body)
        for i in range(len(node.handlers)):
            a, b, h = node.handlers[i]
            if not a:
                # It's a plain "except:".  Find the previous suite.
                if i > 0:
                    prev = node.handlers[i-1][2]
                else:
                    prev = node.body
                self.doPlainWordSuite(prev, h)
            else:
                self.doSuite(a, h)
        self.doElse(node.handlers[-1][2], node)
    
    def visitTryFinally(self, node):
        self.doSuite(node, node.body)
        self.doPlainWordSuite(node.body, node.final)
        
    def visitGlobal(self, node):
        # "global" statements don't execute like others (they don't call the
        # trace function), so don't record their line numbers.
        pass

the_coverage = None

class coverage:
    error = "coverage error"

    # Name of the cache file (unless environment variable is set).
    cache_default = ".coverage"

    # Environment variable naming the cache file.
    cache_env = "COVERAGE_FILE"
    cachedir_env = "COVERAGE_DIR"

    # A map from canonical Python source file name to a dictionary in
    # which there's an entry for each line number that has been
    # executed.
    cexecuted = {}

    # Cache of results of calling the analysis2() method, so that you can
    # specify both -r and -a without doing double work.
    analysis_cache = {}

    # Cache of results of calling the canonical_filename() method, to
    # avoid duplicating work.
    canonical_filename_cache = {}

    def __init__(self):
        global the_coverage
        if the_coverage:
            raise self.error, "Only one coverage object allowed."
        self.usecache = 1
        self.cache = None
        self.exclude_re = ''

    def help(self, error=None):
        if error:
            print error
            print
        print __doc__
        sys.exit(1)

    def command_line(self):
        import getopt
        settings = {}
        optmap = {
            '-a': 'annotate',
            '-d:': 'directory=',
            '-e': 'erase',
            '-h': 'help',
            '-i': 'ignore-errors',
            '-m': 'show-missing',
            '-r': 'report',
            '-x': 'execute',
            }
        short_opts = string.join(map(lambda o: o[1:], optmap.keys()), '')
        long_opts = optmap.values()
        options, args = getopt.getopt(sys.argv[1:], short_opts,
                                      long_opts)
        for o, a in options:
            if optmap.has_key(o):
                settings[optmap[o]] = 1
            elif optmap.has_key(o + ':'):
                settings[optmap[o + ':']] = a
            elif o[2:] in long_opts:
                settings[o[2:]] = 1
            elif o[2:] + '=' in long_opts:
                settings[o[2:]] = a
            else:
                self.help("Unknown option: '%s'." % o)
        if settings.get('help'):
            self.help()
        for i in ['erase', 'execute']:
            for j in ['annotate', 'report']:
                if settings.get(i) and settings.get(j):
                    self.help("You can't specify the '%s' and '%s' "
                              "options at the same time." % (i, j))
        args_needed = (settings.get('execute')
                       or settings.get('annotate')
                       or settings.get('report'))
        action = settings.get('erase') or args_needed
        if not action:
            self.help("You must specify at least one of -e, -x, -r, or -a.")
        if not args_needed and args:
            self.help("Unexpected arguments %s." % args)
        

        if settings.get('erase'):
            self.erase()
        if settings.get('execute'):
            self.get_ready()
            self.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
            if not args:
                self.help("Nothing to do.")
            sys.argv = args
            self.start()
            import __main__
            sys.path[0] = os.path.dirname(sys.argv[0])
            execfile(sys.argv[0], __main__.__dict__)
        if not args:
            args = self.cexecuted.keys()
        self.get_ready(restoreDir=True)
        self.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        ignore_errors = settings.get('ignore-errors')
        show_missing = settings.get('show-missing')
        directory = settings.get('directory=')
        if settings.get('report'):
            self.report(args, show_missing, ignore_errors)
        if settings.get('annotate'):
            self.annotate(args, directory, ignore_errors)

    def use_cache(self, usecache):
        self.usecache = usecache
        
    def get_ready(self, restoreDir=False):
        if self.usecache and not self.cache:
            cacheDir = os.environ.get(self.cachedir_env, None)
            if cacheDir:
                self.cacheDir = cacheDir
                self.cache = self.cacheDir + '/%s' % os.getpid()
                if restoreDir:
                    self.restoreDir()
                else:
                    self.restore()
            else:
                self.cache = os.environ.get(self.cache_env, self.cache_default)
                self.restore()
        self.pid = os.getpid()
        self.analysis_cache = {}
        
    def start(self):
        self.get_ready()
        global c
        c.enable()

    def stop(self):
        global c
        c.disable()

    def erase(self):
        global c
        c.clear()
        self.analysis_cache = {}
        self.cexecuted = {}
        if self.cache and os.path.exists(self.cache):
            os.remove(self.cache)
        self.exclude_re = ''

    def exclude(self, re):
        if self.exclude_re:
            self.exclude_re += "|"
        self.exclude_re += "(" + re + ")"

    # save().  Save coverage data to the coverage cache.

    def save(self):
        if self.usecache and self.cache:
            self.canonicalize_filenames()
            if not len(self.cexecuted):
                # nothing to write - don't create an empty file
                return
            if os.path.exists(self.cache) and self.cacheDir:
                # don't just blithely overwrite the cache,
                # since there may be information in here we need
                # to save
                cacheName = os.path.basename(self.cache)
                parts = cacheName.rsplit('.', 1)
                if len(parts) > 1:
                    pid, ext = parts
                    ext = int(ext)
                else:
                    pid = parts[0]
                    ext = 0
                ext = ext + 1
                self.cache = '%s/%s.%s' % (self.cacheDir, pid, ext)
            cache = open(self.cache, 'wb')
            #numEntries = sum([len(x) for x in self.cexecuted])
            #open('/dev/tty', 'w').write("Writing %s lines for %s files to %s\n" % (numEntries, len(self.cexecuted), self.cache))

            import marshal
            marshal.dump(self.cexecuted, cache)
            cache.close()
            c.clear()
            self.cexecuted = {}

    # restore().  Restore coverage data from the coverage cache (if it
    # exists).

    def restore(self):
        global c
        if self.cexecuted:
            import epdb
            epdb.st()
            return
        c.clear()
        self.cexecuted = {}
        assert self.usecache
        if not os.path.exists(self.cache):
            return
        try:
            cache = open(self.cache, 'rb')
            import marshal
            cexecuted = marshal.load(cache)
            cache.close()
            if isinstance(cexecuted, types.DictType):
                self.cexecuted = cexecuted
                #numEntries = sum([len(x) for x in self.cexecuted])
                #open('/dev/tty', 'w').write('Restored %s lines for %s files from %s\n' % (numEntries, len(self.cexecuted), self.cache))
        except:
            pass

    def restoreDir(self):
        global c
        c.clear()
        self.cexecuted = {}
        assert self.usecache
        if not os.path.exists(self.cacheDir):
            return
        for cacheFile in os.listdir(self.cacheDir):
            try:
                cache = open(os.path.join(self.cacheDir, cacheFile), 'rb')
                import marshal
                cexecuted = marshal.load(cache)
                cache.close()
                if isinstance(cexecuted, types.DictType):
                    for file, lines in cexecuted.iteritems():
                        self.cexecuted.setdefault(file, {}).update(lines)
            except:
                pass
        #numEntries = sum([len(x) for x in self.cexecuted])
        #open('/dev/tty', 'w').write("Read %s entries for %s files\n" % (numEntries, len(self.cexecuted)))



    # canonical_filename(filename).  Return a canonical filename for the
    # file (that is, an absolute path with no redundant components and
    # normalized case).  See [GDR 2001-12-04b, 3.3].

    def canonical_filename(self, filename):
        if not self.canonical_filename_cache.has_key(filename):
            f = filename
            if os.path.isabs(f) and not os.path.exists(f):
                f = os.path.basename(f)
            if not os.path.isabs(f):
                for path in [os.curdir] + sys.path:
                    g = os.path.join(path, f)
                    if os.path.exists(g):
                        f = g
                        break
            cf = os.path.realpath(os.path.normcase(os.path.abspath(f)))
            self.canonical_filename_cache[filename] = cf
        return self.canonical_filename_cache[filename]

    # canonicalize_filenames().  Copy results from "executed" to
    # "cexecuted", canonicalizing filenames on the way.  Clear the
    # "executed" map.

    def canonicalize_filenames(self):
        global c
        c.disable()
        for filename, lineno in c.getlines().iterkeys():
            f = self.canonical_filename(filename)
            if not self.cexecuted.has_key(f):
                self.cexecuted[f] = {}
            self.cexecuted[f][lineno] = 1
        c.clear()

    # morf_filename(morf).  Return the filename for a module or file.

    def morf_filename(self, morf):
        if isinstance(morf, types.ModuleType):
            if not hasattr(morf, '__file__'):
                raise self.error, "Module has no __file__ attribute."
            file = morf.__file__
        else:
            file = morf
        return self.canonical_filename(file)

    # analyze_morf(morf).  Analyze the module or filename passed as
    # the argument.  If the source code can't be found, raise an error.
    # Otherwise, return a tuple of (1) the canonical filename of the
    # source code for the module, (2) a list of lines of statements
    # in the source code, and (3) a list of lines of excluded statements.

    def analyze_morf(self, morf):
        if self.analysis_cache.has_key(morf):
            return self.analysis_cache[morf]
        filename = self.morf_filename(morf)
        ext = os.path.splitext(filename)[1]
        if ext == '.pyc':
            if not os.path.exists(filename[0:-1]):
                raise self.error, ("No source for compiled code '%s'."
                                   % filename)
            filename = filename[0:-1]
        elif ext != '.py':
            raise self.error, "File '%s' not Python source." % filename
        source = open(filename, 'r')
        lines, excluded_lines = self.find_executable_statements(
            source.read(), exclude=self.exclude_re
            )
        source.close()
        result = filename, lines, excluded_lines
        self.analysis_cache[morf] = result
        return result

    def get_suite_spots(self, tree, spots):
        import symbol, token
        for i in range(1, len(tree)):
            if type(tree[i]) == type(()):
                if tree[i][0] == symbol.suite:
                    # Found a suite, look back for the colon and keyword.
                    lineno_colon = lineno_word = None
                    for j in range(i-1, 0, -1):
                        if tree[j][0] == token.COLON:
                            lineno_colon = tree[j][2]
                        elif tree[j][0] == token.NAME:
                            if tree[j][1] == 'elif':
                                # Find the line number of the first non-terminal
                                # after the keyword.
                                t = tree[j+1]
                                while t and token.ISNONTERMINAL(t[0]):
                                    t = t[1]
                                if t:
                                    lineno_word = t[2]
                            else:
                                lineno_word = tree[j][2]
                            break
                        elif tree[j][0] == symbol.except_clause:
                            # "except" clauses look like:
                            # ('except_clause', ('NAME', 'except', lineno), ...)
                            if tree[j][1][0] == token.NAME:
                                lineno_word = tree[j][1][2]
                                break
                            
                    if lineno_colon and lineno_word:
                        # Found colon and keyword, mark all the lines
                        # between the two with the two line numbers.
                        for l in range(lineno_word, lineno_colon+1):
                            spots[l] = (lineno_word, lineno_colon)
                self.get_suite_spots(tree[i], spots)

    def find_executable_statements(self, text, exclude=None):
        # Find lines which match an exclusion pattern.
        excluded = {}
        suite_spots = {}
        if exclude:
            reExclude = re.compile(exclude)
            lines = text.split('\n')
            for i in range(len(lines)):
                if reExclude.search(lines[i]):
                    excluded[i+1] = 1

        import parser
        tree = parser.suite(text+'\n\n').totuple(1)
        self.get_suite_spots(tree, suite_spots)
            
        # Use the compiler module to parse the text and find the executable
        # statements.  We add newlines to be impervious to final partial lines.
        statements = {}
        ast = compiler.parse(text+'\n\n')
        visitor = StatementFindingAstVisitor(statements, excluded, suite_spots)
        compiler.walk(ast, visitor, walker=visitor)

        lines = statements.keys()
        lines.sort()
        excluded_lines = excluded.keys()
        excluded_lines.sort()
        return lines, excluded_lines

    # format_lines(statements, lines).  Format a list of line numbers
    # for printing by coalescing groups of lines as long as the lines
    # represent consecutive statements.  This will coalesce even if
    # there are gaps between statements, so if statements =
    # [1,2,3,4,5,10,11,12,13,14] and lines = [1,2,5,10,11,13,14] then
    # format_lines will return "1-2, 5-11, 13-14".

    def format_lines(self, statements, lines):
        pairs = []
        i = 0
        j = 0
        start = None
        pairs = []
        while i < len(statements) and j < len(lines):
            if statements[i] == lines[j]:
                if start == None:
                    start = lines[j]
                end = lines[j]
                j = j + 1
            elif start:
                pairs.append((start, end))
                start = None
            i = i + 1
        if start:
            pairs.append((start, end))
        def stringify(pair):
            start, end = pair
            if start == end:
                return "%d" % start
            else:
                return "%d-%d" % (start, end)
        import string
        return string.join(map(stringify, pairs), ", ")

    # Backward compatibility with version 1.
    def analysis(self, morf):
        f, s, _, m, mf = self.analysis2(morf)
        return f, s, m, mf

    def analysis2(self, morf, linesToWatch=None):
        filename, statements, excluded = self.analyze_morf(morf)
        if linesToWatch is not None:
            statements = sorted(set(statements) & set(linesToWatch))
        self.canonicalize_filenames()
        if not self.cexecuted.has_key(filename):
            self.cexecuted[filename] = {}
        missing = []
        for line in statements:
            if not self.cexecuted[filename].has_key(line):
                missing.append(line)
        return (filename, statements, excluded, missing,
                self.format_lines(statements, missing))

    def morf_name(self, morf):
        if isinstance(morf, types.ModuleType):
            return morf.__name__
        else:
            # XXX hack
            if morf.startswith('../'):
                return morf[3:]

            return morf
            #return os.path.splitext(os.path.basename(morf))[0]

    def printReportLine(self, file, fmt_coverage, name, statements, missing, readable, show_missing, baseDirs=None):
        n = len(statements)
        m = n - len(missing)
        if baseDirs:
            pos = 0
            for bd in baseDirs:
                if name.startswith(bd):
                    pos = len(os.path.dirname(bd)) + 1
                    break
            name = name[pos:]
        if n > 0:
            pc = 100.0 * m / n
        else:
            pc = 100.0
        pc = '%-4.2f' % pc
        args = (name, n, m, pc)
        if show_missing:
            args = args + (readable,)

        print >>file, fmt_coverage % args

    def report(self, morfs, show_missing=1, ignore_errors=0,
                sortFn = None, file=sys.stdout, baseDirs=None):
        def compare_morfs(a, b):
            # sort things with a / in them after things that don't
            adirs = self.morf_name(a).count(os.sep)
            bdirs = self.morf_name(b).count(os.sep)
            if adirs > bdirs:
                return 1
            if adirs < bdirs:
                return -1
            if a < b:
                return -1
            if a > b:
                return 1
            return 0
        if isinstance(morfs, dict):
            morfLines = morfs
            morfs = list(morfs)
        else:
            if not isinstance(morfs, types.ListType):
                morfs = [morfs]
            morfLines = {}

        if baseDirs:
            baseDirs = [ os.path.realpath(os.path.abspath(x)) for x in baseDirs]
        morfs.sort(compare_morfs)
        max_name = max([5,] + map(len, map(self.morf_name, morfs)))
        fmt_name = "%%- %ds  " % max_name
        fmt_err = fmt_name + "%s: %s"
        header = fmt_name % "Name" + " Stmts   Exec    Cover"
        fmt_coverage = fmt_name + "% 6d % 6d % 7s%%"
        if show_missing:
            header = header + "   Missing"
            fmt_coverage = fmt_coverage + "   %s"
        print >>file, header
        print >>file, "-" * len(header)
        total_statements = 0
        total_executed = 0
        reportData = []
        for morf in morfs:
            name = self.morf_name(morf)
            linesToWatch = morfLines.get(name, None)
            try:
                _, statements, _, missing, readable  = self.analysis2(morf,
                                                            linesToWatch)
                reportData.append((name, statements, missing, readable))
                total_statements = total_statements + len(statements)
                total_executed = total_executed + len(statements) - len(missing)
                if not sortFn:
                    # quick out - 
                    self.printReportLine(file, fmt_coverage, name, statements,
                        missing, readable, show_missing, baseDirs)
            except KeyboardInterrupt:
                raise
            except:
                if not ignore_errors:
                    type, msg = sys.exc_info()[0:2]
                    print >>file, fmt_err % (name, type, msg)
        if sortFn:
            reportData.sort(sortFn)
            for name, statements, missing, readable in reportData:
                self.printReportLine(file, fmt_coverage, name, statements,
                    missing, readable, show_missing, baseDirs)
        if len(morfs) > 1:
            print >>file, "-" * len(header)
            if total_statements > 0:
                pc = 100.0 * total_executed / total_statements
            else:
                pc = 100.0
            args = ("TOTAL", total_statements, total_executed, '%-4.2f' % pc)
            if show_missing:
                args = args + ("",)
            print >>file, fmt_coverage % args

    # annotate(morfs, ignore_errors).

    blank_re = re.compile("\\s*(#|$)")
    else_re = re.compile("\\s*else\\s*:\\s*(#|$)")

    def annotate(self, morfs, directory=None, ignore_errors=0, baseDirs = None):
        if baseDirs:
            baseDirs = [ os.path.realpath(os.path.abspath(x)) for x in baseDirs]
        if not isinstance(morfs, dict):
            morfs = dict.fromkeys(morfs)
        for morf, linesToWatch in morfs.iteritems():
            try:
                filename, statements, excluded, missing, _ = self.analysis2(morf, linesToWatch)
                self.annotate_file(filename, statements, excluded, missing, directory, linesToWatch, baseDirs = baseDirs)
            except KeyboardInterrupt:
                raise
            except:
                if not ignore_errors:
                    raise
                
    def annotate_file(self, filename, statements, excluded, missing, 
                      directory=None, linesToWatch=None, baseDirs = None):
        source = open(filename, 'r')
        if directory:
            prefixPos = 0
            for bd in baseDirs or []:
                if filename.startswith(bd):
                    prefixPos = len(os.path.dirname(bd)) + 1
                    break
            fn = filename[prefixPos:]
            dest_file = os.path.join(directory, fn + ',cover')
            dirs = os.path.dirname(dest_file).split(os.sep)
            path = ''
            for dir in dirs:
                path = path + dir + os.sep
                try:
                    os.mkdir(path)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise
        else:
            dest_file = filename + ',cover'
        dest = open(dest_file, 'w')
        lineno = 0
        i = 0
        j = 0
        covered = 1
        lastWritten = 0
        while 1:
            line = source.readline()
            if line == '':
                break
            lineno = lineno + 1
            while i < len(statements) and statements[i] < lineno:
                i = i + 1
            while j < len(missing) and missing[j] < lineno:
                j = j + 1
            if i < len(statements) and statements[i] == lineno:
                covered = j >= len(missing) or missing[j] > lineno
            if linesToWatch and lineno not in linesToWatch:
                continue
            elif lastWritten != lineno - 1:
                dest.write('Line %d:\n' % lineno)
            if self.blank_re.match(line):
                dest.write('  ')
            elif self.else_re.match(line):
                # Special logic for lines containing only
                # 'else:'.  See [GDR 2001-12-04b, 3.2].
                if i >= len(statements) and j >= len(missing):
                    dest.write('! ')
                elif i >= len(statements) or j >= len(missing):
                    dest.write('  ')
                elif statements[i] == missing[j]:
                    dest.write('! ')
                else:
                    dest.write('  ')
            elif lineno in excluded:
                dest.write('- ')
            elif covered:
                dest.write('  ')
            else:
                dest.write('! ')
            dest.write(line)
            lastWritten = lineno
        source.close()
        dest.close()

# Singleton object.
the_coverage = coverage()

# Module functions call methods in the singleton object.
def use_cache(*args): return the_coverage.use_cache(*args)
def start(*args): return the_coverage.start(*args)
def stop(*args): return the_coverage.stop(*args)
def erase(*args): return the_coverage.erase(*args)
def exclude(*args): return the_coverage.exclude(*args)
def analysis(*args): return the_coverage.analysis(*args)
def analysis2(*args): return the_coverage.analysis2(*args)
def report(*args, **kwargs): return the_coverage.report(*args, **kwargs)
def annotate(*args): return the_coverage.annotate(*args)
def annotate_file(*args): return the_coverage.annotate_file(*args)

# Save coverage data when Python exits.  (The atexit module wasn't
# introduced until Python 2.0, so use sys.exitfunc when it's not
# available.)
try:
    import atexit
    atexit.register(the_coverage.save)
except ImportError:
    sys.exitfunc = the_coverage.save

# Command-line interface.
if __name__ == '__main__':
    the_coverage.command_line()


# A. REFERENCES
#
# [GDR 2001-12-04a] "Statement coverage for Python"; Gareth Rees;
# Ravenbrook Limited; 2001-12-04;
# <http://www.garethrees.org/2001/12/04/python-coverage/>.
#
# [GDR 2001-12-04b] "Statement coverage for Python: design and
# analysis"; Gareth Rees; Ravenbrook Limited; 2001-12-04;
# <http://www.garethrees.org/2001/12/04/python-coverage/design.html>.
#
# [van Rossum 2001-07-20a] "Python Reference Manual (releae 2.1.1)";
# Guide van Rossum; 2001-07-20;
# <http://www.python.org/doc/2.1.1/ref/ref.html>.
#
# [van Rossum 2001-07-20b] "Python Library Reference"; Guido van Rossum;
# 2001-07-20; <http://www.python.org/doc/2.1.1/lib/lib.html>.
#
#
# B. DOCUMENT HISTORY
#
# 2001-12-04 GDR Created.
#
# 2001-12-06 GDR Added command-line interface and source code
# annotation.
#
# 2001-12-09 GDR Moved design and interface to separate documents.
#
# 2001-12-10 GDR Open cache file as binary on Windows.  Allow
# simultaneous -e and -x, or -a and -r.
#
# 2001-12-12 GDR Added command-line help.  Cache analysis so that it
# only needs to be done once when you specify -a and -r.
#
# 2001-12-13 GDR Improved speed while recording.  Portable between
# Python 1.5.2 and 2.1.1.
#
# 2002-01-03 GDR Module-level functions work correctly.
#
# 2002-01-07 GDR Update sys.path when running a file with the -x option,
# so that it matches the value the program would get if it were run on
# its own.
#
# 2004-12-12 NMB Significant code changes.
# - Finding executable statements has been rewritten so that docstrings and
#   other quirks of Python execution aren't mistakenly identified as missing
#   lines.
# - Lines can be excluded from consideration, even entire suites of lines.
# - The filesystem cache of covered lines can be disabled programmatically.
# - Modernized the code.
#
# 2004-12-14 NMB Minor tweaks.  Return 'analysis' to its original behavior
# and add 'analysis2'.  Add a global for 'annotate', and factor it, adding
# 'annotate_file'.
#
# C. COPYRIGHT AND LICENCE
#
# Copyright 2001 Gareth Rees.  All rights reserved.
# Copyright 2004 Ned Batchelder.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS AND CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
# $Id: coverage.py,v 1.8 2004/12/20 20:06:02 msw Exp $
