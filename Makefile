installtargets = install-mimetype install-syntax install-textedit install-plugin install-katefiletype install-i18n
uninstalltargets = uninstall-mimetype uninstall-syntax uninstall-textedit uninstall-i18n uninstall-plugin uninstall-katefiletype
.PHONY: all install clean uninstall $(installtargets) $(uninstalltargets)

KDEHOME ?= $(HOME)/.kde
LILYKDE = $(KDEHOME)/share/apps/lilykde

PYCOMPILE = python -m py_compile

lymodules = lilykde.py lilykde_i18n.py lymenu.py lyversion.py lyutil.py lylog.py

all = ly.png textedit.protocol
all: $(all)
	@make -C po

ly.png: ly.svg
	@echo Creating ly.png from ly.svg...
	@ksvgtopng 128 128 "`pwd`/$<" "`pwd`/$@"

textedit.protocol: textedit.protocol.in
	@echo Creating textedit.protocol...
	@sed 's!LILYKDEDIR!$(LILYKDE)!' $< > $@

install: $(installtargets)
	@kbuildsycoca 2> /dev/null

install-mimetype: ly.png
	@echo Installing LilyPond icon and mimetype:
	@mkdir -p $(KDEHOME)/share/icons
	cp ly.png ly.svg $(KDEHOME)/share/icons/
	@mkdir -p $(KDEHOME)/share/mimelnk/text
	cp x-lilypond.desktop $(KDEHOME)/share/mimelnk/text/

install-syntax:
	@echo Installing LilyPond syntax highlighting:
	@mkdir -p $(KDEHOME)/share/apps/katepart/syntax
	cp lilypond.xml $(KDEHOME)/share/apps/katepart/syntax/

install-textedit: textedit.protocol
	@echo Installing textedit integration:
	@mkdir -p $(KDEHOME)/share/services
	cp textedit.protocol $(KDEHOME)/share/services/
	cp ktexteditservice.py $(LILYKDE)/

install-plugin:
	@echo Installing plugin:
	@mkdir -p $(KDEHOME)/share/apps/kate/pyplugins
	cp lilypond.py $(KDEHOME)/share/apps/kate/pyplugins/
	@mkdir -p $(LILYKDE)/py
	cp $(lymodules) $(LILYKDE)/py/
	@mkdir -p $(KDEHOME)/share/apps/kate/pyplugins/expand
	-cp x-lilypond.conf $(KDEHOME)/share/apps/kate/pyplugins/expand/
	@echo Compiling Python modules:
	@cd $(LILYKDE)/py/ && $(PYCOMPILE) $(lymodules)
	@cd $(KDEHOME)/share/apps/kate/pyplugins/ && $(PYCOMPILE) lilypond.py

install-katefiletype:
	@echo Adding LilyKDE to katefiletyperc:
	@if test -r $(KDEHOME)/share/config/katefiletyperc; then \
		sed -i '/\[LilyKDE\]/,/^$$/d' $(KDEHOME)/share/config/katefiletyperc; fi
	cat katefiletyperc >> $(KDEHOME)/share/config/katefiletyperc

install-i18n:
	@make -C po install

clean:
	rm $(all)
	@make -C po clean

uninstall: $(uninstalltargets)
	@kbuildsycoca 2> /dev/null

uninstall-mimetype:
	@echo Uninstalling LilyPond icon and mimetype:
	rm -f $(KDEHOME)/share/icons/ly.png
	rm -f $(KDEHOME)/share/icons/ly.svg
	rm -f $(KDEHOME)/share/mimelnk/text/x-lilypond.desktop

uninstall-syntax:
	@echo Uninstalling LilyPond syntax highlighting:
	rm -f $(KDEHOME)/share/apps/katepart/syntax/lilypond.xml

uninstall-textedit: textedit.protocol
	@echo Uninstalling textedit integration:
	rm -f $(KDEHOME)/share/services/textedit.protocol
	rm -f $(LILYKDE)/ktexteditservice.py

uninstall-i18n:
	@make -C po uninstall

uninstall-plugin:
	@echo Uninstalling plugin:
	rm -f $(KDEHOME)/share/apps/kate/pyplugins/lilypond.py*
	rm -rf $(LILYKDE)/py
	rm -f $(KDEHOME)/share/apps/kate/pyplugins/expand/x-lilypond.conf

uninstall-katefiletype:
	@echo Removing LilyKDE from katefiletyperc:
	@if test -r $(KDEHOME)/share/config/katefiletyperc; then \
		sed -i '/\[LilyKDE\]/,/^$$/d' $(KDEHOME)/share/config/katefiletyperc; fi
