SAS App Engine Testutils
========================

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
