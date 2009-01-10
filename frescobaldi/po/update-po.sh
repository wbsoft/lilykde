#!/bin/sh

package=$(sed -n 's/^project\s*(\s*\(.*\)\s*).*/\1/p' ../CMakeLists.txt)
version=$(sed -n 's/.*VERSION "\(.*\)".*/\1/p' ../CMakeLists.txt)
email=$(sed -n 's/^bugs\s*=\s*"\(.*\)".*/\1/p' ../frescobaldi.py)

# Update pot file:
xgettext \
    --language=python \
    --output=frescobaldi.pot \
    --package-name="$package" \
    --package-version="$version" \
    --msgid-bugs-address="$email" \
    -ki18n:1 -ki18nc:1c,2 -ki18np:1,2 -ki18ncp:1c,2,3 \
    -kki18n:1 -kki18nc:1c,2 -kki18np:1,2 -kki18ncp:1c,2,3 \
    -kI18N_NOOP:1 -kI18N_NOOP2:1c,2 \
    ../frescobaldi.py \
    dummy.py \
    ../python/ly/*.py \
    ../python/kateshell/*.py \
    ../python/frescobaldi_app/*.py \
    ../python/frescobaldi_app/scorewiz/*.py

# Update po files:
for po in *.po
do
    msgmerge -U "$po" frescobaldi.pot && touch "$po"
done

