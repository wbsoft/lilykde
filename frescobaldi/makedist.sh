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
# ensure pot is up-to-date
( cd "$pkg/po" && ./update-po.sh ; )
# create tarball
tar zcf $pkg.tar.gz $pkg || die "making tarball failed"
rm -fr $pkg 
echo Done.

