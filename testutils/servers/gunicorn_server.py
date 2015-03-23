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

import os
import signal
from testutils import sock_utils
from testutils import subprocutil


class GunicornServer(object):
    def __init__(self, serverDir,
            application,
            port=None,
            workers=2,
            timeout=None,
            environ=(),
            ):
        self.serverDir = os.path.abspath(serverDir)
        self.port = port if port else sock_utils.findPorts(num=1)[0]
        self.accessLog = os.path.join(self.serverDir, 'access.log')
        self.errorLog = os.path.join(self.serverDir, 'error.log')
        self.server = subprocutil.GenericSubprocess(
                args=['gunicorn',
                    '--bind', '[::]:%d' % self.port,
                    '--workers', str(workers),
                    '--timeout', str(timeout or 0),
                    '--access-logfile', self.accessLog,
                    '--log-file', self.errorLog,
                    application,
                    ],
                environ=environ,
                )

    def start(self):
        self.reset()
        self.server.stdout = self.server.stderr = open(self.errorLog, 'a')
        self.server.start()
        sock_utils.tryConnect('::', self.port,
                logFile=self.errorLog,
                abortFunc=self.server.check,
                )

    def check(self):
        return self.server.check()

    def stop(self):
        self.server.kill(signum=signal.SIGQUIT, timeout=15)

    def reset(self):
        if not os.path.isdir(self.serverDir):
            os.makedirs(self.serverDir)
        open(self.accessLog, 'w').close()
        open(self.errorLog, 'w').close()

    def getUrl(self):
        return 'http://127.0.0.1:%d' % self.port

    def getProxyTo(self):
        return 'proxy_pass ' + self.getUrl()
