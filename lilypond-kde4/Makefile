DESTDIR = 
PREFIX = $(shell kde4-config --prefix)
ICONDIR = $(PREFIX)/share/icons/oxygen
KATEDIR = $(PREFIX)/share/apps/katepart

files = text-x-lilypond.svgz

all: $(files)

text-x-lilypond.svgz: text-x-lilypond.svg
	gzip < $< > $@

install:
	install -d $(DESTDIR)$(ICONDIR)/scalable
	install -m 644 text-x-lilypond.svgz $(DESTDIR)$(ICONDIR)/scalable/
	install -d $(DESTDIR)$(KATEDIR)/script
	install -m 644 lilypond.js $(DESTDIR)$(KATEDIR)/script/

clean:
	rm $(files)

