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
	../lilykde/pdftk.py \
	../lilypond-servicemenu-helper.py \


pofiles = $(wildcard *.po)
mofiles = $(patsubst %.po,%.mo,$(pofiles))
CATALOGS = $(patsubst %.po,%,$(pofiles))

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
	@echo Installing message catalogs: $(CATALOGS)
	for i in $(CATALOGS); do \
	 $(INSTALL) -d $(DESTDIR)$(LOCALEDIR)/$$i/LC_MESSAGES; \
	 $(INSTALL) -m 644 $$i.mo \
	  $(DESTDIR)$(LOCALEDIR)/$$i/LC_MESSAGES/$(PACKAGE).mo; \
	done

uninstall:
	@echo Uninstalling message catalogs: $(CATALOGS)
	for i in $(CATALOGS); do \
	 rm -f $(DESTDIR)$(LOCALEDIR)/$$i/LC_MESSAGES/$(PACKAGE).mo; \
	done

clean:
	rm -f $(mofiles)
