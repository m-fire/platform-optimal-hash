plugins {
    alias(libs.plugins.kotlinMultiplatform)
}

val groupPackage: String by properties
val libraryFilename: String by properties
val externalCopyTo: String by properties
val taskCopyReleaseLibBinaries = "copyReleaseLibBinaries"

group = groupPackage
version = "1.0.0"

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
        iosSimulatorArm64(),
        linuxX64(),
        mingwX64("windowsX64"),
    ).apply {
        forEach { target ->
            // 빌드 후 생성될 플렛폼 별 라이브러리 파일명
            target.binaries { sharedLib { baseName = libraryFilename } }
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
        // val iosSimulatorArm64Main by getting { dependencies { } }
        // val iosSimulatorArm64Test by getting { dependencies { } }
    }
}

// build 태스크 완료 후 실행되도록 설정
tasks.named("assemble") {
    finalizedBy(taskCopyReleaseLibBinaries)
}

// --- 네이티브 라이브러리 빌드 결과물(./library/build/bin)을 외부 폴더에 복사  ---
tasks.register<Copy>(taskCopyReleaseLibBinaries) {
    group = "build"
    description = "빌드된 플랫폼별 라이브러리 바이너리 파일을 복사합니다."

    val binaryDir = "bin"
    val copyFrom = layout.buildDirectory.dir(binaryDir).get() // build/bin
    val copyTo = layout.projectDirectory.file("../$externalCopyTo").asFile // library > main > external
    val releasedBinaryDir = "releaseShared" // release 디렉토리만 포함
    val platformReleasedPattern = "**/$releasedBinaryDir/**"
    val excludeExtensions = listOf("**/*.h", "**/*.api.h", "**/*.def")  // 헤더 파일과 정의 파일 제외
    val dot = '.'

    doFirst {
        logger.lifecycle("🚀 Library Binary 복사 시작:")
        logger.lifecycle("$copyFrom")
        if (copyTo.exists()) {
            delete(copyTo)
        }
        copyTo.mkdirs()
    }

    from(copyFrom) // 소스 디렉토리 설정
    includeEmptyDirs = false
    include(platformReleasedPattern) // 특정 패턴 매칭
    exclude(excludeExtensions)
    into(copyTo) // 대상 디렉토리 설정

    // 파일별 경로 및 이름 동적 변경
    eachFile {
        val segments = relativePath.segments // 예: androidNativeArm64/releaseShared/liboptimal_hash.so
        // releaseShared 앞의 폴더명 추출 (플랫폼명)
        val platform =
            segments.getOrNull(segments.indexOf(releasedBinaryDir) - 1)
                ?: return@eachFile // 플랫폼 디렉토리가 없으면 복사하지 않음
        // 결과 경로: dist/플랫폼명/새파일명
        val ext = name.substringAfterLast(dot, "") // 파일명과 확장자 분리
        val copyName = "$libraryFilename$dot$ext"
        relativePath = RelativePath(true, platform, copyName)
        logger.lifecycle("📂 $binaryDir/$platform/$name -> ../$relativePath")
    }

    doLast {
        logger.lifecycle("✅  Library Binary 복사 완료.")
        logger.lifecycle("$copyTo")
    }
}
