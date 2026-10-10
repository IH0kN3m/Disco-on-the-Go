#pragma once
#include "MappedImage.h"
#include <android/asset_manager.h>
#include <atomic>
namespace DiscoRuntime {
extern std::atomic<unsigned> allocations,frees,clockQueries;
void Phase(const char*);
struct Module {DiscoMap::Image* image;unsigned resolved;size_t missing;bool initialized=false;};
Module& Load(AAssetManager*);
void Initialize(Module&);
}
