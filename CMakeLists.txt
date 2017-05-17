# Minimal version of CMake
cmake_minimum_required (VERSION 2.8)

# Build type
if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Setting build type to 'Release' as none was specified.")
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
    # Set the possible values of build type for cmake-gui
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release")
endif ()

# Define project name
project (subscription-manager)

# Try to find Python interpreter
find_package (PythonInterp REQUIRED)

# Try to find pkg_config
find_package (PkgConfig REQUIRED)

# Try to find following development libraries: Python, OpenSSL to be able
# to build compiled module "certificate.so"
find_package (PythonLibs REQUIRED)

# Set output directory for binaries
set (EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin/)

# Set up required subdirectories
add_subdirectory (src/daemons)
add_subdirectory (src/rhsm_icon)
