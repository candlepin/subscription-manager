set (rhsmcertd_src rhsmcertd.c)

# Search for glib module and use first working one
pkg_search_module (GLIB2 REQUIRED glib-2.0)

# Try to get libexec dir directory
if (NOT LIBEXEC_DIR)
    execute_process (COMMAND "shell rpm --eval='%_libexecdir'"
        OUTPUT_VARIABLE LIBEXEC_DIR)
endif()

# Make build flags compiler specific
if (CMAKE_COMPILER_IS_GNUCC)
    if (CMAKE_BUILD_TYPE STREQUAL "Debug")
        set (CMAKE_C_FLAGS "-D_REETRANT -ggdb -Wall -Wextra -pedantic -O0 -DLIBEXECDIR='\"${LIBEXEC_DIR}\"' -std=c99")
        set (CMAKE_EXE_LINKER_FLAGS "${GLIB2_LFLAGS}")
    elseif( CMAKE_BUILD_TYPE STREQUAL "Release" )
        set (CMAKE_C_FLAGS "-D_REETRANT -DNDEBUG -Wall -Wextra -pedantic -O3 -DLIBEXECDIR='\"${LIBEXEC_DIR}\"' -std=c99")
        set (CMAKE_EXE_LINKER_FLAGS "${GLIB2_LFLAGS}")
    endif ()
endif (CMAKE_COMPILER_IS_GNUCC)

include_directories (${GLIB2_INCLUDE_DIRS})

add_executable (rhsmcertd ${rhsmcertd_src})

target_link_libraries (rhsmcertd ${GLIB2_LIBRARIES})

# The rule to install daemon binary
install (TARGETS rhsmcertd
	RUNTIME
	DESTINATION bin)