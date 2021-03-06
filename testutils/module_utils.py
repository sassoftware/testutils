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

import os
import sys


def path_for_module(module):
    """
    Return the PYTHONPATH under which the given module (name or object) can be
    imported.
    """
    if isinstance(module, basestring):
        __import__(module)
        module = sys.modules[module]
    path = os.path.abspath(module.__file__)
    if os.path.basename(path).split('.')[0] == '__init__':
        path = os.path.dirname(path)
    modname = module.__name__.split('.')
    while modname:
        path = os.path.dirname(path)
        modname.pop()
    return path
