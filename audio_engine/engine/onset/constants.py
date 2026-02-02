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

# STFT / 대역 (고정 크로스오버, 드럼 기준: kick / snare·body / hat·click)
DEFAULT_N_FFT = 2048
BAND_HZ = [(20, 200), (200, 3000), (3000, 10000)]
BAND_NAMES = ["Low", "Mid", "High"]

# 대역 분류 (적응형은 MVP에서 미사용; 필요 시 고정 주변 ±몇백 Hz만 허용)
BAND_HZ_FIXED_LOW_MID = 200
BAND_HZ_FIXED_MID_HIGH = 3000
BAND_BLEND_ALPHA = 0.5
BAND_ADAPTIVE_LOW_MID_RANGE = (20, 500)
BAND_ADAPTIVE_MID_HIGH_RANGE = (500, 8000)
BAND_CUMULATIVE_PERCENTILES = (33.0, 66.0)
# Anchor–band evidence 연결: ±tol(초) 이내 band onset을 해당 anchor에 attach
BAND_EVIDENCE_TOL_SEC = 0.04

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
