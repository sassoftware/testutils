#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import errno
import os
import signal
import time
import traceback


class Subprocess(object):
    # Class settings
    setsid = False

    # Runtime variables
    pid = None
    exitStatus = exitPid = None

    @property
    def exitCode(self):
        if self.exitStatus is None:
            return -2
        elif self.exitStatus < 0:
            return self.exitStatus
        elif os.WIFEXITED(self.exitStatus):
            return os.WEXITSTATUS(self.exitStatus)
        else:
            return -2

    def start(self):
        self.exitStatus = self.exitPid = None
        self.pid = os.fork()
        if not self.pid:
            #pylint: disable-msg=W0702,W0212
            try:
                try:
                    if self.setsid:
                        os.setsid()
                    ret = self._run()
                    if not isinstance(ret, (int, long)):
                        ret = bool(ret)
                    os._exit(ret)
                except SystemExit, err:
                    os._exit(err.code)
                except:
                    traceback.print_exc()
            finally:
                os._exit(70)
        return self.pid

    def _run(self):
        raise NotImplementedError

    def _subproc_wait(self, flags):
        if not self.pid:
            return False
        while True:
            try:
                pid, status = os.waitpid(self.pid, flags)
            except OSError, err:
                if err.errno == errno.EINTR:
                    # Interrupted by signal so wait again.
                    continue
                elif err.errno == errno.ECHILD:
                    # Process doesn't exist.
                    self.exitPid, self.pid = self.pid, None
                    self.exitStatus = -1
                    return False
                else:
                    raise
            else:
                if pid:
                    # Process exists and is no longer running.
                    self.exitPid, self.pid = self.pid, None
                    self.exitStatus = status
                    return False
                else:
                    # Process exists and is still running.
                    return True

    def check(self):
        """
        Return C{True} if the subprocess is running.
        """
        return self._subproc_wait(os.WNOHANG)

    def wait(self):
        """
        Wait for the process to exit, then return. Returns the exit code if the
        process exited normally, -2 if the process exited abnormally, or -1 if
        the process does not exist.
        """
        self._subproc_wait(0)
        return self.exitCode

    def kill(self, signum=signal.SIGTERM, timeout=5):
        """
        Kill the subprocess and wait for it to exit.
        """
        if not self.pid:
            return

        try:
            os.kill(self.pid, signum)
        except OSError, err:
            if err.errno != errno.ESRCH:
                raise
            # Process doesn't exist (or is a zombie)

        if timeout:
            # If a timeout is given, wait that long for the process to
            # terminate, then send a SIGKILL.
            start = time.time()
            while time.time() - start < timeout:
                if not self.check():
                    break
                time.sleep(0.1)
            else:
                # If it's still going, use SIGKILL and wait indefinitely.
                os.kill(self.pid, signal.SIGKILL)
                self.wait()


class GenericSubprocess(Subprocess):

    def __init__(self, args, stdout=None, stderr=None, environ=None):
        self.args = args
        if os.path.isabs(args[0]):
            self.executable = args[0]
        elif os.path.sep in args[0]:
            self.executable = os.path.abspath(args[0])
        else:
            for elem in os.environ.get('PATH', '').split(os.pathsep):
                path = os.path.abspath(os.path.join(elem, args[0]))
                if os.path.exists(path) and os.access(path, os.X_OK):
                    self.executable = path
                    break
            else:
                raise RuntimeError("Executable '%s' not found in PATH" %
                        (args[0],))
        self.stdout = stdout
        self.stderr = stderr
        self.environ = os.environ.copy()
        if environ:
            for key, value in environ.items():
                self.environ[key] = value

    def dup2(self, fobj, dest):
        if fobj is None:
            return
        if hasattr(fobj, 'fileno'):
            fobj = fobj.fileno()
        elif not isinstance(fobj, (int, long)):
            raise TypeError("Expected an object with a fileno() method or "
                    "an integer, not %s" % type(fobj).__name__)
        os.dup2(fobj, dest)

    def _run(self):
        self.dup2(self.stdout, 1)
        self.dup2(self.stderr, 2)
        os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
        os.execve(self.executable, self.args, self.environ)
