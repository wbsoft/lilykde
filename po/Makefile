.PHONY: all

PYGETTEXT ?= pygettext.py
MSGMERGE ?= msgmerge
MSGFMT ?= msgfmt.py

KDEHOME ?= $(HOME)/.kde
LILYKDE = $(KDEHOME)/share/apps/lilykde

# Todo: add possibility to place message catalogs in system-wide locale dirs
LOCALE = $(LILYKDE)/mo

translate = \
	../lilypond.py \
	../lilykde.py \
	../lymenu.py \

pofiles = $(wildcard *.po)
mofiles = $(patsubst %.po,%.mo,$(pofiles))

all: $(mofiles)

lilykde.pot:
	$(PYGETTEXT) -o lilykde.pot $(translate)

$(pofiles): lilykde.pot
	$(MSGMERGE) -U $@ $<

$(mofiles): %.mo: %.po
	$(MSGFMT) $<

install: all
	@echo Installing message catalogs...
	@mkdir -p $(LOCALE)
	for m in $(mofiles); do cp $$m "$(LOCALE)/" ; done

uninstall:
	@echo Uninstalling message catalogs...
	@rm -rf "$(LOCALE)"
