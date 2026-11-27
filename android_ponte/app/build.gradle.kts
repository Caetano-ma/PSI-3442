plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val versaoMsdk = "5.20.1"
val djiApiKey: String = (project.findProperty("DJI_API_KEY") as String?) ?: "SEM_APP_KEY"

android {
    namespace = "br.usp.psi3442.ponte"
    compileSdk = 35

    defaultConfig {
        applicationId = "br.usp.psi3442.ponte"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1"
    }

    flavorDimensions += "drone"
    productFlavors {
        create("emulador") {
            dimension = "drone"
            applicationIdSuffix = ".emulador"
            versionNameSuffix = "-emulador"
        }
        create("celular") {
            dimension = "drone"
            ndk { abiFilters += "arm64-v8a" }
            manifestPlaceholders["DJI_API_KEY"] = djiApiKey
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    packaging {
        jniLibs {
            useLegacyPackaging = true
            pickFirsts += listOf("lib/arm64-v8a/libc++_shared.so", "lib/armeabi-v7a/libc++_shared.so")
            keepDebugSymbols += listOf("*/arm64-v8a/*.so")
        }
    }

    testOptions { unitTests.isReturnDefaultValues = true }
}

dependencies {
    "celularImplementation"("com.dji:dji-sdk-v5-aircraft:$versaoMsdk")
    "celularCompileOnly"("com.dji:dji-sdk-v5-aircraft-provided:$versaoMsdk")
    "celularRuntimeOnly"("com.dji:dji-sdk-v5-networkImp:$versaoMsdk")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
