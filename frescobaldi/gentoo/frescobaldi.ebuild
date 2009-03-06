# Copyright 1999-2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="2"
inherit cmake-utils

DESCRIPTION="An easy to use LilyPond sheet music editor"
HOMEPAGE="http://www.frescobaldi.org/"
LICENSE="GPL"
KEYWORDS="~x86"
SLOT="0"
SRC_URI="http://lilykde.googlecode.com/files/${P}.tar.gz"

DEPEND="
  sys-devel/gettext
  media-sound/lilypond
  media-gfx/imagemagick
  dev-python/dbus-python
  dev-python/PyQt4[dbus]
  kde-base/pykde4
"

RDEPEND="
  media-sound/lilypond
  media-gfx/imagemagick
  dev-python/dbus-python
  dev-python/PyQt4[dbus]
  kde-base/pykde4
  kde-base/okular
"

