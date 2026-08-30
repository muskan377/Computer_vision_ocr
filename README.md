
# ScoreVision — Bowling Scoreboard Data Extraction

Computer Vision solution for extracting bowling scoreboard data from `bowling_scoreboard.mp4`.

## What it does

Video → frame sampling → scoreboard detection → calibrated ROI → image preprocessing → OCR → multi-frame consensus → JSON/CSV output → annotated result.

The supplied video was inspected first. The scoreboard remains stationary while some frames switch to bowling animations, so a configurable fixed ROI is used instead of an unnecessary object detector.

## Run

### Web UI
```bash
python -m pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

### CLI
```bash
python -c "from src.pipeline import analyze; print(analyze('bowling_scoreboard.mp4'))"
```

Tesseract OCR must be installed and available as `tesseract` on PATH.

## Outputs

Each run creates a timestamp/job folder under `output/` containing:
- `scoreboard_data.json`
- `scoreboard_data.csv`
- representative frames and scoreboard crops
- `annotated/best_frame.jpg`

## Assignment submission

Use the UI for the demo recording: show the input video, run the analyzer, show the detected green ROI and then open the JSON/CSV result. For the documentation PDF, capture the input frame, detected scoreboard, OCR/annotated frame and final structured output.

## Project structure

- `app.py` — Flask web UI + API
- `src/config.py` — calibrated ROI and scoreboard geometry
- `src/scoreboard.py` — preprocessing, OCR, parsing and temporal consensus
- `src/pipeline.py` — end-to-end video processing
- `templates/`, `static/` — polished dashboard UI


## Windows OCR prerequisite

Install Tesseract OCR separately and make sure `tesseract.exe` is on PATH. Then run:

```bat
run.bat
```

Or:

```bat
python app.py
```

The web app runs locally at `http://127.0.0.1:5000`.
