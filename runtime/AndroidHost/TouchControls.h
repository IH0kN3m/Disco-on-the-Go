// Original Android pinch adapter using the pinned game's camera API.
#pragma once
#include "TouchQueue.h"
#include "TouchControlPolicy.h"
namespace DiscoAndroidTouch {
using namespace DiscoSceneResidency;
using DiscoGameDisplay::Method;
static std::mutex queueLock;
static Queue queue;
static DiscoTouch::Pinch pinch;
static uint32_t cameraHandle=0;
static std::atomic<bool> highlightAllowed{false};
static std::atomic<bool> highlightRequested{false};
static bool highlightOwned=false;
static int firstPointer=0,secondPointer=0;
static Il2CppClass* CameraClass(){return Class("Assembly-CSharp.dll","FortressOccident","CameraController");}
static Il2CppObject* Camera(){return Call(Method(CameraClass(),"get_Current",0,0xaeb8ac),nullptr,nullptr);}
static float Float(Il2CppObject* result) {
    if(!result||il2cpp_type_get_type(il2cpp_class_get_type(il2cpp_object_get_class(result)))!=IL2CPP_TYPE_R4)Fail("zoom result layout");
    float value=*static_cast<float*>(il2cpp_object_unbox(result));if(!std::isfinite(value))Fail("nonfinite zoom");return value;
}
static void Cancel(){highlightAllowed=false;highlightRequested=false;pinch.Cancel();if(cameraHandle){il2cpp_gchandle_free(cameraHandle);cameraHandle=0;}}
static void ApplyHighlight(){
    bool down=highlightRequested.load()&&highlightAllowed.load();
    if(!down&&!highlightOwned)return;
    auto* manager=Class("Assembly-CSharp.dll","","CrossPlatformInputManager");
    auto* singletonField=il2cpp_class_get_field_from_name(manager,"mCPIM");
    if(!singletonField||!(il2cpp_field_get_flags(singletonField)&0x10))Fail("touch input singleton ABI");
    Il2CppObject* singleton=nullptr;il2cpp_field_static_get_value(singletonField,&singleton);if(!singleton)return;
    auto* actionsField=il2cpp_class_get_field_from_name(manager,"InputActions");if(!actionsField)Fail("touch actions field missing");
    Il2CppObject* actions=nullptr;il2cpp_field_get_value(singleton,actionsField,&actions);if(!actions)return;
    auto* highlightField=il2cpp_class_get_field_from_name(il2cpp_object_get_class(actions),"Highlight");if(!highlightField)Fail("touch highlight action missing");
    Il2CppObject* control=nullptr;il2cpp_field_get_value(actions,highlightField,&control);if(!control)return;
    auto* input=Class("InControl.dll","InControl","InputManager");
    auto* tickResult=Call(Method(input,"get_CurrentTick",0,0x1a53c6c),nullptr,nullptr);
    if(!tickResult||il2cpp_type_get_type(il2cpp_class_get_type(il2cpp_object_get_class(tickResult)))!=IL2CPP_TYPE_U8)Fail("touch update tick ABI");
    uint64_t tick=*static_cast<uint64_t*>(il2cpp_object_unbox(tickResult));
    float value=down?1:0,delta=DiscoStencil::Icall<float(*)()>("UnityEngine.Time::get_unscaledDeltaTime")();
    void* args[]={&value,&tick,&delta};
    Call(Method(Class("InControl.dll","InControl","OneAxisInputControl"),"CommitWithValue",3,0x1b57af8,false),control,args);
    if(down!=highlightOwned){
        bool pressed=Boolean(Call(Method(Class("InControl.dll","InControl","OneAxisInputControl"),"get_IsPressed",0,0x1b57e28,false),control,nullptr));
        DiscoSceneResidency::Log("Android touch Highlight action down=%d pressed=%d field=%x\n",down,pressed,il2cpp_field_get_offset(highlightField));
    }
    highlightOwned=down;
}
static bool Eligible(Il2CppObject* camera) {
    if(!camera||!DiscoStencil::Alive(camera))return false;
    auto* world=Class("Assembly-CSharp.dll","","World");
    return Boolean(Call(Method(world,"get_RunningOrCollage",0,0x665e40),nullptr,nullptr))&&
        !Boolean(Call(Method(world,"get_CollageMode",0,0x659fa0),nullptr,nullptr))&&
        !Boolean(Call(Method(CameraClass(),"get_IsLocked",0,0xaec6a0,false),camera,nullptr));
    // CameraController.Update gates native zoom on world state and locks.
    // IsSlaved is a following mode, not a zoom prohibition.
}
static bool OverUI(const Event& event) {
    auto* events=Class("UnityEngine.UI.dll","UnityEngine.EventSystems","EventSystem");
    auto* current=Call(events,"get_current",0,nullptr,nullptr);if(!current)return false;
    // Unity's cached pointer state can still describe the menu tap before
    // ACTION_CANCEL. Raycast the current finger positions instead.
    auto* dataClass=Class("UnityEngine.UI.dll","UnityEngine.EventSystems","PointerEventData");
    auto* raycast=il2cpp_class_get_method_from_name(events,"RaycastAll",2);if(!raycast)Fail("UI raycast method missing");
    auto* listClass=il2cpp_class_from_type(il2cpp_method_get_param(raycast,1));
    auto* list=il2cpp_object_new(listClass);Call(listClass,".ctor",0,list,nullptr);
    auto* data=il2cpp_object_new(dataClass);void* eventArgs[]={current};Call(dataClass,".ctor",1,data,eventArgs);
    auto* screen=Class("UnityEngine.CoreModule.dll","UnityEngine","Screen");
    float width=float(Integer(Call(screen,"get_width",0,nullptr,nullptr))),height=float(Integer(Call(screen,"get_height",0,nullptr,nullptr)));
    for(auto point:{std::pair<float,float>{event.x1,event.y1},{event.x2,event.y2}}){
        struct Position {float x,y;} position{point.first*width,(1-point.second)*height};void* positionArgs[]={&position};
        Call(dataClass,"set_position",1,data,positionArgs);Call(listClass,"Clear",0,list,nullptr);
        void* args[]={data,list};Call(raycast,current,args);
        if(Integer(Call(listClass,"get_Count",0,list,nullptr))>0)return true;
    }
    return false;
}
static void Enqueue(Event event){std::lock_guard<std::mutex> guard(queueLock);queue.Push(event);}
static void Tick() {
    std::array<Event,32> events;size_t count;
    {std::lock_guard<std::mutex> guard(queueLock);count=queue.Drain(events);}
    if(cameraHandle){auto* camera=Camera();if(camera!=il2cpp_gchandle_get_target(cameraHandle)||!Eligible(camera))Cancel();}
    for(size_t i=0;i<count;++i){
        const auto& event=events[i];if(!event.phase){Cancel();continue;}
        auto* camera=Camera();
        if(event.phase==1){
            Cancel();
            bool eligible=Eligible(camera),overUI=eligible&&OverUI(event);
            static unsigned reports=0;if(reports++<32){
                auto* world=Class("Assembly-CSharp.dll","","World");
                DiscoSceneResidency::Log("Android gesture begin eligible=%d overUI=%d running=%d collage=%d camera=%d locked=%d slaved=%d\n",eligible,overUI,
                    Boolean(Call(Method(world,"get_RunningOrCollage",0,0x665e40),nullptr,nullptr)),
                    Boolean(Call(Method(world,"get_CollageMode",0,0x659fa0),nullptr,nullptr)),camera!=nullptr,
                    camera?Boolean(Call(Method(CameraClass(),"get_IsLocked",0,0xaec6a0,false),camera,nullptr)):0,
                    camera?Boolean(Call(Method(CameraClass(),"get_IsSlaved",0,0xaec6f4,false),camera,nullptr)):0);
            }
            if(pinch.Begin(uintptr_t(camera),eligible&&!overUI,event.scale)){
                cameraHandle=il2cpp_gchandle_new(camera,false);DiscoSceneResidency::Log("Android pinch acquired camera\n");
                firstPointer=event.first;secondPointer=event.second;highlightAllowed=true;
            }
        }
    }
}
}
