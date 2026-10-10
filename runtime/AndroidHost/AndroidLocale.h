#pragma once
#include "DarwinLocale.h"
#include "DarwinFoundation.h"
#include <jni.h>
inline void ConfigureAndroidLocale(JNIEnv* env){
    jclass type=env->FindClass("java/util/Locale");
    jmethodID get=env->GetStaticMethodID(type,"getDefault","()Ljava/util/Locale;");
    jmethodID tag=env->GetMethodID(type,"toLanguageTag","()Ljava/lang/String;");
    jobject locale=env->CallStaticObjectMethod(type,get);
    auto text=static_cast<jstring>(env->CallObjectMethod(locale,tag));
    if(env->ExceptionCheck()||!text)std::abort();
    const char* utf8=env->GetStringUTFChars(text,nullptr);if(!utf8)std::abort();DiscoLocale::SetTag(utf8);
    env->ReleaseStringUTFChars(text,utf8);env->DeleteLocalRef(text);env->DeleteLocalRef(locale);env->DeleteLocalRef(type);
    type=env->FindClass("java/util/TimeZone");get=env->GetStaticMethodID(type,"getDefault","()Ljava/util/TimeZone;");
    tag=env->GetMethodID(type,"getID","()Ljava/lang/String;");locale=env->CallStaticObjectMethod(type,get);text=static_cast<jstring>(env->CallObjectMethod(locale,tag));
    if(env->ExceptionCheck()||!text)std::abort();utf8=env->GetStringUTFChars(text,nullptr);if(!utf8)std::abort();DiscoFoundation::SetZone(utf8);
    env->ReleaseStringUTFChars(text,utf8);env->DeleteLocalRef(text);env->DeleteLocalRef(locale);env->DeleteLocalRef(type);
}
