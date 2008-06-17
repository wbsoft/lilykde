include ../config.mk


lys = $(wildcard *.ly)
pngs = $(patsubst %.ly,%.png,$(lys))

all: $(pngs)

$(pngs): %.png: %.ly $(wildcard *.ily)
	lilypond -ddelete-intermediate-files --png $<
	mogrify +repage -trim -bordercolor transparent -border 3 \
		-transparent white $@

clean:
	rm -f *.png

install: all
	@echo Installing generated LilyPond PNGs:
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)/pics
	$(INSTALL) -m 644 $(pngs) $(DESTDIR)$(LILYKDE)/pics/

uninstall:
	@echo Uninstalling generated LilyPond PNGs:
	rm -fr $(DESTDIR)$(LILYKDE)/pics

.PHONY: all clean install uninstall
