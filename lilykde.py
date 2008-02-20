"""

A LilyPond Kate/Pate plugin.

This part is loaded when the LilyPond is first called.

"""

import re
import os.path

import kate
import kate.gui

from qt import *
from kdecore import KApplication, KURL, KProcess
from kdeui import KTextBrowser
from kparts import createReadOnlyPart
from kio import KRun

# Some utility functions
from lyutil import *

# translate the messages
from lilykde_i18n import _

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
        self.pdf and PDFToolView().create().openFile(self.pdf)

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


class Job(object):
    """
    To be subclassed. To instatiate a job, and keep a pointer so the instance
    will not go out of scope. You must call our __init__() if you reimplement
    it.

    Child classes should implement a _finish() method.
    """
    def __init__(self):
        self.p = KProcess()
        busy()
        @onSignal(self.p, "processExited(KProcess*)")
        def finish():
            busy(False)
            self.p.wait()
            self._finish()
            del self.p

    def _finish(self):
        pass


class LyJob(Job):
    """
    To be subclassed.
    Class to run a lilypond job. Expects a LyFile object with all the data, and
    a LogWindow to write stdout and stderr to.
    """
    def __init__(self, f, log):
        super(LyJob, self).__init__()
        self.f = f
        self.p.setExecutable("lilypond")
        self.p.setWorkingDirectory(f.directory)
        self.log = log
        self.stdout = Outputter(log, f)
        self.stderr = Outputter(log, f)

        QObject.connect(self.p, SIGNAL("receivedStdout(KProcess*, char*, int)"),
            self.stdout.receive)
        QObject.connect(self.p, SIGNAL("receivedStderr(KProcess*, char*, int)"),
            self.stderr.receive)

    def _run(self, args, mode=None):
        self.p.setArguments(args)
        if mode:
            self.log.ok(_("LilyPond [%s] starting (%s)...") % (self.f.ly, mode))
        else:
            self.log.ok(_("LilyPond [%s] starting...") % self.f.ly)
        if not self.p.start(KProcess.NotifyOnExit, KProcess.AllOutput):
            self.log.fail(_("Could not start LilyPond."))

    def _finish(self):
        self.stdout.close()
        self.stderr.close()
        success = False
        if self.p.signalled():
            self.log.fail(
              _("LilyPond was terminated by signal %d.") % self.p.exitSignal())
        elif self.p.normalExit():
            if self.p.exitStatus() != 0:
                self.log.fail(
                _("LilyPond exited with return code %d.") % self.p.exitStatus())
            else:
                self.log.ok(_("LilyPond [%s] finished.") % self.f.ly)
                success = True
        else:
            self.log.fail(_("LilyPond exited abnormally."))
        self.completed(success)


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
            actions = [("file://%s" % self.f.directory, _("Open folder"))]
            if self.f.hasUpdatedPDF():
                self.f.previewPDF()
                actions.append(("file://%s" % self.f.pdf, _("Open PDF")))
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
            if midis:
                actions.append(("file://%s" % midis[0], _("Play MIDI")))
                actions.extend([("file://%s" % m, str(n+1))
                    for n, m in enumerate(midis[1:])])
            self.log.actions(actions)


class LazyToolView(object):
    """
    To be subclassed. Creates or returns an existing ToolView. The toolview is
    really created when create() is called.
    """
    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
            cls._instance.tv = None
        return cls._instance

    def create(self):
        if not self.tv:
            self._initialize()    # should be implemented in the child class
        return self

    def show(self):
        if self.tv: self.tv.show()

    def hide(self):
        if self.tv: self.tv.hide()


class PDFToolView(LazyToolView):
    """
    Returns a/the PDF preview ToolView. Call .create() to really create and show
    the view.
    """
    def _initialize(self):
        self.tv = kate.gui.Tool("PDF", "pdf", kate.gui.Tool.right)
        self.pdfpart = createReadOnlyPart("libkpdfpart", self.tv.widget)
        self.pdfpart.widget().setFocusPolicy(QWidget.NoFocus)
        self.show()
        self.file = ""

    def openFile(self, pdf):
        #if self.file != pdf:
            # KPDF does not always watch the file for updates if the inode
            # number changes, which LilyPond does...
            self.pdfpart.openURL(KURL(pdf))
            #self.file = pdf


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

    import lylog
    Ly2PDF(f, lylog).run(preview)

# kate: indent-width 4;
