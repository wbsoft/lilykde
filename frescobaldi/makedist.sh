#/bin/sh

# Exports a SVN checkout, builds the icons in pics/ and MO files in po/ and
# creates a tar ball. Set the LILYPOND environment variable to specify a
# LilyPond binary to build the icons.

package=$(sed -n 's/^project\s*(\s*\(\w*\).*/\1/p' CMakeLists.txt)
version=$(sed -n 's/.*VERSION "\(.*\)".*/\1/p' CMakeLists.txt)

pkg="$package-$version"

die()
{
  local msg=$1
  echo "makedist: error: $msg" >&2
  exit 1
}

CMAKE_ARGS=""
if [ -n "${LILYPOND}" ]; then
  CMAKE_ARGS="-DLILYPOND_EXECUTABLE=${LILYPOND}"
fi

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

# put mo files in source tree
cp build/po/*.mo po/
# put pics (LilyPond-generated icons) in source tree
cp build/pics/*.png pics/

# Remove build directory
rm -fr build

# Remove ourselves, not useful outside SVN checkout
rm makedist.sh

# Create tarball
cd ..
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

