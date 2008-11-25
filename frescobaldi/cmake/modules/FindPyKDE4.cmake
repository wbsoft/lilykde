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

# The rest comes from FindKDE4.cmake and FindKDE4Internal.cmake
file(TO_CMAKE_PATH "$ENV{KDEDIRS}" _KDEDIRS)

# from FindKDE4.cmake: find kde4-config
find_program(KDE4_KDECONFIG_EXECUTABLE NAMES kde4-config
  # the suffix must be used since KDEDIRS can be a list of directories which don't have bin/ appended
  PATH_SUFFIXES bin               
  HINTS
  ${CMAKE_INSTALL_PREFIX}
  ${_KDEDIRS}
  /opt/kde4
  ONLY_CMAKE_FIND_ROOT_PATH
  )

if(NOT KDE4_KDECONFIG_EXECUTABLE)
  message(FATAL_ERROR "ERROR: Could not find KDE4 kde4-config")
endif(NOT KDE4_KDECONFIG_EXECUTABLE)

# Now find the path to KDELibsDependencies.cmake
execute_process(
  COMMAND "${KDE4_KDECONFIG_EXECUTABLE}" --path data
  OUTPUT_VARIABLE _data_DIRS
  ERROR_QUIET OUTPUT_STRIP_TRAILING_WHITESPACE)
file(TO_CMAKE_PATH "${_data_DIRS}" _data_DIRS)
find_path(KDE4_DATA_DIR cmake/modules/KDELibsDependencies.cmake ${_data_DIRS})

# and include it if found
if(KDE4_DATA_DIR)
  include(${KDE4_DATA_DIR}/cmake/modules/KDELibsDependencies.cmake)
endif(KDE4_DATA_DIR)

########## the following are directories where stuff will be installed to  ###########
# Taken from FindKDE4Internal.cmake.
# This has to be after find_xxx() block above, since there KDELibsDependencies.cmake is included
# which contains the install dirs from kdelibs, which are reused below

if (WIN32)
# use relative install prefix to avoid hardcoded install paths in cmake_install.cmake files

  #set(LIB_INSTALL_DIR      "lib${LIB_SUFFIX}" )            # The subdirectory relative to the install prefix where libraries will be installed (default is ${EXEC_INSTALL_PREFIX}/lib${LIB_SUFFIX})

  set(EXEC_INSTALL_PREFIX  "" )        # Base directory for executables and libraries
  set(SHARE_INSTALL_PREFIX "share" )   # Base directory for files which go to share/
  set(BIN_INSTALL_DIR      "bin"   )   # The install dir for executables (default ${EXEC_INSTALL_PREFIX}/bin)
  set(SBIN_INSTALL_DIR     "sbin"  )   # The install dir for system executables (default ${EXEC_INSTALL_PREFIX}/sbin)

  set(LIBEXEC_INSTALL_DIR  "${BIN_INSTALL_DIR}"          ) # The subdirectory relative to the install prefix where libraries will be installed (default is ${BIN_INSTALL_DIR})
  set(INCLUDE_INSTALL_DIR  "include"                     ) # The subdirectory to the header prefix

  #set(PLUGIN_INSTALL_DIR       "lib${LIB_SUFFIX}/kde4"   ) #                "The subdirectory relative to the install prefix where plugins will be installed (default is ${LIB_INSTALL_DIR}/kde4)
  set(CONFIG_INSTALL_DIR       "share/config"            ) # The config file install dir
  set(DATA_INSTALL_DIR         "share/apps"              ) # The parent directory where applications can install their data
  set(HTML_INSTALL_DIR         "share/doc/HTML"          ) # The HTML install dir for documentation
  set(ICON_INSTALL_DIR         "share/icons"             ) # The icon install dir (default ${SHARE_INSTALL_PREFIX}/share/icons/)
  set(KCFG_INSTALL_DIR         "share/config.kcfg"       ) # The install dir for kconfig files
  set(LOCALE_INSTALL_DIR       "share/locale"            ) # The install dir for translations
  set(MIME_INSTALL_DIR         "share/mimelnk"           ) # The install dir for the mimetype desktop files
  set(SERVICES_INSTALL_DIR     "share/kde4/services"     ) # The install dir for service (desktop, protocol, ...) files
  set(SERVICETYPES_INSTALL_DIR "share/kde4/servicetypes" ) # The install dir for servicestypes desktop files
  set(SOUND_INSTALL_DIR        "share/sounds"            ) # The install dir for sound files
  set(TEMPLATES_INSTALL_DIR    "share/templates"         ) # The install dir for templates (Create new file...)
  set(WALLPAPER_INSTALL_DIR    "share/wallpapers"        ) # The install dir for wallpapers
  set(DEMO_INSTALL_DIR         "share/demos"             ) # The install dir for demos
  set(KCONF_UPDATE_INSTALL_DIR "share/apps/kconf_update" ) # The kconf_update install dir
  set(AUTOSTART_INSTALL_DIR    "share/autostart"         ) # The install dir for autostart files

  set(XDG_APPS_INSTALL_DIR      "share/applications/kde4"   ) # The XDG apps dir
  set(XDG_DIRECTORY_INSTALL_DIR "share/desktop-directories" ) # The XDG directory
  set(XDG_MIME_INSTALL_DIR      "share/mime/packages"       ) # The install dir for the xdg mimetypes

  set(SYSCONF_INSTALL_DIR       "etc"                       ) # The kde sysconfig install dir (default /etc)
  set(MAN_INSTALL_DIR           "share/man"                 ) # The kde man install dir (default ${SHARE_INSTALL_PREFIX}/man/)
  set(INFO_INSTALL_DIR          "share/info"                ) # The kde info install dir (default ${SHARE_INSTALL_PREFIX}/info)")
  set(DBUS_INTERFACES_INSTALL_DIR "share/dbus-1/interfaces" ) # The kde dbus interfaces install dir (default  ${SHARE_INSTALL_PREFIX}/dbus-1/interfaces)")
  set(DBUS_SERVICES_INSTALL_DIR "share/dbus-1/services"     ) # The kde dbus services install dir (default  ${SHARE_INSTALL_PREFIX}/dbus-1/services)")

else (WIN32)

  # This macro implements some very special logic how to deal with the cache.
  # By default the various install locations inherit their value from their "parent" variable
  # so if you set CMAKE_INSTALL_PREFIX, then EXEC_INSTALL_PREFIX, PLUGIN_INSTALL_DIR will
  # calculate their value by appending subdirs to CMAKE_INSTALL_PREFIX .
  # This would work completely without using the cache.
  # But if somebody wants e.g. a different EXEC_INSTALL_PREFIX this value has to go into
  # the cache, otherwise it will be forgotten on the next cmake run.
  # Once a variable is in the cache, it doesn't depend on its "parent" variables
  # anymore and you can only change it by editing it directly.
  # this macro helps in this regard, because as long as you don't set one of the
  # variables explicitely to some location, it will always calculate its value from its
  # parents. So modifying CMAKE_INSTALL_PREFIX later on will have the desired effect.
  # But once you decide to set e.g. EXEC_INSTALL_PREFIX to some special location
  # this will go into the cache and it will no longer depend on CMAKE_INSTALL_PREFIX.
  #
  # additionally if installing to the same location as kdelibs, the other install
  # directories are reused from the installed kdelibs
  macro(_SET_FANCY _var _value _comment)
    set(predefinedvalue "${_value}")
    if ("${CMAKE_INSTALL_PREFIX}" STREQUAL "${KDE4_INSTALL_DIR}" AND DEFINED KDE4_${_var})
      set(predefinedvalue "${KDE4_${_var}}")
    endif ("${CMAKE_INSTALL_PREFIX}" STREQUAL "${KDE4_INSTALL_DIR}" AND DEFINED KDE4_${_var})

    if (NOT DEFINED ${_var})
      set(${_var} ${predefinedvalue})
    else (NOT DEFINED ${_var})
      set(${_var} "${${_var}}" CACHE PATH "${_comment}")
    endif (NOT DEFINED ${_var})
  endmacro(_SET_FANCY)

  if(APPLE)
    set(BUNDLE_INSTALL_DIR "/Applications/KDE4" CACHE PATH "Directory where application bundles will be installed to on OSX" )
  endif(APPLE)

  _set_fancy(EXEC_INSTALL_PREFIX  "${CMAKE_INSTALL_PREFIX}"                 "Base directory for executables and libraries")
  _set_fancy(SHARE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}/share"           "Base directory for files which go to share/")
  _set_fancy(BIN_INSTALL_DIR      "${EXEC_INSTALL_PREFIX}/bin"              "The install dir for executables (default ${EXEC_INSTALL_PREFIX}/bin)")
  _set_fancy(SBIN_INSTALL_DIR     "${EXEC_INSTALL_PREFIX}/sbin"             "The install dir for system executables (default ${EXEC_INSTALL_PREFIX}/sbin)")
  #_set_fancy(LIB_INSTALL_DIR      "${EXEC_INSTALL_PREFIX}/lib${LIB_SUFFIX}" "The subdirectory relative to the install prefix where libraries will be installed (default is ${EXEC_INSTALL_PREFIX}/lib${LIB_SUFFIX})")
  _set_fancy(LIBEXEC_INSTALL_DIR  "${LIB_INSTALL_DIR}/kde4/libexec"         "The subdirectory relative to the install prefix where libraries will be installed (default is ${LIB_INSTALL_DIR}/kde4/libexec)")
  _set_fancy(INCLUDE_INSTALL_DIR  "${CMAKE_INSTALL_PREFIX}/include"         "The subdirectory to the header prefix")

  _set_fancy(PLUGIN_INSTALL_DIR       "${LIB_INSTALL_DIR}/kde4"                "The subdirectory relative to the install prefix where plugins will be installed (default is ${LIB_INSTALL_DIR}/kde4)")
  _set_fancy(CONFIG_INSTALL_DIR       "${SHARE_INSTALL_PREFIX}/config"         "The config file install dir")
  _set_fancy(DATA_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/apps"           "The parent directory where applications can install their data")
  _set_fancy(HTML_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/doc/HTML"       "The HTML install dir for documentation")
  _set_fancy(ICON_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/icons"          "The icon install dir (default ${SHARE_INSTALL_PREFIX}/share/icons/)")
  _set_fancy(KCFG_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/config.kcfg"    "The install dir for kconfig files")
  _set_fancy(LOCALE_INSTALL_DIR       "${SHARE_INSTALL_PREFIX}/locale"         "The install dir for translations")
  _set_fancy(MIME_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/mimelnk"        "The install dir for the mimetype desktop files")
  _set_fancy(SERVICES_INSTALL_DIR     "${SHARE_INSTALL_PREFIX}/kde4/services"  "The install dir for service (desktop, protocol, ...) files")
  _set_fancy(SERVICETYPES_INSTALL_DIR "${SHARE_INSTALL_PREFIX}/kde4/servicetypes" "The install dir for servicestypes desktop files")
  _set_fancy(SOUND_INSTALL_DIR        "${SHARE_INSTALL_PREFIX}/sounds"         "The install dir for sound files")
  _set_fancy(TEMPLATES_INSTALL_DIR    "${SHARE_INSTALL_PREFIX}/templates"      "The install dir for templates (Create new file...)")
  _set_fancy(WALLPAPER_INSTALL_DIR    "${SHARE_INSTALL_PREFIX}/wallpapers"     "The install dir for wallpapers")
  _set_fancy(DEMO_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/demos"          "The install dir for demos")
  _set_fancy(KCONF_UPDATE_INSTALL_DIR "${DATA_INSTALL_DIR}/kconf_update"       "The kconf_update install dir")
  _set_fancy(AUTOSTART_INSTALL_DIR    "${SHARE_INSTALL_PREFIX}/autostart"      "The install dir for autostart files")

  _set_fancy(XDG_APPS_INSTALL_DIR     "${SHARE_INSTALL_PREFIX}/applications/kde4"         "The XDG apps dir")
  _set_fancy(XDG_DIRECTORY_INSTALL_DIR "${SHARE_INSTALL_PREFIX}/desktop-directories"      "The XDG directory")
  _set_fancy(XDG_MIME_INSTALL_DIR     "${SHARE_INSTALL_PREFIX}/mime/packages"  "The install dir for the xdg mimetypes")

  _set_fancy(SYSCONF_INSTALL_DIR      "${CMAKE_INSTALL_PREFIX}/etc"            "The kde sysconfig install dir (default ${CMAKE_INSTALL_PREFIX}/etc)")
  _set_fancy(MAN_INSTALL_DIR          "${SHARE_INSTALL_PREFIX}/man"            "The kde man install dir (default ${SHARE_INSTALL_PREFIX}/man/)")
  _set_fancy(INFO_INSTALL_DIR         "${SHARE_INSTALL_PREFIX}/info"           "The kde info install dir (default ${SHARE_INSTALL_PREFIX}/info)")
  _set_fancy(DBUS_INTERFACES_INSTALL_DIR      "${SHARE_INSTALL_PREFIX}/dbus-1/interfaces" "The kde dbus interfaces install dir (default  ${SHARE_INSTALL_PREFIX}/dbus-1/interfaces)")
  _set_fancy(DBUS_SERVICES_INSTALL_DIR      "${SHARE_INSTALL_PREFIX}/dbus-1/services"     "The kde dbus services install dir (default  ${SHARE_INSTALL_PREFIX}/dbus-1/services)")

endif (WIN32)

