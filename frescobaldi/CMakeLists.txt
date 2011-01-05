cmake_minimum_required(VERSION 2.4)
project(frescobaldi NONE)
set(VERSION "1.2.1")

option(HANDBOOK "Install Frescobaldi User Guide" ON)
option(BYTECOMPILE "Byte-compile Python modules on install" ON)
option(CHECKMODULES "Check presence and versions of required Python modules" ON)

# Find our own modules
set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

# some Python macros
include(Python)

# uninstall target
include(uninstall)

# Check if all required Python modules are present by running checkmodules.py
if(CHECKMODULES)
  python_test_script(${CMAKE_SOURCE_DIR}/checkmodules.py)
endif(CHECKMODULES)

 # Where to install stuff, in separate module
include(FindKDEInstallDirs)

# Do not rebuild our MO's and icons if the build rules were changed.
# Makes releasing prebuilt tarballs possible.
set(CMAKE_SKIP_RULE_DEPENDENCY TRUE)

# Set some install directories
set(APP_DIR ${DATA_INSTALL_DIR}/${PROJECT_NAME})
set(MODULE_DIR ${APP_DIR}/lib)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/frescobaldi.py
               ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi @ONLY)
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi DESTINATION ${BIN_INSTALL_DIR})

add_subdirectory(python)
add_subdirectory(data)

if(EXISTS ${CMAKE_SOURCE_DIR}/prebuilt)
  add_subdirectory(prebuilt)
else(EXISTS ${CMAKE_SOURCE_DIR}/prebuilt)
  add_subdirectory(pics)
  add_subdirectory(po)
endif(EXISTS ${CMAKE_SOURCE_DIR}/prebuilt)

if(HANDBOOK)
  add_subdirectory(doc)
endif(HANDBOOK)

install(DIRECTORY 
        rumor
        icons
        css
        DESTINATION ${APP_DIR}
        PATTERN .* EXCLUDE)
