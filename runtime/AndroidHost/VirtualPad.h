// Original overlay input delivered through the game's existing InControl API.
#pragma once
#include "VirtualPadState.h"
namespace DiscoAndroidPad {
using namespace DiscoSceneResidency;
using DiscoGameDisplay::Method;
static std::mutex lock;
static State state;
static Snapshot frame;
static uint32_t deviceHandle=0,delegateHandle=0;
static int controls[13];
static bool attached=false;
static Il2CppClass* Manager(){return Class("InControl.dll","InControl","InputManager");}
static Il2CppClass* DeviceClass(){return Class("InControl.dll","InControl","InputDevice");}
static int Enum(const char* type,const char* name){
    auto* klass=Class("InControl.dll","InControl",type);il2cpp_runtime_class_init(klass);
    auto* field=il2cpp_class_get_field_from_name(klass,name);int value=-1;
    if(!field||il2cpp_type_get_type(il2cpp_class_enum_basetype(klass))!=IL2CPP_TYPE_I4)Fail("pad enum ABI");
    il2cpp_field_static_get_value(field,&value);return value;
}
static void Update(uint64_t tick,float delta,const MethodInfo*) {
    if(!attached)return;
    static unsigned reports=0;if(reports++<4)DiscoSceneResidency::Log("Android virtual gamepad tick=%llu buttons=%x left=%.2f,%.2f\n",(unsigned long long)tick,frame.buttons,frame.axes[0],frame.axes[1]);
    auto* device=il2cpp_gchandle_get_target(deviceHandle);
    for(unsigned i=0;i<13;++i){float value=(frame.buttons&(1u<<i))?1:0;void* args[]={&controls[i],&value,&tick,&delta};
        Call(Method(DeviceClass(),"UpdateWithValue",4,0x1801c70,false),device,args);}
    struct Vector{float x,y;};
    for(int i=0;i<2;++i){Vector value{frame.axes[i*2],frame.axes[i*2+1]};void* args[]={&value,&tick,&delta};
        Call(Method(DeviceClass(),i?"UpdateRightStickWithValue":"UpdateLeftStickWithValue",3,i?0x180251c:0x1801d3c,false),device,args);}
}
static void* Invoke(Il2CppMethodPointer, const MethodInfo* method,void*,void** args){
    Update(*static_cast<uint64_t*>(args[0]),*static_cast<float*>(args[1]),method);return nullptr;
}
static void Create() {
    auto* device=il2cpp_object_new(DeviceClass());deviceHandle=il2cpp_gchandle_new(device,false);
    auto* name=il2cpp_string_new("Disco Touch Xbox Gamepad");void* args[]={name};
    Call(Method(DeviceClass(),".ctor",1,0x1800cf0,false),device,args);
    int kind=Enum("InputDeviceClass","Controller"),style=Enum("InputDeviceStyle","XboxOne");
    void* classArgs[]={&kind};Call(Method(DeviceClass(),"set_DeviceClass",1,0x1800bc4,false),device,classArgs);
    void* styleArgs[]={&style};Call(Method(DeviceClass(),"set_DeviceStyle",1,0x1800bd4,false),device,styleArgs);
    const char* names[]={"Action1","Action2","Action3","Action4","LeftBumper","RightBumper","LeftTrigger","RightTrigger","Menu","DPadUp","DPadDown","DPadLeft","DPadRight"};
    for(unsigned i=0;i<13;++i){controls[i]=Enum("InputControlType",names[i]);}
    for(const char* control:{"Action1","Action2","Action3","Action4","LeftBumper","RightBumper","LeftTrigger","RightTrigger","Menu","DPadUp","DPadDown","DPadLeft","DPadRight","LeftStickUp","LeftStickDown","LeftStickLeft","LeftStickRight","RightStickUp","RightStickDown","RightStickLeft","RightStickRight"}){
        int target=Enum("InputControlType",control);auto* label=il2cpp_string_new(control);void* controlArgs[]={&target,label};
        Call(Method(DeviceClass(),"AddControl",2,0x1801268,false),device,controlArgs);
    }
    auto* field=il2cpp_class_get_field_from_name(Manager(),"OnUpdateDevices");if(!field)Fail("pad update event missing");
    auto* delegateClass=il2cpp_class_from_type(il2cpp_field_get_type(field));
    auto* invoke=il2cpp_class_get_method_from_name(delegateClass,"Invoke",2);
    if(!invoke||il2cpp_type_get_type(il2cpp_method_get_param(invoke,0))!=IL2CPP_TYPE_U8||il2cpp_type_get_type(il2cpp_method_get_param(invoke,1))!=IL2CPP_TYPE_R4)Fail("pad update delegate signature");
    auto* callback=reinterpret_cast<Il2CppDelegate*>(il2cpp_object_new(delegateClass));
    static MethodInfo method;method=*invoke;method.name="DiscoAndroidPadUpdate";method.methodPointer=reinterpret_cast<Il2CppMethodPointer>(&Update);
    method.invoker_method=&Invoke;method.flags=0x16;method.is_marshaled_from_native=true;
    callback->method_ptr=method.methodPointer;callback->method=&method;callback->invoke_impl=&Invoke;
    delegateHandle=il2cpp_gchandle_new(reinterpret_cast<Il2CppObject*>(callback),false);
    void* callbackArgs[]={callback};Call(Method(Manager(),"add_OnUpdateDevices",1,0x1a4f2ac),nullptr,callbackArgs);
    DiscoSceneResidency::Log("Android virtual gamepad update callback installed\n");
}
static void Prepare() {
    {std::lock_guard<std::mutex> guard(lock);frame=state.Take();}
    if(!Boolean(Call(Method(Manager(),"get_IsSetup",0,0x1a4f8ac),nullptr,nullptr)))return;
    if(frame.enabled&&!deviceHandle)Create();
    if(!deviceHandle)return;
    auto* device=il2cpp_gchandle_get_target(deviceHandle);void* args[]={device};
    if(frame.enabled&&!attached){Call(Method(Manager(),"AttachDevice",1,0x1a52028),nullptr,args);attached=true;DiscoSceneResidency::Log("Android virtual gamepad attached\n");}
    if(!frame.enabled&&attached){Call(Method(DeviceClass(),"ClearInputState",0,0x1801ab4,false),device,nullptr);Call(Method(Manager(),"DetachDevice",1,0x1a52338),nullptr,args);attached=false;DiscoSceneResidency::Log("Android virtual gamepad detached\n");}
}
}
