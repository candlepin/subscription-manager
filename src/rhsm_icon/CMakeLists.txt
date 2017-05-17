set (rhsm_icon_src rhsm_icon.c)

# Search for glib module and use first working one
pkg_search_module (GTK REQUIRED gtk+-3.0)
pkg_search_module (LIBNOTIFY REQUIRED libnotify)
pkg_search_module (GCONF2 REQUIRED gconf-2.0)
pkg_search_module (DBUS_GLIB1 REQUIRED dbus-glib-1)

# Make build flags compiler specific
if (CMAKE_COMPILER_IS_GNUCC)
    if (CMAKE_BUILD_TYPE STREQUAL "Debug")
        set (CMAKE_C_FLAGS "-D_REETRANT -ggdb -Wall -Wextra -pedantic -O0 -std=c99")
    elseif( CMAKE_BUILD_TYPE STREQUAL "Release" )
        set (CMAKE_C_FLAGS "-D_REETRANT -DNDEBUG -Wall -Wextra -pedantic -O3 -std=c99")
    endif ()
endif (CMAKE_COMPILER_IS_GNUCC)

include_directories (${GTK_INCLUDE_DIRS} ${LIBNOTIFY_INCLUDE_DIRS} ${GCONF2_INCLUDE_DIRS} ${DBUS_GLIB1_INCLUDE_DIRS})

add_executable (rhsm_icon ${rhsm_icon_src})

target_link_libraries (rhsm_icon ${GTK_LIBRARIES} ${LIBNOTIFY_LIBRARIES} ${GCONF2_LIBRARIES} ${DBUS_GLIB1_LIBRARIES})

# The rule to install rhsm_icon binary
install (TARGETS rhsm_icon
	RUNTIME
	DESTINATION bin)