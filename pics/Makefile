include ../config.mk


lys = $(wildcard *.ly)
pngs = $(patsubst %.ly,%.png,$(lys))

all: $(pngs)

$(pngs): %.png: %.ly
	lilypond -ddelete-intermediate-files --png $<
	convert $@ -trim -bordercolor white -border 3 \
		\( +clone -threshold 100% \) \
		\( -clone 0 -negate \) \
		-delete 0 -compose CopyOpacity -composite +repage $@

# Make some lilypond images also depend on the files they include
$(patsubst %.ly,%.png,$(wildcard note_*.ly)): note_defaults.ily
$(patsubst %.ly,%.png,$(wildcard articulation_*.ly)): articulation_defaults.ily

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
