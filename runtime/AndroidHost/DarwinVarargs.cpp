// Original formatting adapter for Darwin ARM64's stack-based variadic arguments.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <string>
#include <algorithm>
#include <cctype>
#ifdef __ANDROID__
#include <android/log.h>
#endif
namespace {
[[noreturn]] void Unsupported(const char* reason){std::fprintf(stderr,"Darwin format unsupported: %s\n",reason);std::abort();}
uint64_t Next(const uint8_t*& args){uint64_t value;std::memcpy(&value,args,8);args+=8;return value;}
template<class T> void Add(std::string& out,const std::string& token,T value){int n=std::snprintf(nullptr,0,token.c_str(),value);if(n<0||size_t(n)+out.size()>1024*1024)Unsupported("conversion length");size_t old=out.size();out.resize(old+n+1);std::snprintf(&out[old],n+1,token.c_str(),value);out.resize(old+n);}
std::string Format(const char* fmt,const uint8_t* args){
    std::string output;
    for(size_t i=0;fmt[i];){if(output.size()>1024*1024)Unsupported("output length");if(fmt[i]!='%'){output+=fmt[i++];continue;}++i;if(fmt[i]=='%'){output+='%';++i;continue;}
        std::string token="%";while(fmt[i]&&std::strchr("-+ #0'",fmt[i]))token+=fmt[i++];
        if(fmt[i]=='*'){int width=static_cast<int>(Next(args));if(width<0){token+='-';if(width==INT32_MIN)Unsupported("width");width=-width;}token+=std::to_string(width);++i;}else while(std::isdigit(static_cast<unsigned char>(fmt[i])))token+=fmt[i++];
        if(fmt[i]=='.'){++i;if(fmt[i]=='*'){int precision=static_cast<int>(Next(args));if(precision>=0)token+='.'+std::to_string(precision);++i;}else{token+='.';while(std::isdigit(static_cast<unsigned char>(fmt[i])))token+=fmt[i++];}}
        std::string length;if(fmt[i]&&std::strchr("hljztL",fmt[i])){length+=fmt[i++];if((length=="h"||length=="l")&&fmt[i]==length[0])length+=fmt[i++];}
        char code=fmt[i++];if(!code)Unsupported("truncated format");
        if(std::strchr("diouxX",code)){token+=length;token+=code;uint64_t v=Next(args);bool sign=code=='d'||code=='i';if(length=="l"||length=="z"||length=="t") {if(sign)Add(output,token,static_cast<long>(v));else Add(output,token,static_cast<unsigned long>(v));}else if(length=="ll"||length=="j"){if(sign)Add(output,token,static_cast<long long>(v));else Add(output,token,static_cast<unsigned long long>(v));}else if(length.empty()||length=="h"||length=="hh"){if(sign)Add(output,token,static_cast<int>(v));else Add(output,token,static_cast<unsigned>(v));}else Unsupported("integer length");}
        else if(std::strchr("fFeEgGaA",code)){if(!length.empty()&&length!="l"&&length!="L")Unsupported("float length");token+=code;uint64_t raw=Next(args);double value;std::memcpy(&value,&raw,8);Add(output,token,value);}
        else if(code=='s'){if(!length.empty())Unsupported("wide string");token+=code;Add(output,token,reinterpret_cast<const char*>(Next(args)));}
        else if(code=='c'){if(!length.empty())Unsupported("wide character");token+=code;Add(output,token,static_cast<int>(Next(args)));}
        else if(code=='p'){token+=code;Add(output,token,reinterpret_cast<void*>(Next(args)));}
        else Unsupported("conversion");
    }return output;
}
}
extern "C" int DiscoSnprintf(char* output,size_t capacity,const char* format,const uint8_t* args){auto text=Format(format,args);if(capacity){size_t n=std::min(capacity-1,text.size());std::memcpy(output,text.data(),n);output[n]=0;}return text.size();}
extern "C" int DiscoSprintf(char* output,const char* format,const uint8_t* args){auto text=Format(format,args);std::memcpy(output,text.c_str(),text.size()+1);return text.size();}
extern "C" int DiscoVfprintf(FILE* stream,const char* format,const uint8_t* args){auto text=Format(format,args);
#ifdef __ANDROID__
__android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","foreign log: %s",text.c_str());
#endif
size_t n=std::fwrite(text.data(),1,text.size(),stream);return n==text.size()?int(n):-1;}
