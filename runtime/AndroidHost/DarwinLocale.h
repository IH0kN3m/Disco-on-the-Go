// Minimal owned CoreFoundation locale/string handles, populated from Android Locale.
#pragma once
#include <string>
#include <mutex>
#include <cstring>
#include <algorithm>
#include <cstdlib>
#include <cstdint>
namespace DiscoLocale {
struct Object {bool immortal;explicit Object(bool value=false):immortal(value){}virtual ~Object()=default;};
struct String:Object {std::string text;String(std::string value,bool fixed=false):Object(fixed),text(std::move(value)){};};
inline String languageKey{"language",true},countryKey{"country",true},scriptKey{"script",true};
inline String *languageKeyPointer=&languageKey,*countryKeyPointer=&countryKey,*scriptKeyPointer=&scriptKey;
inline std::mutex localeLock;
inline std::string currentTag="en-US";
inline void SetTag(const char* tag){if(!tag||std::strlen(tag)>128)std::abort();for(const char* p=tag;*p;++p)if(!((*p>='a'&&*p<='z')||(*p>='A'&&*p<='Z')||(*p>='0'&&*p<='9')||*p=='-'||*p=='_'))std::abort();std::lock_guard<std::mutex> lock(localeLock);currentTag=tag;}
struct Locale:Object {
    String identifier,language,country,script;
    explicit Locale(const std::string& tag):identifier(tag),language(""),country(""),script(""){
        size_t at=0;unsigned index=0;
        while(at<tag.size()){size_t end=tag.find_first_of("-_",at);if(end==std::string::npos)end=tag.size();std::string part=tag.substr(at,end-at);
            if(index++==0)language.text=part;
            else if(part.size()==4&&script.text.empty())script.text=part;
            else if((part.size()==2||part.size()==3)&&country.text.empty())country.text=part;
            else break;at=end+1;
        }
        std::replace(identifier.text.begin(),identifier.text.end(),'-','_');
        identifier.immortal=language.immortal=country.immortal=script.immortal=true;
    }
};
inline Locale* CopyCurrent(){std::lock_guard<std::mutex> lock(localeLock);return new Locale(currentTag);}
inline String* Identifier(Locale* locale){return &locale->identifier;}
inline String* Value(Locale* locale,String* key){if(key==&languageKey)return &locale->language;if(key==&countryKey)return locale->country.text.empty()?nullptr:&locale->country;if(key==&scriptKey)return locale->script.text.empty()?nullptr:&locale->script;std::abort();}
inline void Release(Object* object){if(object&&!object->immortal)delete object;}
inline intptr_t Length(String* value){return value->text.size();}
inline intptr_t MaxSize(intptr_t count,uint32_t encoding){if(count<0||count>INTPTR_MAX/3)return -1;if(encoding!=0x08000100&&encoding!=0x0600&&encoding!=0)std::abort();return encoding==0x08000100?count*3:count;}
inline bool CString(String* value,char* out,intptr_t capacity,uint32_t encoding){MaxSize(value->text.size(),encoding);if(!out||capacity<=intptr_t(value->text.size()))return false;std::memcpy(out,value->text.c_str(),value->text.size()+1);return true;}
struct Range {intptr_t location,length;};
inline intptr_t Bytes(String* value,Range range,uint32_t encoding,uint8_t,bool,uint8_t* buffer,intptr_t capacity,intptr_t* used){
    MaxSize(value->text.size(),encoding);if(range.location<0||range.length<0||size_t(range.location)>value->text.size()||size_t(range.length)>value->text.size()-range.location||capacity<0)std::abort();
    intptr_t n=buffer?std::min(range.length,capacity):range.length;if(buffer)std::memcpy(buffer,value->text.data()+range.location,n);if(used)*used=n;return n;
}
}
