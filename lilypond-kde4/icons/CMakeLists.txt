set(themes hicolor oxygen crystalsvg)

foreach(theme ${themes})
  install(
    FILES ${theme}/text-x-lilypond.svgz
    DESTINATION ${ICON_INSTALL_DIR}/${theme}/scalable/mimetypes)
endforeach(theme)
