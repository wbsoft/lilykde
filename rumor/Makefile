include ../config.mk

all:
clean:

install: all
	@echo Installing Rumor scripts:
	$(INSTALL) -d $(DESTDIR)$(LILYKDE)/rumor
	$(INSTALL) -m 644 *.scm $(DESTDIR)$(LILYKDE)/rumor/

uninstall:
	@echo Uninstalling Rumor scripts:
	rm -fr $(DESTDIR)$(LILYKDE)/rumor
