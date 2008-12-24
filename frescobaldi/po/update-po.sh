#!/bin/sh

package=$(sed -n 's/^project\s*(\s*\(.*\)\s*).*/\1/p' ../CMakeLists.txt)
version=$(sed -n 's/.*VERSION "\(.*\)".*/\1/p' ../CMakeLists.txt)
email=$(sed -n 's/^bugs\s*=\s*"\(.*\)".*/\1/p' ../frescobaldi.py)

# Update pot file:
xgettext \
    --package-name="$package" \
    --package-version="$version" \
    --msgid-bugs-address="$email" \
    --keyword=i18n --keyword=ki18n --keyword=I18N_NOOP \
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

