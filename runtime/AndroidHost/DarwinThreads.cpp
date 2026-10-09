// Original process-local Mach thread adapter for the conservative collector.
// Only threads that obtained a bridge token can be suspended; no other process
// or unregistered Android/Java thread is targeted.
#include <atomic>
#include <cstdint>
#include <cstring>
#include <cerrno>
#include <mutex>
#include <thread>
#include <cstdlib>
#include <signal.h>
#include <ucontext.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <android/log.h>
namespace DiscoDarwin {
struct ThreadState {uint64_t x[29],fp,lr,sp,pc;uint32_t cpsr,pad;};
static_assert(sizeof(ThreadState)==272,"Darwin ARM_THREAD_STATE64");
struct ThreadSlot {std::atomic<int> tid{0},state{0},references{0};ThreadState registers{};};
static ThreadSlot slots[1024];
static std::once_flag signalOnce;
static std::mutex registryLock;
static_assert(std::atomic<int>::is_always_lock_free,"Signal state must be lock free");
static int stopSignal=0;
static ThreadSlot* Find(int tid){for(auto& s:slots)if(s.tid.load(std::memory_order_acquire)==tid)return &s;return nullptr;}
static void Wake(std::atomic<int>& state){syscall(SYS_futex,reinterpret_cast<int*>(&state),FUTEX_WAKE_PRIVATE,1,nullptr,nullptr,0);}
static void Park(int,siginfo_t*,void* raw){auto* slot=Find(syscall(SYS_gettid));if(!slot||slot->state.load(std::memory_order_acquire)!=1)return;auto* u=static_cast<ucontext_t*>(raw);for(unsigned i=0;i<29;++i)slot->registers.x[i]=u->uc_mcontext.regs[i];slot->registers.fp=u->uc_mcontext.regs[29];slot->registers.lr=u->uc_mcontext.regs[30];slot->registers.sp=u->uc_mcontext.sp;slot->registers.pc=u->uc_mcontext.pc;slot->registers.cpsr=u->uc_mcontext.pstate;slot->registers.pad=0;slot->state.store(2,std::memory_order_release);Wake(slot->state);while(slot->state.load(std::memory_order_acquire)==2)syscall(SYS_futex,reinterpret_cast<int*>(&slot->state),FUTEX_WAIT_PRIVATE,2,nullptr,nullptr,0);slot->state.store(0,std::memory_order_release);Wake(slot->state);}
static void Initialize(){stopSignal=SIGRTMIN+5;struct sigaction old{};sigaction(stopSignal,nullptr,&old);if(old.sa_handler!=SIG_DFL&&old.sa_handler!=SIG_IGN){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Collector stop signal already owned");std::abort();}struct sigaction action{};action.sa_sigaction=Park;action.sa_flags=SA_SIGINFO|SA_RESTART;sigemptyset(&action.sa_mask);if(sigaction(stopSignal,&action,nullptr))std::abort();}
uint32_t MachThreadSelf(){std::call_once(signalOnce,Initialize);sigset_t unblocked;sigemptyset(&unblocked);sigaddset(&unblocked,stopSignal);if(pthread_sigmask(SIG_UNBLOCK,&unblocked,nullptr))std::abort();std::lock_guard<std::mutex> lock(registryLock);int tid=syscall(SYS_gettid);if(auto* s=Find(tid)){++s->references;return tid;}for(auto& s:slots){int empty=0;if(s.tid.compare_exchange_strong(empty,tid)){s.state.store(0);s.references.store(1);return tid;}}__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Collector thread-token registry full");std::abort();}
uint32_t machTask=1;
int MachPortRelease(uint32_t task,uint32_t port){std::lock_guard<std::mutex> lock(registryLock);if(task!=machTask)return 4;auto* s=Find(port);if(!s)return 4;if(s->state.load())return 5;int refs=s->references.fetch_sub(1);if(refs<=0)std::abort();if(refs==1)s->tid.store(0,std::memory_order_release);return 0;}
int ThreadSuspend(uint32_t tid){std::lock_guard<std::mutex> lock(registryLock);if(tid==uint32_t(syscall(SYS_gettid)))return 4;auto* s=Find(tid);if(!s)return 4;int expected=0;if(!s->state.compare_exchange_strong(expected,1))return 5;if(syscall(SYS_tgkill,getpid(),tid,stopSignal)){s->state.store(0);return 5;}timespec timeout{2,0};while(s->state.load(std::memory_order_acquire)!=2){int r=syscall(SYS_futex,reinterpret_cast<int*>(&s->state),FUTEX_WAIT_PRIVATE,1,&timeout,nullptr,0);if(r&&errno==ETIMEDOUT){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Collector thread suspension timed out");std::abort();}}return 0;}
int ThreadResume(uint32_t tid){std::lock_guard<std::mutex> lock(registryLock);auto* s=Find(tid);if(!s||s->state.load()!=2)return 4;s->state.store(3,std::memory_order_release);Wake(s->state);while(s->state.load(std::memory_order_acquire)!=0)syscall(SYS_futex,reinterpret_cast<int*>(&s->state),FUTEX_WAIT_PRIVATE,3,nullptr,nullptr,0);return 0;}
int ThreadGetState(uint32_t tid,int flavor,void* output,uint32_t* count){std::lock_guard<std::mutex> lock(registryLock);auto* s=Find(tid);if(!s||s->state.load(std::memory_order_acquire)!=2||flavor!=6||!count||*count<68||!output)return 4;std::memcpy(output,&s->registers,sizeof(ThreadState));*count=68;return 0;}
// Synthetic Android check before running the foreign collector. No game data.
bool ThreadBridgeSelfTest(){
    std::atomic<uint32_t> token{0};std::atomic<bool> done{false};std::atomic<uint64_t> ticks{0};
    std::thread worker([&]{token.store(MachThreadSelf(),std::memory_order_release);while(!done.load()){++ticks;std::this_thread::yield();}});
    while(!token.load(std::memory_order_acquire))std::this_thread::yield();
    bool ok=true;auto tid=token.load();
    for(int i=0;i<16;++i){if(ThreadSuspend(tid)){ok=false;break;}ThreadState saved{};uint32_t count=68;uint64_t before=ticks.load();
        ok &= ThreadGetState(tid,6,&saved,&count)==0&&count==68&&saved.pc&&saved.sp&&!(saved.sp&15);
        uint32_t shortCount=1;ok &= ThreadGetState(tid,6,&saved,&shortCount)!=0;
        ok &= MachPortRelease(machTask,tid)!=0&&ticks.load()==before;
        if(ThreadResume(tid)){std::abort();}
    }
    done=true;worker.join();ok &= MachPortRelease(machTask,tid)==0;
    ok &= ThreadSuspend(tid)!=0;return ok;
}
}
