cmake_minimum_required(VERSION 2.4)
project(frescobaldi)
set(VERSION "0.1")

set(CMAKE_MODULE_PATH ${frescobaldi_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

find_package(PyKDE4 REQUIRED)
find_package(PythonInterp REQUIRED)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/frescobaldi.py
               ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi @ONLY)

