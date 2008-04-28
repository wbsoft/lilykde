install = \
	install-mimetype \
	install-syntax \
	install-textedit \
	install-servicemenu \
	install-plugin \
	install-rumorscripts

uninstall = \
	uninstall-mimetype \
	uninstall-syntax \
	uninstall-textedit \
	uninstall-servicemenu \
	uninstall-plugin \
	uninstall-rumorscripts

subdirs = po pics

.PHONY: all install clean uninstall $(install) $(uninstall) $(subdirs)

include VERSION
include config.mk

# for making tarballs
DIST = $(PACKAGE)-$(VERSION)

all = ly.png lilykde/about.py

all: $(all) $(subdirs)

ly.png: ly.svg
	@echo Creating ly.png from ly.svg...
	@ksvgtopng 128 128 "`pwd`/ly.svg" "`pwd`/ly.png"

lilykde/about.py: VERSION
	@cp $< $@

$(subdirs):
	@$(MAKE) -C $@ $(MAKECMDGOALS)

install: $(all) $(install) $(subdirs)

clean: $(subdirs)
	rm -f $(all)

uninstall: $(uninstall) $(subdirs)
	rm -rf $(LILYKDE)

dist:
	@echo Creating $(DIST).tar.gz ...
	@svn export -q . $(DIST)
	@-cd $(DIST) && make -s
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

install-servicemenu:
	@echo Installing Konqueror servicemenu:
	@mkdir -p $(LILYKDE)
	cp lilypond-servicemenu-helper.py $(LILYKDE)/
	@mkdir -p $(SERVICEMENUDIR)
	sed 's!LILYKDEDIR!$(REAL_LILYKDE)!' lilypond-servicemenu.desktop.in \
		> $(SERVICEMENUDIR)/lilypond-servicemenu.desktop

uninstall-servicemenu:
	@echo Uninstalling Konqueror servicemenu:
	rm -f $(SERVICEMENUDIR)/lilypond-servicemenu.desktop
	rm -f $(LILYKDE)/lilypond-servicemenu-helper.py

install-rumorscripts:
	@echo Installing Rumor scripts:
	@mkdir -p $(LILYKDE)/rumor
	cp rumor/*.scm $(LILYKDE)/rumor/

uninstall-rumorscripts:
	@echo Uninstalling Rumor scripts:
	rm -fr $(LILYKDE)/rumor
