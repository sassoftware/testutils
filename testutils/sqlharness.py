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
import shutil
import signal
import socket
import tempfile
import time
import subprocess
import sys

from testrunner import testhelp
from testutils.base_server import BaseServer

from conary.lib import util
from conary import dbstore
from conary.dbstore import sqlerrors

def findBin(name):
    for dirname in os.environ['PATH'].split(os.pathsep):
        path = os.path.join(dirname, name)
        if os.path.exists(path):
            return path
    return name


# catch subprocess exec errors and be more informative about them
def osExec(args):
    binpath = findBin(args[0])
    try:
        try:
            os.execv(binpath, args)
            os._exit(1)
        except OSError:
            sys.stderr.write("\nERROR:\nCould not exec: %s\n" % (args,))
        # if we reach here, it's an error anyway
    finally:
        os._exit(-1)

def execute(cmd):
    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         close_fds=True)
    out, err = p.communicate()
    return p.returncode, out, err

class RepositoryDatabase:
    verbose = 0
    def __init__(self, harness, dbName):
        self.harness = harness
        self.driver = harness.driver
        self.path = os.path.join(harness.conn, dbName)
        self.db = None
        if self.verbose:
            print "START DATABASE", self.driver, self.path
        self.dbName = dbName
        
    def getDbName(self):
        return self.dbName
    
    def getDriver(self):
        return "%s %s" % (self.driver, self.path)

    def connect(self):
        if self.db:
            return self.db
        if self.verbose:
            print "CONNECT DATABASE", self.driver, self.path
        self.db = dbstore.connect(self.path, driver = self.driver)
        return self.db

    def initDB(self):
        from conary.server.schema import setupTempTables
        from conary.local.schema import setupTempDepTables
        db = self.connect()
        setupTempTables(db)
        setupTempDepTables(db)
        db.commit() # force file creation
        return db

    def createSchema(self):
        if self.verbose:
            print "CREATE SCHEMA", self.driver, self.path
        db = self.connect()
        from conary.server.schema import loadSchema
        loadSchema(db)
        db.commit()

    def clearSchema(self):
        if self.verbose:
            print "Clearing schema"
        db = self.connect()
        self.harness.clearDBSchema(self.dbName, db)

    def dumpSchema(self, dumpPath):
        if self.verbose:
            print "Dumping schema"
        db = self.connect()
        self.harness.dumpSchema(self.dbName, db, dumpPath)

    def loadSchemaDump(self, dumpPath):
        if self.verbose:
            print "Loading schema dump"
        db = self.connect()
        self.harness.loadSchemaDump(self.dbName, db, dumpPath)

    def _getNetAuth(self):
        db = self.connect()
        from conary.repository.netrepos import netauth
        auth = netauth.NetworkAuthorization(db, 'localhost')
        db.commit()
        return auth

    def createUser(self, auth, name, password, write = False, admin = False,
                   remove = False):
        if not auth:
            auth = self._getNetAuth()
        auth.addRole(name)
        auth.addUser(name, password)
        auth.addRoleMember(name, name)
        auth.addAcl(name, None, None, write = write, remove = remove)
        auth.setAdmin(name, admin)

    def createUsers(self):
        if self.verbose:
            print "CREATE USERS", self.driver, self.path
        auth = self._getNetAuth()
        self.createUser(auth, 'test', 'foo', admin = True, write = True,
                        remove = True)
        self.createUser(auth, 'anonymous', 'anonymous', admin = False, write = False)

    def _reset(self):
        self.stop()
        self.harness.dropDB(self.dbName)
        self.harness.createDB(self.dbName)
        return self.connect()

    def reset(self):
        if self.verbose:
            print "RESET DATABASE", self.driver, self.path
        db = self._reset()
        self.initDB()
        self.createSchema()
        self.createUsers()
        db.commit()
        return db
    
    def stop(self):
        if self.verbose and self.db:
            print "STOP DATABASE", self.driver, self.path
        if self.db:
            self.db.close()
            self.db = None
    __del__ = stop


########################
# SQL SERVERS HANDLERS
########################
class BaseSQLServer(BaseServer):
    driver = "unspecified"
    verbose = 0
    def __init__(self, path, dbClass = RepositoryDatabase):
        self.path = path
        if self.verbose:
            print "\nSTART SQL HARNESS", self.driver, path
        self.dbClass = dbClass

    def __del__(self):
        self.stop()
        BaseServer.__del__(self)

    def createDB(self, name):
        if self.verbose:
            print "CREATE DATABASE", name
    def dropDB(self, name):
        if self.verbose:
            print "DROP DATABASE", name
    def clearDBSchema(self, name, db):
        if self.verbose:
            print "Clearing database schema", name
    def dumpSchema(self, name, db, dumpPath):
        if self.verbose:
            print "Dumping database schema %s to %s" % (name, dumpPath)
    def loadSchemaDump(self, name, db, dumpPath):
        if self.verbose:
            print "Loading database schema %s from %s" % (name, dumpPath)

    def getDB(self, name = "testdb", keepExisting = False):
        if not keepExisting:
            self.dropDB(name)
        db = self.createDB(name)
        return db

    def stop(self):
        if self.verbose:
            print "\nSTOP SQL HARNESS", self.driver, self.path


class SqliteServer(BaseSQLServer):
    driver = "sqlite"
    def __init__(self, path, dbClass = RepositoryDatabase):
        BaseSQLServer.__init__(self, path, dbClass)
        if os.path.exists(path):
            shutil.rmtree(path)
        util.mkdirChain(path)
        self.conn = self.path

    def createDB(self, name):
        BaseSQLServer.createDB(self, name)
        repodb = self.dbClass(self, name)
        # make sure to create the file
        db = repodb.connect()
        db.transaction()
        db.commit()
        repodb.stop()
        return repodb

    def dropDB(self, name):
        BaseSQLServer.dropDB(self, name)
        dbPath = os.path.join(self.path, name)
        if os.path.exists(dbPath):
            os.unlink(dbPath)

    def clearDBSchema(self, name, db):
        BaseSQLServer.clearDBSchema(self, name, db)
        self.dropDB(name)
        self.initDB(name)

    def dumpSchema(self, name, db, dumpPath):
        BaseSQLServer.dumpSchema(self, name, db, dumpPath)
        cmd = "sqlite3 '%s' .dump > '%s'" % (name, dumpPath)
        returncode, out, err = execute(cmd)
        if returncode != 0:
            raise RuntimeError("%s: %s, %s" % (returncode, out, err))

    def loadSchemaDump(self, name, db, dumpPath):
        BaseSQLServer.loadSchemaDump(self, name, db, dumpPath)
        tfile = util.AtomicFile(name)
        cmd = "sqlite3 '%s' < '%s'" % (tfile.name, dumpPath)
        execute(cmd)
        util.removeIfExists(name + '.journal')
        tfile.commit()

    def isStarted(self):
        return self.path is not None

    def stop(self):
        BaseSQLServer.stop(self)
        if self.path and os.path.exists(self.path):
            util.rmtree(self.path)
            self.path = None


class SQLServer(BaseSQLServer):
    rootdb = "unspecified"
    def __init__(self, path, dbClass = RepositoryDatabase):
        BaseSQLServer.__init__(self, path, dbClass)
        self.start()
        self.conn = None
        self.init = None
        self._rootdb = None
        self.signal = signal.SIGTERM
        
    def _initPath(self):
        self.sqlPid = None
        self.port = testhelp.findPorts(num = 1)[0]
        if self.path:
            assert(isinstance(self.path, str))
            if self.path.lower() != self.path:
                raise RuntimeError("The SQL server harness requires that "
                                   "repository dirs be all lowercase")
        else:
            self.path = tempfile.mkdtemp()
            os.rmdir(self.path)
            # this is a sick hack because we're using the lowercase table
            # option on mysql
            self.path = self.path.lower()
        self.log = "%s/log" % self.path
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        util.mkdirChain("%s/data" % self.path)
        util.mkdirChain("%s/tmp" % self.path)

    def fork(self, *args):
        self.sqlPid = os.fork()
        if not self.sqlPid:
            logFd = os.open(self.log, os.O_RDWR | os.O_CREAT)
            os.dup2(logFd, 1)
            os.dup2(logFd, 2)
            os.close(0)
            os.close(logFd)
            osExec(args)
    
    def start(self):
        self._initPath()
        self._start()

    def isStarted(self):
        return self.sqlPid is not None
        
    def stop(self):
        if self.sqlPid == None:
            return
        BaseSQLServer.stop(self)
        os.kill(self.sqlPid, self.signal)
        os.waitpid(self.sqlPid, 0)
        self.sqlPid = None
        shutil.rmtree(self.path)

    def _start(self):
        raise  NotImplementedError
    
    def _hasDB(self, name, cu, query = None):
        if not query:
            raise RuntimeError("invalid call to low-level class member function")
        cu.execute(query)
        for dbname, in cu:
            if dbname.lower() == name.lower():
                return True
        return False
    def _kill(self, name, cu):
        raise NotImplementedError
    def _dropDB(self, name, db):
        cu = db.cursor()
        cu.execute("drop database %s" % name)

    def getRootDB(self):
        if self._rootdb and self._rootdb.alive():
            return self._rootdb
        self._rootdb = dbstore.connect("%s/%s" % (self.conn, self.rootdb),
                                       driver = self.driver)
        return self._rootdb

    def dropDB(self, name):
        db = self.getRootDB()
        cu = db.cursor()
        if not self._hasDB(name, cu):
            return
        BaseSQLServer.dropDB(self, name)
        while self._kill(name, cu):
            db.rollback()
            pass
        self._dropDB(name, db)
        db.commit()
        db.close()

    def createDB(self, name):
        db = self.getRootDB()
        cu = db.cursor()
        if not self._hasDB(name, cu):
            BaseSQLServer.createDB(self, name)
            self._runAutoCommit(db, self.init % name)
        db.commit()
        db.close()
        return self.dbClass(self, name)


class MySQLServer(SQLServer):
    driver = "mysql"
    rootdb = "mysql"
    def __init__(self, path, dbClass = RepositoryDatabase):
        SQLServer.__init__(self, path, dbClass)
        self.conn = "root@localhost.localdomain:%d" % self.port
        self.init = "create database %s character set latin1 collate latin1_bin"
        
    def _start(self):
        # config file
        cfgFile = "%s/my.cnf" % self.path
        f = open(cfgFile, "w")
        d = {"log" : self.log, "dir" : self.path, "port" : self.port}
        f.write("""
[mysqld]
datadir=%(dir)s/data
tmpdir=%(dir)s/tmp
socket=%(dir)s/socket
log_error=%(log)s
pid_file=%(dir)s/pid
character_set_server=latin1
collation_server=latin1_bin
port=%(port)d
sql_mode=TRADITIONAL,NO_AUTO_VALUE_ON_ZERO,ONLY_FULL_GROUP_BY
lower_case_table_names=1
default-table-type=InnoDB
innodb_fast_shutdown
log_slow_queries
long_query_time=1
""" % d)
        f.close()

        # now prepare the new MySQL instance
        cmd = "mysql_install_db --defaults-file=%s" % cfgFile
        returncode, out, err = execute(cmd)
        if returncode != 0:
            raise RuntimeError('mysql db initialization failed: %s' % out+err)
        
        self.fork("mysqld", "--defaults-file=%s" % cfgFile)

        sock = socket.socket()
        count = 500
        while count:
            try:
                sock.connect((("127.0.0.1"), self.port))
                break
            except:
                time.sleep(0.01)
                count -= 1
            if not count:
                raise SystemError, "unable to contact mysql server"

    def _hasDB(self, name, cu):
        return SQLServer._hasDB(self, name, cu, "show databases")

    def _kill(self, name, cu):
        cu.execute("show processlist")
        for proc in cu.fetchall():
            _pid, _dbName = (proc[0], proc[3])
            if _dbName != name:
                continue
            try:
                cu.execute("kill %d" % _pid)
            except sqlerrors.DatabaseError:
                # Gone.
                pass
        # mysql is nice enough that a single kill will suffice
        return 0
    
class PostgreSQLServer(SQLServer):
    driver = "postgresql"
    rootdb = "postgres"

    def __init__(self, path, dbClass = RepositoryDatabase):
        self.user = 'testutils'
        SQLServer.__init__(self, path, dbClass)
        self.conn = "%s@localhost.localdomain:%d" % (self.user, self.port)
        self.init = "create database %s encoding 'UTF8'"
        self.signal = signal.SIGQUIT
        
    def _start(self):
        # prepare the new postgres instance
        cmd = "initdb --encoding=UTF8 --no-locale --pgdata=%s/data -A trust --username=%s >%s" %(
            self.path, self.user, self.log)
        returncode, out, err = execute(cmd)
        if returncode != 0:
            raise RuntimeError('postgresql db initialization failed: %s' % out+err)
        # start up the postgres instance
        self.fork("postmaster",
                  "-D", "%s/data" % self.path,
                  "-p", "%d" % self.port,
                  "-F")
        import pgsql
        count = 50
        while count:
            time.sleep(0.1)
            try:
                db = pgsql.connect(database = "template1", host = "localhost",
                                   user = self.user, port = self.port)
                db.execute("select version()")
            except (pgsql.InternalError, pgsql.ProgrammingError):
                count -= 1
            else:
                break
        if not count:
            raise SystemError, "unable to contact postgresql server"
        try:
            db.execute('create language "plpgsql"')
        except:
            pass
        db.commit()
        db.close()
        del db
        time.sleep(0.1)

    def _kill(self, name, cu):
        cu.execute("select procpid, pg_cancel_backend(procpid) "
                   "from pg_stat_activity where datname = ?", name)
        ret = 0
        for pid, flag in cu.fetchall():
            ret += 1
            t1 = time.time()
            while 1: # kill and wait for each client to succumb to SIGTERM pressure
                try:
                    lr = os.kill(pid, signal.SIGTERM)
                except OSError, e:
                    if e.errno == 3: # no such process
                        break
                    raise
                t2 = time.time()
                if t2 - t1 > 5:
                    raise RuntimeError("Could not kill postgresql client pid %d "
                                       "for database %s. Last return = %s" %(
                        pid, name, lr))
                time.sleep(0.1)
        return ret

    def _dropDB(self, name, db):
        t1 = time.time()
        while True:
            try:
                self._runAutoCommit(db, "drop database %s" % name)
            except sqlerrors.CursorError:
                pass
            else:
                break
            t2 = time.time()
            if t2 - t1 > 5:
                # XXX: need to debug why this is happening here under bamboo
                raise RuntimeError("Could not drop/reload database %s" % (name,))
            time.sleep(0.1)
            
    def _hasDB(self, name, cu):
        return SQLServer._hasDB(self, name, cu, """
        select d.datname from pg_catalog.pg_database as d
        join pg_catalog.pg_roles as r on d.datdba = r.oid""")

    @staticmethod
    def _runAutoCommit(db, *args, **kwargs):
        cu = db.cursor()
        try:
            return db.runAutoCommit(cu.execute, *args, **kwargs)
        except AttributeError:
            return cu.execute(*args, **kwargs)

    def clearDBSchema(self, name, db):
        cu = db.cursor()
        cu2 = db.cursor()
        cu.execute("""
            select proname, pg_get_function_identity_arguments(pg_proc.oid),
                   nspname
              from pg_proc
              join pg_namespace on pg_proc.pronamespace = pg_namespace.oid
             where nspname != 'information_schema' and nspname not like 'pg_%'
        """)
        procs = []
        for procname, procargs, nspname in cu:
            procs.append('"%s"."%s"(%s)' % (nspname, procname, procargs))
            cu2.execute('DROP FUNCTION "%s"."%s"(%s) CASCADE' % (nspname, procname,
                procargs))

        cu.execute("""
            select relname, nspname, relkind
              from pg_class
              join pg_namespace on pg_class.relnamespace = pg_namespace.oid
             where relkind in ('v', 'r')
               and nspname != 'information_schema'
               and nspname not like 'pg_%'
        """)
        tables = []
        views = []
        for relname, relnsp, relkind in cu:
            if relkind == 'v':
                views.append('"%s"."%s"' % (relnsp, relname))
            elif relkind == 'r':
                tables.append('"%s"."%s"' % (relnsp, relname))
        if views:
            cu.execute("DROP VIEW " + ", ".join(views))
        if tables:
            cu.execute("DROP TABLE " + ", ".join(tables))

        cu.execute("""
            select nspname
              from pg_namespace
             where nspname != 'information_schema'
               and nspname not like 'pg_%'
        """)
        for nspname, in cu:
            if nspname == 'public':
                continue
            cu2.execute('drop schema "%s"' % nspname)

        db.commit()

    def dumpSchema(self, name, db, dumpPath):
        BaseSQLServer.dumpSchema(self, name, db, dumpPath)
        cmd = "pg_dump --port=%s --user=%s --format=custom %s > %s" % (
                self.port, self.user, name, dumpPath)
        returncode, out, err = execute(cmd)
        if returncode != 0:
            raise RuntimeError("%s: %s, %s" % (returncode, out, err))

    def loadSchemaDump(self, name, db, dumpPath):
        BaseSQLServer.loadSchemaDump(self, name, db, dumpPath)
        cmd = "pg_restore --port=%s --user=%s -d %s %s" % (
                self.port, self.user, name, dumpPath)
        returncode, out, err = execute(cmd)
        if returncode != 0:
            raise RuntimeError("%s: %s, %s" % (returncode, out, err))

class PgpoolServer(PostgreSQLServer):
    driver = "pgpool"


class PsycoServer(PostgreSQLServer):
    driver = "psycopg2"


def getHarness(driver, topdir = None, dbClass = RepositoryDatabase):
    global _harness

    h = _harness.get(driver, None)
    if h:
        # check that we're not expected to show up in a different
        # place if called with an explicit topdir
        if topdir:
            sqldir = os.path.join(topdir, driver)
            if h.path != sqldir:
                raise RuntimeError("BUG IN TESTSUITE SQL Harness handling: "
                                   "Harness directory should not change during the testrun")
        return h
    # need to create a new harness - start with a clean tree
    if topdir:
        sqldir = os.path.join(topdir, driver)
    else:
        sqldir = testhelp.getTempDir("conarytest-%s-" % driver)
    if os.path.exists(sqldir):
        shutil.rmtree(sqldir)
    os.mkdir(sqldir, 0700)

    if driver == 'sqlite':
        h = SqliteServer(sqldir, dbClass)
    elif driver == 'mysql':
        h = MySQLServer(sqldir, dbClass)
    elif driver == 'postgresql':
        h = PostgreSQLServer(sqldir, dbClass)
    elif driver == 'pgpool':
        h = PgpoolServer(sqldir, dbClass)
    elif driver == 'psycopg2':
        h = PsycoServer(sqldir, dbClass)
    else:
        raise RuntimeError("Unknown database type specified: %s" % driver)
    _harness[driver] = h
    return h
    
def start(topdir = None, dbClass = RepositoryDatabase):
    driver = os.environ.get('CONARY_REPOS_DB', 'sqlite')
    return getHarness(driver, topdir, dbClass)


# init the global sql harness
if not globals().has_key("_harness"):
    _harness = {}

if __name__ == '__main__':
    pass
