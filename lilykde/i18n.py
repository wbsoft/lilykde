from string import Template
from os.path import join, dirname
from locale import getdefaultlocale

# TODO: in system-wide installation use standard locale dirs and lilykde
# textdomain

# Find sibling dir mo/ in parent of current script dir
modir = join(dirname(dirname(__file__)), "mo")

_i18n = lambda s: s

try:
    lang, encoding = getdefaultlocale()
    if lang:
        for mofile in lang, lang.split("_")[0]:
            try:
                fp = open(join(modir, mofile + ".mo"))
                import gettext
                _i18n = gettext.GNUTranslations(fp).ugettext
                break
            except IOError:
                continue
except ValueError:
    pass


class Translatable(str):
    def __new__(cls, value):
        return str.__new__(cls, _i18n(value))

    def args(self, *args, **kwargs):
        return Template(self).substitute(*args, **kwargs)

_ = Translatable

# kate: indent-width 4;
