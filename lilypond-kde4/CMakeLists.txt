project(lilypond-kde4)

find_package( KDE4 REQUIRED )
include_directories( ${KDE4_INCLUDES} )

kde4_add_executable(ktexteditservice ktexteditservice.cpp)
target_link_libraries(ktexteditservice ${KDE4_KDEUI_LIBS})
 
install(TARGETS ktexteditservice ${INSTALL_TARGETS_DEFAULT_ARGS})
