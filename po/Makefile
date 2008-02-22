.PHONY: all install uninstall clean

XGETTEXT = xgettext
MSGMERGE = msgmerge
MSGFMT = msgfmt

DESTDIR =
PREFIX = $(HOME)/.kde
DATADIR = $(DESTDIR)$(PREFIX)/share

LILYKDE = $(DATADIR)/apps/lilykde

# Todo: add possibility to place message catalogs in system-wide locale dirs
MODIR = $(LILYKDE)/mo

translate = \
	../lilypond.py \
	../lilykde/runlily.py \
	../lilykde/menu.py \
	../lilykde/version.py \
	../lilykde/log.py \
	../lilykde/pdf.py \



pofiles = $(wildcard *.po)
mofiles = $(patsubst %.po,%.mo,$(pofiles))

all: $(mofiles)

lilykde.pot: $(translate)
	$(XGETTEXT) -o lilykde.pot $(translate)

$(pofiles): lilykde.pot
	$(MSGMERGE) -U $@ $< && touch $@

$(mofiles): %.mo: %.po
	$(MSGFMT) -o $@ $<

install: all
	@echo Installing message catalogs...
	@mkdir -p $(MODIR)
	for m in $(mofiles); do cp $$m "$(MODIR)/" ; done

uninstall:
	@echo Uninstalling message catalogs...
	@rm -rf "$(MODIR)"

clean:
	rm $(mofiles)
