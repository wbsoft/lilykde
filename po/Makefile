.PHONY: all install uninstall clean

XGETTEXT = xgettext
MSGMERGE = msgmerge
MSGFMT = msgfmt

DESTDIR =
PREFIX = $(HOME)/.kde
DATADIR = $(DESTDIR)$(PREFIX)/share

LILYKDE = $(DATADIR)/apps/lilykde

# get VERSION, PACKAGE and EMAIL
include ../VERSION

# Todo: add possibility to place message catalogs in system-wide locale dirs
MODIR = $(LILYKDE)/mo

translate = \
	../lilypond.py \
	../lilykde/runlily.py \
	../lilykde/menu.py \
	../lilykde/version.py \
	../lilykde/log.py \
	../lilykde/logwidget.py \
	../lilykde/pdf.py \
	../lilykde/util.py \
	../lilykde/kateutil.py \
	../lilykde/hyphen.py \
	../lilykde/settings.py \



pofiles = $(wildcard *.po)
mofiles = $(patsubst %.po,%.mo,$(pofiles))

all: $(mofiles)

lilykde.pot: $(translate) ../VERSION
	$(XGETTEXT) -o lilykde.pot \
		--package-name=$(PACKAGE) \
		--package-version=$(VERSION) \
		--msgid-bugs-address=$(EMAIL) \
		$(translate)

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
	rm -f $(mofiles)
