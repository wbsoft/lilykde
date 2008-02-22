from os.path import join, dirname
from locale import getdefaultlocale

# TODO: in system-wide installation use standard locale dirs and lilykde
# textdomain

# Find sibling dir mo/ in parent of current script dir
modir = join(dirname(dirname(__file__)), "mo")

_ = lambda s: s

try:
    lang, encoding = getdefaultlocale()
    if lang:
        for mofile in lang, lang.split("_")[0]:
            try:
                fp = open(join(modir, mofile + ".mo"))
                import gettext
                _ = gettext.GNUTranslations(fp).ugettext
                break
            except IOError:
                continue
except ValueError:
    pass
