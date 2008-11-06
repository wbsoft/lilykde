include config.mk
include VERSION # for make dist

pkg = $(PACKAGE)-$(VERSION)

icondirs = oxygen crystalsvg hicolor

all:

install: install-icons install-indenter install-textedit
uninstall: uninstall-icons uninstall-indenter uninstall-textedit

install-icons:
	for i in $(icondirs) ;\
	do \
	  dir=$(DESTDIR)$(ICONDIR)/$$i/scalable/mimetypes ;\
	  install -d $$dir ;\
	  install -m 644 icons/$$i/text-x-lilypond.svgz $$dir/ ;\
	done

uninstall-icons:
	for i in $(icondirs) ;\
	do \
	  rm -f "$(DESTDIR)$(ICONDIR)/$$i/scalable/mimetypes/text-x-lilypond.svgz" ;\
	done

install-indenter:
	install -d $(DESTDIR)$(KATEDIR)/script
	install -m 644 lilypond.js $(DESTDIR)$(KATEDIR)/script/

uninstall-indenter:
	rm -f "$(DESTDIR)$(KATEDIR)/script/lilypond.js"

install-textedit:
	install -d $(DESTDIR)$(SERVICEDIR)
	install -m 644 textedit.protocol $(DESTDIR)$(SERVICEDIR)/
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 ktexteditservice $(DESTDIR)$(BINDIR)/

uninstall-textedit:
	rm -f "$(DESTDIR)$(SERVICEDIR)/textedit.protocol"
	rm -f "$(DESTDIR)$(BINDIR)/ktexteditservice"

clean:

dist:
	@svn export -q . $(pkg)
	@tar zcf $(pkg).tar.gz $(pkg)
	@rm -fr $(pkg)/
	@echo Created $(pkg).tar.gz
