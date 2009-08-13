#!/usr/bin/python
# -*- mode: python -*-
#
# Copyright (c) 2009 rPath, Inc.  All Rights Reserved.
#
import os
import os.path
import sys
import stat
# Search order:
# 1. absolute path
# 2. one dir up from the current repo (i.e. the same forest or parallel repo) 
# 3. If $RPATH_USE_SYSTEM_MODULES is set we search the existing system path
# 4. Start at $RPATH_DEV_REPO and look down assuming a directory structure like 
#     the Hg repo and prefering trunk to versioned checkouts
 
discoveryDefaults = { 'CONARY_POLICY_PATH':{'absPath':'/usr/lib/conary/policy'},
                      'CONARY_PATH':{'provides':'conary', 'path':'products/conary/$VERSION/conary'},
                      'CONARY_TEST_PATH':{'provides' : 'conarytest', 'path':'products/conary/$VERSION/conary-test'},
                      'CATALOG_SERVICE_PATH':
                          {'provides':'catalogService', 'path':'products/rbuilder/$VERSION/catalog-service'}, 
                      'CATALOG_SERVICE_TEST_PATH':
                          {'provides':'catalogService_test', 'path':'products/rbuilder/$VERSION/catalog-service-private'}, 
                      'XMLLIB_PATH':{'provides':'rpath-xmllib.xmllib', 'path':'products/rbuilder/$VERSION/rpath-xmllib'},
                      'XMLLIB_TEST_PATH':{'provides':'xmllib_test.xmllibtest', 'path':'products/rbuilder/$VERSION/rpath-xmllib-private'},
                      'STORAGE_PATH':{'provides':'rpath-storage.storage', 
                                      'path':'products/rbuilder/$VERSION/rpath-storage'},
                      'STORAGE_TEST_PATH':{'provides':'storage_test', 
                                      'path':'products/rbuilder/$VERSION/rpath-storage-private'},
                      'PRODUCT_DEFINITION_PATH': {'provides':'rpath-proddef.proddef', 
                                                  'path':'products/rbuilder/$VERSION/rpath-product-definition'},
                      'PRODUCT_DEFINITION_TEST_PATH': {'provides':'proddef_test', 
                                                       'path':'products/rbuilder/$VERSION/rpath-product-definition-private' },
                      'RESTLIB_PATH':{'provides':'restlib', 'path':'products/rbuilder/$VERSION/restlib'},
                      'RESTLIB_TEST_PATH':{'provides':'restlib_test', 'path':'products/rbuilder/$VERSION/restlib-private'},
                      'COMMON_PATH':{'provides':'rpath-common', 'path':'products/rbuilder/$VERSION/rpath-common'},
                      'XOBJ_PATH':{'provides':'xobj', 'path':'products/rbuilder/$VERSION/xobj/py'},
                      'XOBJ_TEST_PATH':{'provides':'xobjtest', 'path':'products/rbuilder/$VERSION/xobj/py/test'},
                      'BOTO_PATH':{'provides':'boto', 'path':'products/boto/$VERSION/boto'},
                      'RMAKE_PATH':{'provides':'rmake', 'path':'products/rmake/$VERSION/rmake'},
                      'RMAKE_TEST_PATH':{'provides':'rmake_test', 'path':'products/rmake/$VERSION/rmake-private'},
                      'MINT_PATH':{'provides':'mint', 'path':'products/rbuilder/$VERSION/mint'},
                      'MINT_TEST_PATH':{'provides':'mint_test', 'path':'products/rbuilder/$VERSION/mint/mint_test'},
                      'MINT_RAA_PLUGINS_PATH':{'provides':'rPath', 'path':'products/rbuilder/$VERSION/mint/raaplugins'},
                      'CREST_PATH':{'provides':'crest','path':'products/rbuilder/$VERSION/crest'},
                      'CREST_TEST_PATH':{'provides':'crest','path':'products/rbuilder/$VERSION/crest-test'},
                      'MCP_PATH':{'provides':'mcp', 'path':'products/rbuilder/$VERSION/mcp'},
                      'MCP_TEST_PATH':{'provides':'mcp_test', 'path':'products/rbuilder/$VERSION/mcp'},
                      'PACKAGE_CREATOR_SERVICE_PATH':{'provides':'preator', 'path':'products/rbuilder/$VERSION/pcreator'},
                      'PACKAGE_CREATOR_SERVICE_TEST_PATH':
                          {'provides':'factory_test', 'path':'products/rbuilder/$VERSION/pcreator-test'},
                      'RBUILD_PATH':{'provides':'rbuild', 'path':'products/rbuild/$VERSION/rbuild'},
                      'RBUILD_TEST_PATH':{'provides':'rbuild_test', 'path':'products/rbuild/$VERSION/rbuild-private'},
                      'STOMP_PATH':{'provides':'stomp', 'path':'products/rbuilder/$VERSION/stomp.py'},
                      'PYOVF_PATH':{'provides':'pyovf', 'path':'products/rbuilder/$VERSION/pyovf'},
                      'PYOVF_TEST_PATH':{'provides':'functionaltests', 'path':'products/rbuilder/$VERSION/pyovf/test'},
                      'JOB_MASTER_PATH':{'provides':'jobmaster', 'path':'products/rbuilder/$VERSION/jobmaster'},
                      'JOB_MASTER_TEST_PATH':{'provides':'jobmaster_helper', 'path':'products/rbuilder/$VERSION/jobmaster/test'},
                      'JOB_SLAVE_PATH':{'provides':'jobslave', 'path':'products/rbuilder/$VERSION/jobslave'},
                      'JOB_SLAVE_TEST_PATH':{'provides':'jobslave_helper', 'path':'products/rbuilder/$VERSION/jobslave/test'},
                      'RAA_PATH':{'provides':'raa', 'path':'products/raa/$VERSION/raa'},
                      'RAA_TEST_PATH':{'provides':'raatest', 'path':'products/raa/$VERSION/raa-test'},
                      'RAA_PLUGINS_PATH':{'provides':'raaplugins', 'path':'products/raa/$VERSION/raa/raaplugins'},
                      'RBM_PATH':{'provides':'rbm_rc', 'path':'products/rbm/$VERSION/rbm/src'},
                      'RBM_TEST_PATH':{'provides':'test', 'path':'products/rbm/$VERSION/rbm'},
                      'RBM_RAA_PLUGINS_PATH':{'provides':'rPath', 'path':'products/rbuilder/$VERSION/rbm/raaplugins'},
                      }

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

def addExecPath( varname, path=None):
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
            else:
                sys.stderr.write("'%s' was set but '%s' does not exist!\n" % (varname,p) )
                sys.exit(-1)
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
        if not pathList:
            sys.stderr.write("Path '%s' provided for '%s' contains no valid paths.\n" % (path,varname) )
            sys.exit(-1)

        # update the environment
        os.environ[varname] = ":".join(pathList)
    else:
        # we have to discover the path
        path = discover(varname)
        if path:
            os.environ[varname] = path
            pathList.append(path)
            updatePaths( path )

    return ":".join(pathList)

def addResourcePath( varname, path, existenceOptional=False):
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

        # we have a valid path so update the enviro
        path = ":".join(pathList)            
        os.environ[varname] = path
    else:
        sys.stderr.write("'%s' was not set and '%s' does not exist!\n" % (varname,path) )
        sys.exit(-1)
    
    return ":".join(pathList)
        
def discover( varname ):
    if not discoveryDefaults.has_key(varname):
        sys.exit("Don't know how to auto-discover variable %r" % (varname,))
    varDict = discoveryDefaults[varname]

    # 1. if there's a absolute path for this variable, we just use it
    if varDict.has_key( 'absPath' ):
        if os.path.exists( varDict['absPath'] ):
            return varDict['absPath']
        else:
            sys.exit("Variable %r is configured to be %r but the "
                    "path does not exist!" % (varname, varDict['absPath']))

    forestName, treeName = varDict['path'].split('$VERSION/', 1)

    # 2. we look in the one level up from the existing repo
    # (this handles forest and simple repos that live next to each other)
    thisTree = getMercurialRoot(sys.path[0])
    if thisTree:
        thisForest = os.path.dirname(thisTree)
        path = os.path.join(thisForest, treeName)
        if os.path.exists(path):
            return path

    # 3. we drill down from the top and prefer trunk to numbered versions
    devRoot = os.getenv('RPATH_DEV_ROOT')
    if devRoot:
        forestPath = os.path.join(devRoot, forestPath)
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
        except ImportError:
            pass
        else:
            path = module.__file__
            if os.path.basename(path).rsplit('.', 1)[0] == '__init__':
                path = os.path.dirname(path)
            for n in range(moduleName.count('.') + 1):
                path = os.path.dirname(path)
            return path

    print >> sys.stderr, "Could not auto-discover variable", varname
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
    pythonPath = os.getenv('PYTHONPATH').split(os.pathsep)
    
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
