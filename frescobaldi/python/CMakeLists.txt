file(GLOB_RECURSE python_files *.py)
set(_pycs)
foreach(_py ${python_files})
  file(RELATIVE_PATH _rel ${CMAKE_CURRENT_SOURCE_DIR} ${_py})
  get_filename_component(_dir ${_rel} PATH)
  get_filename_component(_name ${_rel} NAME)
  file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${_dir})
  set(_pyc ${CMAKE_CURRENT_BINARY_DIR}/${_rel}c)
  add_custom_command(
    OUTPUT ${_pyc}
    COMMAND ${PYTHON_EXECUTABLE}
    ARGS -c "import py_compile; py_compile.compile('${_py}', '${_pyc}')"
    COMMENT "Byte-compiling ${_rel}"
    DEPENDS ${_py}
    VERBATIM
  )
  list(APPEND _pycs ${_pyc})
  # install .py and .pyc file
  install(FILES ${_py} ${_pyc} DESTINATION ${APP_DIR}/lib/${_dir})
endforeach(_py)
add_custom_target(bytecompile ALL DEPENDS ${_pycs})
