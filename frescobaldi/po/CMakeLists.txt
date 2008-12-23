find_package(Gettext REQUIRED)

#file(GLOB _po_files *.po)
gettext_create_translations(frescobaldi.pot ALL nl.po)
