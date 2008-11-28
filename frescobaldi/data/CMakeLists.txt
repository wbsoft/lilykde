# Menu entry
install(FILES frescobaldi.desktop DESTINATION ${XDG_APPS_INSTALL_DIR})

# UI configuration
install(FILES frescobaldiui.rc DESTINATION ${APP_DIR})

# Appicon
install(
    FILES frescobaldi-lily.svgz
    DESTINATION ${ICON_INSTALL_DIR}/hicolor/scalable/apps
    RENAME frescobaldi.svgz
)
