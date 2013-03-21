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
