# Remove files from install_manifest.txt.
# MANIFEST should be defined on the command line.
# DESTDIR is taken into account automatically.

if(NOT EXISTS "${MANIFEST}")
  message(FATAL_ERROR "Cannot find install manifest: \"${MANIFEST}\"")
endif(NOT EXISTS "${MANIFEST}")

file(STRINGS "${MANIFEST}" files)
foreach(file ${files})
  set(file "$ENV{DESTDIR}${file}")
  message(STATUS "Uninstalling: ${file}")
  if(EXISTS "${file}")
    file(REMOVE "${file}")
  else(EXISTS "${file}")
    message("File does not exist: ${file}")
  endif(EXISTS "${file}")
endforeach(file)
