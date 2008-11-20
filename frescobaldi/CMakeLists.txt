cmake_minimum_required(VERSION 2.4)
project(frescobaldi)
set(VERSION "0.1")

set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

find_package(PyKDE4 REQUIRED)
find_package(PythonInterp REQUIRED)
set(APP_DIR ${DATA_INSTALL_DIR}/${PROJECT_NAME})

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/frescobaldi.py
               ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi @ONLY)

add_subdirectory(python)

install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi DESTINATION ${BIN_INSTALL_DIR})
install(FILES data/frescobaldiui.rc DESTINATION ${APP_DIR})

