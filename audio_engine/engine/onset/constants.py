"""
L1 Core: 파라미터 상수.
hop_length, delta, wait, band_hz, n_fft 등. 외부 의존 없음.
"""

# Onset 검출 (librosa)
DEFAULT_HOP_LENGTH = 256
DEFAULT_DELTA = 0.07
DEFAULT_WAIT = 4

# Onset 정제 (로컬 리파인)
DEFAULT_HOP_REFINE = 64
DEFAULT_WIN_REFINE_SEC = 0.08

# STFT / 대역
DEFAULT_N_FFT = 2048
BAND_HZ = [(20, 150), (150, 2000), (2000, 10000)]
BAND_NAMES = ["Low", "Mid", "High"]

# Clarity (attack time)
CLARITY_ATTACK_MIN_MS = 0.05
CLARITY_ATTACK_MAX_MS = 50.0

# Temporal
MIN_IOI_SEC = 0.05
SWING_RATIO = 1.0
LEVEL_WEIGHT = {1: 1.0, 2: 0.95, 4: 0.9, 8: 0.75, 16: 0.6}
GRID_MULTIPLES = [0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
SIGMA_BEAT = 0.08
TEMPO_STD_BPM = 4

# Context dependency
EVENT_WIN_SEC = 0.05
BG_WIN_SEC = 0.1

# Export
DEFAULT_POINT_COLOR = "#5a9fd4"
