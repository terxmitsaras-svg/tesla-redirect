-keep class gr.posokanei4real.app.data.model.** { *; }
# Keep JNI class so R8 does not strip the native method declarations
-keep class gr.posokanei4real.app.utils.NativeUtils { *; }
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn com.google.firebase.**
