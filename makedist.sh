#!/bin/bash

# Makes a zip file for distributing LilyKDE

version=$1

if test -z "$version" ;
then
	path=trunk
	name=lilykde-svn
else
	path=tags/lilykde-$version
	name=lilykde-$version
fi
svn export http://lilykde.googlecode.com/svn/$path $name || exit 1
make -C $name/po     # build the locale files already
rm $name/makedist.sh # remove ourselves
zip -r $name.zip "$name" && rm -fr $name
