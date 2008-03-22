# config module

from lilykde.util import kconfig

def master():
    return kconfig("lilykderc", False, False)

def group(name):
    return master().group(name)


# kate: indent-width 4;
