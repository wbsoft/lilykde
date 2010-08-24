# Remove files from install_manifest.txt.
# MANIFEST should be defined on the command line.
# DESTDIR is taken into account automatically.

if(NOT EXISTS "${MANIFEST}")
  message(FATAL_ERROR "Cannot find install manifest: \"${MANIFEST}\"")
endif(NOT EXISTS "${MANIFEST}")

file(READ "${MANIFEST}" files)
string(REGEX REPLACE "\n" ";" files "${files}")
foreach(file ${files})
  set(file "$ENV{DESTDIR}${file}")
  message(STATUS "Uninstalling: ${file}")
  if(EXISTS "${file}")
    execute_process(
      COMMAND ${CMAKE_COMMAND} -E remove "${file}"
      RESULT_VARIABLE rm_retval
    )
    if(rm_retval)
      message(FATAL_ERROR "Problem when removing \"${file}\"")
    endif(rm_retval)
  else(EXISTS "${file}")
    message(STATUS "File \"${file}\" does not exist.")
  endif(EXISTS "${file}")
endforeach(file)
