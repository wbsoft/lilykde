# CMake module and scripts to add an uninstall target

set(SCRIPTS_DIR "${CMAKE_SOURCE_DIR}/cmake/scripts")

add_custom_target(uninstall)

add_custom_target(uninstall_from_manifest
  COMMAND "${CMAKE_COMMAND}"
    "-DMANIFEST=${CMAKE_BINARY_DIR}/install_manifest.txt"
    -P "${SCRIPTS_DIR}/uninstall_from_manifest.cmake"
)
add_dependencies(uninstall uninstall_from_manifest)

# create unique target names based on a prefix
macro(unique_target _varName _prefix)
  set(_counter "_counter_${_prefix}")
  if(NOT DEFINED ${_counter})
    set(${_counter} 0)
  endif(NOT DEFINED ${_counter})
  math(EXPR ${_counter} "${${_counter}} + 1")
  set(${_varName} "${_prefix}_${${_counter}}")
endmacro(unique_target)

# uninstall_file(name) removes a file or symlink with that name on uninstall,
# taking DESTDIR into account. If NO_CHECK is appended, the file's existence is
# not checked before removing. This can be used to uninstall a broken symlink.
#
# Use this macro to remove a file or symlink that is not in the
# install_manifest.txt file, e.g. because it was generated by an
# install(CODE ...) construct.
macro(uninstall_file _name)
  unique_target(_target "uninstall_file")
  if("${ARGN}" STREQUAL "NO_CHECK")
    add_custom_target(${_target}
      COMMAND "${CMAKE_COMMAND}"
	"-DFILENAME=${_name}"
	"-DNO_CHECK=TRUE"
	-P "${SCRIPTS_DIR}/uninstall_file.cmake"
    )
  else("${ARGN}" STREQUAL "NO_CHECK")
    add_custom_target(${_target}
      COMMAND "${CMAKE_COMMAND}"
	"-DFILENAME=${_name}"
	-P "${SCRIPTS_DIR}/uninstall_file.cmake"
    )
  endif("${ARGN}" STREQUAL "NO_CHECK")
  add_dependencies(uninstall ${_target})
endmacro(uninstall_file)

