import os,sys, shutil

class PythonModule(object):
    """
    Python module meta information to be used to determine
    how to find and load a python module required by another
    program.

    @param moduleName: the canonical name of the package.
       Used mostly to set defaults for other parameters.
    @param environName: environment variable name to look
       at to specify the path for tihs module.
    @param modulePath: a hardcoded path for this module.
       If relative, is relative to the .supporting_modules directory.
    @param test: python code to execute to see if this module
       was loaded successfully.
    @param shouldClone: if true, search in the mercurial
       repository for this package.
    @param reposName: name to use when searching the repository.
       Defaults to moduleName.
    @param setup: shell code to execute after checking out
       this package from the repository.
    """
    def __init__(self, moduleName,  environName=None,
                 test=None, modulePath = None,
                 shouldClone=True, reposName=None,
                 setup=None):
        self.moduleName = moduleName
        if reposName is None:
            reposName = moduleName
        self.reposName = reposName
        if environName is None:
            environName = os.path.basename(moduleName)
            environName = environName.upper().replace('-', '_') + '_PATH'
        self.environName = environName
        if test is None:
            test = 'import %s' % moduleName
        self.setup = setup
        self.testString = test
        self.modulePath = modulePath
        self.shouldClone = shouldClone

    def find(self, moduleDir):
        """
        Find this location to load this module from it if it is on
        disk, using a hard-coded path if given, then looking at
        the environment variable, then searching to see if
        it already exists in higher-level directories.
        """
        if self.modulePath:
            return self.modulePath

        if self.environName in os.environ:
            path = os.environ[self.environName]
            if os.path.exists(path):
                return path
        for i in range(4):
            path = moduleDir + '/%s%s' % ('../' * i,
                                           os.path.basename(self.reposName))
            if os.path.exists(path):
                path = os.path.realpath(path)
                return path

    def test(self):
        """
        Ensure that this module has been loaded successfully.
        """
        if self.testString:
            try:
                exec self.testString
            except Exception, e:
                raise RuntimeError('Error testing %s: %s' % (self.moduleName, e))



class ModuleLoader(object):
    """
    Finds and creates symlinks to modules in a specified
    directory, also creating a pythonPath entry if possible.
    @param moduleList: list of PythonModule objects to be 
    loaded.
    @param topDir: directory under which modules and python path
    directories should be stored.
    @param repositoryLocation: location of mercurial repositories
    """
    def __init__(self, moduleList, topDir, shouldClone=False,
                 repositoryLocation=None):
        moduleDir = os.path.realpath(topDir + '/supporting_modules')
        pythonPathDir = os.path.realpath(topDir + '/pythonpath')
        self.repositoryLocation = repositoryLocation
        self.moduleDir = moduleDir
        self.pythonPathDir = pythonPathDir
        self.moduleList = moduleList

    def loadModules(self):
        if not os.path.exists(self.moduleDir):
            os.makedirs(self.moduleDir)
        if not os.path.exists(self.pythonPathDir):
            os.makedirs(self.pythonPathDir)
        if self.pythonPathDir not in sys.path:
            sys.path.insert(0, self.pythonPathDir)
        for module in self.moduleList:
            self.loadModule(module)

    def testModules(self):
        for module in self.moduleList:
            module.test()

    def loadModule(self, module):
        path = module.find(self.moduleDir)
        if not path:
            if self.shouldClone and module.shouldClone:
                path = self._clone(module, self.moduleDir)
                if module.setup:
                    os.system('cd %s; %s' % (path, module.setup))
            else:
                return
        if not path.startswith('/'):
            path = os.path.join(self.moduleDir, path)
        path = os.path.realpath(path)
        modulePath = '%s/%s' % (self.moduleDir, os.path.basename(module.reposName))
        if path != modulePath:
            _link(path, modulePath)

        self._linkPythonPath(module, path, modulePath)
        module.modulePath = modulePath
        os.environ[module.environName] = module.modulePath

    def _linkPythonPath(self, module, path, modulePath):
        pythonPath = self.pythonPathDir
        pythonFiles = []
        subdirs = []
        for file in os.listdir(modulePath):
            if file.endswith('.py') and file not in ['cotton.py', 'setup.py']:
                pythonFiles.append(file)
                break
            subDirPath = '%s/%s' % (modulePath, file)
            if os.path.exists('%s/__init__.py' % subDirPath):
                subdirs.append(file)
        if pythonFiles:
            sys.path.insert(0, modulePath)
        else:
            for subdir in subdirs:
                pythonPathSubDir = '%s/%s' % (pythonPath, subdir)
                subDirPath = '%s/%s' % (modulePath, subdir)
                _link(subDirPath, pythonPathSubDir)

    def _clone(self, module, targetDir):
        print 'Cloning %s to %s (set %s to use existing version)...' % (module.moduleName, targetDir, module.environName)
        dest = '%s/%s' % (targetDir, os.path.basename(module.reposName))
        _remove(dest)
        os.system('hg clone %s/%s %s' % (self.repositoryLocation, module.reposName, dest))
        if not os.path.exists(dest):
            return None
        return dest



def _remove(path):
   if os.path.lexists(path):
        if os.path.islink(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

def _link(source, target):
    _remove(target)
    os.symlink(source, target)


def loadModules(moduleList, topDir='..'):
    m = ModuleLoader(moduleList, topDir, 'ssh://scc.eng.rpath.com//hg/')
    try:
        m.loadModules()
        m.testModules()
    except Exception, e:
        import epdb
        epdb.post_mortem(sys.exc_info()[2])
    os.environ['PYTHONPATH'] = ':'.join(sys.path)
