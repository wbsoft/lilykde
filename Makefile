install = \
	install-mimetype \
	install-syntax \
	install-textedit \
	install-plugin \
	install-katefiletype \
	install-i18n

uninstall = \
	uninstall-mimetype \
	uninstall-syntax \
	uninstall-textedit \
	uninstall-i18n \
	uninstall-plugin \
	uninstall-katefiletype

.PHONY: all install clean uninstall $(install) $(uninstall)

DESTDIR =
PREFIX = $(HOME)/.kde
DATADIR = $(DESTDIR)$(PREFIX)/share

LILYKDE = $(DATADIR)/apps/lilykde
ICONDIR = $(DATADIR)/icons
SERVICEDIR = $(DATADIR)/services
KATEPARTDIR = $(DATADIR)/apps/katepart
PYPLUGINS = $(DATADIR)/apps/kate/pyplugins
MIMELNK = $(DATADIR)/mimelnk
CONFIGDIR = $(DATADIR)/config

PYCOMPILE = python -m py_compile


all = ly.png lilykde/__init__.py

all: $(all)
	@$(MAKE) -C po

ly.png: ly.svg
	@echo Creating ly.png from ly.svg...
	@ksvgtopng 128 128 "`pwd`/ly.svg" "`pwd`/ly.png"

lilykde/__init__.py: VERSION
	@cp $< $@

install: $(install)

clean:
	rm $(all)
	@$(MAKE) -C po clean

uninstall: $(uninstall)
	rm -rf $(LILYKDE)

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
	sed 's!LILYKDEDIR!$(LILYKDE)!' textedit.protocol.in > $(SERVICEDIR)/textedit.protocol
	@mkdir -p $(LILYKDE)
	cp ktexteditservice.py $(LILYKDE)/

uninstall-textedit: textedit.protocol
	@echo Uninstalling textedit integration:
	rm -f $(SERVICEDIR)/textedit.protocol
	rm -f $(LILYKDE)/ktexteditservice.py

install-plugin:
	@echo Installing plugin:
	@mkdir -p $(PYPLUGINS)
	cp lilypond.py $(PYPLUGINS)/
	@cd $(PYPLUGINS) && $(PYCOMPILE) lilypond.py
	@echo Installing Python package lilykde:
	@mkdir -p $(LILYKDE)/lilykde
	cp lilykde/*.py $(LILYKDE)/lilykde/
	@cd $(LILYKDE)/lilykde && $(PYCOMPILE) *.py
	@echo Installing lilypond stuff for expand Pate plugin:
	@mkdir -p $(PYPLUGINS)/expand
	-cp x-lilypond.conf $(PYPLUGINS)/expand/

uninstall-plugin:
	@echo Uninstalling plugin and lilykde package:
	rm -f $(PYPLUGINS)/lilypond.py*
	rm -rf $(LILYKDE)/lilykde
	rm -f $(PYPLUGINS)/expand/x-lilypond.conf

install-katefiletype:
	@echo Adding LilyKDE to katefiletyperc:
	@mkdir -p $(CONFIGDIR)
	@if test -r $(CONFIGDIR)/katefiletyperc; then \
		sed -i '/\[LilyKDE\]/,/^$$/d' $(CONFIGDIR)/katefiletyperc; fi
	cat katefiletyperc >> $(CONFIGDIR)/katefiletyperc

uninstall-katefiletype:
	@echo Removing LilyKDE from katefiletyperc:
	@if test -r $(CONFIGDIR)/katefiletyperc; then \
		sed -i '/\[LilyKDE\]/,/^$$/d' $(CONFIGDIR)/katefiletyperc; fi

install-i18n:
	@$(MAKE) -C po install

uninstall-i18n:
	@$(MAKE) -C po uninstall
