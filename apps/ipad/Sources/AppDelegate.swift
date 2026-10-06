import UIKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {}

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: scene)
        #if DISCO_NATIVE_RUNTIME_PROBE
        window.rootViewController = NativeRuntimeProbeController()
        #else
        window.rootViewController = TouchViewController()
        #endif
        window.makeKeyAndVisible()
        self.window = window
    }

    func sceneWillResignActive(_ scene: UIScene) {
        (window?.rootViewController as? TouchViewController)?.cancelInput()
    }
}
