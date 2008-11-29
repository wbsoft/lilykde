# Generate PNGs from LilyPond files

file(GLOB lilypond_files *.ly)
set(_pngs)
foreach(_ly ${lilypond_files})
  # check if the ly file includes some other lilypond file
  set(_deps ${_ly})
  file(STRINGS ${_ly} _includes REGEX "\\\\include\\s*")
  foreach(_incl ${_includes})
    string(REGEX REPLACE "[^\"]*\"([^\"]*)\".*" "\\1" _incl ${_incl})
    if(_incl)
      set(_dep ${CMAKE_CURRENT_SOURCE_DIR}/${_incl})
      if(EXISTS ${_dep})
	list(APPEND _deps ${_dep})
      endif(EXISTS ${_dep})
    endif(_incl)
  endforeach(_incl ${_includes})
  get_filename_component(_base ${_ly} NAME_WE)
  set(_outp "${CMAKE_CURRENT_BINARY_DIR}/${_base}.png")
  add_custom_command(
    OUTPUT ${_outp}
    DEPENDS ${_deps}
    COMMAND lilypond 
         -ddelete-intermediate-files
         --png -dpixmap-format=pngalpha
         -o "${CMAKE_CURRENT_BINARY_DIR}/${_base}"
         "${_ly}"
    COMMAND mogrify -trim -bordercolor transparent -border 3 +repage "${_outp}"
    VERBATIM
  )
  list(APPEND _pngs ${_outp})
endforeach(_ly ${lilypond_files})
add_custom_target(lilypond_pngs ALL DEPENDS ${_pngs})
install(FILES ${_pngs} DESTINATION ${APP_DIR}/pics)
