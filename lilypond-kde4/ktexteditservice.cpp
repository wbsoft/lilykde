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

#include <kaboutdata.h>
#include <kcmdlineargs.h>
#include <kmimetypetrader.h>
#include <kmimetype.h>
#include <kapplication.h>
#include <kstartupinfo.h>
#include <kconfiggroup.h>
#include <klocale.h>
#include <kservicetypetrader.h>

#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusMessage>
#include <QDBusReply>
#include <QProcess>

#include <stdio.h>
#include <stdlib.h>

void bye(QString msg, int exitCode = 1)
{
  fputs((msg + '\n').toLocal8Bit().data(), stderr);
  exit(exitCode);
}

int main(int argc, char **argv)
{
  KAboutData aboutData(
    "ktexteditservice", 0, ki18n("KTextEditService"), VERSION,
    ki18n("Helper app to open LilyPond textedit:// URIs"),
    KAboutData::License_LGPL,
    ki18n("Copyright (c) 2008 Wilbert Berendsen"),
    KLocalizedString(), "http://lilykde.googlecode.com/");

  KCmdLineArgs::init(argc, argv, &aboutData);

  KCmdLineOptions options;
  options.add("!+uri", ki18n("A textedit:// URI, like textedit:///home/joe/music.ly:1:3:3"));
  KCmdLineArgs::addCmdLineOptions(options);

  KApplication app(false); // no GUI
  KStartupInfo::appStarted();

  KCmdLineArgs *args = KCmdLineArgs::parsedArgs();

  QString uri = args->arg(0);
  QRegExp rx("textedit:/{,2}(/[^/].*):(\\d+):(\\d+):(\\d+)");
  if (!rx.exactMatch(uri))
    bye(i18n("Not a valid textedit URI: ") + uri);
  
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
  if (!dbus_name.isNull())
  {
    int pos = dbus_name.indexOf('/');
    if (pos != -1)
    {
      QString name = dbus_name.left(pos);
      QString path = dbus_name.mid(pos);
      QDBusConnectionInterface *i = QDBusConnection::sessionBus().interface ();
      QDBusReply<bool> there = i->isServiceRegistered (name);
      if (there.isValid () && there.value())
      {
	// let the remote app open the textedit uri
	QDBusMessage m = QDBusMessage::createMethodCall (name, path,
	  "org.lilypond.TextEdit", "openTextEditUrl");

        QList<QVariant> dbusargs;
        dbusargs.append(uri);
        m.setArguments(dbusargs);

        QDBusConnection::sessionBus().call (m);
	return 0;
      }
    }
    bye(i18n("Could not contact service given in TEXTEDIT_DBUS_PATH\n"));
  }
  
  QString editor = "lilypond-invoke-editor"; // the default editor to run
  bool acceptsTextEditUrl = true;            // does it accept a textedit uri?

  /*
   * 2. Special case: are we running inside Kate?
   */
  if (getenv("KATE_PID"))
  {
    editor = "kate";
    acceptsTextEditUrl = false;
  }

  /*
   * 3. Then find the preferred service.
   */
  else
  {
    KService::Ptr service = KMimeTypeTrader::self()->preferredService("text/x-lilypond");
    if (service)
    {
      editor = service->exec().simplified().section(' ', 0, 0);
      acceptsTextEditUrl = service->property("X-Accepts-TextEditUrl").toBool();
    }
  }
  
  // now find out how to start the editor
  QString sline = QString::number(line);
  QString sline0 = QString::number(line > 0 ? line - 1: 0);
  QString scol = QString::number(col);
  QString scol1 = QString::number(col + 1);
  QString spos = QString::number(pos);
  QString spos1 = QString::number(pos + 1);

  QStringList cmd;
  if (acceptsTextEditUrl)
    cmd << editor << uri;
  else
  {
    // Get info about how to start the editor from our config file
    QString cli(editor + " {file}");
    if (KGlobal::config()->hasGroup("editors"))
      cli = KGlobal::config()->group("editors").readEntry(editor, cli);
    // replace arguments in cli
    cli = cli.simplified();
    cli.replace("{line}", sline, Qt::CaseInsensitive);
    cli.replace("{line0}", sline0, Qt::CaseInsensitive);
    cli.replace("{col}", scol, Qt::CaseInsensitive);
    cli.replace("{col1}", scol1, Qt::CaseInsensitive);
    cli.replace("{pos}", spos, Qt::CaseInsensitive);
    cli.replace("{pos1}", spos1, Qt::CaseInsensitive);
    cmd = cli.split(' ');
    cmd.replaceInStrings("{file}", path, Qt::CaseInsensitive);
  }
  // execute command
  return (int)QProcess::startDetached(cmd.first(), cmd.mid(1));
}
