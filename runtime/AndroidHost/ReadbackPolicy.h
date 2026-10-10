#pragma once
#include <cstddef>
namespace DiscoReadbackPolicy {
inline bool Shape(int width,int height,size_t& bytes) {
    bytes=0;
    if(width<=0||height<=0||width>4096||height>4096)return false;
    bytes=size_t(width)*size_t(height)*4;return true;
}
constexpr size_t Budget=128*1024*1024;
}
