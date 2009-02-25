# mostly taken from KDE4Macros

find_program(KDE4_MEINPROC_EXECUTABLE NAME meinproc4 PATHS ${KDE4_BIN_INSTALL_DIR} NO_DEFAULT_PATH)
find_program(KDE4_MEINPROC_EXECUTABLE NAME meinproc4)

macro(create_handbook _docbook)
  get_filename_component(_input ${_docbook} ABSOLUTE)
  set(_doc ${CMAKE_CURRENT_BINARY_DIR}/index.cache.bz2)
  
  # style sheet
  set(_ssheet ${KDE4_DATA_INSTALL_DIR}/ksgmltools2/customization/kde-chunk.xsl)

  # all docbook files
  file(GLOB _docs *.docbook)
  add_custom_command(
    OUTPUT ${_doc}
    COMMAND ${KDE4_MEINPROC_EXECUTABLE} --check --cache ${_doc} ${_input}
    DEPENDS ${_docs} ${_ssheet}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )

  get_filename_component(_targ ${CMAKE_CURRENT_SOURCE_DIR} NAME)
  set(_targ "${_targ}-handbook")
  add_custom_target(${_targ} ALL DEPENDS ${_doc})

#   set(_htmlDoc ${CMAKE_CURRENT_SOURCE_DIR}/index.html)
#   add_custom_command(OUTPUT ${_htmlDoc}
#     COMMAND ${KDE4_MEINPROC_EXECUTABLE} --check -o ${_htmlDoc} ${_input}
#     DEPENDS ${_input} ${_ssheet}
#     WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
#   )
#   add_custom_target(htmlhandbook ALL DEPENDS ${_htmlDoc})

  set(_args ${ARGN})

  set(_installDest)
  if(_args)
    list(GET _args 0 _tmp)
    if("${_tmp}" STREQUAL "INSTALL_DESTINATION")
      list(GET _args 1 _installDest )
      list(REMOVE_AT _args 0 1)
    endif("${_tmp}" STREQUAL "INSTALL_DESTINATION")
  endif(_args)

  get_filename_component(dirname ${CMAKE_CURRENT_SOURCE_DIR} NAME_WE)
  if(_args)
    list(GET _args 0 _tmp)
    if("${_tmp}" STREQUAL "SUBDIR")
      list(GET _args 1 dirname )
      list(REMOVE_AT _args 0 1)
    endif("${_tmp}" STREQUAL "SUBDIR")
  endif(_args)

  if(_installDest)
    file(GLOB _images *.png)
    install(FILES ${_doc} ${_docs} ${_images} DESTINATION ${_installDest}/${dirname})
    # TODO symlinks on non-unix platforms
    if (UNIX)
      # execute some cmake code on make install which creates the symlink
      install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink \"${_installDest}/common\"  \"\$ENV{DESTDIR}${_installDest}/${dirname}/common\" )" )
    endif (UNIX)
  endif(_installDest)

endmacro(create_handbook)


create_handbook(index.docbook INSTALL_DESTINATION ${HTML_INSTALL_DIR}/en SUBDIR ${PROJECT_NAME})
