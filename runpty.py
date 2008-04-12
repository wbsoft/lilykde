#!python
"""
Runs a program within a PTY.
Some ideas were taken from the pty module, but I don't want
to connect stderr and I implement some signal handling.
"""

import sys, os, tty, pty, signal, select, subprocess

STDIN, STDOUT = 0, 1

master, slave = pty.openpty()
p = subprocess.Popen(sys.argv[1:],
    stdin = slave, stdout = slave, close_fds = True)

for s in signal.SIGINT, signal.SIGTERM:
    signal.signal(s, lambda signalnum, frame:
        os.kill(p.pid, signalnum))

try:
    mode = tty.tcgetattr(STDIN)
    tty.setraw(STDIN)
    restore = 1
except tty.error:
    restore = 0

while p.poll() is None:
    try:
        fds = select.select([master, STDIN], [], [])[0]
    except select.error:
        pass
    else:
        if master in fds:
            os.write(STDOUT, os.read(master, 1024))
        if STDIN in fds:
            data = os.read(STDIN, 1024)
            while data:
                n = os.write(master, data)
                data = data[n:]

if restore:
    tty.tcsetattr(STDIN, tty.TCSAFLUSH, mode)
os.close(master)
sys.exit(p.poll())
