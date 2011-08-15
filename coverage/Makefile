#
# Copyright (c) rPath, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


PYTHON=python
python_files =  *.py
PYINCLUDE = $(shell $(PYTHON) -c 'import os, sys; print os.sep.join((sys.prefix, "include", "python" + sys.version[:3]))')
CFLAGS:=-O2 -Wall -I$(PYINCLUDE) -fPIC $(CFLAGS) -g
CC=gcc $(CFLAGS)


.PHONY: clean

all: _coverage.so $(python_files)

_coverage.so: _coverage.c
	$(CC) -shared -o $@ $^

clean:
	rm -f *.o *.so *.pyc *~

install: all default-install
	cp -a coverage.py $(DESTDIR)/$(sitedir)/coverage.py
	install -m 755 _coverage.so $(DESTDIR)$(coveragedir)/

include ../Make.rules
include ../Make.defs
