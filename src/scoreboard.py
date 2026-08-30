# from __future__ import annotations

# from collections import Counter
# from dataclasses import dataclass
# import re

# import cv2
# import easyocr
# import numpy as np

# from .config import SCOREBOARD_ROI


# # =========================================================
# # OCR RESULT
# # =========================================================

# @dataclass
# class OCRResult:
#     text: str
#     confidence: float
#     detections: list


# _reader = None


# # =========================================================
# # EASY OCR
# # =========================================================

# def get_reader():
#     """
#     Load EasyOCR only once.
#     CPU mode keeps the project compatible with normal PCs.
#     """
#     global _reader

#     if _reader is None:
#         _reader = easyocr.Reader(
#             ["en"],
#             gpu=False,
#             verbose=False,
#         )

#     return _reader


# # =========================================================
# # TEXT HELPERS
# # =========================================================

# def clean_text(text: str) -> str:
#     text = str(text)
#     text = text.replace("\n", " ")
#     text = re.sub(r"\s+", " ", text)
#     return text.strip()


# def normalize_number(value: str) -> str:
#     """
#     Correct common OCR mistakes in numeric values.
#     """

#     if not value:
#         return ""

#     value = clean_text(value).upper()

#     replacements = {
#         "O": "0",
#         "Q": "0",
#         "D": "0",
#         "I": "1",
#         "L": "1",
#         "|": "1",
#         "Z": "2",
#         "S": "5",
#         "G": "6",
#         "B": "8",
#     }

#     for old, new in replacements.items():
#         value = value.replace(old, new)

#     if "X" in value:
#         return "X"

#     if "-" in value:
#         return "-"

#     numbers = re.findall(
#         r"\d{1,3}",
#         value,
#     )

#     return numbers[0] if numbers else ""


# def extract_numbers(text: str) -> list[str]:
#     if not text:
#         return []

#     matches = re.findall(
#         r"(?<!\d)\d{1,3}(?!\d)",
#         text,
#     )

#     return [
#         normalize_number(x)
#         for x in matches
#         if normalize_number(x)
#     ]


# # =========================================================
# # FAST PREPROCESSING
# # =========================================================

# def preprocess(image: np.ndarray) -> np.ndarray:
#     """
#     Lightweight preprocessing.
#     Avoids expensive transformations because EasyOCR
#     already performs its own image processing.
#     """

#     if image is None or image.size == 0:
#         raise ValueError(
#             "OCR received an empty image."
#         )

#     gray = cv2.cvtColor(
#         image,
#         cv2.COLOR_BGR2GRAY,
#     )

#     # Moderate upscale only
#     gray = cv2.resize(
#         gray,
#         None,
#         fx=2.0,
#         fy=2.0,
#         interpolation=cv2.INTER_LINEAR,
#     )

#     return gray


# # =========================================================
# # OCR
# # =========================================================

# def ocr(
#     image: np.ndarray,
#     paragraph: bool = False,
#     numeric_only: bool = False,
# ) -> OCRResult:

#     processed = preprocess(image)
#     reader = get_reader()

#     kwargs = {
#         "detail": 1,
#         "paragraph": paragraph,
#         "text_threshold": 0.45,
#         "low_text": 0.30,
#         "link_threshold": 0.30,
#         "mag_ratio": 1.0,
#         "decoder": "greedy",
#     }

#     # Scoreboard number area can be restricted
#     # to numeric/strike characters.
#     if numeric_only:
#         kwargs["allowlist"] = (
#             "0123456789Xx-"
#         )

#     try:

#         results = reader.readtext(
#             processed,
#             **kwargs,
#         )

#     except Exception as exc:

#         print(f"OCR warning: {exc}")

#         return OCRResult(
#             text="",
#             confidence=0.0,
#             detections=[],
#         )

#     texts = []
#     confidences = []
#     detections = []

#     for item in results:

#         if not item or len(item) < 3:
#             continue

#         bbox, text, confidence = item

#         text = clean_text(text)

#         try:
#             confidence = float(
#                 confidence
#             )
#         except (
#             TypeError,
#             ValueError,
#         ):
#             confidence = 0.0

#         if not text or confidence <= 0:
#             continue

#         texts.append(text)
#         confidences.append(confidence)

#         detections.append({
#             "text": text,
#             "confidence": confidence,
#             "bbox": bbox,
#         })

#     if not texts:

#         return OCRResult(
#             text="",
#             confidence=0.0,
#             detections=[],
#         )

#     return OCRResult(
#         text=clean_text(
#             " ".join(texts)
#         ),
#         confidence=round(
#             float(
#                 np.mean(
#                     confidences
#                 )
#             ),
#             3,
#         ),
#         detections=detections,
#     )


# # =========================================================
# # SCOREBOARD VISIBILITY
# # =========================================================

# def scoreboard_visible(
#     frame: np.ndarray,
# ) -> bool:

#     if frame is None:
#         return False

#     height, width = frame.shape[:2]

#     if height < 705 or width < 1610:
#         return False

#     # Blue scoreboard header
#     header = cv2.cvtColor(
#         frame[20:125, 225:1495],
#         cv2.COLOR_BGR2HSV,
#     )

#     blue_mask = cv2.inRange(
#         header,
#         (90, 70, 60),
#         (140, 255, 255),
#     )

#     blue_ratio = float(
#         (blue_mask > 0).mean()
#     )

#     # Yellow player area
#     left = cv2.cvtColor(
#         frame[120:705, 40:225],
#         cv2.COLOR_BGR2HSV,
#     )

#     yellow_mask = cv2.inRange(
#         left,
#         (18, 100, 100),
#         (40, 255, 255),
#     )

#     yellow_ratio = float(
#         (yellow_mask > 0).mean()
#     )

#     return (
#         blue_ratio > 0.75
#         and yellow_ratio > 0.03
#     )


# # =========================================================
# # SCOREBOARD CROP
# # =========================================================

# def crop_scoreboard(
#     frame: np.ndarray,
# ) -> np.ndarray:

#     x1, y1, x2, y2 = SCOREBOARD_ROI

#     height, width = frame.shape[:2]

#     x1 = max(0, min(x1, width))
#     x2 = max(0, min(x2, width))

#     y1 = max(0, min(y1, height))
#     y2 = max(0, min(y2, height))

#     if x2 <= x1 or y2 <= y1:
#         raise ValueError(
#             f"Invalid SCOREBOARD_ROI: {SCOREBOARD_ROI}"
#         )

#     return frame[
#         y1:y2,
#         x1:x2
#     ]


# # =========================================================
# # ROWS
# # =========================================================

# def row_regions(
#     frame: np.ndarray,
# ) -> dict[str, np.ndarray]:

#     height, width = frame.shape[:2]

#     right = min(
#         1610,
#         width,
#     )

#     regions = {
#         "J": frame[
#             125:285,
#             225:right,
#         ],
#         "V": frame[
#             285:425,
#             225:right,
#         ],
#         "P": frame[
#             425:565,
#             225:right,
#         ],
#         "T": frame[
#             565:705,
#             225:right,
#         ],
#     }

#     return {
#         key: value
#         for key, value in regions.items()
#         if value.size > 0
#     }


# # =========================================================
# # ROW EXTRACTION
# # =========================================================

# def extract_row(
#     row: np.ndarray,
# ) -> dict:

#     # One OCR call for the complete row.
#     result = ocr(
#         row,
#         paragraph=False,
#         numeric_only=False,
#     )

#     raw_text = result.text

#     numbers = extract_numbers(
#         raw_text
#     )

#     # Keep useful OCR detections for debugging.
#     detections = []

#     for item in result.detections:

#         detections.append({
#             "text": item["text"],
#             "confidence": round(
#                 item["confidence"],
#                 3,
#             ),
#         })

#     return {
#         "raw_text": raw_text,
#         "confidence": result.confidence,
#         "numbers_detected": numbers[:12],
#         "cells": detections,
#     }


# # =========================================================
# # SINGLE FRAME
# # =========================================================

# def extract_frame(
#     frame: np.ndarray,
# ) -> dict:

#     # Header / current player
#     header = ocr(
#         frame[
#             22:78,
#             220:800,
#         ],
#         paragraph=False,
#         numeric_only=False,
#     )

#     rows = {}

#     for player, row in row_regions(
#         frame
#     ).items():

#         try:

#             rows[player] = extract_row(
#                 row
#             )

#         except Exception as exc:

#             print(
#                 f"Row OCR warning "
#                 f"({player}): {exc}"
#             )

#             rows[player] = {
#                 "raw_text": "",
#                 "confidence": 0.0,
#                 "numbers_detected": [],
#                 "cells": [],
#             }

#     return {
#         "current_name": clean_text(
#             header.text
#         ),
#         "current_name_confidence":
#             header.confidence,
#         "rows": rows,
#     }


# # =========================================================
# # BEST OBSERVATION
# # =========================================================

# def _best_observation(
#     items: list[dict],
# ) -> dict:

#     if not items:

#         return {
#             "raw_text": "",
#             "confidence": 0.0,
#             "numbers_detected": [],
#             "observations": 0,
#             "cells": [],
#         }

#     best = max(
#         items,
#         key=lambda item: (
#             item.get(
#                 "confidence",
#                 0.0,
#             ),
#             len(
#                 item.get(
#                     "numbers_detected",
#                     [],
#                 )
#             ),
#         ),
#     )

#     return {
#         "raw_text": best.get(
#             "raw_text",
#             "",
#         ),
#         "confidence": best.get(
#             "confidence",
#             0.0,
#         ),
#         "numbers_detected": best.get(
#             "numbers_detected",
#             [],
#         ),
#         "observations": len(
#             items
#         ),
#         "cells": best.get(
#             "cells",
#             [],
#         ),
#     }


# # =========================================================
# # MULTI-FRAME MERGE
# # =========================================================

# def merge_observations(
#     observations: list[tuple[float, dict]],
# ) -> dict:

#     valid = [
#         result
#         for _, result in observations
#         if isinstance(result, dict)
#         and "rows" in result
#     ]

#     if not valid:

#         return {
#             "current_name": "",
#             "current_name_confidence": 0.0,
#             "rows": {},
#         }

#     # -----------------------------------------------------
#     # Current player
#     # -----------------------------------------------------

#     names = [
#         clean_text(
#             result.get(
#                 "current_name",
#                 "",
#             )
#         )
#         for result in valid
#         if result.get(
#             "current_name"
#         )
#     ]

#     if names:

#         current_name = Counter(
#             names
#         ).most_common(1)[0][0]

#     else:

#         current_name = ""

#     name_confidence = max(
#         (
#             float(
#                 result.get(
#                     "current_name_confidence",
#                     0.0,
#                 )
#             )
#             for result in valid
#         ),
#         default=0.0,
#     )

#     # -----------------------------------------------------
#     # Player rows
#     # -----------------------------------------------------

#     rows = {}

#     for player in [
#         "J",
#         "V",
#         "P",
#         "T",
#     ]:

#         items = []

#         for result in valid:

#             row = result.get(
#                 "rows",
#                 {},
#             ).get(player)

#             if not row:
#                 continue

#             if not row.get(
#                 "raw_text"
#             ):
#                 continue

#             items.append(row)

#         rows[player] = (
#             _best_observation(
#                 items
#             )
#         )

#     return {
#         "current_name": current_name,
#         "current_name_confidence":
#             round(
#                 name_confidence,
#                 3,
#             ),
#         "rows": rows,
#     }

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from .config import SCOREBOARD_ROI


# =========================================================
# OCR RESULT
# =========================================================

@dataclass
class OCRResult:
    text: str
    confidence: float
    detections: list


_reader = None


# =========================================================
# TESSERACT OCR
#
# EasyOCR (PyTorch) needed ~1.2 GB RAM just to load the
# model, which does not fit in Render's free-tier 512 MB
# instance. Tesseract is a lightweight C++ OCR engine (no
# deep-learning framework) that uses only a few tens of MB,
# so it fits comfortably. Requires the `tesseract-ocr`
# system binary to be installed (see Dockerfile).
# =========================================================


# =========================================================
# TEXT HELPERS
# =========================================================

def clean_text(text: str) -> str:
    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_number(value: str) -> str:
    """
    Correct common OCR mistakes in numeric values.
    """

    if not value:
        return ""

    value = clean_text(value).upper()

    replacements = {
        "O": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "L": "1",
        "|": "1",
        "Z": "2",
        "S": "5",
        "G": "6",
        "B": "8",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    if "X" in value:
        return "X"

    if "-" in value:
        return "-"

    numbers = re.findall(
        r"\d{1,3}",
        value,
    )

    return numbers[0] if numbers else ""


def extract_numbers(text: str) -> list[str]:
    if not text:
        return []

    matches = re.findall(
        r"(?<!\d)\d{1,3}(?!\d)",
        text,
    )

    return [
        normalize_number(x)
        for x in matches
        if normalize_number(x)
    ]


# =========================================================
# FAST PREPROCESSING
# =========================================================

def preprocess(image: np.ndarray) -> np.ndarray:
    """
    Lightweight preprocessing.
    Avoids expensive transformations because EasyOCR
    already performs its own image processing.
    """

    if image is None or image.size == 0:
        raise ValueError(
            "OCR received an empty image."
        )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    # Moderate upscale only
    gray = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_LINEAR,
    )

    return gray


# =========================================================
# OCR
# =========================================================

def ocr(
    image: np.ndarray,
    paragraph: bool = False,
    numeric_only: bool = False,
) -> OCRResult:

    processed = preprocess(image)

    # --psm 6: assume a uniform block of text (good for a
    # full row). --psm 7: treat as a single line (good for
    # the short header / current-name field).
    psm = "6" if paragraph else "7"

    config = f"--oem 3 --psm {psm}"

    if numeric_only:
        config += " -c tessedit_char_whitelist=0123456789Xx-"

    try:

        data = pytesseract.image_to_data(
            processed,
            config=config,
            output_type=Output.DICT,
        )

    except Exception as exc:

        print(f"OCR warning: {exc}")

        return OCRResult(
            text="",
            confidence=0.0,
            detections=[],
        )

    texts = []
    confidences = []
    detections = []

    count = len(data.get("text", []))

    for i in range(count):

        text = clean_text(
            data["text"][i]
        )

        try:
            # Tesseract confidences are 0-100 (or -1 for
            # non-text rows); normalize to 0-1 to match the
            # scale the rest of the pipeline expects.
            confidence = float(
                data["conf"][i]
            ) / 100.0
        except (
            TypeError,
            ValueError,
        ):
            confidence = 0.0

        if not text or confidence <= 0:
            continue

        texts.append(text)
        confidences.append(confidence)

        detections.append({
            "text": text,
            "confidence": confidence,
            "bbox": [
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            ],
        })

    if not texts:

        return OCRResult(
            text="",
            confidence=0.0,
            detections=[],
        )

    return OCRResult(
        text=clean_text(
            " ".join(texts)
        ),
        confidence=round(
            float(
                np.mean(
                    confidences
                )
            ),
            3,
        ),
        detections=detections,
    )


# =========================================================
# SCOREBOARD VISIBILITY
# =========================================================

def scoreboard_visible(
    frame: np.ndarray,
) -> bool:

    if frame is None:
        return False

    height, width = frame.shape[:2]

    if height < 705 or width < 1610:
        return False

    # Blue scoreboard header
    header = cv2.cvtColor(
        frame[20:125, 225:1495],
        cv2.COLOR_BGR2HSV,
    )

    blue_mask = cv2.inRange(
        header,
        (90, 70, 60),
        (140, 255, 255),
    )

    blue_ratio = float(
        (blue_mask > 0).mean()
    )

    # Yellow player area
    left = cv2.cvtColor(
        frame[120:705, 40:225],
        cv2.COLOR_BGR2HSV,
    )

    yellow_mask = cv2.inRange(
        left,
        (18, 100, 100),
        (40, 255, 255),
    )

    yellow_ratio = float(
        (yellow_mask > 0).mean()
    )

    return (
        blue_ratio > 0.75
        and yellow_ratio > 0.03
    )


# =========================================================
# SCOREBOARD CROP
# =========================================================

def crop_scoreboard(
    frame: np.ndarray,
) -> np.ndarray:

    x1, y1, x2, y2 = SCOREBOARD_ROI

    height, width = frame.shape[:2]

    x1 = max(0, min(x1, width))
    x2 = max(0, min(x2, width))

    y1 = max(0, min(y1, height))
    y2 = max(0, min(y2, height))

    if x2 <= x1 or y2 <= y1:
        raise ValueError(
            f"Invalid SCOREBOARD_ROI: {SCOREBOARD_ROI}"
        )

    return frame[
        y1:y2,
        x1:x2
    ]


# =========================================================
# ROWS
# =========================================================

def row_regions(
    frame: np.ndarray,
) -> dict[str, np.ndarray]:

    height, width = frame.shape[:2]

    right = min(
        1610,
        width,
    )

    regions = {
        "J": frame[
            125:285,
            225:right,
        ],
        "V": frame[
            285:425,
            225:right,
        ],
        "P": frame[
            425:565,
            225:right,
        ],
        "T": frame[
            565:705,
            225:right,
        ],
    }

    return {
        key: value
        for key, value in regions.items()
        if value.size > 0
    }


# =========================================================
# ROW EXTRACTION
# =========================================================

def extract_row(
    row: np.ndarray,
) -> dict:

    # One OCR call for the complete row.
    result = ocr(
        row,
        paragraph=False,
        numeric_only=False,
    )

    raw_text = result.text

    numbers = extract_numbers(
        raw_text
    )

    # Keep useful OCR detections for debugging.
    detections = []

    for item in result.detections:

        detections.append({
            "text": item["text"],
            "confidence": round(
                item["confidence"],
                3,
            ),
        })

    return {
        "raw_text": raw_text,
        "confidence": result.confidence,
        "numbers_detected": numbers[:12],
        "cells": detections,
    }


# =========================================================
# SINGLE FRAME
# =========================================================

def extract_frame(
    frame: np.ndarray,
) -> dict:

    # Header / current player
    header = ocr(
        frame[
            22:78,
            220:800,
        ],
        paragraph=False,
        numeric_only=False,
    )

    rows = {}

    for player, row in row_regions(
        frame
    ).items():

        try:

            rows[player] = extract_row(
                row
            )

        except Exception as exc:

            print(
                f"Row OCR warning "
                f"({player}): {exc}"
            )

            rows[player] = {
                "raw_text": "",
                "confidence": 0.0,
                "numbers_detected": [],
                "cells": [],
            }

    return {
        "current_name": clean_text(
            header.text
        ),
        "current_name_confidence":
            header.confidence,
        "rows": rows,
    }


# =========================================================
# BEST OBSERVATION
# =========================================================

def _best_observation(
    items: list[dict],
) -> dict:

    if not items:

        return {
            "raw_text": "",
            "confidence": 0.0,
            "numbers_detected": [],
            "observations": 0,
            "cells": [],
        }

    best = max(
        items,
        key=lambda item: (
            item.get(
                "confidence",
                0.0,
            ),
            len(
                item.get(
                    "numbers_detected",
                    [],
                )
            ),
        ),
    )

    return {
        "raw_text": best.get(
            "raw_text",
            "",
        ),
        "confidence": best.get(
            "confidence",
            0.0,
        ),
        "numbers_detected": best.get(
            "numbers_detected",
            [],
        ),
        "observations": len(
            items
        ),
        "cells": best.get(
            "cells",
            [],
        ),
    }


# =========================================================
# MULTI-FRAME MERGE
# =========================================================

def merge_observations(
    observations: list[tuple[float, dict]],
) -> dict:

    valid = [
        result
        for _, result in observations
        if isinstance(result, dict)
        and "rows" in result
    ]

    if not valid:

        return {
            "current_name": "",
            "current_name_confidence": 0.0,
            "rows": {},
        }

    # -----------------------------------------------------
    # Current player
    # -----------------------------------------------------

    names = [
        clean_text(
            result.get(
                "current_name",
                "",
            )
        )
        for result in valid
        if result.get(
            "current_name"
        )
    ]

    if names:

        current_name = Counter(
            names
        ).most_common(1)[0][0]

    else:

        current_name = ""

    name_confidence = max(
        (
            float(
                result.get(
                    "current_name_confidence",
                    0.0,
                )
            )
            for result in valid
        ),
        default=0.0,
    )

    # -----------------------------------------------------
    # Player rows
    # -----------------------------------------------------

    rows = {}

    for player in [
        "J",
        "V",
        "P",
        "T",
    ]:

        items = []

        for result in valid:

            row = result.get(
                "rows",
                {},
            ).get(player)

            if not row:
                continue

            if not row.get(
                "raw_text"
            ):
                continue

            items.append(row)

        rows[player] = (
            _best_observation(
                items
            )
        )

    return {
        "current_name": current_name,
        "current_name_confidence":
            round(
                name_confidence,
                3,
            ),
        "rows": rows,
    }