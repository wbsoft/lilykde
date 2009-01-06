cmake_minimum_required(VERSION 2.4)
project(frescobaldi)
set(VERSION "0.7.2")

# Find our own modules
set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

# We need PyKDE4, which will find Python as well.
find_package(PyKDE4 REQUIRED)

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
