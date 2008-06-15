.PHONY: all install uninstall clean

include ../config.mk
# get VERSION, PACKAGE and EMAIL
include ../VERSION

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
LANGUAGES = $(patsubst %.po,%,$(pofiles))

all: $(mofiles)

lilykde.pot: $(translate) ../VERSION
	$(XGETTEXT) --output=lilykde.pot --keyword= \
		--keyword=_:1,2,3t --keyword=_:1,1t \
		--keyword=I18N_NOOP:1,1t \
		--package-name=$(PACKAGE) \
		--package-version=$(VERSION) \
		--msgid-bugs-address=$(EMAIL) \
		$(translate)

$(pofiles): lilykde.pot
	$(MSGMERGE) -U $@ $< && touch $@

$(mofiles): %.mo: %.po
	$(MSGFMT) -o $@ $<

install: all
	@echo Installing message catalogs: $(LANGUAGES)
	@for l in $(LANGUAGES); do \
		d="$(LOCALEDIR)/$$l/LC_MESSAGES"; \
		mkdir -p "$$d"; \
		cp $$l.mo "$$d/lilykde.mo" ; \
		done

uninstall:
	@echo Uninstalling message catalogs
	@rm -f "$(LOCALEDIR)/"*"/LC_MESSAGES/lilykde.mo"

clean:
	rm -f $(mofiles)
