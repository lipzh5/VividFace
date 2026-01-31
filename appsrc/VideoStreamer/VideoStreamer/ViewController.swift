//
//  ViewController.swift
//  VideoStreamer
//
//  Created by Peizhen Li on 17/7/2025.
//

import UIKit
import AVFoundation

class ViewController: UIViewController, AVCaptureVideoDataOutputSampleBufferDelegate {
    var session = AVCaptureSession()

    override func viewDidLoad() {
        super.viewDidLoad()

        session.sessionPreset = .medium
        guard let camera = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: camera) else { return }
        session.addInput(input)

        let output = AVCaptureVideoDataOutput()
        output.setSampleBufferDelegate(self, queue: DispatchQueue(label: "videoQueue"))
        session.addOutput(output)

        session.startRunning()
    }

    func captureOutput(_ output: AVCaptureOutput,
                       didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {

        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()
        if let cgImage = context.createCGImage(ciImage, from: ciImage.extent) {
            let image = UIImage(cgImage: cgImage)
            sendFrame(image)
        }
    }

    func sendFrame(_ image: UIImage) {
        guard let url = URL(string: "http://10.6.39.74:5000/stream"),
              let jpegData = image.jpegData(compressionQuality: 0.8) else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")

        let task = URLSession.shared.uploadTask(with: request, from: jpegData)
        task.resume()
    }
}
