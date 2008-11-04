# Copyright 1999-2008 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

DESCRIPTION="Framework for writing Python plugins for Kate"
HOMEPAGE="http://paul.giannaros.org/pate/"
SRC_URI="http://paul.giannaros.org/pate/releases/source/${P}.tar.gz"

LICENSE="LGPL-2"
SLOT="0"
KEYWORDS="x86"
IUSE=""

DEPEND=">=dev-lang/python-2.4
	=dev-python/PyQt-3*
	=dev-python/pykde-3*
	>=dev-util/cmake-2
	|| ( =kde-base/kate-3.5*
	     =kde-base/kdebase-3.5* )"

src_compile() {
	./configure &&
	cd build &&
	make
}

src_install() {
	dodoc INSTALL.txt  LICENSE.txt  README.txt
	sed -i 's#\${CMAKE_INSTALL_PREFIX}#'${D}'&#' inst/install.cmake
	cd build &&
	make DESTDIR="${D}" install
}

