#pragma once
// Observe the original startup coroutine without changing its decisions.
namespace DiscoStartup {
using namespace DiscoSceneResidency;
static MoveNext original;
static FieldInfo *state,*ownerField,*timer,*complete;
static bool Next(Il2CppObject* coroutine,const MethodInfo* method){
    int before=-1;il2cpp_field_get_value(coroutine,state,&before);
    bool result=original(coroutine,method);
    static time_t previous=0;time_t now=std::time(nullptr);
    if(now!=previous||!result){previous=now;int after=-1;il2cpp_field_get_value(coroutine,state,&after);
        auto* owner=Read(coroutine,ownerField);float elapsed=0;bool ready=false;
        il2cpp_field_get_value(owner,timer,&elapsed);il2cpp_field_get_value(owner,complete,&ready);
        __android_log_print(ANDROID_LOG_INFO,"DiscoUnity","Startup coroutine state=%d -> %d running=%d elapsed=%g ready=%d",before,after,int(result),double(elapsed),int(ready));
    }
    return result;
}
static void Install(){
    auto* klass=Class("Assembly-CSharp.dll","","PreInitialize");
    auto* coroutine=Nested(klass,"<WaitAndStartTheGame>d__13");
    state=Field(coroutine,"<>1__state",0x10);ownerField=Field(coroutine,"<>4__this",0x20);
    timer=Field(klass,"timeCounter",0x30);complete=Field(klass,"loadGamesComplete",0x35);
    auto* method=ValidateHook(coroutine,0x2247448);InstallHook(coroutine,method,Next,&original);
}
}
