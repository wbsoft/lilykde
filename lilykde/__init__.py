"""
LilyKDE
"""

import os

appdir = os.path.dirname(__path__[0])

def config(group=None):
    """
    Return the master KConfig object for "lilykderc", or
    a KConfigGroup (wrapper) object if a group name is given.
    """
    from lilykde.util import kconfig
    k = kconfig("lilykderc", False, False)
    return group and k.group(group) or k


# kate: indent-width 4;
