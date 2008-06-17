install = \
	install-mimetype \
	install-syntax \
	install-textedit \
	install-servicemenu \
	install-plugin

uninstall = \
	uninstall-mimetype \
	uninstall-syntax \
	uninstall-textedit \
	uninstall-servicemenu \
	uninstall-plugin

subdirs = lilykde po rumor pics

modules = hyphenator.py rational.py

.PHONY: all install clean uninstall $(install) $(uninstall) $(subdirs)

include VERSION
include config.mk

# for making tarballs
DIST = $(PACKAGE)-$(VERSION)

all = ly.png textedit.protocol lilypond-servicemenu.desktop

all: $(all) $(subdirs)

ly.png: ly.svg
	@echo Creating ly.png from ly.svg...
	@ksvgtopng 128 128 "`pwd`/ly.svg" "`pwd`/ly.png"

textedit.protocol lilypond-servicemenu.desktop: %: %.in
	sed 's!LILYKDEDIR!$(LILYKDE)!' $< > $@

$(subdirs):
	@$(MAKE) -C $@ $(MAKECMDGOALS)

install: $(all) $(install) $(subdirs)

clean: $(subdirs)
	rm -f $(all)

uninstall: $(uninstall) $(subdirs)
	rm -rf $(DESTDIR)$(LILYKDE)

dist:
	@echo Creating $(DIST).tar.gz ...
	@svn export -q . $(DIST)
	@cd $(DIST) && make -s
	@tar zcf $(DIST).tar.gz $(DIST)
	@rm -rf $(DIST)/
	@echo Finished creating $(DIST).tar.gz.

install-mimetype: ly.png
	@echo Installing LilyPond icon and mimetype:
	$(INSTALL) -d $(DESTDIR)$(ICONDIR)
	$(INSTALL) -m 644 ly.svg ly.png $(DESTDIR)$(ICONDIR)/
	$(INSTALL) -d $(DESTDIR)$(MIMELNK)/text
	$(INSTALL) -m 644 x-lilypond.desktop $(DESTDIR)$(MIMELNK)/text/

uninstall-mimetype:
	@echo Uninstalling LilyPond icon and mimetype:
	rm -f $(DESTDIR)$(ICONDIR)/ly.png
	rm -f $(DESTDIR)$(ICONDIR)/ly.svg
	rm -f $(DESTDIR)$(MIMELNK)/text/x-lilypond.desktop

install-syntax:
	@echo Installing LilyPond syntax highlighting:
	$(INSTALL) -d $(DESTDIR)$(KATEPARTDIR)/syntax
	$(INSTALL) -m 644 lilypond.xml $(DESTDIR)$(KATEPARTDIR)/syntax/

uninstall-syntax:
	@echo Uninstalling LilyPond syntax highlighting:
	rm -f $(DESTDIR)$(KATEPARTDIR)/syntax/lilypond.xml

install-textedit: textedit.protocol
	@echo Installing textedit protocol:
	$(INSTALL) -d $(DESTDIR)$(SERVICEDIR)
	$(INSTALL) -m 644 textedit.protocol $(DESTDIR)$(SERVICEDIR)/
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)
	$(INSTALL) -m 644 ktexteditservice.py $(DESTDIR)$(LILYKDE)/

uninstall-textedit:
	@echo Uninstalling textedit integration:
	rm -f $(DESTDIR)$(SERVICEDIR)/textedit.protocol
	rm -f $(DESTDIR)$(LILYKDE)/ktexteditservice.py

install-plugin:
	@echo Installing plugin:
	$(INSTALL) -d $(DESTDIR)$(PYPLUGINS)
	$(INSTALL) -m 644 lilypond.py $(DESTDIR)$(PYPLUGINS)/
	cd $(DESTDIR)$(PYPLUGINS) && $(PYCOMPILE) lilypond.py
	@echo Installing Python modules $(modules):
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)
	$(INSTALL) -m 644 $(modules) $(DESTDIR)$(LILYKDE)/
	cd $(DESTDIR)$(LILYKDE) && $(PYCOMPILE) $(modules)
	@echo Installing runpty.py helper script:
	$(INSTALL) -m 644 runpty.py $(DESTDIR)$(LILYKDE)/

uninstall-plugin:
	@echo Uninstalling plugin:
	rm -f $(DESTDIR)$(PYPLUGINS)/lilypond.py*
	-cd $(DESTDIR)$(LILYKDE)/ && rm -f $(modules) $(addsuffix c,$(modules))
	rm -f $(DESTDIR)$(LILYKDE)/runpty.py

install-servicemenu: lilypond-servicemenu.desktop
	@echo Installing Konqueror servicemenu:
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)
	$(INSTALL) -m 644 lilypond-servicemenu-helper.py $(DESTDIR)$(LILYKDE)/
	$(INSTALL) -d $(DESTDIR)$(SERVICEMENUDIR)
	$(INSTALL) -m 644 lilypond-servicemenu.desktop $(DESTDIR)$(SERVICEMENUDIR)/

uninstall-servicemenu:
	@echo Uninstalling Konqueror servicemenu:
	rm -f $(DESTDIR)$(SERVICEMENUDIR)/lilypond-servicemenu.desktop
	rm -f $(DESTDIR)$(LILYKDE)/lilypond-servicemenu-helper.py
