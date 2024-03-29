#! python

# This script checks if required modules are present by simply
# importing them, and performs some additional version checks.

import sys, os

def mkver(major, minor, release):
    return major * 65536 + minor * 256 + release

def checkModules():
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
            exec ("import %s" % module) in globals()
        except:
            missing.append(module)
    return missing


def checkVersions():
    # versions
    errors = []
    
    if not (2, 6) <= sys.version_info[:2] < (3, 0):
        errors.append("Python version %s.%s.%s found, but need 2.6 or 2.7.\n"
                    "(Use e.g. cmake -DPYTHON_EXECUTABLE=/path/to/python2.6)" %
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
    
    return errors


if __name__ == "__main__":

    missing = checkModules()
    if missing:
        sys.stderr.write("The following Python modules are missing:\n")
        for m in missing:
            sys.stderr.write("  %s\n" % m)
        sys.exit(1)

    errors = checkVersions()
    if errors:
        sys.stderr.write("Some packages have outdated versions:\n")
        for e in errors:
            sys.stderr.write(e + '\n')
        sys.exit(1)
        
