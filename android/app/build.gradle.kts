plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
    alias(libs.plugins.google.services)
}

android {
    namespace = "gr.posokanei4real.app"
    compileSdk = 35
    ndkVersion = "26.3.11579264" // LTS NDK; install via SDK Manager → NDK (Side by side)

    defaultConfig {
        applicationId = "gr.posokanei4real.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }

        ndk {
            // arm64-v8a: modern phones; x86_64: emulator/Chrome OS
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
        externalNativeBuild {
            cmake {
                cppFlags += "-std=c++17"
                arguments += listOf(
                    "-DANDROID_STL=c++_shared",
                    "-DBUILD_NATIVE_TESTS=OFF", // tests run via nativeTestHost / deviceNativeTest
                )
            }
        }
    }

    externalNativeBuild {
        cmake {
            path = file("CMakeLists.txt")
            version = "3.22.1"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions { jvmTarget = "17" }

    buildFeatures { compose = true }

    packaging {
        resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons)
    implementation(libs.androidx.navigation.compose)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.hilt.navigation.compose)

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.firestore)
    implementation(libs.firebase.analytics)

    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)

    implementation(libs.coil.compose)
    implementation(libs.kotlinx.coroutines.android)

    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)
}

// ═══════════════════════════════════════════════════════════════════════════
// Native C++ / GoogleTest tasks
// ═══════════════════════════════════════════════════════════════════════════

// Resolve the cmake binary: prefer the version bundled in the Android SDK so
// the build is hermetic, then fall back to whatever is on PATH.
fun findCmake(): String {
    val sdkDir = android.sdkDirectory
    listOf("3.22.1", "3.22.0", "3.18.1").forEach { v ->
        val f = File(sdkDir, "cmake/$v/bin/cmake")
        if (f.exists()) return f.absolutePath
    }
    return findProperty("cmake.bin")?.toString() ?: "cmake"
}

val nativeHostBuildDir = layout.buildDirectory.dir("native-test-host")

// ── Host-side tests (no device needed) ───────────────────────────────────
//
//   ./gradlew :app:nativeTestHost
//
// GoogleTest is downloaded by CMake's FetchContent on first run (~10 MB).
// Subsequent runs reuse the CMake cache; the download is skipped.

tasks.register("configureNativeTestHost") {
    group = "verification"
    description = "Configure GoogleTest CMake build for the host platform"
    doLast {
        nativeHostBuildDir.get().asFile.mkdirs()
        exec {
            commandLine(
                findCmake(),
                "-S", projectDir.absolutePath,
                "-B", nativeHostBuildDir.get().asFile.absolutePath,
                "-DCMAKE_BUILD_TYPE=Debug",
                "-DBUILD_NATIVE_TESTS=ON",
            )
        }
    }
}

tasks.register("buildNativeTestHost") {
    group = "verification"
    description = "Compile the native unit-test binary for the host"
    dependsOn("configureNativeTestHost")
    doLast {
        exec {
            commandLine(
                findCmake(),
                "--build", nativeHostBuildDir.get().asFile.absolutePath,
                "--config", "Debug",
                "--parallel",
            )
        }
    }
}

tasks.register("nativeTestHost") {
    group = "verification"
    description = "Run native C++ unit tests on the host (no device or emulator needed)"
    dependsOn("buildNativeTestHost")
    doLast {
        exec {
            workingDir(nativeHostBuildDir.get().asFile)
            commandLine("ctest", "--output-on-failure", "--parallel", "4", "-C", "Debug")
        }
    }
}

// ── Device-side tests (requires a connected device or running emulator) ───
//
//   ./gradlew :app:deviceNativeTest
//   ./gradlew :app:deviceNativeTest -PtestAbi=x86_64        (emulator)
//
// The test binary is built for the target ABI with BUILD_NATIVE_TESTS=ON,
// pushed to /data/local/tmp/, executed via adb shell, and the XML results
// are pulled back to build/native-test-results/.

tasks.register("deviceNativeTest") {
    group = "verification"
    description = "Build + run native C++ tests on a connected Android device via ADB"
    doLast {
        val abi      = findProperty("testAbi")?.toString() ?: "arm64-v8a"
        val buildDir = layout.buildDirectory.dir("native-test-device/$abi").get().asFile
        buildDir.mkdirs()

        val cmake    = findCmake()
        val ndkDir   = android.ndkDirectory.absolutePath
        val toolchain = "$ndkDir/build/cmake/android.toolchain.cmake"

        // Configure for the Android target ABI
        exec {
            commandLine(
                cmake,
                "-S", projectDir.absolutePath,
                "-B", buildDir.absolutePath,
                "-DCMAKE_TOOLCHAIN_FILE=$toolchain",
                "-DANDROID_ABI=$abi",
                "-DANDROID_PLATFORM=android-26",
                "-DANDROID_STL=c++_shared",
                "-DCMAKE_BUILD_TYPE=Debug",
                "-DBUILD_NATIVE_TESTS=ON",
            )
        }

        exec {
            commandLine(cmake, "--build", buildDir.absolutePath, "--parallel")
        }

        val binary     = File(buildDir, "posokanei_native_tests")
        val resultsDir = layout.buildDirectory.dir("native-test-results").get().asFile
        resultsDir.mkdirs()
        val xmlDest    = File(resultsDir, "device_${abi}_results.xml")
        val remoteBin  = "/data/local/tmp/posokanei_native_tests"
        val remoteXml  = "/data/local/tmp/native_test_results.xml"

        exec { commandLine("adb", "push", binary.absolutePath, remoteBin) }
        exec { commandLine("adb", "shell", "chmod", "+x", remoteBin) }
        exec { commandLine("adb", "shell", remoteBin, "--gtest_output=xml:$remoteXml") }
        exec { commandLine("adb", "pull", remoteXml, xmlDest.absolutePath) }

        logger.lifecycle("Device native test results → ${xmlDest.absolutePath}")
    }
}
