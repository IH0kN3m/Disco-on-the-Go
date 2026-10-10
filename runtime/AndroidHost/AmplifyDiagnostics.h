#pragma once
namespace DiscoAmplifyDiagnostics {
using namespace DiscoSceneResidency;
static void* capture=nullptr;
static int captureFrame=-1;
static void Capture(Il2CppObject* texture) {
    if(captureFrame!=-1)return;
    auto native=DiscoStencil::Icall<void*(*)(void*)>("UnityEngine.Texture::GetNativeTexturePtr")(texture);
    capture=DiscoAmplifyReadback::Create(native,512,512);
    captureFrame=DiscoStencil::Icall<int(*)()>("UnityEngine.Time::get_frameCount")();
    DiscoAmplifyReadback::Issue(capture);
    DiscoStencil::Icall<void(*)(void*,int)>("UnityEngine.GL::GLIssuePluginEvent")(DiscoAmplifyReadback::Event(),0);
}
static void SaveCapture() {
    if(!capture)return;
    int frame=DiscoStencil::Icall<int(*)()>("UnityEngine.Time::get_frameCount")();
    if(frame<captureFrame+5)return;
    std::vector<uint8_t> pixels(512*512*4);DiscoAmplifyReadback::Pixels(capture,pixels.data());
    auto* file=std::fopen((metadataRoot+"/disco-cache.rgba").c_str(),"wb");
    if(!file||std::fwrite(pixels.data(),1,pixels.size(),file)!=pixels.size())Fail("cache capture file");
    std::fclose(file);DiscoAmplifyReadback::Destroy(capture);capture=nullptr;
    DiscoSceneResidency::Log("Amplify physical-cache crop saved\n");
}
static void Dump(Il2CppObject* object,unsigned depth) {
    if(!object||depth>2)return;
    auto* klass=il2cpp_object_get_class(object);void* cursor=nullptr;
    Log("Amplify diagnostic class=%s depth=%u\n",il2cpp_class_get_name(klass),depth);
    while(auto* field=il2cpp_class_get_fields(klass,&cursor)) {
        if(il2cpp_field_get_flags(field)&0x10)continue;
        const char* name=il2cpp_field_get_name(field);auto* type=il2cpp_field_get_type(field);int kind=il2cpp_type_get_type(type);
        if(kind==IL2CPP_TYPE_I4||kind==IL2CPP_TYPE_U4){int value=0;il2cpp_field_get_value(object,field,&value);Log("Amplify %s=%d\n",name,value);}
        else if(kind==IL2CPP_TYPE_BOOLEAN){bool value=false;il2cpp_field_get_value(object,field,&value);Log("Amplify %s=%d\n",name,int(value));}
        else if(kind==IL2CPP_TYPE_SZARRAY){auto* value=Read(object,field);Log("Amplify %s array=%llu\n",name,value?(unsigned long long)il2cpp_array_length(reinterpret_cast<Il2CppArray*>(value)):0);}
        else if(kind==IL2CPP_TYPE_VALUETYPE){auto* fieldClass=il2cpp_class_from_type(type);uint32_t align=0;
            if(fieldClass&&il2cpp_class_is_enum(fieldClass)&&il2cpp_class_value_size(fieldClass,&align)==4){int value=0;il2cpp_field_get_value(object,field,&value);Log("Amplify %s enum=%d\n",name,value);}}
        else if(kind==IL2CPP_TYPE_CLASS||kind==IL2CPP_TYPE_GENERICINST){
            auto* fieldClass=il2cpp_class_from_type(type);
            if(!fieldClass||il2cpp_class_is_valuetype(fieldClass))continue;
            auto* value=Read(object,field);if(!value)continue;
            Log("Amplify %s object=%s\n",name,il2cpp_class_get_name(il2cpp_object_get_class(value)));
            auto* textures=Class("UnityEngine.CoreModule.dll","UnityEngine","Texture");
            if(il2cpp_class_is_assignable_from(textures,il2cpp_object_get_class(value))&&DiscoStencil::Alive(value)){
                Log("Amplify texture %s %dx%d\n",name,Integer(Call(textures,"get_width",0,value,nullptr)),Integer(Call(textures,"get_height",0,value,nullptr)));
                if(!std::strcmp(name,"m_diffuseCache"))Capture(value);
            }
            if(std::strstr(name,"prePass")||std::strstr(name,"cache")||std::strstr(name,"Cache")||std::strstr(name,"streamer")||std::strstr(name,"Streamer"))Dump(value,depth+1);
        }
    }
}
static void Tick() {
    static unsigned ticks=0;if(++ticks!=45&&ticks!=90)return;
    auto* klass=Class("AmplifyTexture.dll","","AmplifyTextureManager");
    auto* manager=Call(klass,"get_Instance",0,nullptr,nullptr);if(!manager)return;
    Dump(manager,0);
    auto* list=Call(klass,"get_RuntimeList",0,manager,nullptr);if(!list)return;
    auto* listClass=il2cpp_object_get_class(list);int count=Integer(Call(listClass,"get_Count",0,list,nullptr));
    if(count<0||count>64)Fail("Amplify runtime count");
    for(int i=0;i<count;++i){void* args[]={&i};Dump(Call(listClass,"get_Item",1,list,args),0);}
}
}
