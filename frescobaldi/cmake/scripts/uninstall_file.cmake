# Remove a file or symlink taking DESTDIR into account.
# FILENAME should be defined on the command line.
# If NO_CHECK is also defined, the file's existence is not checked
# before removing. This can be used to remove a broken symlink.

set(file "$ENV{DESTDIR}${FILENAME}")
message(STATUS "Uninstalling: ${file}")
if(DEFINED NO_CHECK OR EXISTS "${file}")
  file(REMOVE "${file}")
else(DEFINED NO_CHECK OR EXISTS "${file}")
  message("File does not exist: ${file}")
endif(DEFINED NO_CHECK OR EXISTS "${file}")
