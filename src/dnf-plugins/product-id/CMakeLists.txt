CMAKE_MINIMUM_REQUIRED (VERSION 3.11.2)

project(product-id C)

include(GNUInstallDirs)

# Warn user because CLion is upset by in source builds
MACRO(MACRO_ENSURE_OUT_OF_SOURCE_BUILD MSG)
    STRING(COMPARE EQUAL "${CMAKE_SOURCE_DIR}"
    "${CMAKE_BINARY_DIR}" insource)
    GET_FILENAME_COMPONENT(PARENTDIR ${CMAKE_SOURCE_DIR} PATH)
    STRING(COMPARE EQUAL "${CMAKE_SOURCE_DIR}"
    "${PARENTDIR}" insourcesubdir)
    IF(insource OR insourcesubdir)
        MESSAGE(WARNING "${MSG}")
    ENDIF(insource OR insourcesubdir)
ENDMACRO(MACRO_ENSURE_OUT_OF_SOURCE_BUILD)

MACRO_ENSURE_OUT_OF_SOURCE_BUILD(
"${CMAKE_PROJECT_NAME} requires an out of source build. Delete all CMake generated files or CLion won't work."
)

set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)

#ADD_COMPILE_OPTIONS(-Wall -fPIC -g -Wl,as-needed)

# Build type
if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Setting build type to 'Debug' as none was specified.")
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Choose the type of build." FORCE)
    # Set the possible values of build type for cmake-gui
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release")
endif ()

if (CMAKE_COMPILER_IS_GNUCC)
    set (CMAKE_C_FLAGS "-Wall -fPIC -Wextra -pedantic -Wno-long-long")
    if (CMAKE_BUILD_TYPE STREQUAL "Debug")
        set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -ggdb -O0 --coverage")
    elseif( CMAKE_BUILD_TYPE STREQUAL "Release" )
        set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DNDEBUG -g -O3 -fno-strict-aliasing")
    endif ()
endif (CMAKE_COMPILER_IS_GNUCC)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB REQUIRED glib-2.0>=2.44.0)
pkg_check_modules(GIO REQUIRED gio-2.0>=2.54.3)
pkg_check_modules(LIBDNF REQUIRED libdnf>=0.22.0)
pkg_check_modules(ZLIB REQUIRED zlib>=1.2.0)
pkg_check_modules(OPENSSL libcrypto libssl REQUIRED)
pkg_check_modules(JSONC json-c REQUIRED)

# Copy ./test_data directory to ${PROJECT_BINARY_DIR}
file (COPY "${PROJECT_SOURCE_DIR}/test_data/corrupted_compressed_productid.pem.gz"
        DESTINATION "${PROJECT_BINARY_DIR}/test_data/")
file (COPY "${PROJECT_SOURCE_DIR}/test_data/59803427316a729fb1d67fd08e7d0c8ccd2a4a5377729b747b76345851bdba6c-productid.gz"
        DESTINATION "${PROJECT_BINARY_DIR}/test_data/")

include_directories(${GLIB_INCLUDE_DIRS})
include_directories(${GIO_INCLUDE_DIRS})
include_directories(${LIBDNF_INCLUDE_DIRS})
include_directories(${ZLIB_INCLUDE_DIRS})
include_directories(${OPENSSL_INCLUDE_DIR})
include_directories(${JSONC_INCLUDE_DIR})

add_library(product-id SHARED product-id.c util.c productdb.c test-product-id.c)

# Don't put "lib" on the front
set_target_properties(product-id PROPERTIES PREFIX "")

target_link_libraries(product-id
    ${GLIB_LIBRARIES}
    ${GIO_LIBRARIES}
    ${LIBDNF_LIBRARIES}
    ${ZLIB_LIBRARIES}
    ${OPENSSL_LIBRARIES}
    ${JSONC_LIBRARIES}
)

# Note: libdnf use "hardcoded" directory /usr/lib64/libdnf/plugins for searching
# libdnf plugins. This directory cannot be changed by any configuration file ATM.
# It can be changed only during building of libdnf using CMAKE_INSTALL_FULL_LIBDIR
install(TARGETS product-id LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}/libdnf/plugins)

enable_testing()

# Testing of productdb
add_executable(test-productdb test-productdb.c)
target_link_libraries(test-productdb product-id)
add_test(productdb test-productdb)

# Testing of product-id
add_executable(test-product-id test-product-id.c)
target_link_libraries(test-product-id product-id)
add_test(product-id test-product-id)
