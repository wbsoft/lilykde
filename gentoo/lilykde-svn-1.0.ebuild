inherit subversion

ESVN_REPO_URI="http://lilykde.googlecode.com/svn/trunk"
ESVN_PROJECT="lilykde"

DESCRIPTION="Tools to integrate LilyPond into KDE"
HOMEPAGE="http://code.google.com/p/lilykde/"
SRC_URI=""

LICENSE="GPL"
SLOT="0"
KEYWORDS="x86"

DEPEND=">=kde-misc/pate-0.5.1
	sys-devel/gettext
	!media-sound/lilykde"

prefix=$(kde-config --prefix)

src_compile() {
	make
}

src_install() {
	make DESTDIR=${D} PREFIX=${prefix} install
	dodoc README INSTALL
}

