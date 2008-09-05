import os,sys, shutil

class Environment(object):
    def __init__(self, repositoryLocation, moduleDir, pythonPathDir):
        self.repositoryLocation = repositoryLocation
        self.moduleDir = moduleDir
        self.pythonPathDir = pythonPathDir

    def clone(self, module):
        print 'Cloning %s to %s...' % (module, self.moduleDir)
        dest = '%s/%s' % (self.moduleDir, os.path.basename(module))
        if os.path.lexists(dest):
            if os.path.islink(dest):
                os.remove(dest)
            elif os.path.isdir(dest):
                shutil.rmtree(dest)
            else:
                os.remove(dest)
        os.system('hg clone %s/%s %s' % (self.repositoryLocation, module, dest))
        if not os.path.exists(dest):
            return None
        return dest

class Module(object):
    def __init__(self, moduleName, setup=None, environName=None, 
                 reposName=None, test=None, modulePath = None,
                 shouldClone=True):
        self.moduleName = moduleName
        if reposName is None:
            reposName = moduleName
        self.reposName = reposName
        if environName is None:
            moduleName = os.path.basename(moduleName)
            environName = moduleName.upper().replace('-', '_') + '_PATH'
        self.environName = environName
        if test is None:
            test = 'import %s' % moduleName
        self.setup = setup
        self.testString = test
        self.modulePath = modulePath
        self.shouldClone = shouldClone

    def findModulePath(self, env):
        if self.environName in os.environ:
            path = os.environ[self.environName]
            if os.path.exists(path):
                return path
        subdir = env.moduleDir
        for i in range(3):
            path = subdir + '/%s%s' % ('../' * i,
                                       os.path.basename(self.reposName))
            if os.path.exists(path):
                path = os.path.realpath(path)
                return path
        if self.shouldClone:
            path = env.clone(self.reposName)
            if path and self.setup:
                os.system('cd %s; %s' % (path, self.setup))
            return path

    def load(self, env):
        if not self.modulePath:
            path = self.findModulePath(env)
            if not path:
                return
        else:
            path = self.modulePath
            if not path.startswith('/'):
                path = os.path.join(env.moduleDir, path)
            path = os.path.realpath(path)
        modulePath = '%s/%s' % (env.moduleDir, os.path.basename(self.reposName))
        pythonPath = env.pythonPathDir
        if path != modulePath:
            linkPath = None
            if os.path.lexists(modulePath):
                if os.path.islink(modulePath):
                    linkPath = os.readlink(modulePath)
                    os.remove(modulePath)
                else:
                    shutil.rmtree(modulePath)
            if linkPath != path:
                print 'Using %s from %s' % (self.reposName, path)
            os.symlink(path, modulePath)
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
                if os.path.lexists(pythonPathSubDir):
                    os.remove(pythonPathSubDir)
                os.symlink(subDirPath, pythonPathSubDir)
        self.modulePath = modulePath
        os.environ[self.environName] = self.modulePath

    def test(self):
        try:
            if self.testString:
                exec self.testString
        except Exception, e:
            raise RuntimeError('Error testing %s: %s' % (self.moduleName, e))

def loadSupportingModules(moduleList=None, topDir='..'):
    if moduleList is None:
        moduleList = modules
    moduleDir = os.path.realpath('%s/supporting_modules' % topDir)
    pythonPath = os.path.realpath('%s/pythonpath' % topDir)
    sys.path.insert(0, pythonPath)
    if not os.path.exists(moduleDir):
        os.mkdir(moduleDir)
    if not os.path.exists(pythonPath):
        os.mkdir(pythonPath)
    env = Environment('ssh://hg//hg/', moduleDir, pythonPath)
    for module in moduleList:
        module.load(env)
    for module in moduleList:
        module.test()
    os.environ['PYTHONPATH'] = ':'.join(sys.path)


if __name__ == '__main__':
    loadSupportingModules(modules, os.path.realpath('../supporting_modules'))
