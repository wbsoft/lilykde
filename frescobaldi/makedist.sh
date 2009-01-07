#/bin/sh
package=$(sed -n 's/^project\s*(\s*\(.*\)\s*).*/\1/p' CMakeLists.txt)
version=$(sed -n 's/.*VERSION "\(.*\)".*/\1/p' CMakeLists.txt)

pkg="$package-$version"

die()
{
  local msg=$1
  echo "makedist: error: $msg" >&2
  exit 1
}

echo Creating $pkg.tar.gz
svn export . $pkg || die "export failed"

# now build the po and pics directories and put the resulting MO
# and PNG files in a "prebuilt" directory. If that directory is present,
# released tar balls will not try to rebuild the LilyPond icons and MO files.
cd "$pkg" || die "could not cd into package"

# ensure pot is up-to-date
( cd po && ./update-po.sh ) || die "could not update po files"

( mkdir build &&
  cd build &&
  cmake .. &&
  make
) || die "could not build package"

mkdir prebuilt prebuilt/pics prebuilt/po
# put mo files in prebuilt
cp build/po/*.mo prebuilt/po/
# put pics (LilyPond-generated icons) in prebuilt
cp build/pics/*.png prebuilt/pics/

# Put a CMakeLists.txt file in the prebuilt directory
cat <<"EOF" > prebuilt/CMakeLists.txt
# These are rules to install the prebuilt MO and PNG files
# to make installing release tarballs easier.
# This directory and its contents has been created by the
# makedist.sh script, and are not part of the Frescobaldi
# SVN repository. To rebuild these files just remove the
# "prebuilt" directory and run cmake again.

# Message Object files (generated from ../po/*.po)
file(GLOB _mo_files po/*.mo)
foreach(_mo ${_mo_files})
  get_filename_component(_lang ${_mo} NAME_WE)
  install(
    FILES ${_mo}
    DESTINATION ${LOCALE_INSTALL_DIR}/${_lang}/LC_MESSAGES
    RENAME ${PROJECT_NAME}.mo
  )
endforeach(_mo)

# LilyPond icons (generated from ../pics/*.ly)
file(GLOB _png_files pics/*.png)
foreach(_png ${_png_files})
  install(FILES ${_png} DESTINATION ${APP_DIR}/pics)
endforeach(_png)
EOF

# Back to parent directory
cd ..

# Create tarball
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

