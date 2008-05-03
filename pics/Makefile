include ../config.mk


lys = $(wildcard *.ly)
pngs = $(patsubst %.ly,%.png,$(lys))

all: $(pngs)

$(pngs): %.png: %.ly
	lilypond --png $<
	mogrify +repage -trim -bordercolor transparent -border 2x2 \
		-transparent white $@

clean:
	rm -f *.png *.ps

install: all
	@echo Installing generated LilyPond PNGs:
	@mkdir -p $(LILYKDE)/pics
	cp $(pngs) $(LILYKDE)/pics/

uninstall:
	@echo Uninstalling generated LilyPond PNGs:
	rm -fr "$(LILYKDE)/pics"

.PHONY: all clean install uninstall
