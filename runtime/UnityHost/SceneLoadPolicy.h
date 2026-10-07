// Original, platform-independent scene admission policy for the native adapter.
#pragma once
#include <algorithm>
#include <string>
#include <vector>

namespace DiscoScenePolicy {
struct PreloadPlan {
    std::string bootstrap;
    std::vector<std::string> deferred;
};
inline bool Plan(const std::vector<std::string>& paths, const std::vector<std::string>& originalSkip,
                 PreloadPlan& output, std::string& error) {
    output = {};
    if (paths.empty() || paths.size() > 256 || originalSkip.size() > 256) {
        error = "unsupported scene count"; return false;
    }
    std::vector<std::string> names;
    for (const std::string& path : paths) {
        const std::string prefix = "Assets/Scenes/";
        if (path.size() > 4096 || path.size() <= prefix.size() + 6 ||
            path.compare(0, prefix.size(), prefix) || path.substr(path.size() - 6) != ".unity" ||
            path.find('\0') != std::string::npos || path.find('\\') != std::string::npos ||
            path.find("//") != std::string::npos || path.find("/../") != std::string::npos ||
            path.find("/./") != std::string::npos) {
            error = "unsupported build scene path"; return false;
        }
        size_t slash = path.find_last_of('/');
        std::string name = "Scenes/" + path.substr(slash + 1, path.size() - slash - 7);
        if (name == "Scenes/" || std::find(names.begin(), names.end(), name) != names.end()) {
            error = "ambiguous scene cache key"; return false;
        }
        names.push_back(name);
    }
    PreloadPlan plan;
    for (const std::string& name : names) {
        if (plan.bootstrap.empty() && std::find(originalSkip.begin(), originalSkip.end(), name) == originalSkip.end())
            plan.bootstrap = name;
        else plan.deferred.push_back(name);
    }
    if (plan.bootstrap.empty()) { error = "no original bootstrap scene"; return false; }
    output = plan; error.clear(); return true;
}
}
