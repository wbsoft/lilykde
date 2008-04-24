# kate: hl Makefile;

# prefix to install LilyKDE to.
# setting DESTDIR enables you to install to a temporary image
# directory, from which you can create a distributable package.
DESTDIR =
PREFIX  := $(shell kde-config --localprefix | sed 's,/$$,,')
ifeq ($(PREFIX),)
PREFIX  := $(HOME)/.kde
endif
DATADIR := $(DESTDIR)$(PREFIX)/share

LILYKDE = $(DATADIR)/apps/lilykde
# next one is LILYKDE without DESTDIR prepended
REAL_LILYKDE = $(PREFIX)/share/apps/lilykde
ICONDIR = $(DATADIR)/icons
SERVICEDIR = $(DATADIR)/services
SERVICEMENUDIR = $(DATADIR)/apps/konqueror/servicemenus
KATEPARTDIR = $(DATADIR)/apps/katepart
PYPLUGINS = $(DATADIR)/apps/kate/pyplugins
MIMELNK = $(DATADIR)/mimelnk
CONFIGDIR = $(DATADIR)/config

# Various programs:
PYCOMPILE = python -m py_compile
XGETTEXT = xgettext
MSGMERGE = msgmerge
MSGFMT = msgfmt -v

