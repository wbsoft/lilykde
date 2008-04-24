"""
LilyKDE
"""

import os
from locale import getdefaultlocale

__all__ = ['appdir', 'language', 'encoding', 'config']

appdir = os.path.dirname(__path__[0])

try:
    language, encoding = getdefaultlocale()
except ValueError:
    language, encoding = None, None

def config(group=None):
    """
    Return the master KConfig object for "lilykderc", or
    a KConfigGroup (wrapper) object if a group name is given.
    """
    from lilykde.util import kconfig
    k = kconfig("lilykderc", False, False)
    return group and k.group(group) or k




# kate: indent-width 4;
