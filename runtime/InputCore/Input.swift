import Foundation
import CoreGraphics

/// UIKit points enter here; game coordinates leave with a bottom-left origin.
public struct GameViewport: Equatable, Sendable {
    public let rect: CGRect

    public init?(bounds: CGRect, aspectRatio: Double) {
        guard bounds.width.isFinite, bounds.height.isFinite,
              bounds.origin.x.isFinite, bounds.origin.y.isFinite,
              bounds.width > 0, bounds.height > 0, aspectRatio.isFinite, aspectRatio > 0 else { return nil }
        let width = min(bounds.width, bounds.height * aspectRatio)
        let height = width / aspectRatio
        guard width > 0, height > 0, width.isFinite, height.isFinite else { return nil }
        rect = CGRect(x: bounds.midX - width / 2, y: bounds.midY - height / 2, width: width, height: height)
    }

    public func gamePoint(from point: CGPoint) -> CGPoint? {
        guard point.x.isFinite, point.y.isFinite,
              point.x >= rect.minX, point.x <= rect.maxX,
              point.y >= rect.minY, point.y <= rect.maxY else { return nil }
        return CGPoint(x: max(0, min(1, (point.x - rect.minX) / rect.width)),
                       y: max(0, min(1, 1 - (point.y - rect.minY) / rect.height)))
    }

    public func viewPoint(from gamePoint: CGPoint) -> CGPoint {
        CGPoint(x: rect.minX + gamePoint.x * rect.width, y: rect.minY + (1 - gamePoint.y) * rect.height)
    }

    public func gameDelta(from translation: CGPoint) -> CGPoint {
        CGPoint(x: translation.x / rect.width, y: -translation.y / rect.height)
    }
}

public enum GameAction: Equatable, Sendable {
    case activate(CGPoint)
    case inspect(CGPoint)
    case pan(CGPoint)
    case zoom(scale: Double, anchor: CGPoint)
    case cancel
}

/// Policy boundary: UI-consumed touches never enter the world action stream.
public struct InputRouter: Sendable {
    public var viewport: GameViewport

    public init(viewport: GameViewport) { self.viewport = viewport }

    public func activate(at point: CGPoint, consumedByUI: Bool = false) -> GameAction? {
        guard !consumedByUI, let game = viewport.gamePoint(from: point) else { return nil }
        return .activate(game)
    }

    public func inspect(at point: CGPoint, consumedByUI: Bool = false) -> GameAction? {
        guard !consumedByUI, let game = viewport.gamePoint(from: point) else { return nil }
        return .inspect(game)
    }

    public func pan(translation: CGPoint, at point: CGPoint, consumedByUI: Bool = false) -> GameAction? {
        guard !consumedByUI, viewport.gamePoint(from: point) != nil,
              translation.x.isFinite, translation.y.isFinite else { return nil }
        return .pan(viewport.gameDelta(from: translation))
    }

    public func zoom(scale: Double, at point: CGPoint, consumedByUI: Bool = false) -> GameAction? {
        guard !consumedByUI, scale.isFinite, scale > 0,
              let game = viewport.gamePoint(from: point) else { return nil }
        return .zoom(scale: scale, anchor: game)
    }
}

/// Recovered gameplay will implement this boundary; the current app is a harness.
@MainActor public protocol GameActionSink: AnyObject {
    func accept(_ action: GameAction)
}
