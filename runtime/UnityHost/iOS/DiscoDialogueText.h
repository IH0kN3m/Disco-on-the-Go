// Original iPad adapter to the game's dialogue-only size configuration.
// Install before the first player frame; later settings and new lines use the
// same original sizing, paragraph splitting and scroll-restoration paths.
#pragma once
#include "DialogueTextPolicy.h"
namespace DiscoDialogueText {
static void Install() {
    using namespace DiscoSceneResidency;
    static bool installed=false;
    if (installed) return;
    if (![NSThread isMainThread]) Fail("dialogue sizing is not on Unity thread");
    auto* config=DiscoSceneResidency::Class("Assembly-CSharp.dll","","TextSizeConfiguration");
    il2cpp_runtime_class_init(config);
    auto* presetsField=Field(config,"fontSizes",0x18);
    auto* currentField=Field(config,"curSize",0);
    if (!(il2cpp_field_get_flags(presetsField)&0x10) ||
        !(il2cpp_field_get_flags(currentField)&0x10) ||
        il2cpp_type_get_type(il2cpp_field_get_type(currentField))!=IL2CPP_TYPE_I4)
        Fail("dialogue size configuration ABI");
    Il2CppArray* presets=nullptr;
    il2cpp_field_static_get_value(presetsField,&presets);
    auto* arrayClass=presets?il2cpp_object_get_class((Il2CppObject*)presets):nullptr;
    auto* element=arrayClass?il2cpp_class_get_element_class(arrayClass):nullptr;
    if (!arrayClass || il2cpp_class_get_rank(arrayClass)!=1 || il2cpp_array_length(presets)!=4 ||
        !element || il2cpp_type_get_type(il2cpp_class_get_type(element))!=IL2CPP_TYPE_I4 ||
        il2cpp_array_element_size(arrayClass)!=sizeof(int32_t)) Fail("dialogue preset array ABI");
    int32_t source[4], enlarged[4], current=0;
    auto* values=((Il2CppArraySize*)presets)->vector;
    std::memcpy(source,values,sizeof(source));
    if (!DiscoDialogue::LargerPresets(source,4,enlarged)) Fail("unsupported dialogue presets");
    il2cpp_field_static_get_value(currentField,&current);
    int selected=-1;
    for (int i=0;i<4;++i) if (source[i]==current) selected=i;
    if (current!=0 && selected<0) Fail("unsupported current dialogue size");
    // Primitive array contents need no managed write barrier. No game or asset
    // file is changed, and the user's selected setting is retained.
    std::memcpy(values,enlarged,sizeof(enlarged));
    if (selected>=0) {
        current=enlarged[selected];
        il2cpp_field_static_set_value(currentField,&current);
    }
    installed=true;
    Log("NATIVE DIALOGUE: presets increased by 12.5%%; current=%d initialized=%d\n",current,selected>=0);
}
}
