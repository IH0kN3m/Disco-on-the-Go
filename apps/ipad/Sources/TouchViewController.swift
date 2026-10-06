import UIKit

/// Exercises the input contract without pretending to execute recovered game code.
final class TouchViewController: UIViewController, UIGestureRecognizerDelegate, GameActionSink {
    private let canvas = TouchCanvas()
    private let status = UILabel()
    private let hint = UILabel()
    private let tap = UITapGestureRecognizer()
    private let hold = UILongPressGestureRecognizer()
    private let pan = UIPanGestureRecognizer()
    private let pinch = UIPinchGestureRecognizer()
    private var cancelling = false

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.06, green: 0.07, blue: 0.10, alpha: 1)
        let title = UILabel()
        title.text = "Disco Port Lab"
        title.font = .preferredFont(forTextStyle: .title1)
        title.textColor = .white
        title.adjustsFontForContentSizeCategory = true
        hint.text = "Touch harness · Unity runtime pending\nTap to place · hold to inspect · two fingers to pan or zoom"
        hint.textColor = .lightGray
        hint.font = .preferredFont(forTextStyle: .body)
        hint.numberOfLines = 0
        hint.adjustsFontForContentSizeCategory = true
        status.text = "Ready"
        status.font = .monospacedSystemFont(ofSize: 15, weight: .regular)
        status.textColor = .white
        status.numberOfLines = 2
        let reset = UIButton(type: .system)
        reset.setTitle("Reset", for: .normal)
        reset.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        reset.addTarget(self, action: #selector(resetHarness), for: .touchUpInside)
        reset.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true
        let footer = UIStackView(arrangedSubviews: [status, reset])
        footer.spacing = 20
        let stack = UIStackView(arrangedSubviews: [title, hint, canvas, footer])
        stack.axis = .vertical
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        let safe = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: safe.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: safe.trailingAnchor, constant: -24),
            stack.topAnchor.constraint(equalTo: safe.topAnchor, constant: 16),
            stack.bottomAnchor.constraint(equalTo: safe.bottomAnchor, constant: -12),
            canvas.heightAnchor.constraint(greaterThanOrEqualToConstant: 100)
        ])
        canvas.isMultipleTouchEnabled = true
        canvas.contentMode = .redraw
        canvas.isAccessibilityElement = true
        canvas.accessibilityLabel = "Input test canvas"
        tap.addTarget(self, action: #selector(tapped(_:)))
        hold.addTarget(self, action: #selector(held(_:)))
        pan.addTarget(self, action: #selector(panned(_:)))
        pan.minimumNumberOfTouches = 2
        pan.maximumNumberOfTouches = 2
        pinch.addTarget(self, action: #selector(pinched(_:)))
        for recognizer in [tap, hold, pan, pinch] {
            recognizer.delegate = self
            canvas.addGestureRecognizer(recognizer)
        }
        tap.require(toFail: hold)
        tap.require(toFail: pan)
        tap.require(toFail: pinch)
    }

    private var router: InputRouter? {
        canvas.viewport.map(InputRouter.init)
    }

    @objc private func tapped(_ recognizer: UITapGestureRecognizer) {
        guard recognizer.state == .ended, let action = router?.activate(at: recognizer.location(in: canvas)) else { return }
        accept(action)
    }

    @objc private func held(_ recognizer: UILongPressGestureRecognizer) {
        if recognizer.state == .began, let action = router?.inspect(at: recognizer.location(in: canvas)) { accept(action) }
        if recognizer.state == .cancelled { cancelInput() }
    }

    @objc private func panned(_ recognizer: UIPanGestureRecognizer) {
        if recognizer.state == .changed, let action = router?.pan(translation: recognizer.translation(in: canvas), at: recognizer.location(in: canvas)) {
            accept(action)
            recognizer.setTranslation(.zero, in: canvas)
        }
        if recognizer.state == .cancelled { cancelInput() }
    }

    @objc private func pinched(_ recognizer: UIPinchGestureRecognizer) {
        if recognizer.state == .changed, let action = router?.zoom(scale: recognizer.scale, at: recognizer.location(in: canvas)) {
            accept(action)
            recognizer.scale = 1
        }
        if recognizer.state == .cancelled { cancelInput() }
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        (gestureRecognizer === pan && otherGestureRecognizer === pinch) || (gestureRecognizer === pinch && otherGestureRecognizer === pan)
    }

    func accept(_ action: GameAction) {
        switch action {
        case .activate(let point):
            canvas.marker = point
            status.text = String(format: "Activate %.3f, %.3f", point.x, point.y)
        case .inspect(let point):
            status.text = String(format: "Inspect %.3f, %.3f", point.x, point.y)
        case .pan(let delta):
            canvas.cameraOffset.x += delta.x
            canvas.cameraOffset.y += delta.y
            status.text = String(format: "Pan %.3f, %.3f", delta.x, delta.y)
        case .zoom(let scale, _):
            canvas.zoom = max(0.5, min(3, canvas.zoom * scale))
            status.text = String(format: "Zoom %.2f×", canvas.zoom)
        case .cancel:
            status.text = "Input cancelled"
        }
        canvas.setNeedsDisplay()
    }

    func cancelInput() {
        guard !cancelling else { return }
        cancelling = true
        defer { cancelling = false }
        for recognizer in [tap, hold, pan, pinch] { recognizer.isEnabled = false }
        for recognizer in [tap, hold, pan, pinch] { recognizer.isEnabled = true }
        accept(.cancel)
    }

    @objc private func resetHarness() {
        canvas.marker = CGPoint(x: 0.5, y: 0.5)
        canvas.cameraOffset = .zero
        canvas.zoom = 1
        canvas.setNeedsDisplay()
        status.text = "Reset"
    }
}

final class TouchCanvas: UIView {
    var marker = CGPoint(x: 0.5, y: 0.5)
    var cameraOffset = CGPoint.zero
    var zoom = 1.0
    var viewport: GameViewport? { GameViewport(bounds: bounds, aspectRatio: 4.0 / 3.0) }

    override func draw(_ rect: CGRect) {
        guard let context = UIGraphicsGetCurrentContext(), let viewport else { return }
        context.setFillColor(UIColor.black.cgColor)
        context.fill(bounds)
        context.setFillColor(UIColor(red: 0.10, green: 0.13, blue: 0.18, alpha: 1).cgColor)
        context.fill(viewport.rect)
        context.saveGState()
        context.clip(to: viewport.rect)
        let center = CGPoint(x: viewport.rect.midX, y: viewport.rect.midY)
        context.translateBy(x: center.x + cameraOffset.x * viewport.rect.width, y: center.y - cameraOffset.y * viewport.rect.height)
        context.scaleBy(x: zoom, y: zoom)
        context.translateBy(x: -center.x, y: -center.y)
        context.setStrokeColor(UIColor.white.withAlphaComponent(0.12).cgColor)
        context.setLineWidth(1 / zoom)
        for i in 0...12 {
            let x = viewport.rect.minX + viewport.rect.width * Double(i) / 12
            context.move(to: CGPoint(x: x, y: viewport.rect.minY))
            context.addLine(to: CGPoint(x: x, y: viewport.rect.maxY))
        }
        for i in 0...9 {
            let y = viewport.rect.minY + viewport.rect.height * Double(i) / 9
            context.move(to: CGPoint(x: viewport.rect.minX, y: y))
            context.addLine(to: CGPoint(x: viewport.rect.maxX, y: y))
        }
        context.strokePath()
        context.restoreGState()
        // Marker remains in viewport space so the coordinate contract is visible.
        let point = viewport.viewPoint(from: marker)
        context.setFillColor(UIColor.systemOrange.cgColor)
        context.fillEllipse(in: CGRect(x: point.x - 12, y: point.y - 12, width: 24, height: 24))
    }
}
