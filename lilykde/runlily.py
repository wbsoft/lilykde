"""

A LilyPond Kate/Pate plugin.

This part is loaded when the LilyPond is first called.

"""

import re
import os

from qt import SIGNAL, QString, QObject
from kdecore import KURL

# Some utility functions
from lilykde.util import htmlescape, encodeurl, kprocess
from lilykde.widgets import sorry

# config settings
from lilykde import config

# translate the messages
from lilykde.i18n import _

# Classes

class LyFile(object):
    """
    Given a kate doc, returns an object that allows for easy determination
    of corresponding PDF files, etc.
    """
    def __init__(self, doc):
        self.doc = doc
        self.kurl = KURL(doc.url)
        self.path = unicode(self.kurl.path()) # the full path to the ly file
        self.ly = os.path.basename(self.path)
        self.directory = os.path.dirname(self.path)
        self.basename, self.extension = os.path.splitext(self.ly)
        self.pdf = self.ly and os.path.join(
            self.directory, self.basename + ".pdf") or None
        self.preview = False    # run with point-and-click?

    def isLocalFile(self):
            return self.kurl.isLocalFile()

    def isLyFile(self):
        return self.doc.information.mimeType == 'text/x-lilypond' or \
               self.extension in ('.ly', '.ily', 'lyi')

    def updated(self, file):
        return os.path.getmtime(self.path) <= os.path.getmtime(file)

    def hasUpdatedPDF(self):
        return self.isLocalFile() and os.path.isfile(self.pdf) and \
            self.updated(self.pdf)

    def previewPDF(self):
        if self.pdf:
            from lilykde import pdf
            pdf.openFile(self.pdf)

    def getUpdated(self, ext):
        from glob import glob
        files = [os.path.join(self.directory, self.basename + ext)]
        files.extend(
            glob(os.path.join(self.directory, self.basename + "?*" + ext)))
        return [f for f in files if os.path.isfile(f) and self.updated(f)]


class Outputter:
    """
    Collects data and as soon as a newline is found,
    sends it to a logger
    """
    def __init__(self, log, f, color=None):
        self.log, self.f, self.color = log, f, color
        self.buf = []

    def receive(self, proc, buf, length):
        l = unicode(QString.fromUtf8(buf, length)).split("\n")
        self.buf.append(l[0])
        if len(l) > 1:
            self.output("".join(self.buf))
            for i in l[1:-1]:
                self.output(i)
            self.buf = [l[-1]]

    _editstr = re.compile(r"^(.*?):(\d+):(?:(\d+):)?").sub

    def output(self, line):
        """
        Write a line of LilyPond console output to the logger, replacing
        file- and line numbers with clickable textedit:// links.
        """
        line = htmlescape(line)
        line = self._editstr(self._texteditrepl, line, 1)
        self.log.append(
          u'<span style="font-family:monospace;">%s</span>' % line, self.color)

    def _texteditrepl(self, m):
        (file, line), col = m.group(1,2), m.group(3) or "0"
        file = os.path.join(self.f.directory, file)
        return u'<a href="textedit://%s:%s:%s:%s">%s</a>' % \
            (encodeurl(file), line, col, col, m.group())

    def close(self):
        s = "".join(self.buf)
        if s:
            self.log.append(s, self.color)


class LyJob(kprocess):
    """
    To be subclassed.
    Class to run a lilypond job. Expects a LyFile object with all the data, and
    a LogWindow to write stdout and stderr to.
    """
    def __init__(self, f, log):
        super(LyJob, self).__init__()
        self.f = f
        self.setExecutable(config.group("commands").get("lilypond", "lilypond"))
        self.setWorkingDirectory(f.directory)
        self.log = log
        self.stdout = Outputter(log, f)
        self.stderr = Outputter(log, f)

        QObject.connect(self, SIGNAL("receivedStdout(KProcess*, char*, int)"),
            self.stdout.receive)
        QObject.connect(self, SIGNAL("receivedStderr(KProcess*, char*, int)"),
            self.stderr.receive)

    def _run(self, args, mode=None):
        self.setArguments(args)
        if mode:
            self.log.ok(
                _("LilyPond [$filename] starting ($mode)...").args(
                filename = self.f.ly, mode = mode))
        else:
            self.log.ok(_("LilyPond [$filename] starting...").args(
                filename = self.f.ly))
        self.start() or self.log.fail(_("Could not start LilyPond."))

    def _finish(self):
        self.stdout.close()
        self.stderr.close()
        success = False
        if self.signalled():
            self.log.fail(
              _("LilyPond was terminated by signal %d.") % self.exitSignal())
        elif self.normalExit():
            if self.exitStatus() != 0:
                self.log.fail(
                _("LilyPond exited with return code %d.") % self.exitStatus())
            else:
                self.log.ok(_("LilyPond [$filename] finished.").args(
                    filename = self.f.ly))
                success = True
        else:
            self.log.fail(_("LilyPond exited abnormally."))
        self.completed(success)

    @staticmethod
    def instances():
        return [i for i in kprocess.instances() if isinstance(i, LyJob)]


class Ly2PDF(LyJob):
    """
    Converts a LilyPond file to PDF
    """
    def run(self, preview=False):
        self.preview = preview
        args = ["--pdf", "-o", self.f.basename]
        if preview:
            mode = _("preview mode")
        else:
            mode = _("publish mode")
            args.append("-dno-point-and-click")
        args.append(self.f.ly)
        self._run(args, mode)

    def completed(self, success):
        if success and self.f.pdf:
            def act(action):
                return int(config.group("actions").get(action, 1))
            actions = []
            if act("open_folder"):
                actions.append(("file://%s" % self.f.directory,
                    _("Open folder")))
            if self.f.hasUpdatedPDF():
                self.f.previewPDF()
                if act("open_pdf"):
                    actions.append(("file://%s" % self.f.pdf, _("Open PDF")))
                if act("print_pdf"):
                    actions.append(("print=file://%s" % self.f.pdf, _("Print")))
                if act("email_pdf"):
                    # hack: prevent QTextView from recognizing mailto urls, as
                    # it then uses the mailClick signal, which does not give us
                    # the query string. Later on, we prepend the "mailto:?" :)
                    if self.preview:
                        actions.append(("emailpreview=file://%s" % self.f.pdf,
                            _("Email PDF (preview)")))
                    else:
                        actions.append(("email=file://%s" % self.f.pdf,
                            _("Email PDF")))
            else:
                self.log.msg(_("LilyPond did not write a PDF. "
                               "You probably forgot <b>\layout</b>?"))
            midis = self.f.getUpdated(".midi")
            if act("play_midi") and midis:
                actions.append(("file://%s" % midis[0], _("Play MIDI")))
                actions.extend([("file://%s" % m, str(n+1))
                    for n, m in enumerate(midis[1:])])
            self.log.actions(actions)


def runLilyPond(doc, preview=False):
    """
    Run Lilypond on the specified kate.document() and produce a PDF in the same
    directory if that is writable. If param `preview` is True, the PDF will
    contain clickable notes and other objects (point-and-click). If false, the
    PDF will not contain those textedit:// links.
    """
    if doc.url == "":
        sorry(_("Your document currently has no filename, please save first."))
        return

    if doc.modified:
        sorry(_("Your document has been modified, please save first."))
        return

    f = LyFile(doc)
    if not f.isLocalFile():
        # TODO: implement remote file support
        sorry(_("Sorry, support for remote files is not yet implemented.\n"
                   "Please save your document to a local file."))
        return

    from lilykde import log
    Ly2PDF(f, log.logWidget()).run(preview)

def interrupt(doc):
    """
    Interrupt a LilyPond task if there is one running on the specified document.
    """
    if doc.url:
        f = LyFile(doc)
        for i in LyJob.instances():
            if i.f.ly == f.ly:
                i.kill(2)
                break


# kate: indent-width 4;
