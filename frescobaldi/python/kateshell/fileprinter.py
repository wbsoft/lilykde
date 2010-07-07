# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

from __future__ import unicode_literals

"""
Code to print PDF (or PS) files to a QPrinter.
Based on ideas from Okular's core/fileprinter.cpp.
"""

import os
import shutil
import subprocess
from itertools import repeat

from PyQt4.QtGui import QPrintEngine, QPrinter
from PyKDE4.kdecore import KShell, KStandardDirs


# Exceptions:
class NoPrintCommandFound(Exception):
    """Raised if no valid print command can be found."""
    pass

class CommandNotFound(Exception):
    """Raised if the command could not be started."""
    pass

class CommandFailed(Exception):
    """Raised if the command could be started but exited with a non-zero
    return value."""

def printFiles(fileNames, printer):
    """Prints a list of files (PS or PDF) via a printer command.

    The printer command is constructed by quering the QPrinter object.
    If there is more than one PDF file, print to file should have been disabled
    in the QPrintDialog that configured the printer.
    
    """
    output = printer.outputFileName()
    if output:
        # Print to File, determine suffixes, assume one file
        fileName = fileNames[0]
        inext, outext = (os.path.splitext(name)[1].lower()
                    for name in (fileName, output))
        if inext == outext:
            # just copy
            shutil.copyfile(fileName, output)
        else:
            cmd = "pdf2ps" if outext == ".ps" else "ps2pdf"
            try:
                ret = subprocess.call([cmd, fileName, output])
                if ret:
                    raise CommandFailed(KShell.joinArgs([cmd, fileName, output]), ret)
            except OSError:
                raise CommandNotFound(cmd)
        return
        
    # print to a printer
    
    cmd = []
    
    # Which exe?
    for exe in "lpr-cups", "lpr.cups", "lpr", "lp":
        if KStandardDirs.findExe(exe):
            break
    else:
        raise NoPrintCommandFound()

    cmd.append(exe)
    
    # Add the arguments.
    
    # printer name
    if exe == "lp":
        cmd.append('-d')
    else:
        cmd.append('-P')
    cmd.append(printer.printerName())
    
    # helper for adding (Cups) options to the command line
    def option(s):
        cmd.append('-o')
        cmd.append(s)
    
    # copies
    try:
        copies = printer.actualNumCopies()
    except AttributeError: # only available in Qt >= 4.6
        copies = printer.numCopies()
        
    if exe == "lp":
        cmd.append('-n')
        cmd.append(format(copies))
    else:
        cmd.append('-#{0}'.format(copies))
    
    # job name
    if printer.docName():
        if exe == "lp":
            cmd.append('-t')
            cmd.append(printer.docName())
        elif exe.startswith('lpr'):
            cmd.append('-J')
            cmd.append(printer.docName())
            
    # page range
    if printer.printRange() == QPrinter.PageRange:
        pageRange = "{0}-{1}".format(printer.fromPage(), printer.toPage())
        if exe == "lp":
            cmd.append('-P')
            cmd.append(pageRange)
        else:
            option('page-ranges={0}'.format(pageRange))
    
    # CUPS-specific options; detect if CUPS is available.
    test = QPrinter()
    test.setNumCopies(2)
    cups = test.numCopies() == 1
    
    if cups:
        
        # media, size etc.
        media = []
        size = printer.paperSize()
        if size == QPrinter.Custom:
            media.append("Custom.{0}x{1}mm".format(printer.heightMM(), printer.widthMM()))
        elif size in PAGE_SIZES:
            media.append(PAGE_SIZES[size])
        
        # media source
        source = printer.paperSource()
        if source in PAPER_SOURCES:
            media.append(PAPER_SOURCES[source])
        
        if media:
            option('media={0}'.format(",".join(media)))
        
        # orientation
        orientation = printer.orientation()
        if orientation in ORIENTATIONS:
            option(ORIENTATIONS[orientation])
            
        # double sided
        duplex = printer.duplex()
        if duplex == QPrinter.DuplexNone:
            option("sides=one-sided")
        elif duplex == QPrinter.DuplexAuto:
            if orientation == QPrinter.Landscape:
                option("sides=two-sided-short-edge")
            else:
                option("sides=two-sided-long-edge")
        elif duplex == QPrinter.DuplexLongSide:
            option("sides=two-sided-long-edge")
        elif duplex == QPrinter.DuplexShortSide:
            option("sides=two-sided-short-edge")

        # page order
        if printer.pageOrder() == QPrinter.LastPageFirst:
            option("outputorder=reverse")
        else:
            option("outputorder=normal")
        
        # collate copies
        if printer.collateCopies():
            option("Collate=True")
        else:
            option("Collate=False")
        
        # page margins
        if printer.printEngine().property(QPrintEngine.PPK_PageMargins):
            left, top, right, bottom = printer.getPageMargins(QPrinter.Point)
            option("page-left={0}".format(left))
            option("page-top={0}".format(top))
            option("page-right={0}".format(right))
            option("page-bottom={0}".format(bottom))
            
        # cups properties
        properties = printer.printEngine().property(QPrintEngine.PrintEnginePropertyKey(0xfe00))
        for name, value in zip(*repeat(iter(properties), 2)):
            option("{0}={1}".format(name, value) if value else name)
    
    # file names
    cmd.extend(fileNames)
    try:
        ret = subprocess.call(cmd)
        if ret:
            raise CommandFailed(KShell.joinArgs(cmd), ret)
    except OSError:
        raise CommandNotFound(cmd[0])
    

PAGE_SIZES = {
    QPrinter.A0: "A0",
    QPrinter.A1: "A1",
    QPrinter.A2: "A2",
    QPrinter.A3: "A3",
    QPrinter.A4: "A4",
    QPrinter.A5: "A5",
    QPrinter.A6: "A6",
    QPrinter.A7: "A7",
    QPrinter.A8: "A8",
    QPrinter.A9: "A9",
    QPrinter.B0: "B0",
    QPrinter.B1: "B1",
    QPrinter.B10: "B10",
    QPrinter.B2: "B2",
    QPrinter.B3: "B3",
    QPrinter.B4: "B4",
    QPrinter.B5: "B5",
    QPrinter.B6: "B6",
    QPrinter.B7: "B7",
    QPrinter.B8: "B8",
    QPrinter.B9: "B9",
    QPrinter.C5E: "C5",         # Correct Translation?
    QPrinter.Comm10E: "Comm10", # Correct Translation?
    QPrinter.DLE: "DL",         # Correct Translation?
    QPrinter.Executive: "Executive",
    QPrinter.Folio: "Folio",
    QPrinter.Ledger: "Ledger",
    QPrinter.Legal: "Legal",
    QPrinter.Letter: "Letter",
    QPrinter.Tabloid: "Tabloid",
}

PAPER_SOURCES = {
    # QPrinter.Auto: "",
    QPrinter.Cassette: "Cassette",
    QPrinter.Envelope: "Envelope",
    QPrinter.EnvelopeManual: "EnvelopeManual",
    QPrinter.FormSource: "FormSource",
    QPrinter.LargeCapacity: "LargeCapacity",
    QPrinter.LargeFormat: "LargeFormat",
    QPrinter.Lower: "Lower",
    QPrinter.MaxPageSource: "MaxPageSource",
    QPrinter.Middle: "Middle",
    QPrinter.Manual: "Manual",
    QPrinter.OnlyOne: "OnlyOne",
    QPrinter.Tractor: "Tractor",
    QPrinter.SmallFormat: "SmallFormat",
}

ORIENTATIONS = {
    QPrinter.Portrait: "portrait",
    QPrinter.Landscape: "landscape",
}

