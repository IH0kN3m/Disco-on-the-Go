import XCTest
import CoreGraphics
@testable import InputCore

final class InputTests: XCTestCase {
    func testLetterboxRejectsOutsideAndFlipsOrigin() throws {
        let viewport = try XCTUnwrap(GameViewport(bounds: CGRect(x: 0, y: 0, width: 1200, height: 800), aspectRatio: 4.0 / 3.0))
        XCTAssertEqual(viewport.rect.width, 1066.6666666667, accuracy: 0.0001)
        XCTAssertNil(viewport.gamePoint(from: CGPoint(x: 10, y: 400)))
        XCTAssertEqual(viewport.gamePoint(from: CGPoint(x: viewport.rect.minX, y: viewport.rect.minY)), CGPoint(x: 0, y: 1))
        XCTAssertEqual(viewport.gamePoint(from: CGPoint(x: viewport.rect.maxX, y: viewport.rect.maxY)), CGPoint(x: 1, y: 0))
    }

    func testPortraitLetterboxAndInsetRoundTrip() throws {
        let viewport = try XCTUnwrap(GameViewport(bounds: CGRect(x: 40, y: 60, width: 800, height: 1200), aspectRatio: 4.0 / 3.0))
        XCTAssertEqual(viewport.rect.height, 600)
        XCTAssertNil(viewport.gamePoint(from: CGPoint(x: 440, y: 100)))
        let point = CGPoint(x: 0.35, y: 0.8)
        let result = try XCTUnwrap(viewport.gamePoint(from: viewport.viewPoint(from: point)))
        XCTAssertEqual(result.x, point.x, accuracy: 0.000001)
        XCTAssertEqual(result.y, point.y, accuracy: 0.000001)
    }

    func testUIConsumesEveryWorldGesture() throws {
        let router = InputRouter(viewport: try XCTUnwrap(GameViewport(bounds: CGRect(x: 0, y: 0, width: 100, height: 100), aspectRatio: 1)))
        let center = CGPoint(x: 50, y: 50)
        XCTAssertNil(router.activate(at: center, consumedByUI: true))
        XCTAssertNil(router.inspect(at: center, consumedByUI: true))
        XCTAssertNil(router.pan(translation: CGPoint(x: 20, y: 10), at: center, consumedByUI: true))
        XCTAssertNil(router.zoom(scale: 2, at: center, consumedByUI: true))
        XCTAssertEqual(router.pan(translation: CGPoint(x: 20, y: 10), at: center), .pan(CGPoint(x: 0.2, y: -0.1)))
    }

    func testRejectsInvalidGeometryAndGestureValues() throws {
        XCTAssertNil(GameViewport(bounds: .zero, aspectRatio: 1))
        XCTAssertNil(GameViewport(bounds: CGRect(x: 0, y: 0, width: 100, height: 100), aspectRatio: .infinity))
        let router = InputRouter(viewport: try XCTUnwrap(GameViewport(bounds: CGRect(x: 0, y: 0, width: 100, height: 100), aspectRatio: 1)))
        XCTAssertNil(router.activate(at: CGPoint(x: Double.nan, y: 10)))
        XCTAssertNil(router.zoom(scale: -1, at: CGPoint(x: 50, y: 50)))
        XCTAssertNil(router.zoom(scale: .nan, at: CGPoint(x: 50, y: 50)))
        XCTAssertNil(router.pan(translation: CGPoint(x: Double.infinity, y: 0), at: CGPoint(x: 50, y: 50)))
    }
}
