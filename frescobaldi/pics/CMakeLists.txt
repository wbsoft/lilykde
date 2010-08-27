# Generate PNGs from LilyPond files

find_program(LILYPOND_EXECUTABLE NAMES lilypond)
find_program(CONVERT_EXECUTABLE NAMES convert)

# keep a list of all pngs for adding them to our target
set(all_pngs)

# find out which local files a LilyPond file includes
macro(lilypond_deps _varname _lyfile)
  set(_deps ${_lyfile})
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


# convert a ly file to a PNG icon (e.g. 22x22) pix.
macro(lilypond_png_icon _lyfile _size)
  lilypond_deps(_deps ${_lyfile})
  get_filename_component(_base ${_lyfile} NAME_WE)
  set(_outp "${CMAKE_CURRENT_BINARY_DIR}/${_base}.png")
  add_custom_command(
    OUTPUT ${_outp}
    DEPENDS ${_deps}
    COMMAND ${LILYPOND_EXECUTABLE}
        -ddelete-intermediate-files
        --png -dpixmap-format=pngalpha
        -o "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}"
        "${_lyfile}"
    COMMAND ${CONVERT_EXECUTABLE}
        "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
        -trim
        -bordercolor transparent -border ${_size}
        +repage
        -gravity Center -crop "${_size}x${_size}+0+0"
        +repage
        "${_outp}"
    COMMAND ${CMAKE_COMMAND} -E remove "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
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
    COMMAND ${CMAKE_COMMAND} -E remove "${CMAKE_CURRENT_BINARY_DIR}/temp_${_base}.png"
    VERBATIM
  )
  list(APPEND all_pngs ${_outp})
endmacro(lilypond_png_image)


# Make icons for articulations and notes etc. at 22px
file(GLOB lilypond_files articulation_*.ly note_*.ly time_*.ly bar_*.ly)
foreach(_ly ${lilypond_files})
  lilypond_png_icon(${_ly} 22)
endforeach(_ly ${lilypond_files})

# Clefs, etc at 48px
file(GLOB lilypond_files clef_*.ly system_*.ly)
foreach(_ly ${lilypond_files})
  lilypond_png_icon(${_ly} 48)
endforeach(_ly ${lilypond_files})

# Make misc. larger images
file(GLOB lilypond_files scorewiz.ly)
foreach(_ly ${lilypond_files})
  lilypond_png_image(${_ly})
endforeach(_ly ${lilypond_files})

# Build and install all LilyPond-generated pictures
add_custom_target(lilypond_pngs ALL DEPENDS ${all_pngs})
install(FILES ${all_pngs} DESTINATION ${APP_DIR}/pics)
