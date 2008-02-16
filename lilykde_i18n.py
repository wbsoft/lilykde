import gettext
try:
    _ = gettext.translation('lilykde').ugettext
except IOError:
    _ = lambda s: s
