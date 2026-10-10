#include <cstdint>
extern "C" void* DiscoTextPopulateTarget;
extern "C" int DiscoTextPopulateTestCaller(uint32_t*);
static int Check(uintptr_t a,uintptr_t b,uintptr_t c,uintptr_t d,int e,float f,float g,int h,
                 bool i,bool j,int k,int l,int m,int n,bool o,int p,float q,float r,float s,float t,
                 bool u,bool v,uint32_t* error){
    bool valid=a==1&&b==2&&c==3&&d==4&&e==5&&f==1&&g==2&&h==6&&i&&!j&&
        k==7&&l==8&&m==9&&n==10&&o&&p==11&&q==3&&r==4&&s==5&&t==6&&!u&&v;
    if(valid)*error=0x12345678;
    return valid?1:0;
}
bool DiscoIcallSelfTest(){
    uint32_t values[]={0x76543210,0,0x87654321};
    DiscoTextPopulateTarget=reinterpret_cast<void*>(&Check);
    int result=DiscoTextPopulateTestCaller(values+1);DiscoTextPopulateTarget=nullptr;
    return result==1&&values[0]==0x76543210&&values[1]==0x12345678&&values[2]==0x87654321;
}
