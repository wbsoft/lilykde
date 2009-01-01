/*
 *  Copyright (c) 2008, Wilbert Berendsen <info@wilbertberendsen.nl>
 *
 *  This program is free software; you can redistribute it and/or
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
#include <kurl.h>
#include <kmimetypetrader.h>
#include <kapplication.h>
#include <kstartupinfo.h>
#include <kconfiggroup.h>

#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusMessage>
#include <QDBusReply>
#include <QProcess>

#include <stdio.h>
#include <stdlib.h>

void bye(QString msg, int exitCode = 1)
{
  fprintf(stderr, "ktexteditservice: %s\n", msg.toLocal8Bit().data());
  exit(exitCode);
}

int main(int argc, char **argv)
{
  KAboutData aboutData(
    "ktexteditservice", 0, ki18n("KTextEditService"), VERSION,
    ki18n("Helper app to open LilyPond textedit:// URLs"),
    KAboutData::License_LGPL,
    ki18n("Copyright (c) 2008 Wilbert Berendsen"),
    KLocalizedString(), "http://lilykde.googlecode.com/");

  KCmdLineArgs::init(argc, argv, &aboutData);

  KCmdLineOptions options;
  options.add("!+url", ki18n("A textedit:// URL, like textedit:///home/joe/music.ly:1:3:3"));
  KCmdLineArgs::addCmdLineOptions(options);

  KComponentData cdata(aboutData);
  KStartupInfo::appStarted();

  KCmdLineArgs *args = KCmdLineArgs::parsedArgs();
  if (args->count() != 1)
    KCmdLineArgs::usageError(i18n("Please specify exactly one textedit URL."));
  KUrl uri = args->url(0);
  // LilyPond always encodes filenames in UTF8 encoding so decode them.
  QString decodedPath = QString::fromUtf8(uri.path().toLatin1());
  QRegExp rx("(/.*[^/]):(\\d+):(\\d+):(\\d+)");
  if (uri.protocol() != "textedit" or !rx.exactMatch(decodedPath))
    KCmdLineArgs::usageError(i18n("Not a valid textedit URL: %1", uri.url()));
  
  /*
   * We have a valid uri. Now find the preferred app/service to run.
   *
   * First check if there's a DBUS app running that can open textedit URLs.
   * This is used for apps that embed e.g. a Okular/PDF part, and want to
   * handle clicks on a LilyPond object themselves.
   * TEXTEDIT_DBUS_PATH should look like org.app.name/path/to/handlerobject
   * The interface name is 'org.lilypond.TextEdit'.
   * The method called is openTextEditUrl(url).
   */
  QString dbus_name(getenv("TEXTEDIT_DBUS_PATH"));
  if (!dbus_name.isNull())
  {
    int slash = dbus_name.indexOf('/');
    if (slash != -1)
    {
      QString name = dbus_name.left(slash);
      QString path = dbus_name.mid(slash);
      QDBusConnectionInterface *i = QDBusConnection::sessionBus().interface ();
      QDBusReply<bool> there = i->isServiceRegistered (name);
      if (there.isValid () && there.value())
      {
	QDBusMessage m = QDBusMessage::createMethodCall (name, path,
	  "org.lilypond.TextEdit", "openTextEditUrl");
	
        QList<QVariant> dbusargs;
        dbusargs.append(uri.url());
        m.setArguments(dbusargs);
	
        QDBusConnection::sessionBus().call (m);
	return 0;
      }
    }
    bye(i18n("Could not contact service given in TEXTEDIT_DBUS_PATH."));
  }
  
  QString editor = "lilypond-invoke-editor"; // the default editor to run
  bool acceptsTextEditUrl = true;            // does it accept a textedit uri?

  /*
   * Special case: are we running inside Kate?
   * Then just run kate (with the --use argument).
   */
  if (getenv("KATE_PID"))
  {
    editor = "kate";
    acceptsTextEditUrl = false;
  }

  /*
   * Otherwise find the preferred service (application).
   * If the application has the X-Accepts-TextEditUrl property set to
   * true in its desktop file, it is assumed to be able to open a LilyPond
   * textedit:// URL directly. (But it should parse the URL itself
   * and not let KIO do it, otherwise we would create an endless loop,
   * calling ktexteditservice recursively.)
   */
  else
  {
    KService::Ptr service = KMimeTypeTrader::self()->preferredService("text/x-lilypond");
    if (service)
    {
      editor = service->exec().simplified().section(' ', 0, 0);
      acceptsTextEditUrl = service->property("X-Accepts-TextEditUrl", QVariant::Bool).toBool();
    }
  }
  
  /*
   * Find out how to start the editor.
   * If the application accepts a textedit URL, just run it now.
   *
   * Otherwise, read our config file to determine how to start the editor.
   */

  QStringList cmd;
  if (acceptsTextEditUrl)
    cmd << editor << uri.url();
  else
  {
    /*
    * Make strings of all possible parameters.
    * Some editor use line numbers or col number starting at 1, others at 0.
    * Most editors start line numbers at 1 and columns at 0, but Kate and KWrite
    * number columns from 1 as well.
    *
    * The user can configure in ktexteditservicerc how different editors are to
    * be started to open a file and jump to a specific cursor position.
    */
    QString file = rx.cap(1);		// the full path of the .ly file
    int line = rx.cap(2).toInt();	// the line number
    int pos  = rx.cap(3).toInt();	// the character position
    int col  = rx.cap(4).toInt();	// the column (differs if tabs are used)

    QString sline = QString::number(line);
    QString sline0 = QString::number(line > 0 ? line - 1: 0);
    QString scol = QString::number(col);
    QString scol1 = QString::number(col + 1);
    QString spos = QString::number(pos);
    QString spos1 = QString::number(pos + 1);

    QString cli(editor + " {file}"); // default value
    if (KGlobal::config()->hasGroup("editors"))
    {
      cli = KGlobal::config()->group("editors").readEntry(editor, cli);
      cli = cli.simplified();
      // robustness checks
      if (! cli.contains("{file}", Qt::CaseInsensitive))
        cli.append(" {file}");     // at least add the file to open
      else if (! cli.contains(' '))
	cli = editor + " {file}";  // fall back to default if invalid command
    }  
    // replace arguments in cli
    cli.replace("{line}", sline, Qt::CaseInsensitive);
    cli.replace("{line0}", sline0, Qt::CaseInsensitive);
    cli.replace("{col}", scol, Qt::CaseInsensitive);
    cli.replace("{col1}", scol1, Qt::CaseInsensitive);
    cli.replace("{pos}", spos, Qt::CaseInsensitive);
    cli.replace("{pos1}", spos1, Qt::CaseInsensitive);
    cmd = cli.split(' ');
    // only now replace the file name, since it might contain spaces 
    cmd.replaceInStrings("{file}", file, Qt::CaseInsensitive);
  }
  // execute the command
  return (int)QProcess::startDetached(cmd.first(), cmd.mid(1));
}
