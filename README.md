# SAS App Engine Testutils -- Archived Repository
**Notice: This repository is part of a Conary/rpath project at SAS that is no longer supported or maintained. Hence, the repository is being archived and will live in a read-only state moving forward. Issues, pull requests, and changes will no longer be accepted.**

Overview
--------
Testutils is a collection of python libraries that support various testsuites
within the SAS App Engine forest.

testrunner
----------
The testrunner module extends the Python unittest library with a handful of
enhancements. Among these are JUnit output, debugging, test selection by
context, and coverage hooks.

testutils
---------
A collection of helpers that setup and tear down application servers, reverse
proxies, and databases in order to support functional and integration testing.

trial
-----
testrunner.trial wraps around Twisted Trial in order to add JUnit output.
