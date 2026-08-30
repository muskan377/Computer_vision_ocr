from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

# Measured from the supplied assignment video after frame inspection.
# x1, y1, x2, y2 at the original 1920x1080 resolution.
SCOREBOARD_ROI = (40, 22, 1890, 705)
SAMPLE_EVERY_SECONDS = 0.75
MAX_OCR_FRAMES = 45

# Scoreboard grid in original 1920x1080 frame coordinates.
GRID_X1, GRID_X2 = 225, 1495
FRAME_WIDTH = (GRID_X2 - GRID_X1) / 10

PLAYER_ROWS = {
    "J": (128, 287),
    "V": (288, 424),
    "P": (425, 560),
    "T": (561, 701),
}

ROLL_HEIGHTS = {
    "J": ((128, 178), (178, 263)),
    "V": ((288, 338), (338, 424)),
    "P": ((425, 472), (472, 560)),
    "T": ((561, 610), (610, 701)),
}
