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

import signal
from testutils import sock_utils
from testutils import subprocutil


class MemcacheServer(object):
    def __init__(self, port=None):
        self.port = port if port else sock_utils.findPorts(num=1)[0]
        self.server = subprocutil.GenericSubprocess(
                args=['memcached',
                    '-p', str(self.port),
                    ],
                )

    def start(self):
        self.server.start()
        sock_utils.tryConnect('::', self.port, abortFunc=self.server.check)

    def check(self):
        return self.server.check()

    def stop(self):
        self.server.kill(signum=signal.SIGQUIT, timeout=3)

    def reset(self):
        pass

    def getHostPort(self):
        return '127.0.0.1:%d' % self.port
