.PHONY: all install uninstall clean

XGETTEXT ?= xgettext
MSGMERGE ?= msgmerge
MSGFMT ?= msgfmt

KDEHOME ?= $(HOME)/.kde
LILYKDE ?= $(KDEHOME)/share/apps/lilykde

# Todo: add possibility to place message catalogs in system-wide locale dirs
LOCALE = $(LILYKDE)/mo

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
	$(MSGFMT) $<

install: all
	@echo Installing message catalogs...
	@mkdir -p $(LOCALE)
	for m in $(mofiles); do cp $$m "$(LOCALE)/" ; done

uninstall:
	@echo Uninstalling message catalogs...
	@rm -rf "$(LOCALE)"

clean:
	rm $(mofiles)
