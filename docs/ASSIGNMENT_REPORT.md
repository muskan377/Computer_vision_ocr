# ScoreVision — Assignment Documentation

## 1. Problem Statement
Extract bowling scoreboard information automatically from a supplied video using Computer Vision and OCR.

## 2. Input
`bowling_scoreboard.mp4` — 1920×1080, 30 FPS, approximately 57.83 seconds.

## 3. Approach
1. Read the video with OpenCV.
2. Sample frames at a fixed interval to reduce redundant OCR work.
3. Detect scoreboard presence using color/layout cues.
4. Crop a calibrated scoreboard ROI.
5. Preprocess the crop and run Tesseract OCR.
6. Repeat extraction across multiple scoreboard frames.
7. Keep the strongest readable observations and export JSON/CSV.
8. Save an annotated frame showing the detected region.

## 4. Screenshots to include in the PDF
- Input video/frame: `docs/screenshots/input_frame.jpg`
- Detected scoreboard: `docs/screenshots/detected_scoreboard.jpg`
- OCR output: `docs/screenshots/ocr_output.png`
- Final output: `docs/screenshots/final_output.json`

## 5. Important implementation note
The supplied recording keeps the scoreboard in a stable position, but includes bowling animations between scoreboard segments. A calibrated ROI is therefore more reliable and simpler than adding an unnecessary object-detection model.

## 6. Reproducibility
Install dependencies from `requirements.txt`, ensure Tesseract OCR is installed and available on PATH, then run `python app.py`.
