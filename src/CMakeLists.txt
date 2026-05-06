cmake_minimum_required(VERSION 3.20)
project(crypto_algos C)

set(CMAKE_C_STANDARD 11)

find_package(PkgConfig REQUIRED)
pkg_check_modules(OPENSSL REQUIRED IMPORTED_TARGET libcrypto libssl)

find_package(Python3 COMPONENTS Development)
include_directories(${Python3_INCLUDE_DIRS})

add_library (_certificate SHARED certificate.c)
set_target_properties(_certificate PROPERTIES PREFIX "")

target_link_libraries(_certificate PUBLIC PkgConfig::OPENSSL ${Python3_LIBRARIES})

enable_testing()

pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0)
pkg_check_modules(GIO REQUIRED IMPORTED_TARGET gio-2.0)

# Testing of _certificate
add_executable(test_certificate test_certificate.c)
target_link_libraries(test_certificate
        _certificate
        PkgConfig::GLIB
        PkgConfig::GIO
)
add_test(certificate test_certificate)
