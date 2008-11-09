# Copyright 1999-2008 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header:  $

EAPI="2"

NEED_KDE=":4.1"
inherit kde4-base

DESCRIPTION="LilyPond document icons, indent script and protocol handler for KDE4"
HOMEPAGE="http://lilykde.googlecode.com/"

LICENSE="LGPL"
KEYWORDS="~x86"
SLOT="0"
SRC_URI="http://lilykde.googlecode.com/files/${P}.tar.gz"

DEPEND="
	kde-base/kdelibs:4.1
	"

src_configure() {
	mycmakeargs="${mycmakeargs}
		-DCMAKE_INSTALL_PREFIX=${PREFIX}
	"
	kde4-base_src_configure
}
