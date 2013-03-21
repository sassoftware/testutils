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
