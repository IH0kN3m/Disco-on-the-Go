#if DISCO_NATIVE_RUNTIME_PROBE
import UIKit
import Darwin

/// Device-only CPU compatibility check. No Unity engine or gameplay is started.
@MainActor
final class NativeRuntimeProbeController: UIViewController {
    private let output = UITextView()
    private var started = false
    private var library: UnsafeMutableRawPointer?
    private var report: [String] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        output.translatesAutoresizingMaskIntoConstraints = false
        output.isEditable = false
        output.font = .monospacedSystemFont(ofSize: 19, weight: .regular)
        view.addSubview(output)
        NSLayoutConstraint.activate([
            output.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 24),
            output.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -24),
            output.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 24),
            output.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24)
        ])
        record("Native IL2CPP CPU diagnostic\nGameplay and Unity engine integration are absent.")
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        guard !started else { return }
        started = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
            guard let self else { return }
            do { try self.runProbe() }
            catch { self.record("FAILED: \(error)") }
        }
    }

    private func record(_ message: String) {
        report.append(message)
        output.text = report.joined(separator: "\n\n")
        let path = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("native-runtime.log")
        try? output.text.write(to: path, atomically: true, encoding: .utf8)
    }

    private func function<T>(_ name: String, as type: T.Type) throws -> T {
        guard let library, let address = dlsym(library, name), MemoryLayout<T>.size == MemoryLayout<UnsafeMutableRawPointer>.size else {
            throw ProbeError.failure("Missing native entry point: \(name)")
        }
        return unsafeBitCast(address, to: type)
    }

    private func runProbe() throws {
        let root = Bundle.main.bundleURL
        let module = root.appendingPathComponent("Frameworks/GameAssembly.framework/GameAssembly")
        let metadata = root.appendingPathComponent("NativeMetadata")
        guard FileManager.default.fileExists(atPath: metadata.appendingPathComponent("Metadata/global-metadata.dat").path) else {
            throw ProbeError.failure("Original metadata was not embedded")
        }
        record("Loading the derived ARM64 module on iPadOS…")
        library = dlopen(module.path, RTLD_NOW | RTLD_LOCAL)
        guard library != nil else {
            throw ProbeError.failure(dlerror().map { String(cString: $0) } ?? "dlopen failed")
        }
        record("Module loaded. Resolving the original runtime API…")
        typealias SetData = @convention(c) (UnsafePointer<CChar>?) -> Void
        typealias Initialize = @convention(c) (UnsafePointer<CChar>?) -> Int32
        typealias GetDomain = @convention(c) () -> UnsafeMutableRawPointer?
        typealias OpenAssembly = @convention(c) (UnsafeMutableRawPointer?, UnsafePointer<CChar>?) -> UnsafeMutableRawPointer?
        typealias GetImage = @convention(c) (UnsafeMutableRawPointer?) -> UnsafeMutableRawPointer?
        typealias FindClass = @convention(c) (UnsafeMutableRawPointer?, UnsafePointer<CChar>?, UnsafePointer<CChar>?) -> UnsafeMutableRawPointer?
        typealias FindMethod = @convention(c) (UnsafeMutableRawPointer?, UnsafePointer<CChar>?, Int32) -> UnsafeMutableRawPointer?
        typealias Invoke = @convention(c) (UnsafeMutableRawPointer?, UnsafeMutableRawPointer?, UnsafeMutablePointer<UnsafeMutableRawPointer?>?, UnsafeMutablePointer<UnsafeMutableRawPointer?>?) -> UnsafeMutableRawPointer?
        typealias Unbox = @convention(c) (UnsafeMutableRawPointer?) -> UnsafeMutableRawPointer?
        let setData = try function("il2cpp_set_data_dir", as: SetData.self)
        let initialize = try function("il2cpp_init", as: Initialize.self)
        let getDomain = try function("il2cpp_domain_get", as: GetDomain.self)
        let openAssembly = try function("il2cpp_domain_assembly_open", as: OpenAssembly.self)
        let getImage = try function("il2cpp_assembly_get_image", as: GetImage.self)
        let findClass = try function("il2cpp_class_from_name", as: FindClass.self)
        let findMethod = try function("il2cpp_class_get_method_from_name", as: FindMethod.self)
        let invoke = try function("il2cpp_runtime_invoke", as: Invoke.self)
        let unbox = try function("il2cpp_object_unbox", as: Unbox.self)
        metadata.path.withCString { setData($0) }
        record("Initializing the original metadata/runtime…")
        let initialized = "DiscoNativeCPUProbe".withCString { initialize($0) }
        guard initialized != 0, let domain = getDomain() else { throw ProbeError.failure("Runtime initialization failed") }
        record("Runtime initialized. Looking up Vector3.Dot…")
        guard let assembly = "UnityEngine.CoreModule.dll".withCString({ openAssembly(domain, $0) }),
              let image = getImage(assembly),
              let klass = "UnityEngine".withCString({ namespace in "Vector3".withCString { findClass(image, namespace, $0) } }),
              let method = "Dot".withCString({ findMethod(klass, $0, 2) }) else {
            throw ProbeError.failure("Original method metadata did not resolve")
        }
        var left: [Float] = [1, 2, 3]
        var right: [Float] = [4, 5, 6]
        var exception: UnsafeMutableRawPointer?
        let boxed = left.withUnsafeMutableBytes { a in
            right.withUnsafeMutableBytes { b in
                var parameters: [UnsafeMutableRawPointer?] = [a.baseAddress, b.baseAddress]
                return parameters.withUnsafeMutableBufferPointer { invoke(method, nil, $0.baseAddress, &exception) }
            }
        }
        guard exception == nil, let boxed, let result = unbox(boxed) else { throw ProbeError.failure("Original invocation failed or raised an exception") }
        let value = result.load(as: Float.self)
        guard value == 32 else { throw ProbeError.failure("Unexpected vector dot product: \(value)") }
        record("PASS: original ARM64 IL2CPP Vector3.Dot returned 32.\nThis establishes CPU/runtime compatibility for this check. Unity bindings, plugins, assets, and gameplay remain untested.")
        // The runtime retains native callbacks and threads; keep the library loaded for this process.
    }

    private enum ProbeError: Error {
        case failure(String)
    }
}
#endif
