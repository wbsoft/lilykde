cmake_minimum_required(VERSION 2.4)
project(frescobaldi)
set(VERSION "0.1")

# Find our own modules
set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

# We need PyKDE4, which will find Python as well.
find_package(PyKDE4 REQUIRED)

set(APP_DIR ${DATA_INSTALL_DIR}/${PROJECT_NAME})
set(MODULE_DIR ${APP_DIR}/lib)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/frescobaldi.py
               ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi @ONLY)

add_subdirectory(python)

install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi DESTINATION ${BIN_INSTALL_DIR})
install(FILES data/frescobaldiui.rc DESTINATION ${APP_DIR})

