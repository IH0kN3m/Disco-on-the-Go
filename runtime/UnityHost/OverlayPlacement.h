// Portable geometry for a movable icon inside a view's safe area.
#pragma once
#include <algorithm>
#include <cmath>
#include <initializer_list>
namespace DiscoOverlay {
struct Point { double x,y;Point(double x=0,double y=0):x(x),y(y){} };
struct Area { double x,y,width,height;Area(double x=0,double y=0,double width=0,double height=0):x(x),y(y),width(width),height(height){} };
inline double Unit(double v) { return std::max(0.0,std::min(v,1.0)); }
inline bool Bounds(double width,double height,double left,double top,double right,double bottom,
                   double iconWidth,double iconHeight,Area& result) {
    result={};
    for(double v:{width,height,left,top,right,bottom,iconWidth,iconHeight})
        if(!std::isfinite(v)||v<0)return false;
    if(iconWidth<=0||iconHeight<=0||width<=0||height<=0)return false;
    double availableWidth=width-left-right-iconWidth,availableHeight=height-top-bottom-iconHeight;
    if(availableWidth<0||availableHeight<0)return false;
    result={left+iconWidth/2,top+iconHeight/2,availableWidth,availableHeight};return true;
}
inline Point Clamp(const Area& area,Point p) {
    if(!std::isfinite(p.x)||!std::isfinite(p.y))return {area.x,area.y};
    return {std::max(area.x,std::min(p.x,area.x+area.width)),std::max(area.y,std::min(p.y,area.y+area.height))};
}
inline Point Normalize(const Area& area,Point p) {
    p=Clamp(area,p);
    return {area.width>0?(p.x-area.x)/area.width:0,area.height>0?(p.y-area.y)/area.height:0};
}
inline Point Restore(const Area& area,Point normalized) {
    if(!std::isfinite(normalized.x)||!std::isfinite(normalized.y))normalized={1,0};
    return {area.x+Unit(normalized.x)*area.width,area.y+Unit(normalized.y)*area.height};
}
}
