#!/usr/bin/python
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


import bz2
import coverage
import cPickle
import optparse
import os
import re
import sys


# Get a list of files from the given baseDirs to cover
# (stolen from coveragewrapper)
def _isPythonFile(fullPath, posFilters=[r'\.py$'], negFilters=['sqlite']):
    found = False
    for posFilter in posFilters:
        if re.search(posFilter, fullPath):
            found = True
            break
    if not found:
        return False

    foundNeg = False
    for negFilter in negFilters:
        if re.search(negFilter, fullPath):
            foundNeg = True
            break
    if foundNeg:
        return False
    return True
def getFilesToAnnotate(baseDirs=[], filesToFind=[], exclude=[]):

    notExists = set(filesToFind)
    addAll = not filesToFind

    allFiles = set(x for x in filesToFind if os.path.exists(x))
    filesToFind = [ x for x in filesToFind if x not in allFiles ]

    if not isinstance(exclude, list):
        exclude = [ exclude ]
    negFilters = ['sqlite'] + exclude

    baseDirs = [ os.path.realpath(x) for x in baseDirs ]
    for baseDir in baseDirs:
        for root, dirs, pathList in os.walk(baseDir):
            for path in filesToFind:
                if os.path.exists(os.path.join(root, path)):
                    allFiles.add(os.path.join(root, path))
                    notExists.discard(path)

            if addAll:
                for path in pathList:
                    fullPath = '/'.join((root, path))
                    if _isPythonFile(fullPath, negFilters=negFilters):
                        allFiles.add(fullPath)
    return list(allFiles), notExists

def main(args):
    parser = optparse.OptionParser()
    parser.usage = '%prog [-o <output file>] [-t <testsuite file>] ' \
        '<testsuite root> [<alias>=]<covered path>+'

    parser.add_option('-o', '--output', dest='output_file',
        help='Write coverage data to FILE', metavar='FILE')
    parser.add_option('-t', '--testsuite', dest='testsuite_file',
        help='Testsuite file FILE in which EXCLUDED_PATHS may be found',
        metavar='FILE')
    parser.set_defaults(testsuite_file='testsuite.py')
    (options, args) = parser.parse_args(args)

    if len(args) < 2:
        parser.error('Need a testsuite root and at least one covered path')

    test_root, path_pairs = args[0], args[1:]

    # Try to extract excluded paths from testsuite.py
    excludePaths = ['test', 'setup.py']
    found = False
    testsuite_path = os.path.join(test_root, options.testsuite_file)
    if os.path.exists(testsuite_path):
        testsuite_contents = open(testsuite_path).read()
        match = re.search('EXCLUDED_PATHS = (\[.*?\])',
            testsuite_contents, re.M | re.S)
        if match:
            excludePaths = eval(match.group(1))
            found = True
    if not found:
        print >>sys.stderr, 'EXCLUDED_PATHS not found in %s' % testsuite_path

    # Create mapping of coverage base dirs and their aliases
    baseDirs = []
    trees = {}
    for path_pair in path_pairs:
        if '=' in path_pair:
            tree, path = path_pair.split('=', 1)
        else:
            tree, path = '__main__', path_pair
        path = os.path.abspath(path)
        baseDirs.append(path)
        if tree in trees:
            print >>sys.stderr, 'Warning: path %s is replacing path %s ' \
                'in tree %s' % (path, trees[tree], tree)
        trees[tree] = path

    # Find all files to cover
    files, notExists = getFilesToAnnotate(baseDirs, exclude=excludePaths)

    # Collect data from this coverage run
    global coverage
    coverage = coverage.the_coverage
    coverage.cacheDir = os.path.join(test_root, '.coverage')
    coverage.restoreDir()

    # Analyze data and map files to sets of total and missing statements
    cover_data = {}
    for file in files:
        _, statements, _, missing, _ = coverage.analysis2(file)
        tree = tree_path = None
        for name, path in trees.iteritems():
            if file.startswith(path + os.path.sep):
                tree, tree_path = name, path
                break
        if tree:
            subpath = file[len(tree_path) + 1:]
            if tree == '__main__':
                path = subpath
            else:
                path = tree + '/' + subpath
            cover_data[path] = (statements, missing)
        else:
            print >>sys.stderr, 'File %s is part of the coverage report, ' \
                'but not part of any configured tree'

    # Dump a pickle in the requested format
    if options.output_file:
        cPickle.dump(cover_data, open(options.output_file, 'wb'), 2)
    else:
        out = cPickle.dumps(cover_data, 2)
        out = bz2.compress(out)
        out = out.encode('base64').strip()

        print '-----BEGIN COVERAGE DATA-----'
        print out
        print '-----END COVERAGE DATA-----'

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
