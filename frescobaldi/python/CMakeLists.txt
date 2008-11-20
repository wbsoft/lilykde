add_custom_target(bytecompile ALL)
file(GLOB_RECURSE python_files *.py)

foreach(_file ${python_files})
  file(RELATIVE_PATH _rel ${CMAKE_CURRENT_SOURCE_DIR} ${_file})
  get_filename_component(_dir ${_rel} PATH)
  get_filename_component(_name ${_rel} NAME)
  file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${_dir})
  set(_pyc ${CMAKE_CURRENT_BINARY_DIR}/${_rel}c)
  add_custom_command(
    TARGET bytecompile
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_SOURCE_DIR}/cmake/modules/PythonCompileFile.py ${_file} ${_pyc}
    COMMENT "Byte-compiling ${_rel}"
  )
  # install .py and .pyc file
  install(FILES ${_file} ${_pyc} DESTINATION ${APP_DIR}/lib/${_dir})
endforeach(_file)
