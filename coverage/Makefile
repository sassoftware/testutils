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
	$(PYTHON) -c "import compileall; compileall.compile_dir('$(DESTDIR)$(coveragedir)', ddir='$(coveragedir)', quiet=1)"
	$(PYTHON) -OO -c "import compileall; compileall.compile_dir('$(DESTDIR)$(coveragedir)', ddir='$(coveragedir)', quiet=1)"
	cp -a coverage.py $(DESTDIR)/$(sitedir)/coverage.py
	install -m 755 _coverage.so $(DESTDIR)$(coveragedir)/

include ../Make.rules
include ../Make.defs
