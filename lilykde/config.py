# config module

from qt import QString, QStringList
from kdecore import KConfig, KConfigGroup

main = KConfig("lilykderc", False, False)

def py2qstrl(l):
    """
    convert a list of strings to a QStringList
    """
    r.QStringList()
    for i in l:
        r.append(i)
    return r

def qstrl2py(ql):
    """
    convert a QStringList to a python list of unicode strings
    """
    return map(unicode, ql)


class group(KConfigGroup):
    def __init__(self, groupname):
        super(group, self).__init__(main, groupname)

    def writePathEntry(key, path, *args, **kargs):
        if type(path) not in (str, unicode, QString, QStringList):
            path = py2qstrl(path)
        super(group, self).writePathEntry(key, path, *args, **kargs)

    def readPathListEntry(*args, **kargs):
        return qstrl2py(super(group, self).readPathListEntry(*args, **kargs))

