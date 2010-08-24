# CMake file for installing docbook files for the KDE Helpcenter

find_program(KDE4_MEINPROC_EXECUTABLE NAMES meinproc4 PATHS ${KDE4_BIN_INSTALL_DIR} NO_DEFAULT_PATH)
find_program(KDE4_MEINPROC_EXECUTABLE NAMES meinproc4)

find_file(KDE4_XSL_STYLESHEET NAMES kde-chunk.xsl PATHS ${KDE4_DATA_INSTALL_DIR}/ksgmltools2/customization NO_DEFAULT_PATH)

# Create a symlink on install
macro(install_symlink _to _from)
  install(CODE "
    message(STATUS \"Creating symlink '${_to}' at \$ENV{DESTDIR}${_from}\")
    execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink ${_to} \"\$ENV{DESTDIR}${_from}\" )
    ")
endmacro(install_symlink)

# This macro can install docbook files and images from the current directory to the
# correct location for KDE Helpcenter files.  If meinproc and the stylesheets are available,
# a index.cache.bz2 is generated so the Helpcenter doesn't have to generate one per user.
macro(create_handbook _docbook _language)
  
  # determine install dir
  if(NOT _language)
    set(_lang "en")
  else(NOT _language)
    set(_lang ${_language})
  endif(NOT _language)
  set(_installdir "${HTML_INSTALL_DIR}/${_lang}/${PROJECT_NAME}")
  
  # docbook source files
  file(GLOB _docbooks *.docbook)

  # images
  file(GLOB _images *.png)

  # install those directly
  install(FILES ${_docbooks} ${_images} DESTINATION ${_installdir})
  
  # make the ../common symlink
  install_symlink("../common" "${_installdir}/common")
  
  # remove the ../common symlink on uninstall
  uninstall_file(${_installdir}/common)

  # if meinproc and the default style sheets are found, install a cached help file
  if(KDE4_MEINPROC_EXECUTABLE AND KDE4_XSL_STYLESHEET)
    get_filename_component(_input ${_docbook} ABSOLUTE)
    set(_cache ${CMAKE_CURRENT_BINARY_DIR}/index.cache.bz2)
    add_custom_command(
      OUTPUT ${_cache}
      COMMAND ${KDE4_MEINPROC_EXECUTABLE} --check --cache ${_cache} ${_input}
      DEPENDS ${_docbooks}
      WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    get_filename_component(_targ ${CMAKE_CURRENT_SOURCE_DIR} NAME)
    set(_targ "${_targ}-cache")
    add_custom_target(${_targ} ALL DEPENDS ${_cache})
    install(FILES ${_cache} DESTINATION  ${_installdir})
  else(KDE4_MEINPROC_EXECUTABLE AND KDE4_XSL_STYLESHEET)
    message(STATUS "The help cache index.cache.bz2 will not be generated:")
    if(NOT KDE4_MEINPROC_EXECUTABLE)
      message(STATUS "*** meinproc4 could not be found.")
    endif(NOT KDE4_MEINPROC_EXECUTABLE)
    if(NOT KDE4_XSL_STYLESHEET)
      message(STATUS "*** The KDE XSL StyleSheets could not be found.")
    endif(NOT KDE4_XSL_STYLESHEET)
  endif(KDE4_MEINPROC_EXECUTABLE AND KDE4_XSL_STYLESHEET)
endmacro(create_handbook)


create_handbook(index.docbook en)

