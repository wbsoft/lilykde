# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
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
Runs a program within a PTY.
Some ideas were taken from the pty module, but I don't want
to connect stderr and I implement some signal handling.
"""

import sys, os, tty, pty, signal, select, subprocess

STDIN, STDOUT = 0, 1

master, slave = pty.openpty()
p = subprocess.Popen(sys.argv[1:],
    stdin = slave, stdout = STDOUT, close_fds = True)

def terminate(signalnum, frame):
    os.kill(p.pid, signalnum)
signal.signal(signal.SIGINT, terminate)
signal.signal(signal.SIGTERM, terminate)

try:
    mode = tty.tcgetattr(STDIN)
    tty.setraw(STDIN)
    restore = 1
except tty.error:
    restore = 0

while p.poll() is None:
    try:
        fds = select.select([STDIN], [], [], 0.5)[0]
    except select.error:
        pass
    else:
        if STDIN in fds:
            data = os.read(STDIN, 1024)
            while data:
                n = os.write(master, data)
                data = data[n:]

if restore:
    tty.tcsetattr(STDIN, tty.TCSAFLUSH, mode)
os.close(master)
sys.exit(p.poll())
