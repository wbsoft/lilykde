# Menu entry
install(FILES frescobaldi.desktop DESTINATION ${XDG_APPS_INSTALL_DIR})

# UI configuration
install(FILES frescobaldiui.rc expansions lilydoc.css DESTINATION ${APP_DIR})

# Appicon
install(
    FILES frescobaldi-lily.svg
    DESTINATION ${ICON_INSTALL_DIR}/hicolor/scalable/apps
    RENAME frescobaldi.svg
)
