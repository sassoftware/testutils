#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
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
