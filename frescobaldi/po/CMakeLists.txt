# Translations

find_program(GETTEXT_MSGFMT_EXECUTABLE msgfmt)

file(GLOB _po_files *.po)
set(_mo_files)
foreach(_po ${_po_files})
  get_filename_component(_lang ${_po} NAME_WE)
  set(_mo ${CMAKE_CURRENT_BINARY_DIR}/${_lang}.mo)
  add_custom_command(
    OUTPUT ${_mo}
    COMMAND ${GETTEXT_MSGFMT_EXECUTABLE} -v -o ${_mo} ${_po}
    DEPENDS ${_po}
    COMMENT "Creating MO file for language ${_lang}:"
  )
  install(
    FILES ${_mo}
    DESTINATION ${LOCALE_INSTALL_DIR}/${_lang}/LC_MESSAGES
    RENAME ${PROJECT_NAME}.mo
  )
  list(APPEND _mo_files ${_mo})
endforeach(_po)
add_custom_target(translations ALL DEPENDS ${_mo_files})
