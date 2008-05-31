.PHONY: all install uninstall clean

include ../config.mk
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
	../lilykde/pdf.py \
	../lilykde/util.py \
	../lilykde/kateutil.py \
	../lilykde/widgets.py \
	../lilykde/hyphen.py \
	../lilykde/settings.py \
	../lilykde/rumor.py \
	../lilykde/scorewiz.py \
	../lilykde/parts.py \
	../lilypond-servicemenu-helper.py \



pofiles = $(wildcard *.po)
mofiles = $(patsubst %.po,%.mo,$(pofiles))

all: $(mofiles)

lilykde.pot: $(translate) ../VERSION
	$(XGETTEXT) --output=lilykde.pot --keyword= \
		--keyword=_:1,2,3t --keyword=_:1,1t\
		--package-name=$(PACKAGE) \
		--package-version=$(VERSION) \
		--msgid-bugs-address=$(EMAIL) \
		$(translate)

$(pofiles): lilykde.pot
	$(MSGMERGE) -U $@ $< && touch $@

$(mofiles): %.mo: %.po
	$(MSGFMT) -o $@ $<

install: all
	@echo Installing message catalogs:
	@mkdir -p "$(MODIR)"
	cp $(mofiles) "$(MODIR)/"

uninstall:
	@echo Uninstalling message catalogs:
	@rm -rf "$(MODIR)"

clean:
	rm -f $(mofiles)
