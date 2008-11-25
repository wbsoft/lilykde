cmake_minimum_required(VERSION 2.4)
project(frescobaldi)
set(VERSION "0.1")

set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules ${CMAKE_MODULE_PATH})

find_package(PyKDE4 REQUIRED)
find_package(PythonInterp REQUIRED)

# Our own logic to install everything in the right place
execute_process(COMMAND kde4-config --exec-prefix OUTPUT_VARIABLE _prefix OUTPUT_STRIP_TRAILING_WHITESPACE)
execute_process(COMMAND kde4-config --install data OUTPUT_VARIABLE _data OUTPUT_STRIP_TRAILING_WHITESPACE)
file(RELATIVE_PATH _data ${_prefix} ${_data})
set(DATA_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/${_data})
execute_process(COMMAND kde4-config --install config OUTPUT_VARIABLE _config OUTPUT_STRIP_TRAILING_WHITESPACE)
file(RELATIVE_PATH _config ${_prefix} ${_config})
set(CONFIG_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/${_config})
execute_process(COMMAND kde4-config --install icon OUTPUT_VARIABLE _icon OUTPUT_STRIP_TRAILING_WHITESPACE)
file(RELATIVE_PATH _icon ${_prefix} ${_icon})
set(ICON_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/${_icon})


set(APP_DIR ${DATA_INSTALL_DIR}/${PROJECT_NAME})
set(MODULE_DIR ${APP_DIR}/lib)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/frescobaldi.py
               ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi @ONLY)

add_subdirectory(python)

install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/frescobaldi DESTINATION ${BIN_INSTALL_DIR})
install(FILES data/frescobaldiui.rc DESTINATION ${APP_DIR})

