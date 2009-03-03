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

# Prebuild the icons and mo files
cd "$pkg" || die "could not cd into package"

# ensure pot is up-to-date
( cd po && ./update-po.sh ) || die "could not update po files"

( mkdir build &&
  cd build &&
  cmake .. &&
  make
) || die "could not build package"

# put mo files in source tree
cp build/po/*.mo po/
# put pics (LilyPond-generated icons) in source tree
cp build/pics/*.png pics/
# put compiled handbook in source tree
cp build/doc/index.cache.* doc/

# Remove build directory
rm -fr build

# Create tarball
cd ..
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

