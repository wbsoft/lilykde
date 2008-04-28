include ../config.mk


lys = $(wildcard *.ly)
pngs = $(patsubst %.ly,%.png,$(lys))

all: $(pngs)

$(pngs): %.png: %.ly
	lilypond -dbackend=eps --png $<

clean:
	rm -f *.png *.tex* *.count *.eps

install: all
	@echo Installing generated LilyPond PNGs:
	@mkdir -p $(LILYKDE)/pics
	cp $(pngs) $(LILYKDE)/pics/

uninstall:
	@echo Uninstalling generated LilyPond PNGs:
	rm -fr "$(LILYKDE)/pics"

.PHONY: all clean install uninstall
