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
# create build tree and make Lily pics and po files
mkdir build
cd build
cmake .. || die "cmake in export failed"
make -C po || die "make failed in po/"
make -C pics || die "make failed in pics/"
# remove most cmake generated files
find . -maxdepth 2 \
  \( -type d -a -name CMakeFiles \) \
  -o -name cmake*.cmake \
  -o -name CMakeCache.txt \
  -o -name Makefile \
  | xargs rm -fr
rm -f frescobaldi data python
cd ../..
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

