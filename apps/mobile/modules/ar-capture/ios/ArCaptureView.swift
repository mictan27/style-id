import ARKit
import CoreImage
import ExpoModulesCore
import ImageIO
import SceneKit
import UIKit
import UniformTypeIdentifiers

/// ARSession-backed camera preview.
///
/// `flatlay` mode tracks horizontal planes and reports the metric scale (cm per pixel)
/// of the camera image at the floor plane, so a garment laid flat can be measured.
/// `body` mode enables `sceneDepth` and, once `startBodyScan` is called, keeps
/// evenly spaced keyframes (by camera yaw) across a full turn, writing RGB, depth
/// (uint16 millimetres, high-confidence pixels only), confidence, intrinsics and the
/// camera transform for each one into a directory with a `manifest.json`.
final class ArCaptureView: ExpoView, ARSessionDelegate {
  /// The most recently created view; module functions address it.
  static weak var active: ArCaptureView?

  // Events
  let onPlaneDetected = EventDispatcher()
  let onFrame = EventDispatcher()
  let onKeyframe = EventDispatcher()
  let onScanComplete = EventDispatcher()
  let onError = EventDispatcher()

  // Props
  var mode: CaptureMode = .flatlay {
    didSet {
      if mode != oldValue, window != nil {
        configureSession()
      }
    }
  }

  private let arView = ARSCNView(frame: .zero)
  private let ciContext = CIContext(options: [.useSoftwareRenderer: false])
  private let writeQueue = DispatchQueue(label: "id.style.arcapture.write", qos: .userInitiated)

  // Flat-lay state
  private var floorAnchor: ARPlaneAnchor?
  private var frameCounter: UInt64 = 0

  // Body-scan state
  private var scanning = false
  private var targetKeyframes = 40
  private var capturedBuckets = Set<Int>()
  private var startYaw: Float?
  private var scanDirectory: URL?
  private var keyframeManifests: [[String: Any]] = []
  private var scanStartedAt: Date?

  required init(appContext: AppContext? = nil) {
    super.init(appContext: appContext)
    clipsToBounds = true
    arView.automaticallyUpdatesLighting = true
    arView.session.delegate = self
    addSubview(arView)
    ArCaptureView.active = self
  }

  override func layoutSubviews() {
    super.layoutSubviews()
    arView.frame = bounds
  }

  override func didMoveToWindow() {
    super.didMoveToWindow()
    if window != nil {
      ArCaptureView.active = self
      configureSession()
    } else {
      arView.session.pause()
    }
  }

  // MARK: - Session

  private func configureSession() {
    guard ARWorldTrackingConfiguration.isSupported else {
      onError(["code": "ERR_AR_UNSUPPORTED", "message": "ARKit world tracking is not supported on this device."])
      return
    }
    let configuration = ARWorldTrackingConfiguration()
    configuration.worldAlignment = .gravity
    switch mode {
    case .flatlay:
      configuration.planeDetection = [.horizontal]
    case .body:
      configuration.planeDetection = []
      if ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) {
        configuration.frameSemantics.insert(.sceneDepth)
      }
    }
    floorAnchor = nil
    arView.session.run(configuration, options: [.resetTracking, .removeExistingAnchors])
  }

  // MARK: - ARSessionDelegate

  func session(_ session: ARSession, didAdd anchors: [ARAnchor]) {
    updateFloorAnchor(from: anchors)
  }

  func session(_ session: ARSession, didUpdate anchors: [ARAnchor]) {
    updateFloorAnchor(from: anchors)
  }

  func session(_ session: ARSession, didFailWithError error: Error) {
    onError(["code": "ERR_AR_SESSION", "message": error.localizedDescription])
  }

  func session(_ session: ARSession, didUpdate frame: ARFrame) {
    frameCounter &+= 1

    if mode == .body, scanning {
      considerKeyframe(frame)
    }

    // Throttle JS-facing frame events to ~6 Hz; the session runs at 60 Hz.
    guard frameCounter % 10 == 0 else { return }

    var payload: [String: Any] = [
      "trackingState": trackingStateName(frame.camera.trackingState),
      "hasDepth": frame.sceneDepth != nil,
    ]
    if let reason = limitedReasonName(frame.camera.trackingState) {
      payload["limitedReason"] = reason
    }
    if mode == .body {
      payload["yawDeg"] = Double(frame.camera.eulerAngles.y * 180 / .pi)
    }
    onFrame(payload)

    if mode == .flatlay, let plane = floorAnchor, let distance = planeDistance(frame: frame, plane: plane) {
      let fx = frame.camera.intrinsics.columns.0.x
      onPlaneDetected([
        "distanceM": Double(distance),
        "cmPerPixel": Double(distance * 100 / fx),
        "extentM": [Double(planeExtent(plane).x), Double(planeExtent(plane).y)],
      ])
    }
  }

  private func updateFloorAnchor(from anchors: [ARAnchor]) {
    for case let plane as ARPlaneAnchor in anchors where plane.alignment == .horizontal {
      if let current = floorAnchor, current.identifier != plane.identifier {
        // Keep the largest horizontal plane: the floor or table the garment lies on.
        let currentArea = planeExtent(current).x * planeExtent(current).y
        let newArea = planeExtent(plane).x * planeExtent(plane).y
        if newArea > currentArea { floorAnchor = plane }
      } else {
        floorAnchor = plane
      }
    }
  }

  private func planeExtent(_ plane: ARPlaneAnchor) -> simd_float2 {
    return simd_float2(plane.planeExtent.width, plane.planeExtent.height)
  }

  /// Distance from the camera to the plane along the camera's optical axis (metres).
  private func planeDistance(frame: ARFrame, plane: ARPlaneAnchor) -> Float? {
    let cameraTransform = frame.camera.transform
    let origin = simd_make_float3(cameraTransform.columns.3)
    // ARKit cameras look down their local -Z axis.
    let forward = -simd_normalize(simd_make_float3(cameraTransform.columns.2))

    let planeTransform = plane.transform
    let normal = simd_normalize(simd_make_float3(planeTransform.columns.1))
    let centerLocal = simd_make_float4(plane.center, 1)
    let center = simd_make_float3(simd_mul(planeTransform, centerLocal))

    let denominator = simd_dot(forward, normal)
    guard abs(denominator) > 1e-4 else { return nil }
    let t = simd_dot(center - origin, normal) / denominator
    return t > 0.05 ? t : nil
  }

  // MARK: - Flat-lay capture

  func captureFlatLay(promise: Promise) {
    guard mode == .flatlay else {
      promise.reject("ERR_WRONG_MODE", "captureFlatLay requires mode = 'flatlay'.")
      return
    }
    guard let frame = arView.session.currentFrame else {
      promise.reject("ERR_NO_FRAME", "The AR session has not produced a frame yet.")
      return
    }
    guard let plane = floorAnchor, let distance = planeDistance(frame: frame, plane: plane) else {
      promise.reject("ERR_NO_PLANE", "No floor plane detected yet. Move the phone slowly over the garment.")
      return
    }

    let pixelBuffer = frame.capturedImage
    let intrinsics = frame.camera.intrinsics
    let fx = intrinsics.columns.0.x
    let fy = intrinsics.columns.1.y
    let cx = intrinsics.columns.2.x
    let cy = intrinsics.columns.2.y
    let sensorHeight = Float(CVPixelBufferGetHeight(pixelBuffer))

    writeQueue.async { [ciContext] in
      // The sensor image is landscape; rotate 90° clockwise so the saved JPEG is portrait,
      // matching how the user holds the phone over the garment. For a clockwise rotation
      // (x', y') = (H - y, x), so fx/fy swap and the principal point moves accordingly.
      let image = CIImage(cvPixelBuffer: pixelBuffer).oriented(.right)
      let rotated: [Double] = [Double(fy), Double(fx), Double(sensorHeight - cy), Double(cx)]
      let colorSpace = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()
      guard let jpeg = ciContext.jpegRepresentation(of: image, colorSpace: colorSpace, options: [
        kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.92,
      ]) else {
        promise.reject("ERR_ENCODE", "Could not encode the captured frame.")
        return
      }
      let url = FileManager.default.temporaryDirectory
        .appendingPathComponent("flatlay-\(UUID().uuidString)")
        .appendingPathExtension("jpg")
      do {
        try jpeg.write(to: url, options: .atomic)
      } catch {
        promise.reject("ERR_WRITE", error.localizedDescription)
        return
      }
      promise.resolve([
        "imageUri": url.absoluteString,
        "imageWidth": Int(image.extent.width),
        "imageHeight": Int(image.extent.height),
        "cmPerPixel": Double(distance * 100 / fx),
        "intrinsics": rotated,
        "planeDistanceM": Double(distance),
      ])
    }
  }

  // MARK: - Body scan

  func startBodyScan(targetKeyframes: Int) throws {
    guard mode == .body else {
      throw NSError(domain: "ArCapture", code: 1, userInfo: [NSLocalizedDescriptionKey: "startBodyScan requires mode = 'body'."])
    }
    let directory = FileManager.default.temporaryDirectory
      .appendingPathComponent("bodyscan-\(UUID().uuidString)", isDirectory: true)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    scanDirectory = directory
    self.targetKeyframes = targetKeyframes
    capturedBuckets.removeAll()
    keyframeManifests.removeAll()
    startYaw = nil
    scanStartedAt = Date()
    scanning = true
  }

  func stopScan(promise: Promise) {
    let wasScanning = scanning
    scanning = false
    guard wasScanning || !keyframeManifests.isEmpty, let directory = scanDirectory else {
      promise.resolve(nil)
      return
    }
    finishScan(directory: directory, promise: promise)
  }

  private func considerKeyframe(_ frame: ARFrame) {
    guard case .normal = frame.camera.trackingState else { return }
    guard let depth = frame.sceneDepth, let confidenceMap = depth.confidenceMap else { return }

    let yaw = frame.camera.eulerAngles.y
    if startYaw == nil { startYaw = yaw }
    let relative = normalizedAngle(yaw - (startYaw ?? yaw))
    let bucketWidth = (2 * Float.pi) / Float(targetKeyframes)
    let bucket = min(targetKeyframes - 1, Int(relative / bucketWidth))
    guard !capturedBuckets.contains(bucket), let directory = scanDirectory else { return }
    capturedBuckets.insert(bucket)

    let index = keyframeManifests.count
    let yawDeg = Double(relative * 180 / .pi)

    // Pull everything we need out of the frame on this thread; ARFrames must not be retained.
    let rgb = CIImage(cvPixelBuffer: frame.capturedImage)
    let depthPixels = readFloat32(depth.depthMap)
    let confidencePixels = readUInt8(confidenceMap)
    let intrinsics = frame.camera.intrinsics
    let transform = frame.camera.transform
    let timestamp = frame.timestamp
    let imageSize = frame.camera.imageResolution

    var manifest: [String: Any] = [
      "index": index,
      "timestamp": timestamp,
      "yaw_deg": yawDeg,
      "rgb": "kf_\(pad(index)).jpg",
      "depth": "kf_\(pad(index))_depth.png",
      "confidence": "kf_\(pad(index))_conf.png",
      "image_size": [Int(imageSize.width), Int(imageSize.height)],
      "depth_size": [depthPixels.width, depthPixels.height],
      "intrinsics": [
        Double(intrinsics.columns.0.x), Double(intrinsics.columns.1.y),
        Double(intrinsics.columns.2.x), Double(intrinsics.columns.2.y),
      ],
      "camera_transform": flatten(transform),
    ]
    manifest["orientation"] = "sensor_landscape_right"
    keyframeManifests.append(manifest)

    let count = keyframeManifests.count
    onKeyframe(["index": index, "count": count, "target": targetKeyframes, "yawDeg": yawDeg])

    writeQueue.async { [ciContext] in
      do {
        let colorSpace = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()
        if let jpeg = ciContext.jpegRepresentation(of: rgb, colorSpace: colorSpace, options: [
          kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.9,
        ]) {
          try jpeg.write(to: directory.appendingPathComponent("kf_\(self.pad(index)).jpg"), options: .atomic)
        }
        // Depth in millimetres; pixels whose confidence is not `.high` are zeroed.
        var depthMM = [UInt16](repeating: 0, count: depthPixels.values.count)
        for i in 0..<depthPixels.values.count {
          let keep = i < confidencePixels.values.count && confidencePixels.values[i] == UInt8(ARConfidenceLevel.high.rawValue)
          if keep {
            let mm = depthPixels.values[i] * 1000
            depthMM[i] = mm.isFinite ? UInt16(clamping: Int(mm.rounded())) : 0
          }
        }
        try Self.writeGray16PNG(depthMM, width: depthPixels.width, height: depthPixels.height,
                                to: directory.appendingPathComponent("kf_\(self.pad(index))_depth.png"))
        try Self.writeGray8PNG(confidencePixels.values, width: confidencePixels.width, height: confidencePixels.height,
                               to: directory.appendingPathComponent("kf_\(self.pad(index))_conf.png"))
      } catch {
        DispatchQueue.main.async {
          self.onError(["code": "ERR_KEYFRAME_WRITE", "message": error.localizedDescription])
        }
      }
    }

    if capturedBuckets.count >= targetKeyframes {
      scanning = false
      finishScan(directory: directory, promise: nil)
    }
  }

  private func finishScan(directory: URL, promise: Promise?) {
    let manifests = keyframeManifests
    let startedAt = scanStartedAt ?? Date()
    let count = manifests.count
    writeQueue.async {
      let manifest: [String: Any] = [
        "version": 1,
        "device": UIDevice.current.model,
        "system_version": UIDevice.current.systemVersion,
        "started_at": ISO8601DateFormatter().string(from: startedAt),
        "finished_at": ISO8601DateFormatter().string(from: Date()),
        "keyframe_count": count,
        "depth_unit": "mm",
        "depth_confidence_kept": "high",
        "keyframes": manifests,
      ]
      do {
        let data = try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: directory.appendingPathComponent("manifest.json"), options: .atomic)
      } catch {
        DispatchQueue.main.async {
          promise?.reject("ERR_MANIFEST", error.localizedDescription)
        }
        return
      }
      let result: [String: Any] = ["directoryPath": directory.path, "keyframeCount": count]
      DispatchQueue.main.async {
        self.onScanComplete(result)
        promise?.resolve(result)
      }
    }
  }

  // MARK: - Helpers

  private struct Plane<T> {
    let width: Int
    let height: Int
    let values: [T]
  }

  private func readFloat32(_ buffer: CVPixelBuffer) -> Plane<Float32> {
    CVPixelBufferLockBaseAddress(buffer, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
    let width = CVPixelBufferGetWidth(buffer)
    let height = CVPixelBufferGetHeight(buffer)
    let bytesPerRow = CVPixelBufferGetBytesPerRow(buffer)
    guard let base = CVPixelBufferGetBaseAddress(buffer) else {
      return Plane(width: width, height: height, values: [])
    }
    var values = [Float32](repeating: 0, count: width * height)
    for y in 0..<height {
      let row = base.advanced(by: y * bytesPerRow).assumingMemoryBound(to: Float32.self)
      for x in 0..<width {
        values[y * width + x] = row[x]
      }
    }
    return Plane(width: width, height: height, values: values)
  }

  private func readUInt8(_ buffer: CVPixelBuffer) -> Plane<UInt8> {
    CVPixelBufferLockBaseAddress(buffer, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
    let width = CVPixelBufferGetWidth(buffer)
    let height = CVPixelBufferGetHeight(buffer)
    let bytesPerRow = CVPixelBufferGetBytesPerRow(buffer)
    guard let base = CVPixelBufferGetBaseAddress(buffer) else {
      return Plane(width: width, height: height, values: [])
    }
    var values = [UInt8](repeating: 0, count: width * height)
    for y in 0..<height {
      let row = base.advanced(by: y * bytesPerRow).assumingMemoryBound(to: UInt8.self)
      for x in 0..<width {
        values[y * width + x] = row[x]
      }
    }
    return Plane(width: width, height: height, values: values)
  }

  private static func writeGray16PNG(_ values: [UInt16], width: Int, height: Int, to url: URL) throws {
    let data = values.withUnsafeBufferPointer { Data(buffer: $0) }
    guard let provider = CGDataProvider(data: data as CFData) else { throw ImageWriteError.provider }
    let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue | CGBitmapInfo.byteOrder16Little.rawValue)
    guard let image = CGImage(
      width: width, height: height, bitsPerComponent: 16, bitsPerPixel: 16, bytesPerRow: width * 2,
      space: CGColorSpaceCreateDeviceGray(), bitmapInfo: bitmapInfo, provider: provider,
      decode: nil, shouldInterpolate: false, intent: .defaultIntent
    ) else { throw ImageWriteError.image }
    try writePNG(image, to: url)
  }

  private static func writeGray8PNG(_ values: [UInt8], width: Int, height: Int, to url: URL) throws {
    let data = Data(values)
    guard let provider = CGDataProvider(data: data as CFData) else { throw ImageWriteError.provider }
    let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue)
    guard let image = CGImage(
      width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: width,
      space: CGColorSpaceCreateDeviceGray(), bitmapInfo: bitmapInfo, provider: provider,
      decode: nil, shouldInterpolate: false, intent: .defaultIntent
    ) else { throw ImageWriteError.image }
    try writePNG(image, to: url)
  }

  private static func writePNG(_ image: CGImage, to url: URL) throws {
    guard let destination = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
      throw ImageWriteError.destination
    }
    CGImageDestinationAddImage(destination, image, nil)
    guard CGImageDestinationFinalize(destination) else { throw ImageWriteError.finalize }
  }

  private enum ImageWriteError: Error {
    case provider, image, destination, finalize
  }

  private func normalizedAngle(_ angle: Float) -> Float {
    var a = angle.truncatingRemainder(dividingBy: 2 * .pi)
    if a < 0 { a += 2 * .pi }
    return a
  }

  private func pad(_ index: Int) -> String {
    return String(format: "%03d", index)
  }

  private func flatten(_ m: simd_float4x4) -> [Double] {
    return [m.columns.0, m.columns.1, m.columns.2, m.columns.3].flatMap { c in
      [Double(c.x), Double(c.y), Double(c.z), Double(c.w)]
    }
  }

  private func trackingStateName(_ state: ARCamera.TrackingState) -> String {
    switch state {
    case .notAvailable: return "notAvailable"
    case .limited: return "limited"
    case .normal: return "normal"
    }
  }

  private func limitedReasonName(_ state: ARCamera.TrackingState) -> String? {
    guard case let .limited(reason) = state else { return nil }
    switch reason {
    case .initializing: return "initializing"
    case .excessiveMotion: return "excessiveMotion"
    case .insufficientFeatures: return "insufficientFeatures"
    case .relocalizing: return "relocalizing"
    @unknown default: return "limited"
    }
  }
}
