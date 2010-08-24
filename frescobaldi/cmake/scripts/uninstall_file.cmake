# Remove a file or symlink taking DESTDIR into account.
# FILENAME should be defined on the command line.

set(file "$ENV{DESTDIR}${FILENAME}")
message(STATUS "Uninstalling: ${file}")
execute_process(
  COMMAND ${CMAKE_COMMAND} -E remove "${file}"
  RESULT_VARIABLE rm_retval
)
if(rm_retval)
  message(WARNING "Could not remove: ${file}")
endif(rm_retval)
