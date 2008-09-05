import sys
import types
import unittest

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

