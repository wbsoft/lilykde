include ../config.mk

scripts = $(wildcard *.scm)

all:
clean:

install: all
	@echo Installing Rumor scripts:
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)/rumor
	$(INSTALL) -m 644 $(scripts) $(DESTDIR)$(LILYKDE)/rumor/

uninstall:
	@echo Uninstalling Rumor scripts:
	cd $(DESTDIR)$(LILYKDE)/rumor && rm -f $(scripts)
	-rmdir $(DESTDIR)$(LILYKDE)/rumor
