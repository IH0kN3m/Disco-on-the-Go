// Original UIKit controls calling the pinned game's camera methods and
// the pinned Unity host's existing keyboard event API. No recovered method bodies.
#pragma once
#include "TouchControlPolicy.h"
#import "UI/UnityView.h"
#import <GameController/GameController.h>

namespace DiscoTouchControls {
using DiscoSceneResidency::Call;
using DiscoSceneResidency::Boolean;
using DiscoSceneResidency::Fail;
using DiscoGameDisplay::Method;
static DiscoTouch::Pinch pinch;
static DiscoTouch::Keys keys;
static uint32_t cameraHandle;
static int escapeKey;
static Il2CppClass* CameraClass() { return DiscoSceneResidency::Class("Assembly-CSharp.dll", "FortressOccident", "CameraController"); }
static Il2CppObject* Camera() { return Call(Method(CameraClass(), "get_Current", 0, 0xaeb8ac), nullptr, nullptr); }
static float Float(Il2CppObject* object) {
    if (!object || il2cpp_type_get_type(il2cpp_class_get_type(il2cpp_object_get_class(object))) != IL2CPP_TYPE_R4)
        Fail("camera result is not a boxed Single");
    float result = *(float*)il2cpp_object_unbox(object);
    if (!std::isfinite(result)) Fail("nonfinite camera result");
    return result;
}
static bool Eligible(Il2CppObject* camera) {
    if (!camera) return false;
    Il2CppClass* world = DiscoSceneResidency::Class("Assembly-CSharp.dll", "", "World");
    if (!Boolean(Call(Method(world, "get_RunningOrCollage", 0, 0x665e40), nullptr, nullptr)) ||
        Boolean(Call(Method(world, "get_CollageMode", 0, 0x659fa0), nullptr, nullptr))) return false;
    void* objectArgs[] = {camera};
    if (!Boolean(Call(DiscoSceneResidency::Class("UnityEngine.CoreModule.dll", "UnityEngine", "Object"), "op_Implicit", 1, nullptr, objectArgs))) return false;
    if (Boolean(Call(Method(CameraClass(), "get_IsLocked", 0, 0xaec6a0, false), camera, nullptr))) return false;
    return !Boolean(Call(Method(CameraClass(), "get_IsSlaved", 0, 0xaec6f4, false), camera, nullptr));
}
static bool PointerOverUI() {
    Il2CppClass* events = DiscoSceneResidency::Class("UnityEngine.UI.dll", "UnityEngine.EventSystems", "EventSystem");
    Il2CppObject* current = Call(events, "get_current", 0, nullptr, nullptr);
    return current && Boolean(Call(events, "IsPointerOverGameObject", 0, current, nullptr));
}
static void CancelPinch() {
    pinch.Cancel();
    if (cameraHandle) { il2cpp_gchandle_free(cameraHandle); cameraHandle = 0; }
}
static void ReleaseKeys() {
    uint32_t held = keys.Cancel();
    if (held & 1) UnitySetKeyboardKeyState(escapeKey, 0);
}
static void Change(UIPinchGestureRecognizer* gesture) {
    if (![NSThread isMainThread]) Fail("pinch is not on Unity thread");
    if (gesture.state == UIGestureRecognizerStateBegan) {
        CancelPinch();
        Il2CppObject* camera = Camera();
        if (pinch.Begin((uintptr_t)camera, Eligible(camera), gesture.scale)) {
            cameraHandle = il2cpp_gchandle_new(camera, false);
            printf("NATIVE TOUCH: pinch began\n");
        }
    } else if (gesture.state == UIGestureRecognizerStateChanged && cameraHandle) {
        Il2CppObject* camera = Camera();
        float delta;
        bool sameOwner = camera == il2cpp_gchandle_get_target(cameraHandle);
        if (!pinch.Change((uintptr_t)camera, sameOwner && Eligible(camera), gesture.scale, delta)) { CancelPinch(); return; }
        float value = Float(Call(Method(CameraClass(), "get_ZoomFactor", 0, 0xaec42c, false), camera, nullptr)) + delta;
        void* args[] = { &value };
        value = Float(Call(Method(CameraClass(), "ClampZoomFactor", 1, 0xaed2fc, false), camera, args));
        Call(Method(CameraClass(), "set_ZoomFactor", 1, 0xaec434, false), camera, args);
    } else if (gesture.state == UIGestureRecognizerStateEnded || gesture.state == UIGestureRecognizerStateCancelled || gesture.state == UIGestureRecognizerStateFailed) {
        CancelPinch();
    }
}
}

@interface DiscoTouchPanel : UIView
@end
@implementation DiscoTouchPanel
- (UIView*)hitTest:(CGPoint)point withEvent:(UIEvent*)event {
    UIView* hit = [super hitTest:point withEvent:event];
    return hit == self ? nil : hit;
}
@end

@interface DiscoAnalogStick : UIControl
@property(nonatomic, retain) GCVirtualController* controller;
@property(nonatomic, copy) NSString* element;
@property(nonatomic, retain) UITouch* tracked;
@property(nonatomic) CGPoint position;
- (void)reset;
@end
@implementation DiscoAnalogStick
- (void)drawRect:(CGRect)rect {
    CGContextRef context = UIGraphicsGetCurrentContext();
    if ([self.element isEqualToString:GCInputDirectionPad]) {
        CGFloat mid = self.bounds.size.width/2;
        CGContextSetLineCap(context,kCGLineCapRound); CGContextSetLineWidth(context,32);
        [[UIColor colorWithWhite:0.05 alpha:0.65] setStroke];
        CGContextMoveToPoint(context,18,mid); CGContextAddLineToPoint(context,self.bounds.size.width-18,mid);
        CGContextMoveToPoint(context,mid,18); CGContextAddLineToPoint(context,mid,self.bounds.size.height-18);
        CGContextStrokePath(context);
        NSDictionary* attributes = @{NSFontAttributeName:[UIFont systemFontOfSize:20], NSForegroundColorAttributeName:UIColor.whiteColor};
        [@"↑" drawAtPoint:CGPointMake(mid-8,7) withAttributes:attributes];
        [@"↓" drawAtPoint:CGPointMake(mid-8,self.bounds.size.height-31) withAttributes:attributes];
        [@"←" drawAtPoint:CGPointMake(5,mid-12) withAttributes:attributes];
        [@"→" drawAtPoint:CGPointMake(self.bounds.size.width-29,mid-12) withAttributes:attributes];
        return;
    }
    CGRect ring = CGRectInset(self.bounds, 6, 6);
    [[UIColor colorWithWhite:0.05 alpha:0.50] setFill];
    CGContextFillEllipseInRect(context, ring);
    [[UIColor colorWithWhite:1 alpha:0.45] setStroke];
    CGContextSetLineWidth(context, 2); CGContextStrokeEllipseInRect(context, ring);
    CGFloat radius = self.bounds.size.width * 0.30;
    CGPoint center = CGPointMake(CGRectGetMidX(self.bounds) + self.position.x * radius,
                                 CGRectGetMidY(self.bounds) - self.position.y * radius);
    [[UIColor colorWithWhite:1 alpha:0.55] setFill];
    CGContextFillEllipseInRect(context, CGRectMake(center.x-20,center.y-20,40,40));
}
- (void)update:(UITouch*)touch {
    CGPoint point = [touch locationInView:self];
    float x, y;
    if (!DiscoTouch::Stick((float)(point.x-CGRectGetMidX(self.bounds)),
                          (float)(CGRectGetMidY(self.bounds)-point.y),
                          (float)(self.bounds.size.width * 0.30), x, y)) { [self reset]; return; }
    self.position = CGPointMake(x,y);
    [self.controller setPosition:self.position forDirectionPadElement:self.element];
    [self setNeedsDisplay];
}
- (void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    if (!self.tracked) { self.tracked = touches.anyObject; [self update:self.tracked]; }
}
- (void)touchesMoved:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    if (self.tracked && [touches containsObject:self.tracked]) [self update:self.tracked];
}
- (void)touchesEnded:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    if (self.tracked && [touches containsObject:self.tracked]) [self reset];
}
- (void)touchesCancelled:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event { [self reset]; }
- (void)reset {
    self.tracked = nil; self.position = CGPointZero;
    [self.controller setPosition:CGPointZero forDirectionPadElement:self.element];
    [self setNeedsDisplay];
}
@end

@interface DiscoTouchOverlay : NSObject<UIGestureRecognizerDelegate>
@property(nonatomic, retain) UIView* leftPanel;
@property(nonatomic, retain) UIView* rightPanel;
@property(nonatomic, retain) UIButton* toggle;
@property(nonatomic, retain) GCVirtualController* controller;
@property(nonatomic, retain) NSArray<NSString*>* buttons;
@property(nonatomic, retain) NSMutableArray<DiscoAnalogStick*>* sticks;
@property(nonatomic) BOOL connecting;
- (void)reset;
@end

@implementation DiscoTouchOverlay
- (void)pinched:(UIPinchGestureRecognizer*)gesture { DiscoTouchControls::Change(gesture); }
- (BOOL)gestureRecognizerShouldBegin:(UIGestureRecognizer*)gesture {
    return self.leftPanel.hidden && DiscoTouchControls::Eligible(DiscoTouchControls::Camera()) && !DiscoTouchControls::PointerOverUI();
}
- (BOOL)gestureRecognizer:(UIGestureRecognizer*)gesture shouldReceiveTouch:(UITouch*)touch {
    for (UIView* view = touch.view; view; view = view.superview)
        if ([view isKindOfClass:UIControl.class]) return NO;
    return YES;
}
- (void)pressed:(UIButton*)button {
    if (self.leftPanel.hidden) return;
    if ((NSUInteger)button.tag < self.buttons.count) {
        [self.controller setValue:1 forButtonElement:self.buttons[button.tag]];
        printf("NATIVE TOUCH: controller button=%s down\n", self.buttons[button.tag].UTF8String);
    } else if (DiscoTouchControls::keys.Set(0, true)) UnitySetKeyboardKeyState(DiscoTouchControls::escapeKey, 1);
}
- (void)released:(UIButton*)button {
    if ((NSUInteger)button.tag < self.buttons.count)
        [self.controller setValue:0 forButtonElement:self.buttons[button.tag]];
    else if (DiscoTouchControls::keys.Set(0, false)) UnitySetKeyboardKeyState(DiscoTouchControls::escapeKey, 0);
}
- (void)reset {
    DiscoTouchControls::CancelPinch(); DiscoTouchControls::ReleaseKeys();
    for (NSString* element in self.buttons) [self.controller setValue:0 forButtonElement:element];
    for (DiscoAnalogStick* stick in self.sticks) [stick reset];
}
- (void)inactive:(NSNotification*)notification { [self reset]; }
- (void)toggled:(UIButton*)button {
    if (self.connecting) return;
    [self reset];
    if (!self.leftPanel.hidden) {
        self.leftPanel.hidden = YES; self.rightPanel.hidden = YES;
        self.toggle.selected = NO;
        [self.controller disconnect];
        printf("NATIVE TOUCH: virtual gamepad hidden/disconnected\n");
        return;
    }
    self.connecting = YES;
    [self.controller connectWithReplyHandler:^(NSError* error) {
        dispatch_async(dispatch_get_main_queue(), ^{
            self.connecting = NO;
            if (error) { printf("NATIVE TOUCH: virtual gamepad connection failed=%s\n", error.description.UTF8String); return; }
            if (UIApplication.sharedApplication.applicationState != UIApplicationStateActive) {
                [self.controller disconnect]; return;
            }
            self.leftPanel.hidden = NO; self.rightPanel.hidden = NO;
            self.toggle.selected = YES;
            printf("NATIVE TOUCH: virtual gamepad connected extended=%d controllers=%lu\n",
                self.controller.controller.extendedGamepad != nil, (unsigned long)GCController.controllers.count);
        });
    }];
}
@end

namespace DiscoTouchControls {
static UIButton* Button(DiscoTouchOverlay* owner, UIView* parent, NSString* title, CGRect frame, unsigned index) {
    UIButton* button = [UIButton buttonWithType:UIButtonTypeSystem];
    button.frame = frame; button.tag = index;
    button.backgroundColor = [UIColor colorWithWhite:0.05 alpha:0.65];
    button.tintColor = UIColor.whiteColor; button.layer.cornerRadius = MIN(frame.size.width,frame.size.height)/2;
    if (index < 4) {
        UIColor* colors[] = {UIColor.systemGreenColor,UIColor.systemRedColor,UIColor.systemBlueColor,UIColor.systemYellowColor};
        button.tintColor = colors[index];
    }
    button.titleLabel.font = [UIFont systemFontOfSize:18 weight:UIFontWeightSemibold];
    [button setTitle:title forState:UIControlStateNormal];
    [button addTarget:owner action:@selector(pressed:) forControlEvents:UIControlEventTouchDown];
    [button addTarget:owner action:@selector(released:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside | UIControlEventTouchCancel];
    [parent addSubview:button]; return button;
}
static void Stick(DiscoTouchOverlay* owner, UIView* parent, CGRect frame, NSString* element) {
    DiscoAnalogStick* stick = [[DiscoAnalogStick alloc] initWithFrame:frame];
    stick.controller = owner.controller; stick.element = element;
    stick.backgroundColor = UIColor.clearColor;
    [parent addSubview:stick]; [owner.sticks addObject:stick];
}
static void LogController() {
    if (!GCController.controllers.count) return;
    Il2CppClass* input = DiscoSceneResidency::Class("UnityEngine.InputLegacyModule.dll", "UnityEngine", "Input");
    Il2CppArray* names = (Il2CppArray*)Call(input, "GetJoystickNames", 0, nullptr, nullptr);
    unsigned count = names ? (unsigned)il2cpp_array_length(names) : 0;
    if (count > 32) { printf("NATIVE TOUCH: unexpected joystick count\n"); return; }
    Il2CppClass* manager = DiscoSceneResidency::Class("InControl.dll", "InControl", "InputManager");
    if (!Boolean(Call(manager, "get_IsSetup", 0, nullptr, nullptr))) return;
    Il2CppObject* active = Call(manager, "get_ActiveDevice", 0, nullptr, nullptr);
    NSString* name = @"none";
    if (active) {
        Il2CppString* text = (Il2CppString*)Call(il2cpp_object_get_class(active), "get_Name", 0, active, nullptr);
        if (text && il2cpp_string_length(text) <= 256)
            name = [NSString stringWithCharacters:(const unichar*)il2cpp_string_chars(text) length:il2cpp_string_length(text)];
    }
    static NSString* previous;
    static unsigned previousCount = UINT32_MAX;
    if (count != previousCount || ![previous isEqualToString:name]) {
        printf("NATIVE TOUCH: Unity joystick count=%u InControl active=%s\n", count, name.UTF8String);
        previous = name; previousCount = count;
    }
}
static void Install() {
    if (![[NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoTouchControls"] boolValue]) return;
    static DiscoTouchOverlay* owner;
    if (owner) return;
    UIView* view = GetAppController().unityView;
    if (!view) Fail("touch surface absent");
    owner = [[DiscoTouchOverlay alloc] init];
    escapeKey = UnityStringToKey("escape");
    if (escapeKey <= 0) Fail("menu key mapping unavailable");
    UIPinchGestureRecognizer* recognizer = [[UIPinchGestureRecognizer alloc] initWithTarget:owner action:@selector(pinched:)];
    recognizer.delegate = owner; recognizer.cancelsTouchesInView = YES;
    [view addGestureRecognizer:recognizer];
    owner.buttons = @[GCInputButtonA, GCInputButtonB, GCInputButtonX, GCInputButtonY,
        GCInputLeftShoulder, GCInputRightShoulder, GCInputLeftTrigger, GCInputRightTrigger];
    NSMutableSet* elements = [NSMutableSet setWithArray:owner.buttons];
    [elements addObjectsFromArray:@[GCInputLeftThumbstick, GCInputRightThumbstick, GCInputDirectionPad]];
    GCVirtualControllerConfiguration* configuration = [[GCVirtualControllerConfiguration alloc] init];
    configuration.elements = elements; configuration.hidden = YES;
    owner.controller = [[GCVirtualController alloc] initWithConfiguration:configuration];
    owner.sticks = [NSMutableArray array];
    owner.leftPanel = [[DiscoTouchPanel alloc] initWithFrame:CGRectMake(20,view.bounds.size.height-340,270,235)];
    owner.leftPanel.autoresizingMask = UIViewAutoresizingFlexibleTopMargin;
    owner.rightPanel = [[DiscoTouchPanel alloc] initWithFrame:CGRectMake(view.bounds.size.width-340,view.bounds.size.height-340,320,235)];
    owner.rightPanel.autoresizingMask = UIViewAutoresizingFlexibleTopMargin | UIViewAutoresizingFlexibleLeftMargin;
    owner.leftPanel.hidden = YES; owner.rightPanel.hidden = YES;
    Stick(owner,owner.leftPanel,CGRectMake(0,60,135,135),GCInputLeftThumbstick);
    Stick(owner,owner.leftPanel,CGRectMake(150,110,100,100),GCInputDirectionPad);
    Stick(owner,owner.rightPanel,CGRectMake(0,90,120,120),GCInputRightThumbstick);
    Button(owner,owner.leftPanel,@"LB",CGRectMake(0,0,60,42),4);
    Button(owner,owner.leftPanel,@"LT",CGRectMake(68,0,60,42),6);
    Button(owner,owner.rightPanel,@"RB",CGRectMake(188,0,60,42),5);
    Button(owner,owner.rightPanel,@"RT",CGRectMake(256,0,60,42),7);
    Button(owner,owner.rightPanel,@"A",CGRectMake(212,154,50,50),0);
    Button(owner,owner.rightPanel,@"B",CGRectMake(266,100,50,50),1);
    Button(owner,owner.rightPanel,@"X",CGRectMake(158,100,50,50),2);
    Button(owner,owner.rightPanel,@"Y",CGRectMake(212,46,50,50),3);
    Button(owner,owner.rightPanel,@"≡",CGRectMake(76,0,60,42),8);
    [view addSubview:owner.leftPanel]; [view addSubview:owner.rightPanel];
    owner.toggle = [UIButton buttonWithType:UIButtonTypeSystem];
    owner.toggle.frame = CGRectMake(view.bounds.size.width-58,72,42,38);
    owner.toggle.autoresizingMask = UIViewAutoresizingFlexibleLeftMargin | UIViewAutoresizingFlexibleBottomMargin;
    owner.toggle.backgroundColor = [UIColor colorWithWhite:0.05 alpha:0.55];
    owner.toggle.tintColor = UIColor.whiteColor; owner.toggle.layer.cornerRadius = 10;
    [owner.toggle setImage:[UIImage systemImageNamed:@"gamecontroller"] forState:UIControlStateNormal];
    [owner.toggle setImage:[UIImage systemImageNamed:@"gamecontroller.fill"] forState:UIControlStateSelected];
    owner.toggle.accessibilityLabel = @"Show or hide gamepad";
    [owner.toggle addTarget:owner action:@selector(toggled:) forControlEvents:UIControlEventTouchUpInside];
    [view addSubview:owner.toggle];
    [NSNotificationCenter.defaultCenter addObserver:owner selector:@selector(inactive:) name:UIApplicationWillResignActiveNotification object:nil];
    printf("NATIVE TOUCH: pinch and hidden native virtual gamepad installed\n");
}
}
