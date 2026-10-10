// Android has no Steam client. Report unavailable so the original game takes
// its existing local settings/save path. No account, ownership, achievements,
// cloud storage, or authenticated Steam interfaces are supplied.
#include <cstdint>
static_assert(sizeof(bool)==1&&sizeof(uint32_t)==4,"Native store ABI");
extern "C" bool SteamAPI_Init(){return false;}
extern "C" bool SteamAPI_IsSteamRunning(){return false;}
extern "C" bool SteamAPI_RestartAppIfNecessary(uint32_t){return false;}
extern "C" void SteamAPI_Shutdown(){}
