from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import cv2

from .config import (
    OUTPUT_DIR,
    SAMPLE_EVERY_SECONDS,
    SCOREBOARD_ROI,
)

from .scoreboard import (
    scoreboard_visible,
    crop_scoreboard,
    extract_frame,
    merge_observations,
)


# =========================================================
# VIDEO INFO
# =========================================================

def video_info(
    path: Path | str,
) -> dict:

    cap = cv2.VideoCapture(
        str(path)
    )

    if not cap.isOpened():
        raise ValueError(
            f"Unable to open video: {path}"
        )

    fps = (
        cap.get(
            cv2.CAP_PROP_FPS
        )
        or 30.0
    )

    frames = int(
        cap.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    duration = (
        frames / fps
        if fps
        else 0
    )

    cap.release()

    return {
        "width": width,
        "height": height,
        "fps": round(
            fps,
            2,
        ),
        "frames": frames,
        "duration_seconds":
            round(
                duration,
                2,
            ),
    }


# =========================================================
# FAST QUALITY SCORE
# =========================================================

def frame_quality(
    frame
) -> float:

    if frame is None:
        return 0.0

    height, width = frame.shape[:2]

    if height < 705 or width < 1610:
        return 0.0

    # Blue header
    header = cv2.cvtColor(
        frame[
            20:125,
            225:1495,
        ],
        cv2.COLOR_BGR2HSV,
    )

    blue_mask = cv2.inRange(
        header,
        (90, 70, 60),
        (140, 255, 255),
    )

    blue_ratio = float(
        (
            blue_mask > 0
        ).mean()
    )

    # Yellow player section
    left = cv2.cvtColor(
        frame[
            120:705,
            40:225,
        ],
        cv2.COLOR_BGR2HSV,
    )

    yellow_mask = cv2.inRange(
        left,
        (18, 100, 100),
        (40, 255, 255),
    )

    yellow_ratio = float(
        (
            yellow_mask > 0
        ).mean()
    )

    return (
        blue_ratio
        +
        min(
            yellow_ratio,
            0.35,
        )
    )


# =========================================================
# BEST FRAME SELECTION
# =========================================================

def select_best_frames(
    candidates,
    max_frames=2,
):

    if not candidates:
        return []

    ranked = sorted(
        candidates,
        key=lambda item: item[2],
        reverse=True,
    )

    selected = []

    for candidate in ranked:

        frame_index = candidate[0]

        # Avoid choosing almost identical frames.
        if any(
            abs(
                frame_index
                - selected_item[0]
            ) < 30
            for selected_item in selected
        ):
            continue

        selected.append(
            candidate
        )

        if len(selected) >= max_frames:
            break

    return sorted(
        selected,
        key=lambda item: item[0],
    )


# =========================================================
# ANNOTATION
# =========================================================

def annotate(
    frame,
    data,
):

    output = frame.copy()

    x1, y1, x2, y2 = SCOREBOARD_ROI

    cv2.rectangle(
        output,
        (x1, y1),
        (x2, y2),
        (84, 211, 154),
        4,
    )

    cv2.putText(
        output,
        "SCOREBOARD DETECTED",
        (x1 + 15, y1 + 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (84, 211, 154),
        2,
        cv2.LINE_AA,
    )

    current_name = data.get(
        "current_name",
        "",
    )

    if current_name:

        cv2.rectangle(
            output,
            (x1, y2 - 48),
            (x1 + 520, y2 - 8),
            (7, 17, 31),
            -1,
        )

        cv2.putText(
            output,
            f"EasyOCR: {current_name}",
            (x1 + 15, y2 - 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (245, 248, 255),
            2,
            cv2.LINE_AA,
        )

    return output


# =========================================================
# ANALYZE
# =========================================================

def analyze(
    video_path,
    job_dir=None,
):

    video_path = Path(
        video_path
    )

    if not video_path.exists():
        raise FileNotFoundError(
            video_path
        )

    # -----------------------------------------------------
    # Metadata
    # -----------------------------------------------------

    info = video_info(
        video_path
    )

    # -----------------------------------------------------
    # Job directory
    # -----------------------------------------------------

    job = Path(
        job_dir
        or (
            OUTPUT_DIR
            / time.strftime(
                "%Y%m%d_%H%M%S"
            )
        )
    )

    job.mkdir(
        parents=True,
        exist_ok=True,
    )

    sample_dir = (
        job / "samples"
    )

    crop_dir = (
        job / "crops"
    )

    annotated_dir = (
        job / "annotated"
    )

    sample_dir.mkdir(
        exist_ok=True
    )

    crop_dir.mkdir(
        exist_ok=True
    )

    annotated_dir.mkdir(
        exist_ok=True
    )

    # -----------------------------------------------------
    # Open video
    # -----------------------------------------------------

    cap = cv2.VideoCapture(
        str(video_path)
    )

    if not cap.isOpened():
        raise ValueError(
            "Could not open uploaded video."
        )

    fps = (
        info["fps"]
        or 30.0
    )

    # -----------------------------------------------------
    # Frame sampling
    # -----------------------------------------------------

    step = max(
        1,
        int(
            round(
                fps
                * SAMPLE_EVERY_SECONDS
            )
        ),
    )

    frame_index = 0
    sampled_frames = 0
    detected_frames = 0

    candidates = []

    while True:

        ok, frame = cap.read()

        if not ok:
            break

        if frame_index % step == 0:

            sampled_frames += 1

            if scoreboard_visible(
                frame
            ):

                detected_frames += 1

                quality = frame_quality(
                    frame
                )

                candidates.append(
                    (
                        frame_index,
                        frame.copy(),
                        quality,
                    )
                )

        frame_index += 1

    cap.release()

    # -----------------------------------------------------
    # Only 2 frames go to OCR
    # -----------------------------------------------------

    selected = select_best_frames(
        candidates,
        max_frames=2,
    )

    observations = []

    best_result = None
    best_frame = None
    best_quality = -1.0

    # -----------------------------------------------------
    # OCR
    # -----------------------------------------------------

    for (
        selected_index,
        frame,
        quality,
    ) in selected:

        try:

            result = extract_frame(
                frame
            )

            observations.append(
                (
                    selected_index / fps,
                    result,
                )
            )

            # Keep strongest OCR result.
            if quality > best_quality:

                best_quality = quality
                best_frame = frame
                best_result = result

        except Exception as exc:

            print(
                f"OCR warning on frame "
                f"{selected_index}: {exc}"
            )

        # Save frame
        cv2.imwrite(
            str(
                sample_dir
                / (
                    f"frame_"
                    f"{selected_index:05d}.jpg"
                )
            ),
            frame,
        )

        # Save scoreboard crop
        cv2.imwrite(
            str(
                crop_dir
                / (
                    f"crop_"
                    f"{selected_index:05d}.jpg"
                )
            ),
            crop_scoreboard(
                frame
            ),
        )

    # -----------------------------------------------------
    # Multi-frame merge
    # -----------------------------------------------------

    merged = merge_observations(
        observations
    )

    # -----------------------------------------------------
    # Annotated best frame
    #
    # IMPORTANT:
    # We DO NOT run OCR again here.
    # This removes another 5+ OCR calls.
    # -----------------------------------------------------

    if (
        best_frame is not None
        and best_result is not None
    ):

        annotated = annotate(
            best_frame,
            best_result,
        )

        cv2.imwrite(
            str(
                annotated_dir
                / "best_frame.jpg"
            ),
            annotated,
        )

        cv2.imwrite(
            str(
                annotated_dir
                / "scoreboard_crop.jpg"
            ),
            crop_scoreboard(
                best_frame
            ),
        )

    # -----------------------------------------------------
    # CSV
    # -----------------------------------------------------

    rows = []

    for player, value in (
        merged.get(
            "rows",
            {}
        ).items()
    ):

        rows.append(
            {
                "player": player,
                "raw_text": value.get(
                    "raw_text",
                    "",
                ),
                "numbers_detected":
                    " ".join(
                        value.get(
                            "numbers_detected",
                            [],
                        )
                    ),
                "confidence":
                    value.get(
                        "confidence",
                        0.0,
                    ),
                "observations":
                    value.get(
                        "observations",
                        0,
                    ),
            }
        )

    csv_path = (
        job
        / "scoreboard_data.csv"
    )

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fh:

        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "player",
                "raw_text",
                "numbers_detected",
                "confidence",
                "observations",
            ],
        )

        writer.writeheader()
        writer.writerows(
            rows
        )

    # -----------------------------------------------------
    # JSON
    # -----------------------------------------------------

    payload = {

        "video":
            video_path.name,

        "video_info":
            info,

        "scoreboard_roi":
            list(
                SCOREBOARD_ROI
            ),

        "frames_sampled":
            sampled_frames,

        "scoreboard_frames_detected":
            detected_frames,

        "ocr_frames_used":
            len(observations),

        "current_name":
            merged.get(
                "current_name",
                "",
            ),

        "current_name_confidence":
            merged.get(
                "current_name_confidence",
                0.0,
            ),

        "players":
            merged.get(
                "rows",
                {},
            ),

        "artifacts": {

            "json":
                "scoreboard_data.json",

            "csv":
                "scoreboard_data.csv",

            "best_frame":
                "annotated/best_frame.jpg",

            "scoreboard_crop":
                "annotated/scoreboard_crop.jpg",
        },
    }

    json_path = (
        job
        / "scoreboard_data.json"
    )

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "job_id":
            job.name,

        "data":
            payload,
    }