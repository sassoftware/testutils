
import os
import shutil
import signal
import subprocess
import time
import traceback

from testutils import base_server
from testutils import os_utils
from testutils import sock_utils

class ApacheServer(base_server.BaseServer):
    def __init__(self, topDir):
        base_server.BaseServer.__init__(self)
        self.serverpid = -1

        self.serverRoot = topDir + '/httpd'
        self.traceLog = os.path.join(self.serverRoot, 'trace.log')

        if os.path.exists(topDir):
            shutil.rmtree(topDir)

        # If a port has been initialized, don't overwrite it
        if not hasattr(self, 'port'):
            self.initPort()
        self.createConfig()
        self.semaphores = None
        self._serverFileName = self._getServerFileName()

    def getServerDir(self):
        raise NotImplementedError

    def getHttpdConfTemplate(self):
        return "%s/httpd.conf.in" % (self.getServerDir(), )

    def getPythonHandler(self):
        """
        Return the module that implements the handler code for mod_python
        """
        raise NotImplementedError

    def createConfig(self):
        paths = [ '/usr/lib64/httpd/modules', '/usr/lib/apache2',
                  '/usr/lib/httpd/modules', '/usr/lib64/apache2', ]
        os.makedirs(self.serverRoot + "/tmp")
        for path in paths:
            if os.path.isdir(path):
                os.symlink(path, self.serverRoot + "/modules")
                break
        httpdConfTemplate = self.getHttpdConfTemplate()
        os.system("sed 's|@PORT@|%s|;s|@DOCROOT@|%s|;s|@HANDLER@|%s|'"
                  " < %s > %s/httpd.conf"
                  % (str(self.port), self.serverRoot, self.getPythonHandler(),
                     httpdConfTemplate, self.serverRoot))
        self.tmpDir = self.serverRoot + '/tmp'
        self._createAppConfig()

    def _createAppConfig(self):
        pass

    def __del__(self):
        try:
            self.stop()
        except:
            pass

    def reset(self):
        self._reset()
        super(ApacheServer, self).reset()

    def _getServerFileName(self):
        for fname in [ '/usr/sbin/httpd', '/usr/sbin/httpd2',
                       '/usr/sbin/httpd2-prefork' ]:
            if os.path.exists(fname):
                return fname
        raise Exception("Unable to find apache executable")

    def start(self, resetDir = True):
        self._startAppSpecificTasks(resetDir = resetDir)
        if self.serverpid != -1:
            return

        # This may not be catching all semaphores (and may catch extra ones
        # too)
        oldSemaphores = os_utils.listSemaphores()

        if getattr(self, 'socket', None):
            self.socket.close()
            self.socket = None
        self.serverpid = os.fork()
        if self.serverpid == 0:
            try:
                os.chdir('/')
                #print "starting server in %s" % self.serverRoot
                args = (self._serverFileName,
                        "-X",
                        "-d", self.serverRoot,
                        "-f", "httpd.conf",
                        "-C", 'DocumentRoot "%s"' % self.serverRoot)
                # need to setpgrp because httpd stop kills the processgroup
                os.setpgrp()
                if getattr(self, 'socket', None):
                    self.socket.close()
                    self.socket = None
                os_utils.osEec(args)
            finally:
                traceback.print_exc()
                os._exit(70)
        else:
            pass
        sock_utils.tryConnect("localhost", self.port,
                             logFile = self.serverRoot + '/error_log')
        for _ in range(200):
            self.semaphores = os_utils.listSemaphores() - oldSemaphores
            if self.semaphores:
                break
            time.sleep(.1)

        os.mkdir(os.path.join(self.serverRoot, 'cscache'))

    def stop(self):
        if self.serverpid != -1:
            args = (self._serverFileName,
                    "-d", self.serverRoot,
                    "-f", "httpd.conf",
                    "-k", "stop",)
            stdout = stderr = open(os.devnull, "w")
            subprocess.call(args, stdout=stdout, stderr=stderr)

            try:
                os.kill(self.serverpid, signal.SIGTERM)
                os.kill(self.serverpid, signal.SIGKILL)
            except OSError, e:
                if e.errno != 0:
                    raise
            # Get rid of the semaphores we may have started (hopefully all of
            # them)
            if self.semaphores:
                args = ["/usr/bin/ipcrm", ]
                for sem in self.semaphores:
                    args.extend(["-s", sem])
                subprocess.call(args, stderr = open(os.devnull, "w"))
            self._stopAppSpecificTasks()
            self.serverpid = -1
            self.semaphores = None
            os.waitpid(self.serverpid, os.WNOHANG)

    def _startAppSpecificTasks(self, resetDir = True):
        pass

    def _stopAppSpecificTasks(self):
        pass

    def _reset(self):
        pass

class ApacheSSLMixin(object):
    # Assumes inheritance from ApacheServer, plus self.sslCert, self.sslKey
    def initPort(self):
        self.port, self.plainPort = sock_utils.findPorts(num = 2)

    def createConfig(self):
        shutil.copy(self.sslCert, os.path.join(self.serverRoot, "server.crt"))
        shutil.copy(self.sslKey, os.path.join(self.serverRoot, "server.key"))
        # append ssl config to standard config
        sslConfTemplate = "%s/httpd.conf.ssl.in" % (self.getServerDir(), )
        os.system("sed 's|@PORT@|%s|;s|@PLAINPORT@|%s|;"
                  "s|@DOCROOT@|%s|;s|@HANDLER@|%s|'"
                  " < %s >> %s/httpd.conf"
                  % (self.port, self.plainPort, self.serverRoot,
                     self.getPythonHandler(),
                     sslConfTemplate, self.serverRoot))
