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

import re
from string import Template

from qt import *
from kdecore import KCompletion
from kdeui import *

import kate

from lilykde import config
from lilykde.util import py2qstringlist

# Translate messages
from lilykde.i18n import _

lylangs = ('nederlands', 'english', 'deutsch', 'norsk', 'svenska', 'suomi',
    'italiano', 'catalan', 'espanol', 'portuges', 'vlaams')

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

headerNames = zip(*headers)[0]

html = Template(r"""<table style='font-family:serif;'>
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
    dict((k, "<a href='%s'>%s</a>" % (k, v)) for k, v in headers)) % (
        _("bottom of first page"),
        _("bottom of last page"))


class Titles(object):
    """
    A widget where users can fill in all the titles that are put
    in the \header block.
    """

    def __init__(self, parent):
        self.p = parent.addPage(_("Titles and Headers"))

        l = QHBoxLayout(self.p)
        # The html view with the score layout example
        t = KTextBrowser(self.p, None, True)
        t.setLinkUnderline(False)
        t.setText(html)
        t.setMinimumWidth(t.contentsWidth() + 10)
        t.setMinimumHeight(t.contentsHeight() + 5)
        l.addWidget(t)
        QObject.connect(t, SIGNAL("urlClick(const QString &)"), self.focus)

        l.addSpacing(6)

        g = QGridLayout(len(headers), 2, 0)
        g.setColSpacing(1, 200)
        l.addLayout(g)

        # The text entries for all headers, with completion for easy
        # reuse of information.
        completion = config("scorewiz completion")
        for c, h in enumerate(headers):
            name, title = h
            g.addWidget(QLabel(title + ":", self.p), c, 0)
            e = KLineEdit(self.p, name)
            g.addWidget(e, c, 1)
            # set completion items
            compObj = e.completionObject()
            compObj.setItems(
                py2qstringlist(completion.get(name, '').splitlines()))
            compObj.setOrder(KCompletion.Sorted)

    def focus(self, name):
        """
        Give the text entry for the clicked header name keyboard focus.
        """
        self.p.child(str(name)).setFocus()

    def read(self):
        """
        Return a dictionary with header names mapped to
        unicode values for all the text entries.
        """
        return dict((h, unicode(self.p.child(h).text())) for h in headerNames)

    def saveState(self):
        """
        Saves completion items for all lineedits.
        """
        completion = config("scorewiz completion")
        for name, text in self.read().iteritems():
            items = completion.get(name, '').splitlines()
            if text and text not in items:
                items.append(text)
                completion[name] = '\n'.join(items)


class Parts(object):
    """
    The widget where users can select parts and adjust their settings.
    """
    def __init__(self, parent):
        self.p = parent.addPage(_("Parts"))


class Settings(object):
    """
    The widget where users can set other preferences.
    """
    def __init__(self, parent):
        self.p = parent.addPage(_("Score settings"))
        l = QHBoxLayout(self.p)
        self.score = QGroupBox(1, Qt.Horizontal, _("Score settings"), self.p)
        self.prefs = QGroupBox(1, Qt.Horizontal, _("General preferences"), self.p)
        l.addWidget(self.score)
        l.addSpacing(8)
        l.addWidget(self.prefs)

        # General preferences
        h = QHBox(self.prefs)
        QLabel(_("Language:"), h)
        self.lylang = QComboBox(False, h)
        self.lylang.insertItem(_("Default"))
        self.lylang.insertStringList(py2qstringlist(lylangs))
        QToolTip.add(self.lylang, _(
            "Select the LilyPond pitchnames language you want to use."))

        self.typq = QCheckBox(_("Use typographical quotes"), self.prefs)
        QToolTip.add(self.typq, _(
            "Replace normal quotes in titles with nice typographical quotes."))

        self.tagl = QCheckBox(_("Remove default tagline"), self.prefs)
        QToolTip.add(self.tagl, _(
            "Suppress the default tagline output by LilyPond."))


class ScoreWizard(KDialogBase):
    """
    The main score wizard dialog.
    """
    def __init__(self, parent):
        KDialogBase.__init__(self,
            KDialogBase.Tabbed,
            "LilyKDE " + _("Score Setup Wizard"),
            KDialogBase.Ok|KDialogBase.Cancel,
            KDialogBase.Ok,
            parent)

        self.titles = Titles(self)
        self.parts = Parts(self)
        self.settings = Settings(self)


    def printout(self):
        """
        Creates the score output and writes it to the current document.
        """
        output = []
        out = output.append

        # version: TODO

        # language:
        lang = str(self.settings.lylang.currentText())
        if lang != _("Default"):
            out('\n\n\\include "%s.ly"\n' % lang)

        # header:
        noTagline = self.settings.tagl.isChecked()
        typographical = self.settings.typq.isChecked()
        head = self.titles.read()
        if max(head.values()) or noTagline:
            out('\n\\header {\n')
            for h in headerNames:
                val = head[h]
                if val:
                    # replace quotes
                    if typographical:
                        val = re.sub(r'"(.*?)"', u'\u201C\\1\u201D', val)
                        val = re.sub(r"'(.*?)'", u'\u2018\\1\u2019', val)
                        val = val.replace("'", u'\u2018')
                    # escape regular double quotes
                    val = val.replace('"', '\\"')
                    out('  %s = "%s"\n' % (h, val))
                elif h == 'tagline' and noTagline:
                    out('  tagline = ##f\n')
            out('}\n\n')


        # and finally print out:
        kate.view().insertText(''.join(output))

    def done(self, result):
        """
        Close the dialog and create the score if Ok was clicked.
        """
        self.titles.saveState()
        if result == KDialogBase.Accepted:
            self.printout()
        KDialogBase.done(self, result)



# kate: indent-width 4;
