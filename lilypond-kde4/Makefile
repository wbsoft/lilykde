DESTDIR = 
PREFIX = $(shell kde4-config --prefix)
ICONDIR = $(PREFIX)/share/icons
KATEDIR = $(PREFIX)/share/apps/katepart

# for make dist
include VERSION
pkg = lilypond-kde4-$(VERSION)

icondirs = oxygen crystalsvg hicolor

icons = $(patsubst %,icons/%/text-x-lilypond.svgz,$(icondirs))

all: $(icons)

$(icons): %z: %
	gzip < $< > $@

install: install-icons install-indenter

install-icons: $(icons)
	for i in $(icondirs) ;\
	do \
	  dir=$(DESTDIR)$(ICONDIR)/$$i/scalable/mimetypes ;\
	  install -d $$dir ;\
	  install -m 644 icons/$$i/text-x-lilypond.svgz $$dir/ ;\
	done;

install-indenter:
	install -d $(DESTDIR)$(KATEDIR)/script
	install -m 644 lilypond.js $(DESTDIR)$(KATEDIR)/script/

clean:
	rm $(icons)

dist:
	@svn export -q . $(pkg)
	@tar zcf $(pkg).tar.gz $(pkg)
	@rm -fr $(pkg)/
	@echo Created $(pkg).tar.gz
