#!/usr/bin/env python

"""
extracts messages from a desktop file and outputs a dummy
Python file that xgettext can extract the messages from.
"""

import fileinput, sys

# Keys to translate
keys = (
    'Name',
    )

# startswith cache
keys_test = tuple('%s=' % key for key in keys)

for line in fileinput.input():
    line = line.decode('utf-8')
    if line.startswith(keys_test):
        # translate this:
        line = line.split('=', 1)[1]
        line = line.replace('"', '\\"')
        line = line.strip()
        line = 'i18n("%s")\n' % line
        sys.stdout.write(line.encode('utf-8'))


