DESTDIR = 
PREFIX = $(shell kde4-config --prefix)
ICONDIR = $(PREFIX)/share/icons/hicolor
KATEDIR = $(PREFIX)/share/apps/katepart

files = text-x-lilypond.svgz

all: $(files)

text-x-lilypond.svgz: text-x-lilypond.svg
	gzip < $< > $@

install:
	install -d $(DESTDIR)$(ICONDIR)/scalable/mimetypes
	install -m 644 text-x-lilypond.svgz $(DESTDIR)$(ICONDIR)/scalable/mimetypes/
	install -d $(DESTDIR)$(KATEDIR)/script
	install -m 644 lilypond.js $(DESTDIR)$(KATEDIR)/script/

clean:
	rm $(files)

