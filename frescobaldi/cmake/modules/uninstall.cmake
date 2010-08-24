# CMake module and scripts to add an uninstall target

set(SCRIPTS_DIR "${CMAKE_SOURCE_DIR}/cmake/scripts")

add_custom_target(uninstall)
add_custom_target(uninstall_files)

add_custom_target(uninstall_from_manifest
  COMMAND "${CMAKE_COMMAND}"
    "-DMANIFEST=${CMAKE_BINARY_DIR}/install_manifest.txt"
    -P "${SCRIPTS_DIR}/uninstall_from_manifest.cmake"
)

add_dependencies(uninstall uninstall_files)
add_dependencies(uninstall_files uninstall_from_manifest)

# uninstall_file(name) removes a file with that name on uninstall
# DESTDIR is taken into account automatically
macro(uninstall_file _name)
  string(REGEX REPLACE "[^a-z]+" "_" _target ${_name})
  add_custom_target("uninstall_file${_target}"
    COMMAND "${CMAKE_COMMAND}"
      "-DFILENAME=${_name}"
      -P "${SCRIPTS_DIR}/uninstall_file.cmake"
  )
  add_dependencies(uninstall_files "uninstall_file${_target}")
endmacro(uninstall_file)

