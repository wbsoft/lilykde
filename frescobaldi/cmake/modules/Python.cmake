# We need Python
find_package(PythonInterp REQUIRED)


# Check if all required Python modules are present by running checkmodules.py
macro(python_test_script _script)
  execute_process(
    COMMAND ${PYTHON_EXECUTABLE} "${_script}"
    ERROR_VARIABLE _error)
  if(_error)
    message(FATAL_ERROR ${_error})
  endif(_error)
endmacro(python_test_script)


# install all python files in the current directory recursively to a
# destination and create a target to byte-compile them.
macro(python_install_directory _destination)
  file(GLOB_RECURSE python_files *.py)
  set(_pycs)
  foreach(_py ${python_files})
    file(RELATIVE_PATH _rel ${CMAKE_CURRENT_SOURCE_DIR} ${_py})
    get_filename_component(_dir ${_rel} PATH)
    file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${_dir})
    set(_pyc ${CMAKE_CURRENT_BINARY_DIR}/${_rel}c)
    add_custom_command(
      OUTPUT ${_pyc}
      COMMAND ${PYTHON_EXECUTABLE}
      ARGS -c "import py_compile; py_compile.compile('${_py}', '${_pyc}', doraise=True)"
      COMMENT "Byte-compiling ${_rel}"
      DEPENDS ${_py}
      VERBATIM
    )
    list(APPEND _pycs ${_pyc})
    # install .py and .pyc file
    install(FILES ${_py} ${_pyc} DESTINATION ${_destination}/${_dir})
  endforeach(_py)
  # make unique target name
  file(RELATIVE_PATH _target ${CMAKE_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  string(REGEX REPLACE "[/]" "_" _target ${_target})
  add_custom_target("bytecompile_${_target}" ALL DEPENDS ${_pycs})
endmacro(python_install_directory _destination)

