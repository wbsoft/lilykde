cmake_minimum_required(VERSION 2.4)
project(lilypond-kde4)
set(version "0.3")

find_package(KDE4 REQUIRED)
include_directories(${KDE4_INCLUDES})

add_definitions(-DVERSION=\\"${version}\\")

add_subdirectory(icons)

kde4_add_executable(ktexteditservice ktexteditservice.cpp)
target_link_libraries(ktexteditservice ${KDE4_KDEUI_LIBS})
 
install(TARGETS ktexteditservice ${INSTALL_TARGETS_DEFAULT_ARGS})
install(FILES ktexteditservicerc DESTINATION ${CONFIG_INSTALL_DIR})
install(FILES lilypond.js DESTINATION ${DATA_INSTALL_DIR}/katepart/script)
install(FILES textedit.protocol DESTINATION ${SERVICES_INSTALL_DIR})
