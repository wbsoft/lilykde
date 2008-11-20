add_custom_target(bytecompile ALL)

file(GLOB_RECURSE python_files *.py)

foreach(_file ${python_files})
  get_filename_component(_path ${_file} PATH)
  get_filename_component(_name ${_file} NAME)
  file(RELATIVE_PATH _dir ${CMAKE_CURRENT_SOURCE_DIR} ${_path})
  file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${_dir})
  set(_pyc ${CMAKE_CURRENT_BINARY_DIR}/${_dir}/${_name}c)
  set(_dest ${DATA_INSTALL_DIR}/${PROJECT_NAME}/lib/${_dir})
  
  # install source file
  install(FILES ${_file} DESTINATION ${_dest})

  add_custom_command(
    TARGET bytecompile
    COMMAND ${CMAKE_COMMAND} -E echo Byte-compiling ${_dir}/${_name}
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_SOURCE_DIR}/cmake/modules/PythonCompileFile.py ${_file} ${_pyc}
    DEPENDS ${_file}
    VERBATIM
  )

  # install pyc file
  install (FILES ${_pyc} DESTINATION ${_dest})

endforeach(_file)
