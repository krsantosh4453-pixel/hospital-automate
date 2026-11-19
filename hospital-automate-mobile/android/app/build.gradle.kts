import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Release builds are signed with the hospital's upload key, read from
// android/key.properties (git-ignored, never committed):
//     storeFile=/secure/path/upload-keystore.jks
//     storePassword=...
//     keyAlias=upload
//     keyPassword=...
// Without it a release build stops. Debug signing must be asked for
// explicitly, for local testing only and never for distribution:
//     ORG_GRADLE_PROJECT_hmsAllowDebugReleaseSigning=true flutter build apk --release ...
val keystoreProperties = Properties().apply {
    val file = rootProject.file("key.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}
val hasUploadKey = keystoreProperties.getProperty("storeFile") != null
val allowDebugReleaseSigning = findProperty("hmsAllowDebugReleaseSigning") == "true"

android {
    namespace = "com.hospitalautomate.hms_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.hospitalautomate.hms_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (hasUploadKey) {
            create("release") {
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // R8: shrink, optimise and obfuscate the Java/Kotlin layer and drop
            // unused resources. Dart code is obfuscated separately with
            // `flutter build apk --obfuscate --split-debug-info=<dir>` (keep the
            // symbols dir private; it de-obfuscates crash stack traces).
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig = when {
                hasUploadKey -> signingConfigs.getByName("release")
                allowDebugReleaseSigning -> signingConfigs.getByName("debug")
                else -> null
            }
        }
    }
}

// A release build never falls back to the public debug key silently.
gradle.taskGraph.whenReady {
    val buildsRelease = allTasks.any { it.project == project && it.name.contains("Release") }
    if (buildsRelease && !hasUploadKey && !allowDebugReleaseSigning) {
        throw GradleException(
            "Release signing: create android/key.properties (see build.gradle.kts), or set " +
                "ORG_GRADLE_PROJECT_hmsAllowDebugReleaseSigning=true for a local test build only.",
        )
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
