# setting DESTDIR enables you to install to a temporary image
# directory, from which you can create a distributable package.
DESTDIR =

# prefix to install lilypond-kde4 to.
PREFIX = $(shell kde4-config --prefix)

BINDIR = $(PREFIX)/bin
DATADIR = $(PREFIX)/share
ICONDIR = $(DATADIR)/icons
KATEDIR = $(DATADIR)/apps/katepart
SERVICEDIR = $(DATADIR)/kde4/services
