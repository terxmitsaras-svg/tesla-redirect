#include <jni.h>
#include <vector>
#include "price_utils.h"
#include "string_utils.h"

// JNI method names must match: Java_<pkg_underscored>_<Class>_<method>
// Package: gr.posokanei4real.app.utils  Class: NativeUtils

extern "C" {

JNIEXPORT jdouble JNICALL
Java_gr_posokanei4real_app_utils_NativeUtils_parsePrice(
    JNIEnv* env, jobject /*thiz*/, jstring text)
{
    const char* s = env->GetStringUTFChars(text, nullptr);
    double result = posokanei::parsePrice(s ? s : "");
    env->ReleaseStringUTFChars(text, s);
    return result;
}

JNIEXPORT jstring JNICALL
Java_gr_posokanei4real_app_utils_NativeUtils_formatPrice(
    JNIEnv* env, jobject /*thiz*/, jdouble price)
{
    return env->NewStringUTF(posokanei::formatPrice(price).c_str());
}

JNIEXPORT jint JNICALL
Java_gr_posokanei4real_app_utils_NativeUtils_findCheapestIndex(
    JNIEnv* env, jobject /*thiz*/, jdoubleArray prices)
{
    jsize len = env->GetArrayLength(prices);
    if (len == 0) return -1;
    std::vector<double> vec(static_cast<std::size_t>(len));
    env->GetDoubleArrayRegion(prices, 0, len, vec.data());
    return posokanei::findCheapestIndex(vec);
}

JNIEXPORT jstring JNICALL
Java_gr_posokanei4real_app_utils_NativeUtils_normalizeGreek(
    JNIEnv* env, jobject /*thiz*/, jstring text)
{
    const char* s = env->GetStringUTFChars(text, nullptr);
    std::string result = posokanei::normalizeGreek(s ? s : "");
    env->ReleaseStringUTFChars(text, s);
    return env->NewStringUTF(result.c_str());
}

JNIEXPORT jboolean JNICALL
Java_gr_posokanei4real_app_utils_NativeUtils_containsNormalized(
    JNIEnv* env, jobject /*thiz*/, jstring haystack, jstring needle)
{
    const char* h = env->GetStringUTFChars(haystack, nullptr);
    const char* n = env->GetStringUTFChars(needle,   nullptr);
    bool result = posokanei::containsNormalized(h ? h : "", n ? n : "");
    env->ReleaseStringUTFChars(haystack, h);
    env->ReleaseStringUTFChars(needle,   n);
    return result ? JNI_TRUE : JNI_FALSE;
}

} // extern "C"
