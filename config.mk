# kate: hl Makefile;

# setting DESTDIR enables you to install to a temporary image
# directory, from which you can create a distributable package.
DESTDIR =

# prefix to install LilyKDE to.
PREFIX  := $(shell kde-config --localprefix | sed 's,/$$,,')
ifeq ($(PREFIX),)
PREFIX  := $(HOME)/.kde
endif
DATADIR := $(PREFIX)/share

LILYKDE = $(DATADIR)/apps/lilykde
LOCALEDIR = $(DATADIR)/locale
ICONDIR = $(DATADIR)/icons
SERVICEDIR = $(DATADIR)/services
SERVICEMENUDIR = $(DATADIR)/apps/konqueror/servicemenus
KATEPARTDIR = $(DATADIR)/apps/katepart
PYPLUGINS = $(DATADIR)/apps/kate/pyplugins
MIMELNK = $(DATADIR)/mimelnk
CONFIGDIR = $(DATADIR)/config

# Various programs:
INSTALL = install
PYCOMPILE = python -m py_compile
XGETTEXT = xgettext
MSGMERGE = msgmerge
MSGFMT = msgfmt -v

