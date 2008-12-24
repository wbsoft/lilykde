#!/bin/sh

# Update pot file:
xgettext --keyword=i18n --keyword=ki18n --keyword=I18N_NOOP \
    --output=frescobaldi.pot \
    --language=python \
    dummy.py \
    ../frescobaldi.py \
    ../python/*.py \
    ../python/ly/*.py \
    ../python/kateshell/*.py \
    ../python/frescobaldi_app/*.py 


# Update po files:
for po in *.po
do
    msgmerge -U "$po" frescobaldi.pot && touch "$po"
done

