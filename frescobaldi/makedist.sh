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
cd "$pkg"
# make sure pot is up-to-date
cd po
./update-po.sh
cd ..
mkdir build2
cd build2
cmake .. || die "cmake failed"
make || die "make failed"
# create clean build dir and copy over .png and .mo files
cd ..
mkdir build build/po build/pics
cp -a build2/po/*.mo build/po/
cp -a build2/pics/*.png build/pics/
rm -fr build2
cd ..
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

