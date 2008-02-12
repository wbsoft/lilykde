KDEHOME ?= ~/.kde
LILYKDE = $(KDEHOME)/share/apps/lilykde

all = ly.png textedit.protocol
all: $(all)

ly.png: ly.svg
	ksvgtopng 128 128 "`pwd`/$<" "`pwd`/$@"

textedit.protocol: textedit.protocol.in
	sed 's!LILYKDEDIR!$(LILYKDE)!' $< > $@

install: all
	# plugin
	mkdir -p $(KDEHOME)/share/apps/kate/pyplugins
	cp lilypond.py $(KDEHOME)/share/apps/kate/pyplugins/
	mkdir -p $(LILYKDE)/py
	cp lilykde.py $(LILYKDE)/py/
	cp lilykde_i18n.py $(LILYKDE)/py/

	# LilyPond icon and mimetype
	mkdir -p $(KDEHOME)/share/icons
	cp ly.png ly.svg $(KDEHOME)/share/icons/
	mkdir -p $(KDEHOME)/share/mimelnk/text
	cp x-lilypond.desktop $(KDEHOME)/share/mimelnk/text/

	# textedit integration
	mkdir -p $(KDEHOME)/share/services
	cp textedit.protocol $(KDEHOME)/share/services/
	cp ktexteditservice.py $(LILYKDE)/

	# LilyPond syntax highlighting
	mkdir -p $(KDEHOME)/share/apps/katepart/syntax
	cp lilypond.xml $(KDEHOME)/share/apps/katepart/syntax/

	# Finally, rebuild the local kde config database
	kbuildsycoca

clean:
	rm $(all)
