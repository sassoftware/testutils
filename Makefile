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


all: all-subdirs default-all

all-subdirs:
	for d in $(SUBDIRS); do make -C $$d DIR=$$d || exit 1; done

export TOPDIR = $(shell pwd)

SUBDIRS = testrunner testutils twisted coverage scripts

extra_files = \
	Make.rules 		\
	Makefile		\
	Make.defs		\
	NEWS

dist_files = $(extra_files)

.PHONY: clean dist install subdirs html

subdirs: default-subdirs

install: install-subdirs
	$(PYTHON) -c "import compileall; compileall.compile_dir('$(DESTDIR)$(sitedir)', ddir='$(sitedir)', quiet=1)"

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
