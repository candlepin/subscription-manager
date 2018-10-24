CMAKE_MINIMUM_REQUIRED (VERSION 3.11.2)

project(product-id C)

# Warn user because CLion is upset by in source builds
MACRO(MACRO_ENSURE_OUT_OF_SOURCE_BUILD MSG)
    STRING(COMPARE EQUAL "${CMAKE_SOURCE_DIR}"
    "${CMAKE_BINARY_DIR}" insource)
    GET_FILENAME_COMPONENT(PARENTDIR ${CMAKE_SOURCE_DIR} PATH)
    STRING(COMPARE EQUAL "${CMAKE_SOURCE_DIR}"
    "${PARENTDIR}" insourcesubdir)
    IF(insource OR insourcesubdir)
        MESSAGE(FATAL_ERROR "${MSG}")
    ENDIF(insource OR insourcesubdir)
ENDMACRO(MACRO_ENSURE_OUT_OF_SOURCE_BUILD)

MACRO_ENSURE_OUT_OF_SOURCE_BUILD(
"${CMAKE_PROJECT_NAME} requires an out of source build. Delete all CMake generated files or CLion won't work."
)


set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)

ADD_COMPILE_OPTIONS(-Wall -fPIC -g -Wl,as-needed)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB REQUIRED glib-2.0>=2.44.0)
pkg_check_modules(GIO REQUIRED gio-2.0>=2.54.3)
pkg_check_modules(LIBDNF REQUIRED libdnf>=0.7.0)
pkg_check_modules(ZLIB zlib REQUIRED zlib>=1.2.0)
pkg_check_modules(OPENSSL libcrypto libssl REQUIRED)
pkg_check_modules(JSONC json-c REQUIRED)

include_directories(${GLIB_INCLUDE_DIRS})
include_directories(${GIO_INCLUDE_DIRS})
include_directories(${LIBDNF_INCLUDE_DIRS})
include_directories(${ZLIB_INCLUDE_DIRS})
include_directories(${OPENSSL_INCLUDE_DIR})
include_directories(${JSONC_INCLUDE_DIR})

add_library(product-id SHARED product-id.c util.c productdb.c)

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

install(TARGETS product-id LIBRARY DESTINATION /usr/lib64/libdnf/plugins)

enable_testing()
add_executable(test-productdb test-productdb.c)
target_link_libraries(test-productdb product-id)
add_test(productdb test-productdb)
