// Original ABI adapters. Foreign synchronization objects are opaque keys;
// Android pthread objects never overwrite the differently sized Darwin storage.
#pragma once
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <vector>
#include <pthread.h>
#include <time.h>
#include <errno.h>

namespace DiscoDarwin {
struct Mutex { std::atomic<unsigned> held{0}; pthread_mutex_t value; explicit Mutex(int type=0){pthread_mutexattr_t a;pthread_mutexattr_init(&a);pthread_mutexattr_settype(&a,type==2?PTHREAD_MUTEX_RECURSIVE:type==1?PTHREAD_MUTEX_ERRORCHECK:PTHREAD_MUTEX_NORMAL);pthread_mutex_init(&value,&a);pthread_mutexattr_destroy(&a);} ~Mutex(){pthread_mutex_destroy(&value);} };
struct Cond { pthread_cond_t value=PTHREAD_COND_INITIALIZER;~Cond(){pthread_cond_destroy(&value);} };
struct RW {std::atomic<unsigned> held{0};pthread_rwlock_t value=PTHREAD_RWLOCK_INITIALIZER;~RW(){pthread_rwlock_destroy(&value);} };
inline std::mutex tableLock;
inline std::unordered_map<void*,std::shared_ptr<Mutex>> mutexes;
inline std::unordered_map<void*,std::shared_ptr<Cond>> conditions;
inline std::unordered_map<void*,std::shared_ptr<RW>> rwlocks;
inline std::unordered_map<void*,int> attributes;
template<class T> std::shared_ptr<T> Get(std::unordered_map<void*,std::shared_ptr<T>>& table,void* key){if(!key)std::abort();std::lock_guard<std::mutex> lock(tableLock);auto& p=table[key];if(!p)p=std::make_shared<T>();return p;}
inline int MutexInit(void* p,void* attr){if(!p)return EINVAL;std::lock_guard<std::mutex> lock(tableLock);int type=0;if(attr){auto it=attributes.find(attr);if(it==attributes.end())return EINVAL;type=it->second;}if(mutexes.count(p))return EBUSY;mutexes[p]=std::make_shared<Mutex>(type);return 0;}
inline int MutexLock(void* p){auto m=Get(mutexes,p);int r=pthread_mutex_lock(&m->value);if(!r)++m->held;return r;}
inline int MutexUnlock(void* p){auto m=Get(mutexes,p);if(!m->held.load())return EPERM;--m->held;int r=pthread_mutex_unlock(&m->value);if(r)++m->held;return r;}
inline int MutexDestroy(void* p){std::lock_guard<std::mutex> lock(tableLock);auto i=mutexes.find(p);if(i==mutexes.end())return 0;if(i->second.use_count()!=1||i->second->held.load())return EBUSY;mutexes.erase(i);return 0;}
inline int AttrInit(void* p){if(!p)return EINVAL;std::lock_guard<std::mutex> lock(tableLock);attributes[p]=0;return 0;}
inline int AttrType(void* p,int type){std::lock_guard<std::mutex> lock(tableLock);if(type<0||type>2||!attributes.count(p))return EINVAL;attributes[p]=type;return 0;}
inline int AttrDestroy(void* p){std::lock_guard<std::mutex> lock(tableLock);attributes.erase(p);return 0;}
inline int CondInit(void* p,void* attr){if(!p||attr)return EINVAL;std::lock_guard<std::mutex> lock(tableLock);if(conditions.count(p))return EBUSY;conditions[p]=std::make_shared<Cond>();return 0;}
inline int CondDestroy(void* p){std::lock_guard<std::mutex> lock(tableLock);auto i=conditions.find(p);if(i!=conditions.end()&&i->second.use_count()!=1)return EBUSY;conditions.erase(p);return 0;}
inline int CondSignal(void* p){return pthread_cond_signal(&Get(conditions,p)->value);}
inline int CondBroadcast(void* p){return pthread_cond_broadcast(&Get(conditions,p)->value);}
inline int CondWait(void* p,void* m){auto c=Get(conditions,p);auto mu=Get(mutexes,m);return pthread_cond_wait(&c->value,&mu->value);}
inline int CondTimedWait(void* p,void* m,const timespec* deadline){auto c=Get(conditions,p);auto mu=Get(mutexes,m);int r=pthread_cond_timedwait(&c->value,&mu->value,deadline);return r==ETIMEDOUT?60:r;}
inline int CondRelativeWait(void* p,void* m,const timespec* delta){if(!delta||delta->tv_sec<0||delta->tv_nsec<0||delta->tv_nsec>=1000000000)return EINVAL;timespec t;clock_gettime(CLOCK_REALTIME,&t);t.tv_sec+=delta->tv_sec;t.tv_nsec+=delta->tv_nsec;if(t.tv_nsec>=1000000000){++t.tv_sec;t.tv_nsec-=1000000000;}return CondTimedWait(p,m,&t);}
inline int RWInit(void* p,void* attr){if(!p||attr)return EINVAL;std::lock_guard<std::mutex> lock(tableLock);if(rwlocks.count(p))return EBUSY;rwlocks[p]=std::make_shared<RW>();return 0;}
inline int RWRead(void* p){auto m=Get(rwlocks,p);int r=pthread_rwlock_rdlock(&m->value);if(!r)++m->held;return r;}
inline int RWWrite(void* p){auto m=Get(rwlocks,p);int r=pthread_rwlock_wrlock(&m->value);if(!r)++m->held;return r;}
inline int RWUnlock(void* p){auto m=Get(rwlocks,p);if(!m->held.load())return EPERM;--m->held;int r=pthread_rwlock_unlock(&m->value);if(r)++m->held;return r;}
inline int RWDestroy(void* p){std::lock_guard<std::mutex> lock(tableLock);auto i=rwlocks.find(p);if(i!=rwlocks.end()&&(i->second.use_count()!=1||i->second->held.load()))return EBUSY;rwlocks.erase(p);return 0;}
inline int KeyCreate(uint64_t* key,void(*destructor)(void*)){if(!key)return EINVAL;pthread_key_t native;int r=pthread_key_create(&native,destructor);if(!r)*key=native;return r;}
inline int KeyDelete(uint64_t key){return pthread_key_delete(static_cast<pthread_key_t>(key));}
inline void* KeyGet(uint64_t key){return pthread_getspecific(static_cast<pthread_key_t>(key));}
inline int KeySet(uint64_t key,void* value){return pthread_setspecific(static_cast<pthread_key_t>(key),value);}
inline uint64_t AbsoluteTime(){timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))std::abort();return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
struct Semaphore{std::mutex mutex;std::condition_variable changed;int64_t count;unsigned waiters=0;explicit Semaphore(int64_t n):count(n){}};
inline void* SemaphoreCreate(int64_t n){return n<0?nullptr:new Semaphore(n);}
inline int64_t SemaphoreSignal(void* p){auto& s=*static_cast<Semaphore*>(p);std::lock_guard<std::mutex> lock(s.mutex);++s.count;bool waking=s.waiters!=0;s.changed.notify_one();return waking;}
inline int64_t SemaphoreWait(void* p,uint64_t deadline){auto& s=*static_cast<Semaphore*>(p);std::unique_lock<std::mutex> lock(s.mutex);++s.waiters;bool ready=true;if(deadline==UINT64_MAX)s.changed.wait(lock,[&]{return s.count>0;});else if(!deadline)ready=s.count>0;else{uint64_t now=AbsoluteTime();ready=s.count>0||(deadline>now&&s.changed.wait_for(lock,std::chrono::nanoseconds(deadline-now),[&]{return s.count>0;}));}--s.waiters;if(ready)--s.count;return ready?0:1;}
inline void SemaphoreRelease(void* p){delete static_cast<Semaphore*>(p);}
struct Guard {std::condition_variable changed;bool busy=false;std::thread::id owner;};
inline std::unordered_map<void*,std::shared_ptr<Guard>> guards;
inline int GuardAcquire(uint64_t* p){std::unique_lock<std::mutex> lock(tableLock);auto& slot=guards[p];if(!slot)slot=std::make_shared<Guard>();auto state=slot;while(state->busy){if(state->owner==std::this_thread::get_id())std::abort();state->changed.wait(lock);}if(__atomic_load_n(reinterpret_cast<uint8_t*>(p),__ATOMIC_ACQUIRE)&1)return 0;state->busy=true;state->owner=std::this_thread::get_id();return 1;}
inline void GuardFinish(uint64_t* p,bool success){std::lock_guard<std::mutex> lock(tableLock);auto i=guards.find(p);if(i==guards.end()||!i->second->busy||i->second->owner!=std::this_thread::get_id())std::abort();if(success)__atomic_store_n(reinterpret_cast<uint8_t*>(p),uint8_t(1),__ATOMIC_RELEASE);i->second->busy=false;i->second->changed.notify_all();}
inline void GuardRelease(uint64_t* p){GuardFinish(p,true);}
inline void GuardAbort(uint64_t* p){GuardFinish(p,false);}
struct Destructor {void(*function)(void*);void* object;void* dso;};
inline std::vector<Destructor> destructors;
inline std::vector<void(*)()> exitCallbacks;
inline int PlainAtExit(void(*f)()){if(!f)return -1;std::lock_guard<std::mutex> lock(tableLock);exitCallbacks.push_back(f);return 0;}
inline int AtExit(void(*function)(void*),void* object,void* dso){if(!function)return -1;std::lock_guard<std::mutex> lock(tableLock);destructors.push_back({function,object,dso});return 0;}
// The mapped image is process-lifetime during integration. Do not register its
// callbacks with Android's libc finalizer, which cannot own the foreign image.
inline void* MutexDtor(void* p){if(MutexDestroy(p))std::abort();return p;}
inline void* CondDtor(void* p){if(CondDestroy(p))std::abort();return p;}
}
