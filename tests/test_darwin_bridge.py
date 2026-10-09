from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parent.parent
class DarwinBridgeTests(unittest.TestCase):
    def test_foreign_storage_guards_tls_semaphores_and_string_ownership(self):
        work=ROOT/'artifacts/tests/darwin-bridge';work.mkdir(parents=True,exist_ok=True)
        source=work/'test.cpp';source.write_text(r'''
#include "DarwinBridge.h"
#include "DarwinString.h"
#include "DarwinSystem.h"
#include <cassert>
#include <array>
#include <thread>
using namespace DiscoDarwin;
int main(){
    std::array<uint8_t,80> storage;storage.fill(0x5a);void* foreign=storage.data()+8;
    assert(MutexInit(foreign,nullptr)==0);assert(MutexLock(foreign)==0);
    std::atomic<bool> acquired{false};std::thread worker([&]{assert(MutexLock(foreign)==0);acquired=true;assert(MutexUnlock(foreign)==0);});
    assert(MutexUnlock(foreign)==0);worker.join();assert(acquired);assert(MutexDestroy(foreign)==0);
    for(auto b:storage)assert(b==0x5a);
    int attr=0;assert(AttrInit(&attr)==0);assert(AttrType(&attr,2)==0);
    assert(MutexInit(foreign,&attr)==0);assert(MutexLock(foreign)==0);assert(MutexLock(foreign)==0);
    assert(MutexDestroy(foreign)==EBUSY);assert(MutexUnlock(foreign)==0);assert(MutexDestroy(foreign)==EBUSY);
    assert(MutexUnlock(foreign)==0);assert(MutexDestroy(foreign)==0);assert(AttrDestroy(&attr)==0);
    int condition=0;assert(CondInit(&condition,nullptr)==0);assert(CondInit(&condition,nullptr)==EBUSY);
    assert(MutexLock(foreign)==0);timespec delta{0,1000000};assert(CondRelativeWait(&condition,foreign,&delta)==60);
    delta.tv_nsec=-1;assert(CondRelativeWait(&condition,foreign,&delta)==EINVAL);
    assert(MutexUnlock(foreign)==0);assert(CondDestroy(&condition)==0);assert(MutexDestroy(foreign)==0);
    assert(RWInit(foreign,nullptr)==0);assert(RWRead(foreign)==0);assert(RWDestroy(foreign)==EBUSY);
    assert(RWUnlock(foreign)==0);assert(RWWrite(foreign)==0);assert(RWDestroy(foreign)==EBUSY);
    assert(RWUnlock(foreign)==0);assert(RWDestroy(foreign)==0);
    int mib[]={6,3};struct {int cpu;int guard;} query{0,0x76543210};size_t bytes=sizeof(int);
    assert(QuerySystem(mib,2,&query.cpu,&bytes,nullptr,0,8,{123,456,0})==0&&query.cpu==8&&query.guard==0x76543210);
    bytes=0;assert(QuerySystem(mib,2,nullptr,&bytes,nullptr,0,8,{})==0&&bytes==4);
    bytes=1;assert(QuerySystem(mib,2,&query.cpu,&bytes,nullptr,0,8,{})==-1&&errno==ENOMEM&&bytes==4);
    mib[0]=1;mib[1]=21;Timeval boot{};bytes=sizeof(boot);assert(QuerySystem(mib,2,&boot,&bytes,nullptr,0,8,{123,456,0})==0&&boot.seconds==123&&boot.microseconds==456);
    mib[0]=99;assert(QuerySystem(mib,2,&boot,&bytes,nullptr,0,8,{})==-1&&errno==ENOENT);
    assert(QuerySystem(mib,1,&boot,&bytes,nullptr,0,8,{})==-1&&errno==EINVAL);

    uint64_t keyWithGuards[3]={0x1234567812345678ULL,0,0x1234567812345678ULL};
    assert(KeyCreate(&keyWithGuards[1],nullptr)==0);int value=7;assert(KeySet(keyWithGuards[1],&value)==0);assert(KeyGet(keyWithGuards[1])==&value);
    std::thread other([&]{assert(KeyGet(keyWithGuards[1])==nullptr);});other.join();assert(KeyDelete(keyWithGuards[1])==0);assert(keyWithGuards[0]==keyWithGuards[2]);
    alignas(8) uint64_t guard=0;std::atomic<unsigned> initializations{0};std::vector<std::thread> callers;
    for(unsigned i=0;i<8;++i)callers.emplace_back([&]{if(GuardAcquire(&guard)){++initializations;GuardRelease(&guard);}});
    for(auto& t:callers)t.join();assert(initializations==1 && guard==1);
    alignas(8) uint64_t aborted=0;assert(GuardAcquire(&aborted)==1);GuardAbort(&aborted);assert(GuardAcquire(&aborted)==1);GuardRelease(&aborted);
    auto sem=SemaphoreCreate(0);assert(SemaphoreWait(sem,0)==1);std::thread signaler([&]{SemaphoreSignal(sem);});assert(SemaphoreWait(sem,UINT64_MAX)==0);signaler.join();assert(SemaphoreWait(sem,AbsoluteTime()+1000000)==1);SemaphoreRelease(sem);
    struct {uint64_t left=0x12345678;String s{};uint64_t right=0x87654321;} data;
    StringAssign(&data.s,"short");assert(!data.s.Long()&&data.s.Size()==5&&!std::strcmp(data.s.Data(),"short"));
    std::string large(200,'x');StringAppendN(&data.s,large.data(),large.size());assert(data.s.Long()&&data.s.Size()==205&&data.s.Capacity()>=205);
    StringAssignN(&data.s,data.s.Data()+2,4);assert(!data.s.Long()&&!std::strcmp(data.s.Data(),"ortx"));
    StringReserve(&data.s,500);assert(data.s.Long()&&data.s.Capacity()>=500&&data.s.Size()==4&&!std::strcmp(data.s.Data(),"ortx"));
    StringInsert(&data.s,2,data.s.Data());assert(!std::strcmp(data.s.Data(),"orortxtx"));
    String sub{};assert(StringSubstring(&sub,&data.s,2,4,nullptr)==&sub);assert(!std::strcmp(sub.Data(),"ortx"));StringCopyAssign(&data.s,&sub);StringDestroy(&sub);
    String copy{};assert(StringCopyConstruct(&copy,&data.s)==&copy);StringPush(&copy,'!');assert(!std::strcmp(copy.Data(),"ortx!"));assert(StringDestroy(&copy)==&copy);assert(StringDestroy(&data.s)==&data.s);
    assert(data.left==0x12345678&&data.right==0x87654321);
}
''')
        exe=work/'test';subprocess.run(['xcrun','clang++','-std=c++17','-pthread','-I',str(ROOT/'runtime/AndroidHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True,timeout=10)
