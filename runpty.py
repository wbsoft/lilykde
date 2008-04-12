#!python
"""
Runs a program within a PTY.
Parts were taken from the pty module, but I don't want
to connect stderr and I try to implement some signal handling.
"""

import sys, os, tty, pty, signal, select

STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2
CHILD = 0

def fork():
    """
    fork() -> (pid, master_fd)
    Fork and make the child a session leader with a controlling terminal.
    """
    master_fd, slave_fd = pty.openpty()
    pid = os.fork()
    if pid == CHILD:
        # Establish a new session.
        os.setsid()
        os.close(master_fd)

        # Slave becomes stdin and stdout of child.
        os.dup2(slave_fd, STDIN_FILENO)
        os.dup2(slave_fd, STDOUT_FILENO)
        if (slave_fd > STDERR_FILENO):
            os.close (slave_fd)

        # Explicitly open the tty to make it become a controlling tty.
        tmp_fd = os.open(os.ttyname(STDOUT_FILENO), os.O_RDWR)
        os.close(tmp_fd)
    else:
        os.close(slave_fd)
    # Parent and child process.
    return pid, master_fd

def copy_data(master_fd):
    """
    Parent copy loop.
    Copies pty master -> standard output and standard input -> pty master
    """
    while True:
        try:
            rfds = select.select([master_fd, STDIN_FILENO], [], [])[0]
        except select.error:
            # just call again in case of EINTR
            pass
        else:
            if master_fd in rfds:
                data = os.read(master_fd, 1024)
                os.write(STDOUT_FILENO, data)
            if STDIN_FILENO in rfds:
                data = os.read(STDIN_FILENO, 1024)
                while data != '':
                    n = os.write(master_fd, data)
                    data = data[n:]

def spawn(argv, signals=()):
    """Create a spawned process."""
    pid, master_fd = fork()
    if pid == CHILD:
        os.execlp(argv[0], *argv)
    # install signal handler that passes the signal to the child
    def handler(signalnum, frame):
        os.kill(pid, signalnum)
    for s in signals:
        signal.signal(s, handler)
    try:
        mode = tty.tcgetattr(STDIN_FILENO)
        tty.setraw(STDIN_FILENO)
        restore = 1
    except tty.error:    # This is the same as termios.error
        restore = 0
    try:
        copy_data(master_fd)
    except (IOError, OSError):
        if restore:
            tty.tcsetattr(STDIN_FILENO, tty.TCSAFLUSH, mode)
    os.close(master_fd)

if __name__ == "__main__":
    spawn(sys.argv[1:], (2, 15))
