"""
A Score Wizard

provides a wizard dialog to quickly set up a LilyPond score.

The user can select items (staffs or different types of staffgroup)
and define their order. All items will live in Score, i.e.

general preambule (main settings, title etc.)
preambule of item1 (assignments etc.)
preambule of item2

\score {
  <<
    music of item1
    music of item2
  >>
  \layout {
    general layout stuff
  }
  optional midi block
}

aftermath of item1 (additional score blocks,)
aftermath of item2 (e.g. for extra midi output files)


Wizard:

    Page 1:

        Titling, etc.

    page 2:

        Parts with associated settings



"""

from string import Template

# Translate messages
from lilykde.i18n import _

headers = (
    ('dedication',  _("Dedication")),
    ('title',       _("Title")),
    ('subtitle',    _("Subtitle")),
    ('subsubtitle', _("Subsubtitle")),
    ('instrument',  _("Instrument")),
    ('composer',    _("Composer")),
    ('arranger',    _("Arranger")),
    ('poet',        _("Poet")),
    ('meter',       _("Meter")),
    ('piece',       _("Piece")),
    ('opus',        _("Opus")),
    ('copyright',   _("Copyright")),
    ('tagline',     _("Tagline")),
)

html = Template(r"""<table width=360 style='font-family: serif;'>
<tr><td colspan=3 align=center>$dedication</td><tr>
<tr><td colspan=3 align=center style='font-size:20pt;'><b>$title</b></td><tr>
<tr><td colspan=3 align=center style='font-size:12pt;'><b>$subtitle</b></td><tr>
<tr><td colspan=3 align=center><b>$subsubtitle</b></td><tr>
<tr>
    <td align=left width='25%%'>$poet</td>
    <td align=center><b>$instrument</b></td>
    <td align=right width='25%%'>$composer</td>
</tr>
<tr>
    <td align=left>$meter</td>
    <td> </td>
    <td align=right>$arranger</td>
</tr>
<tr>
    <td align=left>$piece</td>
    <td> </td>
    <td align=right>$opus</td>
</tr>
<tr><td colspan=3 align=center><img src='scorewiz.png'></td></tr>
<tr><td colspan=3 align=center>$copyright <i>(%s)</i></td></tr>
<tr><td colspan=3 align=center>$tagline <i>(%s)</i></td></tr>
</table>""").substitute(
    dict((k, "<a href='#%s'>%s</a>" % (k, v)) for k, v in headers)) % (
        _("bottom of first page"),
        _("bottom of last page"))

