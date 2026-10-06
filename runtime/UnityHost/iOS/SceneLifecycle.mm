// Original bridge for the pinned Unity 2020.3.12f1 iOS trampoline.
// App launch records options; the first window scene initializes Unity.
// Single-window diagnostic only. Multi-window game support is not implemented.
#import "UnityAppController.h"

@interface UnityAppController (DiscoSceneStartup)
- (BOOL)discoStartWithScene:(UIWindowScene*)scene application:(UIApplication*)application launchOptions:(NSDictionary*)options;
@end

static NSDictionary* DiscoLaunchOptions;

@interface DiscoUnitySceneDelegate : NSObject <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow* window;
@end

@implementation UnityAppController (DiscoSceneLifecycle)
- (BOOL)application:(UIApplication*)application didFinishLaunchingWithOptions:(NSDictionary*)options
{
    DiscoLaunchOptions = [options copy];
    return YES;
}
@end

@implementation DiscoUnitySceneDelegate
- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options
{
    if (![scene isKindOfClass:[UIWindowScene class]]) return;
    UnityAppController* controller = GetAppController();
    if (controller.window == nil)
        [controller discoStartWithScene:(UIWindowScene*)scene application:UIApplication.sharedApplication launchOptions:DiscoLaunchOptions];
    else
        controller.window.windowScene = (UIWindowScene*)scene;
    self.window = controller.window;
    [self.window makeKeyAndVisible];
    NSLog(@"Disco Unity window scene connected");
}

- (void)sceneDidBecomeActive:(UIScene*)scene
{
    [GetAppController() applicationDidBecomeActive:UIApplication.sharedApplication];
}

- (void)sceneWillResignActive:(UIScene*)scene
{
    [GetAppController() applicationWillResignActive:UIApplication.sharedApplication];
}

- (void)sceneWillEnterForeground:(UIScene*)scene
{
    [GetAppController() applicationWillEnterForeground:UIApplication.sharedApplication];
}

- (void)sceneDidEnterBackground:(UIScene*)scene
{
    [GetAppController() applicationDidEnterBackground:UIApplication.sharedApplication];
}
@end
