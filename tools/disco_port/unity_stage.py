"""Compatibility changes for the pinned Unity iOS export."""

def modernize_ios_project(text):
    """Remove the exact obsolete flags emitted by our pinned Unity exporter."""
    thumb = '\t\t\t\t\t"-mno-thumb",\n'
    if text.count(thumb) != 4:
        raise ValueError("Unsupported Unity Xcode layout: expected four legacy Thumb flags")
    text = text.replace(thumb, "")
    if "-mno-thumb" in text:
        raise ValueError("Unsupported Unity Xcode layout: additional Thumb flags")
    return text.replace("ENABLE_BITCODE = YES;", "ENABLE_BITCODE = NO;")


def modernize_ios_trampoline(text, adapter):
    startup = '- (BOOL)application:(UIApplication*)application didFinishLaunchingWithOptions:(NSDictionary*)launchOptions'
    window = '_window         = [[UIWindow alloc] initWithFrame: [UIScreen mainScreen].bounds];'
    if text.count(startup) != 1 or text.count(window) != 1 or 'discoStartWithScene:' in text:
        raise ValueError("Unsupported Unity iOS startup layout")
    text = text.replace(startup, '- (BOOL)discoStartWithScene:(UIWindowScene*)scene application:(UIApplication*)application launchOptions:(NSDictionary*)launchOptions')
    text = text.replace(window, '_window         = [[UIWindow alloc] initWithWindowScene: scene];')
    return text + '\n' + adapter
def modernize_orientation_transition(text):
    """Update the delegate's controller before UIKit queries its orientation mask."""
    old = '    _rootController = _window.rootViewController = vc;'
    new = '    _rootController = vc;\n    _window.rootViewController = vc;'
    if new in text:
        if text.count(new) != 1 or old in text:
            raise ValueError('Ambiguous modern controller transition')
        return text
    if text.count(old) != 1:
        raise ValueError('Unsupported pinned controller transition')
    return text.replace(old, new)
