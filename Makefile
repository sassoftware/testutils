#
# Copyright (c) 2006-2008 rPath, Inc.
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

all: all-subdirs default-all

all-subdirs:
	for d in $(SUBDIRS); do make -C $$d DIR=$$d || exit 1; done

export TOPDIR = $(shell pwd)

SUBDIRS=testrunner testutils coverage

extra_files = \
	Make.rules 		\
	Makefile		\
	Make.defs		\
	NEWS

dist_files = $(extra_files)

.PHONY: clean dist install subdirs html

subdirs: default-subdirs

install: install-subdirs

clean: clean-subdirs default-clean

dist:
	$(MAKE) forcedist


archive: $(dist_files)
	hg archive  --exclude .hgignore -t tbz2 testutils-$(VERSION).tar.bz2

forcedist: archive

forcetag:
	hg tag -f testutils-$(VERSION)

tag:
	hg tag testutils-$(VERSION)

clean: clean-subdirs default-clean

include Make.rules
include Make.defs
 
# vim: set sts=8 sw=8 noexpandtab :
