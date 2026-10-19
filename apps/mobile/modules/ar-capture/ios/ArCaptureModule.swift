import ARKit
import ExpoModulesCore

enum CaptureMode: String, Enumerable {
  case flatlay
  case body
}

struct BodyScanOptions: Record {
  @Field var keyframes: Int = 40
}

public final class ArCaptureModule: Module {
  public func definition() -> ModuleDefinition {
    Name("ArCapture")

    /// LiDAR (or equivalent) depth is exposed by ARKit as the `sceneDepth` frame semantic.
    Function("isLidarAvailable") { () -> Bool in
      return ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth)
    }

    AsyncFunction("captureFlatLay") { (promise: Promise) in
      guard let view = ArCaptureView.active else {
        promise.reject("ERR_NO_VIEW", "Mount an ArCaptureView in flatlay mode before capturing.")
        return
      }
      view.captureFlatLay(promise: promise)
    }.runOnQueue(.main)

    AsyncFunction("startBodyScan") { (options: BodyScanOptions?, promise: Promise) in
      guard let view = ArCaptureView.active else {
        promise.reject("ERR_NO_VIEW", "Mount an ArCaptureView in body mode before scanning.")
        return
      }
      do {
        try view.startBodyScan(targetKeyframes: max(8, options?.keyframes ?? 40))
        promise.resolve(nil)
      } catch {
        promise.reject("ERR_SCAN_START", error.localizedDescription)
      }
    }.runOnQueue(.main)

    AsyncFunction("stopScan") { (promise: Promise) in
      guard let view = ArCaptureView.active else {
        promise.resolve(nil)
        return
      }
      view.stopScan(promise: promise)
    }.runOnQueue(.main)

    View(ArCaptureView.self) {
      Events("onPlaneDetected", "onFrame", "onKeyframe", "onScanComplete", "onError")

      Prop("mode") { (view: ArCaptureView, mode: CaptureMode) in
        view.mode = mode
      }
    }
  }
}
