# R8 rules for the release build (build.gradle.kts: isMinifyEnabled = true).
# The Flutter Gradle plugin adds the engine's own keep rules; plugins ship
# consumer rules in their AARs. Only gaps found in release builds go here.

# flutter_secure_storage uses Google Tink, whose optional annotations are not
# on the runtime classpath.
-dontwarn com.google.errorprone.annotations.**
-dontwarn javax.annotation.**

# Flutter's deferred-components support references Play Core, which this app
# does not ship.
-dontwarn com.google.android.play.core.**

# Readable crash reports: keep line numbers, hide original source file names.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
