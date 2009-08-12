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
            
        if not path:
            sys.stderr.write("Auto-discovery of path for '%s' has failed!\n" % (varname) )
            sys.exit(-1)
        else:
            os.environ[varname] = path
            pathList.append(path)
            if path != '**SYSTEM**':
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
    # lookup the var in our default
    if discoveryDefaults.has_key( varname ):
        varDict = discoveryDefaults[ varname ]
        # 1. if there's a absolute path for this variable, we just use it
        if varDict.has_key( 'absPath' ):
            if os.path.exists( varDict['absPath'] ):
                return varDict['absPath']
            else:
                sys.stderr.write("'%s' was configured to be '%s' but the path does not exist!\n" 
                                 % (varname, varDict['absPath'] ) )
                sys.exit(-1)
        
        # 2. we look in the one level up from the existing repo
        # (this handles forest and simple repos that live next to each other)
        outOfRepoPath = walkOutOfRepo(sys.path[0])
        pathTemplate = os.path.join( os.getenv("RPATH_DEV_ROOT"), varDict['path'] )
        ( preVerPath, postVerPath ) = pathTemplate.split('$VERSION/',1)

        path = os.path.join( outOfRepoPath, postVerPath )
        if os.path.exists( path ):
            return path

        # 3. we look in the system if the right env var is set
        if os.getenv("RPATH_USE_SYSTEM_MODULES"):
            try:
                cmd = 'import ' + varDict['provides']
                exec cmd
            except KeyError:
                sys.stderr.write("Auto-discovery configuration doesn't have a 'module' "
                                 "entry for '%s' even though RPATH_USE_SYSTEM_MODULES is set!\n" % (varname) )
                sys.exit(-1)
            except ImportError:
                sys.stderr.write("Unable to import '%s' for '%s' even though RPATH_USE_SYSTEM_MODULES "
                                 "is set!\n" % (varDict['provides'], varname) )
                sys.exit(-1)
            # ok, we've sucessfully imported so all is good
            return "**SYSTEM**"
        
        # 4. we drill down from the top and prefer trunk to numbered versions
        dirL = os.listdir( preVerPath )
        vers = {}
        selectedVer = None
        for f in dirL:
            fp = os.path.join( preVerPath, f )

            if os.path.isdir( fp ):
                if f.lower() == 'trunk':
                    selectedVer = f
                    break
                
                try:
                    vers[float(f)] = f
                except:
                    pass
        
        if selectedVer:
            path = os.path.join(preVerPath,selectedVer,postVerPath)
            if os.path.exists(path):
                return path
            else:
                sys.stderr.write("Auto discovered path ''%s'' for '%s' but it doesn't exist. You might need"
                                 " to check something out or the discovery config is wront.\n"
                                 % (varDict['provides'], varname) )
                sys.exit(-1)
        maxKey = max(vers.keys())
        path = os.path.join(preVerPath,vers[maxKey],postVerPath)
        if os.path.exists(path):
            return path

    sys.stderr.write("'%s' has no configuration for auto-discovery!\n" % (varname) )
    sys.exit(-1)

def updatePaths( path ):
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

def walkOutOfRepo( path ):
    # walk up and look for the .hg dir
    repoStr = None
    currPath = path
    while True:
        try:
            hgPath = os.path.join( currPath, '.hg/hgrc' )    
            for l in open(hgPath):
                if l[0:7] == 'default':
                    repoStr = l
                    break
        except:
            # we could distinguish failures here and flag .hg/hgrc instance with no read access
            pass

        if currPath != '/' and not repoStr:
            (currPath, currDir) = os.path.split( currPath )
        else:
            break

    if not repoStr:
        sys.stderr.write("Unable to find the .hg/hgrc in the dir stack. '%s' does not appear to be in a repository.\n"
                         % (path) )
        sys.exit(-1)

    # walk up and look for the first instance of a non-matching or nonexistent repo str
    (currPath, currDir) = os.path.split( currPath )
    weAreOut=False
    while not weAreOut:
        try:
            hgPath = os.path.join( currPath, '.hg/hgrc' )    
            for l in open(hgPath):
                if l[0:7] == 'default':
                    if l != repoStr:
                        weAreOut = True
                    break
            if not weAreOut:
                (currPath, currDir) = os.path.split( path )
        except:
            weAreOut = True
            
    return currPath            
