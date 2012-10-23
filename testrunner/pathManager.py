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


import os
import os.path
import sys

# Search order:
# 1. absolute path
# 2. one dir up from the current repo (i.e. the same forest or parallel repo)
# 3. Start at $RPATH_DEV_ROOT and look down assuming a directory structure like
#     the Hg repo and prefering trunk to versioned checkouts
# 4. If $RPATH_USE_SYSTEM_MODULES is set we search the existing system path

discoveryDefaults = {
        # Conary, etc.
        'CONARY_CIM_PATH' : {
            'path' : 'products/conary-cim/$VERSION/conary-cim',
        },
        'CONARY_POLICY_PATH': {
            'absPath':'/usr/lib/conary/policy'},
        'CONARY_PATH': {
            'provides':'conary',
            'path':'products/conary/$VERSION/conary'},
        'CONARY_TEST_PATH': {
            'provides':'conarytest',
            'path':'products/conary/$VERSION/conary-test'},
        'CREST_PATH': {
            'provides':'crest',
            'path':'products/rbuilder/$VERSION/crest'},
        'CREST_TEST_PATH': {
            'provides':'crest',
            'path':'products/rbuilder/$VERSION/crest-test'},
        'RBCLIENT_PATH': {
            'provides':'rbclient',
            'path':'products/rbuild/$VERSION/rbuilder-client'},
        'RBCLIENT_TEST_PATH': {
            'provides':'rbiclient_test',
            'path':'products/rbuild/$VERSION/rbuilder-client-private'},
        'RBUILD_PATH': {
            'provides':'rbuild',
            'path':'products/rbuild/$VERSION/rbuild'},
        'RBUILD_TEST_PATH': {
            'provides':'rbuild_test',
            'path':'products/rbuild/$VERSION/rbuild-private'},
        'REPODATA_PATH' : {
            'provides':'repodata',
            'path':'products/rbuilder/$VERSION/repodata'},
        'RMAKE_PATH': {
            'provides':'rmake',
            'path':'products/rmake/$VERSION/rmake'},
        'RMAKE_TEST_PATH': {
            'provides':'rmake_test',
            'path':'products/rmake/$VERSION/rmake-private'},
        'REPEATER_PATH' : {
            'provides':'rpath_repeater',
            'path':'products/rbuilder/$VERSION/rpath-repeater'},
        'ICONFIG_PATH': {
            'provides':'iconfig',
            'path':'products/iconfig/$VERSION/iconfig'},
        'ICONFIG_TEST_PATH': {
            'path':'products/iconfig/$VERSION/iconfig/test'},

        # rBuilder
        'CATALOG_SERVICE_PATH': {
            'provides':'catalogService',
            'path':'products/rbuilder/$VERSION/catalog-service'},
        'CATALOG_SERVICE_TEST_PATH': {
            'provides':'catalogService_test',
            'path':'products/rbuilder/$VERSION/catalog-service-private'},
        'CAPSULE_INDEXER_PATH' : {
            'provides':'rpath_capsule_indexer',
            'path':'products/rbuilder/$VERSION/rpath-capsule-indexer'},
        'CAPSULE_INDEXER_TEST_PATH' : {
            'provides':'capsule_indexertest',
            'path':'products/rbuilder/$VERSION/rpath-capsule-indexer-test'},
        'JOB_MASTER_PATH': {
            'provides':'jobmaster',
            'path':'products/rbuilder/$VERSION/jobmaster'},
        'JOB_SLAVE_PATH': {
            'provides':'jobslave',
            'path':'products/rbuilder/$VERSION/jobslave'},
        'MCP_PATH': {
            'provides':'mcp',
            'path':'products/rbuilder/$VERSION/mcp'},
        'MINT_PATH': {
            'provides':'mint',
            'path':'products/rbuilder/$VERSION/mint'},
        'MINT_TEST_PATH': {
            'provides':'mint_test',
            'path':'products/rbuilder/$VERSION/mint'},
        'MINT_RAA_PLUGINS_PATH': {
            'provides':'rPath',
            'path':'products/rbuilder/$VERSION/mint/raaplugins'},
        'PACKAGE_CREATOR_SERVICE_PATH': {
            'provides':'pcreator',
            'path':'products/rbuilder/$VERSION/pcreator'},
        'PACKAGE_CREATOR_SERVICE_TEST_PATH': {
            'provides':'factory_test',
            'path':'products/rbuilder/$VERSION/pcreator-test'},

        # rPA
        'RAA_PATH': {
            'provides':'raa',
            'path':'products/raa/$VERSION/raa'},
        'RAA_TEST_PATH': {
            'provides':'raatest',
            'path':'products/raa/$VERSION/raa-test'},
        'RAA_PLUGINS_PATH': {
            'provides':'raaplugins',
            'path':'products/raa/$VERSION/raa/raaplugins'},

        # Other products
        'RBM_PATH': {
            'provides':'rbm_rc',
            'path':'products/rbm/$VERSION/rbm/src'},
        'RBM_TEST_PATH': {
            'provides':'test',
            'path':'products/rbm/$VERSION/rbm'},
        'RBM_RAA_PLUGINS_PATH': {
            'provides':'rPath',
            'path':'products/rbuilder/$VERSION/rbm/raaplugins'},
        'RPATH_TOOLS_PATH': {
            'provides':'rpath_tools',
            'path':'products/rpath-tools/$VERSION/rpath-tools'},

        # Common libraries
        'JOB_PATH': {
            'provides':'rpath_job',
            'path':'products/rbuilder/$VERSION/rpath-job'},
        'MODELS_PATH': {
            'provides':'rpath_models',
            'path':'products/rbuilder/$VERSION/rpath-models'},
        'PYOVF_PATH': {
            'provides':'pyovf',
            'path':'products/rbuilder/$VERSION/pyovf'},
        'PYOVF_TEST_PATH': {
            'provides':'functionaltests',
            'path':'products/rbuilder/$VERSION/pyovf/test'},
        'PRODUCT_DEFINITION_PATH': {
            'provides':'rpath_proddef',
            'path':'products/rbuilder/$VERSION/rpath-product-definition'},
        'PRODUCT_DEFINITION_TEST_PATH': {
            'provides':'proddef_test',
            'path':'products/rbuilder/$VERSION/rpath-product-definition-private'},
        'RESTLIB_PATH': {
            'provides':'restlib',
            'path':'products/rbuilder/$VERSION/restlib'},
        'RESTLIB_TEST_PATH': {
            'provides':'restlib_test',
            'path':'products/rbuilder/$VERSION/restlib-private'},
        'SMARTFORM_PATH' : {
            'provides':'smartform',
            'path':'products/rbuilder/$VERSION/smartform/py'},
        'STORAGE_PATH': {
            'provides':'rpath_storage',
            'path':'products/rbuilder/$VERSION/rpath-storage'},
        'STORAGE_TEST_PATH': {
            'provides':'storage_test',
            'path':'products/rbuilder/$VERSION/rpath-storage-private'},
        'XMLLIB_PATH': {
            'provides':'rpath_xmllib',
            'path':'products/rbuilder/$VERSION/rpath-xmllib'},
        'XMLLIB_TEST_PATH': {
            'provides':'xmllibtest',
            'path':'products/rbuilder/$VERSION/rpath-xmllib-private'},
        'XOBJ_PATH': {
            'provides':'xobj',
            'path':'products/rbuilder/$VERSION/xobj/py'},
        'XOBJ_TEST_PATH': {
            'provides':'xobjtest',
            'path':'products/rbuilder/$VERSION/xobj/py/test'},
        'ROBJ_PATH': {
            'provides':'robj',
            'path':'products/rbuilder/$VERSION/robj'},
        'ROBJ_TEST_PATH': {
            'provides':'robjtest',
            'path':'products/rbuilder/$VERSION/robj/test'},
        'WMICLIENT_PATH' : {
            'provides':'wmiclient',
            'path':'products/rbuilder/$VERSION/wmiclient/py'},

        # Third-party libraries
        'BOTO_PATH': {
            'provides':'boto',
            'path':'products/boto/$VERSION/boto'},
        'STOMP_PATH': {
            'provides':'stomp',
            'path':'products/rbuilder/$VERSION/stomp.py'},

        # infra projects
        'SELFSERVE_PATH' : {
            'provides': 'models',
            'path' : 'infra/selfserve'},
        'SELFSERVE_TEST_PATH' : {
            'provides':'unit_test',
            'path':'infra/selfserve/selfserve_test/'},
        }

class SystemPathTemplate(object):
    def __init__(self, variable, returnTrue, returnFalse):
        self.variable = variable
        self.returnTrue = returnTrue
        self.returnFalse = returnFalse

    def evaluate(self):
        value = getPath(self.variable)
        if 'site-packages' in value:
            return self.returnTrue
        return self.returnFalse

resourceDefaults = dict(
    CONARY_ARCHIVE_PATH = dict(
        variables = [ 'CONARY_TEST_PATH' ],
        template = "%(CONARY_TEST_PATH)s/archive",
    ),
    RMAKE_ARCHIVE_PATH = dict(
        variables = [ 'RMAKE_TEST_PATH' ],
        template = "%(RMAKE_TEST_PATH)s/rmake_test/archive",
    ),
    RBUILD_ARCHIVE_PATH = dict(
        variables = [ 'RBUILD_TEST_PATH' ],
        template = "%(RBUILD_TEST_PATH)s/rbuild_test/archive",
    ),
    RBUILD_PLUGIN_PATH = dict(
        variables = [ 'RBUILD_PATH' ],
        template = SystemPathTemplate('RBUILD_PATH',
            '/usr/share/rbuild/plugins',
            '%(RBUILD_PATH)s/plugins'),
    ),
    RMAKE_PLUGIN_PATHS = dict(
        variables = [ 'RMAKE_PATH' ],
        template = SystemPathTemplate('RMAKE_PATH',
            [ '/usr/share/rmake/plugins' ], [ '%(RMAKE_PATH)s/rmake_plugins' ]),
    ),
)

def getPath( varname ):
    v = os.getenv(varname)
    if v:
        return v
    sys.stderr.write("Path '%s' was requested but it is not defined. Perhaps something needs to be added to testsuite.py?\n" % (varname) )
    sys.exit(-1)

def getPathList( varname ):
    v = os.getenv(varname)
    if v:
        return v.split(":")
    sys.stderr.write("Path '%s' was requested but it is not defined. Perhaps something needs to be added to testsuite.py?\n" % (varname) )
    sys.exit(-1)

def getCoveragePath(varname):
    if not discoveryDefaults.has_key(varname):
        sys.exit("Don't know how to auto-discover variable %r" % (varname,))
    varDict = discoveryDefaults[varname]
    v = getPath(varname)
    return os.path.join(v, varDict['provides'])

def addExecPath(varname, path=None, isTestRoot=False, existenceOptional=False):
    varval = os.getenv(varname)
    if type(path) == str:
        path = path.split(":")
    pathList = []
    if varval:
        pl = varval.split(":")
        for p in pl:
            if os.path.exists( p ):
                # env var already exists so we just update the paths
                updatePaths( p )
                pathList.append(p)
            elif not existenceOptional:
                sys.stderr.write("'%s' was set but '%s' does not exist!\n" 
                                 % (varname,p) )
                sys.exit(-1)
            else:
                return ""
    elif path:
        for p in path:
            p = os.path.abspath(p)
            if os.path.exists( p ):
                # we have a valid path
                updatePaths( p )
                pathList.append(p)
            else:
                sys.stderr.write("WARNING: Path specified for '%s' contains '%s' but it does not exist. "
                                 "Ignoring\n" % (varname,p) )
        if not pathList and not existenceOptional:
            sys.stderr.write(
                "Path '%s' provided for '%s' contains no valid paths.\n"
                % (path,varname) )
            sys.exit(-1)

        # update the environment
        os.environ[varname] = ":".join(pathList)
    else:
        # we have to discover the path
        path = discover(varname,discoveryOptional=existenceOptional)
        if path:
            os.environ[varname] = path
            pathList.append(path)
            updatePaths( path )

    if isTestRoot:
        assert len(pathList) == 1
        addExecPath('TEST_PATH', pathList[0])

    return ":".join(pathList)

def addResourcePath( varname, path=None, existenceOptional=False):
    varval = os.getenv(varname)
    if type(path) == str:
        path = path.split(":")

    pathList = []
    if varval:
        pl = varval.split(":")
        for p in pl:
            if os.path.exists( p ) or existenceOptional:
                pathList.append(p)
            else:
                sys.stderr.write("WARNING: '%s' contains '%s' but it does not exist.  Ignoring\n" % (varname,p) )
        if not pathList:
            sys.stderr.write("'%s' was set but contains no valid paths.\n" % (varname) )
            sys.exit(-1)
    elif path:
        for p in path:
            p = os.path.abspath(p)
            if os.path.exists( p ) or existenceOptional:
                pathList.append(p)
            else:
                sys.stderr.write("WARNING: Path specified for '%s' contains '%s' but it does not exist.  Ignoring\n" % (varname,p) )
        if not pathList:
            sys.stderr.write("Path '%s' provided for '%s' contains no valid paths.\n" % (path,varname) )
            sys.exit(-1)
    else:
        pathList = discoverResource(varname)

    # we have a valid path so update the enviro
    path = ":".join(pathList)
    os.environ[varname] = path
    return path

def discoverResource(varname):
    if varname not in resourceDefaults:
        sys.stderr.write("'%s' could not be auto-discovered!\n" % (varname,) )
        sys.exit(-1)
    discovered = resourceDefaults[varname]
    # Grab the variables needed for computing the value
    varDict = dict( (v, getPath(v)) for v in discovered['variables'])
    template = discovered['template']
    if isinstance(template, SystemPathTemplate):
        template = template.evaluate()
    # Expand template values
    if isinstance(template, basestring):
        return [ template % varDict ]
    return [ x % varDict for x in template ]

def discover( varname, discoveryOptional = False ):
    devRoot = os.getenv('RPATH_DEV_ROOT')

    if not discoveryDefaults.has_key(varname):
        sys.exit("Don't know how to auto-discover variable %r" % (varname,))
    varDict = discoveryDefaults[varname]

    # 1. if there's a absolute path for this variable, we just use it
    absPath = varDict.get('absPath')
    if absPath:
        if os.path.exists(absPath):
            return absPath
        elif not discoveryOptional:
            sys.exit("Variable %r is configured to be %r but the "
                    "path does not exist!" % (varname, absPath))

    l = varDict['path'].split('$VERSION/', 1)
    if len(l) == 2:
        (forestName, treeName) = l
        # 2. we look in the one level up from the existing repo
        # (this handles forest and simple repos that live next to each other)
        thisTree = getMercurialRoot()
        if thisTree:
            thisForest = os.path.dirname(thisTree)
            path = os.path.join(thisForest, treeName)
            if os.path.exists(path):
                return path
    else:
        treeName = l[0]
        #2.1. we see if the give path is valid relitive to the repo root
        if devRoot:
            path = os.path.join(devRoot, treeName)
            if os.path.exists(path):
                return path
        return None
    # 3. we drill down from the top and prefer trunk to numbered versions
    forestPath = None
    if devRoot:
        forestPath = os.path.join(devRoot, forestName)
        if os.path.isdir(forestPath):
            dirL = os.listdir(forestPath)
            vers = {}
            selectedVer = None
            for f in dirL:
                fp = os.path.join(forestPath, f)

                if os.path.isdir( fp ):
                    if f.lower() == 'trunk':
                        selectedVer = f
                        break

                    try:
                        vers[float(f)] = f
                    except ValueError:
                        pass

            if vers:
                if not selectedVer:
                    maxVersion = max(vers.keys())
                    selectedVer = vers[maxVersion]

                path = os.path.join(forestPath, selectedVer, treeName)
                if os.path.exists(path):
                    return path

    # 4. we look in the system
    if os.getenv("RPATH_USE_SYSTEM_MODULES") and 'provides' in varDict:
        moduleName = varDict['provides']
        try:
            module = __import__(moduleName)
        except ImportError, e:
            print "Trying to import ", moduleName, " resulted in: ", str(e)
        else:
            path = module.__file__
            if os.path.basename(path).rsplit('.', 1)[0] == '__init__':
                path = os.path.dirname(path)
            for n in range(moduleName.count('.') + 1):
                path = os.path.dirname(path)
            return path

    if not discoveryOptional:
        print >> sys.stderr, "Could not auto-discover variable", varname
    else:
        return ""
    if not devRoot:
        print >> sys.stderr, ("HINT: Try setting RPATH_DEV_ROOT to the root "
                "of your checkout tree.")
    elif not thisTree:
        print >> sys.stderr, ("HINT: Try running this command from inside "
                "the Hg checkout.")
    elif not os.path.isdir(forestPath):
        suggest = os.path.join(forestPath, 'trunk', treeName)
        print >> sys.stderr, ("HINT: Try checking out %s , if it exists."
                % (suggest,))

    sys.exit(1)


def updatePaths( path ):
    if path.endswith('/site-packages'):
        # Imported from the system; no need to explicitly insert it.
        return

    # add path to sys.path and PYTHONPATH
    pythonPath = os.getenv('PYTHONPATH', '').split(os.pathsep)

    if path in pythonPath:
        pythonPath.remove(path)
    pythonPath.insert(0,path)

    if path != sys.path[0]:
        if path in sys.path:
            sys.path.remove(path)
        sys.path.insert(1,path)

    os.environ['PYTHONPATH'] = os.pathsep.join(pythonPath)


def getMercurialRoot(path='.'):
    """
    Find the root of the current mercurial checkout, if any. Returns the
    absolute path to the root, or C{None} if not in a checkout.
    """
    path = os.path.normpath(os.path.abspath(path))
    while path != '/':
        if os.path.isdir(path + '/.hg'):
            return path
        path = os.path.dirname(path)
    return None
