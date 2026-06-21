cmake_minimum_required(VERSION 3.22.1)
project(posokanei_native VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_NATIVE_TESTS "Build GoogleTest unit tests" OFF)

# ── Core logic library (no JNI, no Android deps — links into both the
#    Android shared lib and the host/device test binary) ──────────────────
set(CORE_SOURCES
    src/main/cpp/price_utils.cpp
    src/main/cpp/string_utils.cpp
)

add_library(posokanei_core STATIC ${CORE_SOURCES})
target_include_directories(posokanei_core PUBLIC src/main/cpp)
target_compile_options(posokanei_core PRIVATE -Wall -Wextra -Wpedantic)

# ── Android shared library (JNI bridge, loaded by System.loadLibrary) ────
if(ANDROID)
    add_library(posokanei SHARED src/main/cpp/jni_bridge.cpp)
    target_include_directories(posokanei PRIVATE src/main/cpp)
    find_library(log-lib log)
    target_link_libraries(posokanei PRIVATE posokanei_core ${log-lib} android)
endif()

# ── GoogleTest (fetched at configure time, only when tests requested) ─────
if(BUILD_NATIVE_TESTS)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        URL      https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz
        URL_HASH SHA256=8ad598c73ad796e0d8280b082cebd82a630d73e73cd3c70057938a6501bba5d7
    )
    set(gtest_force_shared_crt ON  CACHE BOOL "" FORCE)
    set(INSTALL_GTEST           OFF CACHE BOOL "" FORCE)
    set(BUILD_GMOCK             OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    add_executable(posokanei_native_tests
        src/test_native/cpp/price_utils_test.cpp
        src/test_native/cpp/string_utils_test.cpp
    )
    target_link_libraries(posokanei_native_tests
        PRIVATE posokanei_core GTest::gtest_main
    )

    if(ANDROID)
        find_library(log-lib log)
        target_link_libraries(posokanei_native_tests PRIVATE ${log-lib} android)
    endif()

    include(GoogleTest)
    gtest_discover_tests(posokanei_native_tests)
endif()
