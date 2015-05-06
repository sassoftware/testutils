#!/bin/bash
HOSTS="testproject.rpath.local2 test.rpath.local test.rpath.local2"
if ! grep -q "test.rpath.local" /etc/hosts; then
    echo "127.0.0.1 $HOSTS" >>/etc/hosts
fi
exit 0
