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
from testutils import sock_utils
from testutils import subprocutil


class NginxServer(object):
    def __init__(self, serverDir,
            proxyTo,
            plainPort=None,
            sslPort=None,
            sslCertAndKey=None,
            ):
        self.serverDir = os.path.abspath(serverDir)
        self.proxyTo = proxyTo
        self.plainPort = plainPort if plainPort else sock_utils.findPorts(num=1)[0]
        if sslCertAndKey:
            self.sslCert, self.sslKey = sslCertAndKey
            if sslPort:
                self.sslPort = sslPort
            else:
                self.sslPort = sock_utils.findPorts(num=1)[0]
        else:
            self.sslCert = self.sslKey = None
            self.sslPort = 0
        self.configPath = os.path.join(self.serverDir, 'nginx.conf')
        self.accessLog = os.path.join(self.serverDir, 'access.log')
        self.errorLog = os.path.join(self.serverDir, 'error.log')
        if not os.path.isdir(self.serverDir):
            os.makedirs(self.serverDir)
        self.server = subprocutil.GenericSubprocess(
            args=['nginx',
                '-c', self.configPath,
                '-p', self.serverDir,
                ],
            stderr=open(self.errorLog, 'a'),
            )

    def start(self):
        self.reset()
        self.server.start()
        sock_utils.tryConnect('::', self.plainPort,
                logFile=self.errorLog,
                abortFunc=self.server.check,
                )

    def check(self):
        return self.server.check()

    def stop(self):
        self.server.kill()

    def reset(self):
        if not os.path.isdir(self.serverDir):
            os.makedirs(self.serverDir)
        self.writeConfig()
        open(self.accessLog, 'w').close()
        open(self.errorLog, 'w').close()

    def writeConfig(self):
        config = """\
worker_processes  1;
pid nginx.pid;
lock_file nginx.lock;
daemon off;
error_log %(errorLog)s warn;
events { worker_connections  1024; }
http {
    log_format  main  '[$time_iso8601] remote=$remote_addr ff=$http_x_forwarded_for cnyhost=$http_x_conary_servername method=$request_method uri="$scheme://$http_host$request_uri" status=$status bytes=$body_bytes_sent ua="$http_user_agent" referrer=$http_referer';
    access_log  %(accessLog)s main;
    sendfile        on;
    keepalive_timeout  65;

    client_body_temp_path client_temp;
    proxy_temp_path proxy_temp;
    fastcgi_temp_path fastcgi_temp;
    uwsgi_temp_path uwsgi_temp;
    scgi_temp_path scgi_temp;

    server {
        listen [::]:%(plainPort)s default_server ipv6only=off;
        listen [::]:%(sslPort)s ssl default_server ipv6only=off;
        ssl_certificate %(sslCert)s;
        ssl_certificate_key %(sslKey)s;
        client_max_body_size 0;
        client_body_buffer_size 64k;
        client_header_buffer_size 4k;
        merge_slashes off;

        proxy_max_temp_file_size 0;
        proxy_read_timeout 36000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-Ip $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $http_host;

        uwsgi_param  QUERY_STRING       $query_string;
        uwsgi_param  REQUEST_METHOD     $request_method;
        uwsgi_param  CONTENT_TYPE       $content_type;
        uwsgi_param  CONTENT_LENGTH     $content_length;
        uwsgi_param  REQUEST_URI        $request_uri;
        uwsgi_param  PATH_INFO          $document_uri;
        uwsgi_param  SERVER_PROTOCOL    $server_protocol;
        uwsgi_param  HTTPS              $https if_not_empty;
        uwsgi_param  REMOTE_ADDR        $remote_addr;
        uwsgi_param  REMOTE_PORT        $remote_port;
        uwsgi_param  SERVER_PORT        $server_port;
        uwsgi_param  SERVER_NAME        $server_name;

        location / { %(proxyTo)s; }
    }
}
""" % dict(
                accessLog=self.accessLog,
                errorLog=self.errorLog,
                plainPort=self.plainPort,
                sslPort=self.sslPort,
                sslCert=self.sslCert,
                sslKey=self.sslKey,
                proxyTo=self.proxyTo,
                )
        config = [x + '\n' for x in config.splitlines()]
        if not self.sslCert:
            config = [x for x in config if 'ssl' not in x]
        with open(self.configPath, 'w') as f:
            f.writelines(config)

    def getUrl(self, ssl=True):
        if ssl and self.sslCert:
            return 'https://127.0.0.1:%d' % self.sslPort
        else:
            return 'http://127.0.0.1:%d' % self.plainPort
