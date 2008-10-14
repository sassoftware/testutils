from testrunner import testhelp

class BaseServer(object):
    "Base server class. Responsible with setting up the ports etc."
    # We only want standalone repositories to have SSL support added via
    # useSSL
    sslEnabled = False

    def start(self, resetDir = True):
        raise NotImplementedError

    def cleanup(self):
        pass

    def stop(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def initPort(self):
        ports = testhelp.findPorts(num = 1, closeSockets=False)[0]
        self.port = ports[0]
        self.socket = ports[1]
