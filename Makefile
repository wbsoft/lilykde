install = \
	install-mimetype \
	install-syntax \
	install-textedit \
	install-servicemenu \
	install-plugin \
	install-i18n \
	install-rumorscripts

uninstall = \
	uninstall-mimetype \
	uninstall-syntax \
	uninstall-textedit \
	uninstall-servicemenu \
	uninstall-i18n \
	uninstall-plugin \
	uninstall-rumorscripts

.PHONY: all install clean uninstall $(install) $(uninstall)

include VERSION

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

PYCOMPILE = python -m py_compile

# for making tarballs
DIST = $(PACKAGE)-$(VERSION)

all = ly.png lilykde/about.py

all: $(all)
	@$(MAKE) -C po

ly.png: ly.svg
	@echo Creating ly.png from ly.svg...
	@ksvgtopng 128 128 "`pwd`/ly.svg" "`pwd`/ly.png"

lilykde/about.py: VERSION
	@cp $< $@

install: all $(install)

clean:
	rm -f $(all)
	@$(MAKE) -C po clean

uninstall: $(uninstall)
	rm -rf $(LILYKDE)

dist:
	@echo Creating $(DIST).tar.gz ...
	@svn export -q . $(DIST)
	@-cd $(DIST) && make -s ly.png && make -s -C po
	@tar zcf $(DIST).tar.gz $(DIST)
	@rm -rf $(DIST)/

install-mimetype: ly.png
	@echo Installing LilyPond icon and mimetype:
	@mkdir -p $(ICONDIR)
	cp ly.svg ly.png $(ICONDIR)/
	@mkdir -p $(MIMELNK)/text
	cp x-lilypond.desktop $(MIMELNK)/text/

uninstall-mimetype:
	@echo Uninstalling LilyPond icon and mimetype:
	rm -f $(ICONDIR)/ly.png
	rm -f $(ICONDIR)/ly.svg
	rm -f $(MIMELNK)/text/x-lilypond.desktop

install-syntax:
	@echo Installing LilyPond syntax highlighting:
	@mkdir -p $(KATEPARTDIR)/syntax
	cp lilypond.xml $(KATEPARTDIR)/syntax

uninstall-syntax:
	@echo Uninstalling LilyPond syntax highlighting:
	rm -f $(KATEPARTDIR)/syntax/lilypond.xml

install-textedit:
	@echo Installing textedit protocol:
	@mkdir -p $(SERVICEDIR)
	sed 's!LILYKDEDIR!$(REAL_LILYKDE)!' textedit.protocol.in \
		> $(SERVICEDIR)/textedit.protocol
	@mkdir -p $(LILYKDE)
	cp ktexteditservice.py $(LILYKDE)/

uninstall-textedit:
	@echo Uninstalling textedit integration:
	rm -f $(SERVICEDIR)/textedit.protocol
	rm -f $(LILYKDE)/ktexteditservice.py

install-plugin: lilykde/about.py
	@echo Installing plugin:
	@mkdir -p $(PYPLUGINS)
	cp lilypond.py $(PYPLUGINS)/
	@cd $(PYPLUGINS) && $(PYCOMPILE) lilypond.py
	@echo Installing Python package lilykde:
	@mkdir -p $(LILYKDE)/lilykde
	@cd $(LILYKDE)/lilykde && rm -f *.py*
	cp lilykde/*.py $(LILYKDE)/lilykde/
	@cd $(LILYKDE)/lilykde && $(PYCOMPILE) *.py
	@echo Installing Python module hyphenator:
	cp hyphenator.py $(LILYKDE)/
	@cd $(LILYKDE) && $(PYCOMPILE) hyphenator.py
	@echo Installing runpty.py helper script:
	cp runpty.py $(LILYKDE)/
	@echo Installing lilypond stuff for expand Pate plugin:
	@mkdir -p $(PYPLUGINS)/expand
	-cp x-lilypond.conf $(PYPLUGINS)/expand/

uninstall-plugin:
	@echo Uninstalling plugin and lilykde package:
	rm -f $(PYPLUGINS)/lilypond.py*
	rm -rf $(LILYKDE)/lilykde
	rm -f $(LILYKDE)/hyphenator.py
	rm -f $(LILYKDE)/runpty.py
	rm -f $(PYPLUGINS)/expand/x-lilypond.conf

install-i18n:
	@$(MAKE) -C po install

uninstall-i18n:
	@$(MAKE) -C po uninstall

install-servicemenu:
	@echo Installing Konqueror servicemenu
	@mkdir -p $(LILYKDE)
	cp lilypond-servicemenu-helper.py $(LILYKDE)/
	@mkdir -p $(SERVICEMENUDIR)
	sed 's!LILYKDEDIR!$(REAL_LILYKDE)!' lilypond-servicemenu.desktop.in \
		> $(SERVICEMENUDIR)/lilypond-servicemenu.desktop

uninstall-servicemenu:
	@echo Uninstalling Konqueror servicemenu
	rm -f $(SERVICEMENUDIR)/lilypond-servicemenu.desktop
	rm -f $(LILYKDE)/lilypond-servicemenu-helper.py

install-rumorscripts:
	@echo Installing Rumor scripts
	@mkdir -p $(LILYKDE)/rumor
	cp rumor/*.scm $(LILYKDE)/rumor/

uninstall-rumorscripts:
	@echo Uninstalling Rumor scripts
	rm -fr $(LILYKDE)/rumor
