# Generate PNGs from LilyPond files

# keep a list of all pngs for adding them to our target
set(all_pngs)

# find out which local files a LilyPond file includes
macro(lilypond_deps _varname _lyfile)
  set(_deps)
  file(READ ${_lyfile} _contents)
  string(REGEX MATCHALL "\\\\include *\"[^\"]+\"" _includes ${_contents})
  foreach(_incl ${_includes})
    string(REGEX REPLACE "[^\"]*\"([^\"]*)\".*" "\\1" _incl ${_incl})
    if(_incl)
      set(_dep ${CMAKE_CURRENT_SOURCE_DIR}/${_incl})
      if(EXISTS ${_dep})
	list(APPEND _deps ${_dep})
      endif(EXISTS ${_dep})
    endif(_incl)
  endforeach(_incl ${_includes})
  set(${_varname} ${_deps})
endmacro(lilypond_deps)


# convert a ly file to a PNG icon 22x22 pix.
macro(lilypond_png_icon _lyfile)
  lilypond_deps(_deps ${_lyfile})
  get_filename_component(_base ${_lyfile} NAME_WE)
  set(_outp "${CMAKE_CURRENT_BINARY_DIR}/${_base}.png")
  add_custom_command(
    OUTPUT ${_outp}
    DEPENDS ${_deps}
    COMMAND lilypond 
        -ddelete-intermediate-files
        --png -dpixmap-format=pngalpha
        -o "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}"
        "${_lyfile}"
    COMMAND convert
        "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
        -trim
        -bordercolor transparent -border 20
        +repage
        -gravity Center -crop 22x22+0+0
        +repage
        "${_outp}"
    COMMAND /bin/rm "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
    VERBATIM
  )
  list(APPEND all_pngs ${_outp})
endmacro(lilypond_png_icon)

# convert a ly file to a PNG image with a 3px border.
macro(lilypond_png_image _lyfile_arg)
  set(_lyfile ${_lyfile_arg})
  if(NOT IS_ABSOLUTE ${_lyfile_arg})
    set(_lyfile "${CMAKE_CURRENT_SOURCE_DIR}/${_lyfile_arg}")
  endif(NOT IS_ABSOLUTE ${_lyfile_arg})
  lilypond_deps(_deps ${_lyfile})
  get_filename_component(_base ${_lyfile} NAME_WE)
  set(_outp "${CMAKE_CURRENT_BINARY_DIR}/${_base}.png")
  add_custom_command(
    OUTPUT ${_outp}
    DEPENDS ${_deps}
    COMMAND lilypond 
        -ddelete-intermediate-files
        --png -dpixmap-format=pngalpha
        -o "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}"
        "${_lyfile}"
    COMMAND convert
        "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
        -trim
        -bordercolor transparent -border 3
        +repage
        "${_outp}"
    COMMAND /bin/rm "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
    VERBATIM
  )
  list(APPEND all_pngs ${_outp})
endmacro(lilypond_png_image)


# Make icons for articulations and notes etc.
file(GLOB lilypond_files articulation_*.ly note_*.ly time_*.ly)
foreach(_ly ${lilypond_files})
  lilypond_png_icon(${_ly})
endforeach(_ly ${lilypond_files})

# Make misc. other images
lilypond_png_image(scorewiz.ly)

# Build and install all LilyPond-generaged pictures
add_custom_target(lilypond_pngs ALL DEPENDS ${all_pngs})
install(FILES ${all_pngs} DESTINATION ${APP_DIR}/pics)
