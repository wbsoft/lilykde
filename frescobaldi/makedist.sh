#/bin/sh

# Exports a SVN checkout, builds the icons in pics/ and MO files in po/ and
# creates a tar ball. Set the LILYPOND environment variable to specify a
# LilyPond binary to build the icons.

package=$(sed -n 's/^project\s*(\s*\(\w*\).*/\1/p' CMakeLists.txt)
version=$(sed -n 's/.*VERSION "\(.*\)".*/\1/p' CMakeLists.txt)

pkg="$package-$version"
PREBUILT_DIR="prebuilt"

CMAKE_ARGS=""
if [ -n "${LILYPOND}" ]; then
  CMAKE_ARGS="-DLILYPOND_EXECUTABLE=${LILYPOND}"
fi

die()
{
  local msg=$1
  echo "makedist: error: $msg" >&2
  exit 1
}

echo Creating $pkg.tar.gz
svn export . $pkg || die "export failed"

# Prebuild the icons and mo files
cd "$pkg" || die "could not cd into package"

# ensure pot is up-to-date
( cd po && VERSION_CONTROL=none ./update-po.sh ) || die "could not update po files"

( mkdir build &&
  cd build &&
  cmake ${CMAKE_ARGS} .. &&
  make
) || die "could not build package"


# This directory contains prebuilt stuff so release tarballs don't have
# difficult dependencies.
mkdir ${PREBUILT_DIR}

# Put CMakeLists.txt in prebuilt dir
cat <<-"EOF" > ${PREBUILT_DIR}/CMakeLists.txt
add_subdirectory(pics)
add_subdirectory(po)
EOF

# Add LilyPond-generated icons etc:
mkdir ${PREBUILT_DIR}/pics
cp build/pics/*.png ${PREBUILT_DIR}/pics/

# Put CMakeLists.txt in prebuilt/pics
cat <<-"EOF" > ${PREBUILT_DIR}/pics/CMakeLists.txt
file(GLOB pngs *.png)
install(FILES ${pngs} DESTINATION ${APP_DIR}/pics)
EOF

# Add translated PO files:
mkdir ${PREBUILT_DIR}/po
cp build/po/*.mo ${PREBUILT_DIR}/po/

# Put CMakeLists.txt in prebuilt/po
cat <<-"EOF" > ${PREBUILT_DIR}/po/CMakeLists.txt
file(GLOB mo_files *.mo)
foreach(mo ${mo_files})
  get_filename_component(lang ${mo} NAME_WE)
  install(
    FILES ${mo}
    DESTINATION ${LOCALE_INSTALL_DIR}/${lang}/LC_MESSAGES
    RENAME ${PROJECT_NAME}.mo
  )
endforeach(mo)
EOF

# Remove build directory
rm -fr build

# Remove ourselves, not useful outside SVN checkout
rm makedist.sh

# Create tarball
cd ..
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

