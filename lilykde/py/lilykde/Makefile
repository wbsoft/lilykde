include ../config.mk

all = about.py

all: $(all)

about.py: ../VERSION
	@cp $< $@

clean:
	rm -f $(all)

install: all
	@echo Installing Python package lilykde:
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)/lilykde
	$(INSTALL) -m 644 *.py $(DESTDIR)$(LILYKDE)/lilykde/
	cd $(DESTDIR)$(LILYKDE)/lilykde && $(PYCOMPILE) *.py

uninstall:
	@echo Uninstalling Python package lilykde:
	rm -rf $(DESTDIR)$(LILYKDE)/lilykde
