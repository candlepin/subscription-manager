CMAKE_MINIMUM_REQUIRED (VERSION 3.11.2)

set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
project(product-id C)

ADD_COMPILE_OPTIONS(-Wall -fPIC -g -Wl,as-needed)

find_package (PkgConfig REQUIRED)
pkg_check_modules (GLIB REQUIRED glib-2.0>=2.44.0)
pkg_check_modules (LIBDNF REQUIRED libdnf>=0.7.0)
pkg_check_modules (ZLIB zlib REQUIRED zlib>=1.2.0)
pkg_check_modules (OPENSSL libcrypto libssl REQUIRED)

include_directories (${GLIB_INCLUDE_DIRS})
include_directories (${LIBDNF_INCLUDE_DIRS})
include_directories(${ZLIB_INCLUDE_DIRS})
include_directories(${OPENSSL_INCLUDE_DIR})

add_library(product-id SHARED product-id.c)

# Don't put "lib" on the front
set_target_properties(product-id PROPERTIES PREFIX "")

target_link_libraries(product-id ${ZLIB_LIBRARIES} ${OPENSSL_LIBRARIES})

install(TARGETS product-id LIBRARY DESTINATION /usr/lib64/libdnf/plugins)
