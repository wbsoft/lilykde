DESCRIPTION="Tools to integrate LilyPond into KDE"
HOMEPAGE="http://lilykde.googlecode.com/"
SRC_URI="http://lilykde.googlecode.com/files/${P}.tar.gz"

LICENSE="GPL"
SLOT="0"
KEYWORDS="x86"

DEPEND=">=kde-misc/pate-0.5.1
	!media-sound/lilykde-svn"

prefix=$(kde-config --prefix)

src_compile() {
	make
}

src_install() {
	make DESTDIR=${D} PREFIX=${prefix} install
	dodoc README INSTALL THANKS TODO NEWS x-lilypond.conf
}

