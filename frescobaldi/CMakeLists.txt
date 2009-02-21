cmake_minimum_required(VERSION 2.4)
project(frescobaldi)
set(VERSION "0.7.7")

# Find our own modules
set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

# some Python macros
include(Python)

# Check if all required Python modules are present by running checkmodules.py
python_test_script(${CMAKE_SOURCE_DIR}/checkmodules.py)

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
add_subdirectory(pics)
add_subdirectory(po)

install(DIRECTORY 
        rumor
        icons
        DESTINATION ${APP_DIR}
        PATTERN .* EXCLUDE)
