set (certificate_src certificate.c)

# Make build flags compiler specific
if (CMAKE_COMPILER_IS_GNUCC)
	if (CMAKE_BUILD_TYPE STREQUAL "Debug")
		set (CMAKE_C_FLAGS "-D_REETRANT -ggdb -fPIC -Wall -Wextra -pedantic -O0 -std=c99")
	elseif (CMAKE_BUILD_TYPE STREQUAL "Release")
		set (CMAKE_C_FLAGS "-D_REETRANT -DNDEBUG -fPIC -Wall -Wextra -pedantic -O3 -std=c99")
	endif ()
endif (CMAKE_COMPILER_IS_GNUCC)

# Add Python and OpenSSL directories to those
# the compiler uses to search for include files
include_directories (${PYTHON_INCLUDE_DIRS})
include_directories (${OPENSSL_INCLUDE_DIR})

# Create shared library _certificate.so
add_library (certificate SHARED ${certificate_src})
# Python binary modules have "_" prefix in this case
set_target_properties (certificate PROPERTIES PREFIX "_")

# Link library with Python and OpenSSL libraries
target_link_libraries (certificate ${PYTHON_LIBRARIES})
target_link_libraries (certificate ${OPENSSL_LIBRARIES})

# The rule to install certificate binary module
install (TARGETS certificate
	LIBRARY
	DESTINATION lib)