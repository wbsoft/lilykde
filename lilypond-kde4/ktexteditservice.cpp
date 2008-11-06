/*
 *  Copyright (c) 2008, Wilbert Berendsen <info@wilbertberendsen.nl>
 *
 *  This library is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU Library General Public
 *  License version 2 as published by the Free Software Foundation;
 *
 *  This library is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *  Library General Public License for more details.
 *
 *  You should have received a copy of the GNU Library General Public License
 *  along with this library; see the file COPYING.LIB.  If not, write to
 *  the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 *  Boston, MA 02110-1301, USA.
 */

#include <kcmdlineargs.h>
#include <kmimetypetrader.h>
#include <kmimetype.h>
#include <kapplication.h>
#include <kstartupinfo.h>
#include <klocale.h>
#include <kservicetypetrader.h>

#include <QtDbus>

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
  KCmdLineArgs::init(argc, argv, "ktexteditservice", 0,
    ki18n("KTextEditService"), "1.0",
    ki18n("Helper app to open LilyPond textedit:// URIs"));

  KCmdLineOptions options;
  options.add("!+uri", ki18n(
    "A textedit:// URI, like textedit:///home/joe/music.ly:1:3:3"));
  KCmdLineArgs::addCmdLineOptions(options);

  KApplication app();
  KStartupInfo::appStarted();

  KCmdLineArgs *args = KCmdLineArgs::parsedArgs();

  QString uri = args->arg(0);
  QRegExp rx("textedit:/{,2}(/[^/].*):(\\d+):(\\d+):(\\d+)");
  if (!rx.exactMatch(uri))
  {
    fprintf(stderr,
      i18n("Not a valid textedit URI: %1").arg(uri).toLocal8Bit().data());
    exit(1);
  }
  
  // We have a valid uri.
  QString path = rx.cap(1);		// the path of the .ly file
  int line = rx.cap(2).toInt();		// the line number
  int pos  = rx.cap(3).toInt();		// the character position
  int col  = rx.cap(4).toInt();		// the column (differs if tabs are used)

  // Now find the preferred app/service to run.

  /*
   * 1. Is there a DBUS app running that can open textedit URLs?
   * This is used for apps that embed e.g. a Okular/PDF part, and want to
   * handle clicks on a LilyPond object themselves.
   * TEXTEDIT_DBUS_PATH should look like org.app.name/path/to/handlerobject
   * The interface name is 'org.lilypond.TextEdit'.
   * The method called openTextEditUrl(url).
   */
  QString dbus_name(getenv("TEXTEDIT_DBUS_PATH"));
  if (dbus_name)
  {
    int pos = dbus_name.indexOf('/');
    

  }

  
