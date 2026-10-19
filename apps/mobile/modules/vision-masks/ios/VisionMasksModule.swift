import CoreImage
import ExpoModulesCore
import ImageIO
import UIKit
import UniformTypeIdentifiers
import Vision

/// Apple Vision wrappers used by the capture flows:
///  - `foregroundMask`: salient-object mask of the garment on the floor plus its outline polygon;
///  - `personSegmentation`: person mask for the photo body-scan path;
///  - `bodyPose`: 2D body joints for the photo body-scan path.
public final class VisionMasksModule: Module {
  private let workQueue = DispatchQueue(label: "id.style.visionmasks", qos: .userInitiated)
  private let ciContext = CIContext(options: [.useSoftwareRenderer: false])

  public func definition() -> ModuleDefinition {
    Name("VisionMasks")

    Function("supportsForegroundMask") { () -> Bool in
      if #available(iOS 17.0, *) { return true }
      return false
    }

    AsyncFunction("foregroundMask") { (imageUri: String, promise: Promise) in
      self.workQueue.async {
        do {
          guard #available(iOS 17.0, *) else {
            throw VisionError.unsupported("Foreground masks need iOS 17 or later.")
          }
          let (cgImage, orientation) = try self.loadImage(imageUri)
          let result = try self.generateForegroundMask(cgImage, orientation: orientation)
          promise.resolve(result)
        } catch {
          promise.reject(VisionError.code(for: error), error.localizedDescription)
        }
      }
    }

    AsyncFunction("personSegmentation") { (imageUri: String, promise: Promise) in
      self.workQueue.async {
        do {
          let (cgImage, orientation) = try self.loadImage(imageUri)
          let result = try self.generatePersonSegmentation(cgImage, orientation: orientation)
          promise.resolve(result)
        } catch {
          promise.reject(VisionError.code(for: error), error.localizedDescription)
        }
      }
    }

    AsyncFunction("bodyPose") { (imageUri: String, promise: Promise) in
      self.workQueue.async {
        do {
          let (cgImage, orientation) = try self.loadImage(imageUri)
          let result = try self.detectBodyPose(cgImage, orientation: orientation)
          promise.resolve(result)
        } catch {
          promise.reject(VisionError.code(for: error), error.localizedDescription)
        }
      }
    }
  }

  // MARK: - Requests

  @available(iOS 17.0, *)
  private func generateForegroundMask(_ image: CGImage, orientation: CGImagePropertyOrientation) throws -> [String: Any] {
    let request = VNGenerateForegroundInstanceMaskRequest()
    let handler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    try handler.perform([request])
    guard let observation = request.results?.first else {
      throw VisionError.noResult("No foreground object found. Lay the garment on a plain floor.")
    }
    // A mask the size of the input image, 1.0 where any detected instance is present.
    let maskBuffer = try observation.generateScaledMaskForImage(forInstances: observation.allInstances, from: handler)
    let maskImage = try grayscaleImage(from: CIImage(cvPixelBuffer: maskBuffer))
    let polygon = try largestContour(of: maskImage)
    let url = try writePNG(maskImage, prefix: "foreground-mask")
    return [
      "maskUri": url.absoluteString,
      "imageWidth": maskImage.width,
      "imageHeight": maskImage.height,
      "polygon": polygon.map { [Double($0.x), Double($0.y)] },
    ]
  }

  private func generatePersonSegmentation(_ image: CGImage, orientation: CGImagePropertyOrientation) throws -> [String: Any] {
    let request = VNGeneratePersonSegmentationRequest()
    request.qualityLevel = .accurate
    request.outputPixelFormat = kCVPixelFormatType_OneComponent8
    let handler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    try handler.perform([request])
    guard let observation = request.results?.first else {
      throw VisionError.noResult("No person found in the photo.")
    }
    // The segmentation mask comes back at a reduced resolution; scale it to the input.
    let oriented = CIImage(cgImage: image).oriented(orientation)
    let mask = CIImage(cvPixelBuffer: observation.pixelBuffer)
    let scaleX = oriented.extent.width / mask.extent.width
    let scaleY = oriented.extent.height / mask.extent.height
    let scaled = mask.transformed(by: CGAffineTransform(scaleX: scaleX, y: scaleY))
    let maskImage = try grayscaleImage(from: scaled)
    let url = try writePNG(maskImage, prefix: "person-mask")
    return [
      "maskUri": url.absoluteString,
      "imageWidth": maskImage.width,
      "imageHeight": maskImage.height,
    ]
  }

  private func detectBodyPose(_ image: CGImage, orientation: CGImagePropertyOrientation) throws -> [String: Any] {
    let request = VNDetectHumanBodyPoseRequest()
    let handler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    try handler.perform([request])
    guard let observation = request.results?.first else {
      throw VisionError.noResult("No person found in the photo.")
    }
    let recognized = try observation.recognizedPoints(.all)
    var points: [String: [Double]] = [:]
    for (joint, point) in recognized where point.confidence > 0 {
      // Vision uses a bottom-left origin; the app works top-left.
      points[joint.rawValue.rawValue] = [Double(point.location.x), Double(1 - point.location.y), Double(point.confidence)]
    }
    let oriented = CIImage(cgImage: image).oriented(orientation)
    return [
      "points": points,
      "imageWidth": Int(oriented.extent.width),
      "imageHeight": Int(oriented.extent.height),
    ]
  }

  // MARK: - Contours

  /// Traces the mask with VNDetectContoursRequest, keeps the largest top-level contour and
  /// simplifies it to at most 200 points. Output is normalised with a top-left origin.
  private func largestContour(of mask: CGImage) throws -> [CGPoint] {
    let request = VNDetectContoursRequest()
    request.contrastAdjustment = 1.0
    request.detectsDarkOnLight = false
    request.maximumImageDimension = 1024
    let handler = VNImageRequestHandler(cgImage: mask, options: [:])
    try handler.perform([request])
    guard let observation = request.results?.first, observation.contourCount > 0 else {
      return []
    }
    var best: VNContour?
    var bestArea: CGFloat = 0
    for contour in observation.topLevelContours {
      let box = contour.normalizedPath.boundingBoxOfPath
      let area = box.width * box.height
      if area > bestArea {
        bestArea = area
        best = contour
      }
    }
    guard let contour = best else { return [] }

    var simplified = contour
    // Increase epsilon until the contour fits the point budget.
    var epsilon: Float = 0.002
    while simplified.pointCount > 200 && epsilon < 0.1 {
      simplified = try contour.polygonApproximation(epsilon: epsilon)
      epsilon *= 1.5
    }
    var points = simplified.normalizedPoints.map { CGPoint(x: CGFloat($0.x), y: CGFloat(1 - $0.y)) }
    if points.count > 200 {
      let stride = Double(points.count) / 200
      points = (0..<200).map { points[Int(Double($0) * stride)] }
    }
    return points
  }

  // MARK: - Image IO

  private func loadImage(_ uri: String) throws -> (CGImage, CGImagePropertyOrientation) {
    let url: URL
    if let parsed = URL(string: uri), parsed.scheme != nil {
      url = parsed
    } else {
      url = URL(fileURLWithPath: uri)
    }
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
      throw VisionError.badImage("Could not read image at \(uri).")
    }
    var orientation = CGImagePropertyOrientation.up
    if let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
       let raw = properties[kCGImagePropertyOrientation] as? UInt32,
       let parsed = CGImagePropertyOrientation(rawValue: raw) {
      orientation = parsed
    }
    return (image, orientation)
  }

  /// Renders a single-channel CIImage (0..1) to an 8-bit grayscale CGImage.
  private func grayscaleImage(from image: CIImage) throws -> CGImage {
    let extent = image.extent.integral
    let format = CIFormat.L8
    guard let colorSpace = CGColorSpace(name: CGColorSpace.linearGray) else {
      throw VisionError.render("No grayscale colour space available.")
    }
    guard let cgImage = ciContext.createCGImage(image, from: extent, format: format, colorSpace: colorSpace) else {
      throw VisionError.render("Could not render the mask.")
    }
    return cgImage
  }

  private func writePNG(_ image: CGImage, prefix: String) throws -> URL {
    let url = FileManager.default.temporaryDirectory
      .appendingPathComponent("\(prefix)-\(UUID().uuidString)")
      .appendingPathExtension("png")
    guard let destination = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
      throw VisionError.render("Could not create the PNG destination.")
    }
    CGImageDestinationAddImage(destination, image, nil)
    guard CGImageDestinationFinalize(destination) else {
      throw VisionError.render("Could not write the PNG.")
    }
    return url
  }
}

enum VisionError: LocalizedError {
  case unsupported(String)
  case badImage(String)
  case noResult(String)
  case render(String)

  var errorDescription: String? {
    switch self {
    case let .unsupported(message), let .badImage(message), let .noResult(message), let .render(message):
      return message
    }
  }

  static func code(for error: Error) -> String {
    guard let visionError = error as? VisionError else { return "ERR_VISION" }
    switch visionError {
    case .unsupported: return "ERR_UNSUPPORTED"
    case .badImage: return "ERR_BAD_IMAGE"
    case .noResult: return "ERR_NO_RESULT"
    case .render: return "ERR_RENDER"
    }
  }
}
