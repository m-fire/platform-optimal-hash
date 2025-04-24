plugins {
    alias(libs.plugins.kotlinMultiplatform)
}

group = "io.stormi.support.platform.collection.hash"
version = "0.0.1"

val binaryFilename: String by properties

kotlin {
    applyDefaultHierarchyTemplate()

    // 네이티브 라이브러리 배포를 위한 64-bit Platform Targets
    listOf(
        // Android OS Targets (Intel & Apple Silicon)
        androidNativeX64(),
        androidNativeArm64(),
        // macOS Targets (Intel & Apple Silicon)
        macosX64(),
        macosArm64(),
        // iOS & iPadOS Targets (Device & Simulators)
        iosX64(), // iPadOS는 iOS 와 동일하게 처리
        iosArm64(),
        linuxX64(),
        mingwX64("windowsX64"),
    ).apply {
        forEach { target ->
            // 빌드 후 생성될 플렛폼 별 라이브러리 파일명
            target.binaries { sharedLib { baseName = binaryFilename } }
        }
    }

    sourceSets {
        // common source sets
        val commonMain by getting {
            dependencies {
                // put current sets dependencies here
            }
        }
        val commonTest by getting {
            dependencies {
                // KMP Kotest 필수 의존성(
                implementation(libs.kotlin.test)
                // 아직 KMP 에서 Kotest 미지원
                // implementation(libs.kotest.framework.engine)
                // implementation(libs.kotest.assertions.core)
                // implementation(libs.kotest.property)
            }
        }

        // native source sets
        val nativeMain by getting { dependencies { } }
        val nativeTest by getting { dependencies { } }

        // platform-specific source sets
        // val androidNativeX64Main by getting { dependencies { } }
        // val androidNativeX64Test by getting { dependencies { } }
        // val androidNativeArm64Main by getting { dependencies { } }
        // val androidNativeArm64Test by getting { dependencies { } }
        // val iosMain by getting { dependencies { } }
        // val iosTest by getting { dependencies { } }
        // val linuxMain by getting { dependencies { } }
        // val linuxTest by getting { dependencies { } }
        // val windowsX64Main by getting { dependencies { } }
        // val windowsX64Test by getting { dependencies { } }
        // val iosX64Main by getting { dependencies { } }
        // val iosX64Test by getting { dependencies { } }
        // val iosArm64Main by getting { dependencies { } }
        // val iosArm64Test by getting { dependencies { } }
    }
}
