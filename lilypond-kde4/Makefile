DESTDIR = 
PREFIX = $(shell kde4-config --prefix)
ICONDIR = $(PREFIX)/share/icons
KATEDIR = $(PREFIX)/share/apps/katepart

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

