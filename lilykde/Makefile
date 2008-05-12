include ../config.mk

all = about.py

all: $(all)

about.py: ../VERSION
	@cp $< $@

clean:
	rm -f $(all)

install: all
	@echo Installing Python package lilykde:
	@mkdir -p $(LILYKDE)/lilykde
	@cd $(LILYKDE)/lilykde && rm -f *.py*
	cp *.py $(LILYKDE)/lilykde/
	@cd $(LILYKDE)/lilykde && $(PYCOMPILE) *.py

uninstall:
	@echo Uninstalling Python package lilykde:
	rm -rf $(LILYKDE)/lilykde
