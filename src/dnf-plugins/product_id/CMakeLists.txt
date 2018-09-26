CMAKE_MINIMUM_REQUIRED (VERSION 3.11.2)

set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
project(product_id C)

ADD_COMPILE_OPTIONS(-Wall -fPIC -g -Wl,as-needed)

find_package (PkgConfig REQUIRED)
pkg_check_modules (GLIB REQUIRED glib-2.0>=2.44.0)
pkg_check_modules (LIBDNF REQUIRED libdnf>=0.7.0)

include_directories (${GLIB_INCLUDE_DIRS})
include_directories (${LIBDNF_INCLUDE_DIRS})

add_library(product_id SHARED product_id.c)

set_target_properties(product_id PROPERTIES PREFIX "")

install(TARGETS product_id LIBRARY DESTINATION /usr/lib64/libdnf/plugins)
