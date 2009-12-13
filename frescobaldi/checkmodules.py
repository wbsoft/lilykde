#! python

# This script checks if required modules are present by simply
# importing them, and performs some additional version checks.

import sys, os

missing = []

# these are checks for modules Frescobaldi needs, but you can tailor it
# for other needs.

for module in (
    "sip", "PyQt4", "PyQt4.QtCore", "PyQt4.QtGui",
    "PyKDE4", "PyKDE4.kdecore", "PyKDE4.kdeui", "PyKDE4.kparts", "PyKDE4.kio",
    "PyKDE4.ktexteditor",
    "dbus", "dbus.mainloop.qt",
    ):
    try:
        exec "import %s" % module
    except:
        missing.append(module)

if missing:
    sys.stderr.write("The following Python modules are missing:\n")
    for m in missing:
        sys.stderr.write("  %s\n" % m)
    sys.exit(1)

errors = []
mkver = lambda major, minor, release: major * 65536 + minor * 256 + release
    
# versions
if sys.version_info[:2] != (2, 6):
    errors.append("Python version %s.%s.%s found, but need 2.6.\n"
                  "(Use cmake -DPYTHON_EXECUTABLE=/path/to/python2.6)" %
        sys.version_info[:3])
        
if sip.SIP_VERSION < mkver(4, 9, 1):
    errors.append("(python-)sip version %s found, but need at least 4.9.1." %
        sip.SIP_VERSION_STR)
        
if PyQt4.QtCore.PYQT_VERSION < mkver(4, 6, 0):
    errors.append("PyQt4 version %s found, but need at least 4.6.0." %
        PyQt4.QtCore.PYQT_VERSION_STR)
        
if PyKDE4.kdecore.pykde_version() < mkver(4, 0, 2):
    errors.append("PyKDE4 version %s found, but need at least 4.0.2." %
        PyKDE4.kdecore.pykde_versionString())

if dbus.version < (0, 82, 4):
    errors.append("python-dbus version %s found, but need at least 0.82.4." %
        '.'.join(map(str, dbus.version)))
        
if errors:
    sys.stderr.write("Some packages have outdated versions:\n")
    for e in errors:
        sys.stderr.write(e + '\n')
    sys.exit(1)
    
