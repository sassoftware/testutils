#
# Copyright (c) 2010 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

plugin_files = $(wildcard plugins/*.py)

all: default-subdirs default-all

install: all install-subdirs default-install
	mkdir -p $(DESTDIR)$(sitedir)/twisted/plugins
	install -m0644 $(plugin_files) $(DESTDIR)$(sitedir)/twisted/plugins/

dist: default-dist

clean: clean-subdirs default-clean

include ../Make.rules
include ../Make.defs
