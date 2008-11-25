# FindPyKDE4

# by Wilbert Berendsen <info@wilbertberendsen.nl>,
# based on Simon Edwards' FindPyKDE4.
# This file is in the public domain.

# Find Python.
find_package(PythonInterp REQUIRED)

# Find PyKDE4.
execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_SOURCE_DIR}/cmake/modules/FindPyKDE4.py OUTPUT_VARIABLE pykde_config)
if(NOT pykde_config)
  # Failure to run
  message(FATAL_ERROR "PyKDE4 not found")
endif(NOT pykde_config)

string(REGEX REPLACE ".*\npykde_version:([^\n]+).*$" "\\1" PYKDE4_VERSION ${pykde_config})
string(REGEX REPLACE ".*\npykde_version_str:([^\n]+).*$" "\\1" PYKDE4_VERSION_STR ${pykde_config})
message(STATUS "Found PyKDE4 version ${PYKDE4_VERSION_STR}")

# Where to install stuff, in separate module
include(FindKDEInstallDirs)

