#/bin/sh
package=$(sed -n 's/^project\s*(\s*\(.*\)\s*).*/\1/p' CMakeLists.txt)
version=$(sed -n 's/.*version "\(.*\)".*/\1/p' CMakeLists.txt)

pkg="$package-$version"

echo Creating $pkg.tar.gz
svn export . $pkg && \
tar zcf $pkg.tar.gz $pkg && \
rm -fr $pkg && \
echo Done.

