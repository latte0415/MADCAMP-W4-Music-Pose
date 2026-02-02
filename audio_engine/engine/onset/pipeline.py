"""
L2 Pipeline: onset 검출·정제·컨텍스트 생성 (오디오 → OnsetContext).
L1만 사용. librosa는 여기서만 사용.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

import librosa
import numpy as np
from scipy.signal import butter, filtfilt

from audio_engine.engine.onset.types import OnsetContext
from audio_engine.engine.onset.constants import (
    DEFAULT_HOP_LENGTH,
    DEFAULT_DELTA,
    DEFAULT_WAIT,
    DEFAULT_HOP_REFINE,
    DEFAULT_WIN_REFINE_SEC,
    SWING_RATIO,
    TEMPO_STD_BPM,
    BAND_HZ,
    BAND_EVIDENCE_TOL_SEC,
)


def detect_onsets(
    y: np.ndarray,
    sr: int,
    hop_length: int = DEFAULT_HOP_LENGTH,
    delta: float = DEFAULT_DELTA,
    wait: int = DEFAULT_WAIT,
):
    """
    Onset 검출. (onset_frames, onset_times, onset_env, strengths) 반환.
    """
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        delta=delta,
        wait=wait,
        backtrack=False,
    )
    onset_times = librosa.frames_to_time(
        onset_frames, sr=sr, hop_length=hop_length
    )
    strengths = onset_env[onset_frames]
    return onset_frames, onset_times, onset_env, strengths


def refine_onset_times(
    y: np.ndarray,
    sr: int,
    onset_frames: np.ndarray,
    onset_times: np.ndarray,
    hop_length: int = DEFAULT_HOP_LENGTH,
    hop_refine: int = DEFAULT_HOP_REFINE,
    win_refine_sec: float = DEFAULT_WIN_REFINE_SEC,
):
    """
    각 onset 주변 ±win_refine_sec 구간만 hop_refine으로 재계산 후 피크 프레임으로 정제.
    (onset_frames_refined, onset_times_refined) 반환.
    """
    n = len(onset_frames)
    onset_frames_refined = []
    onset_times_refined = []
    for i in range(n):
        t = onset_times[i]
        start_s = max(0, int(round((t - win_refine_sec) * sr)))
        end_s = min(len(y), int(round((t + win_refine_sec) * sr)))
        seg = y[start_s:end_s]
        if len(seg) < hop_refine:
            onset_frames_refined.append(onset_frames[i])
            onset_times_refined.append(onset_times[i])
            continue
        env_local = librosa.onset.onset_strength(
            y=seg, sr=sr, hop_length=hop_refine
        )
        if len(env_local) == 0:
            onset_frames_refined.append(onset_frames[i])
            onset_times_refined.append(onset_times[i])
            continue
        peak_local = np.argmax(env_local)
        t_refined = start_s / sr + librosa.frames_to_time(
            peak_local, sr=sr, hop_length=hop_refine
        )
        frame_refined = librosa.time_to_frames(
            t_refined, sr=sr, hop_length=hop_length
        )
        onset_frames_refined.append(frame_refined)
        onset_times_refined.append(t_refined)
    return np.array(onset_frames_refined), np.array(onset_times_refined)


def _build_temporal_aux(
    y: np.ndarray,
    sr: int,
    onset_env: np.ndarray,
    hop_length: int,
    bpm: float,
):
    """Temporal용 beats_dynamic, grid_times, grid_levels 생성."""
    tempo_dynamic = librosa.feature.tempo(
        y=y, sr=sr, aggregate=None, std_bpm=TEMPO_STD_BPM
    )
    tempo_times = librosa.times_like(tempo_dynamic, sr=sr)
    onset_env_times = librosa.times_like(onset_env, sr=sr, hop_length=hop_length)
    tempo_dynamic = np.interp(
        onset_env_times,
        tempo_times,
        np.nan_to_num(tempo_dynamic, nan=bpm),
    )
    _, beats_dynamic = librosa.beat.beat_track(
        y=y,
        sr=sr,
        hop_length=hop_length,
        bpm=tempo_dynamic,
        units="time",
        trim=False,
    )
    beats_dynamic = np.asarray(beats_dynamic).flatten()
    bpm_dynamic_used = True
    if len(beats_dynamic) < 4:
        _, beats_dynamic = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=hop_length, units="time", trim=False
        )
        beats_dynamic = np.asarray(beats_dynamic).flatten()
        bpm_dynamic_used = False
    beats_dynamic = np.sort(beats_dynamic)
    grid_times, grid_levels = _build_variable_grid_with_levels(
        beats_dynamic, SWING_RATIO
    )
    return beats_dynamic, tempo_dynamic, grid_times, grid_levels, bpm_dynamic_used


def _build_variable_grid_with_levels(
    beats: np.ndarray,
    swing_ratio: float = 1.0,
):
    """비트 시퀀스로부터 서브비트 그리드 생성. (grid_times, grid_levels) 반환."""
    grid_times = []
    grid_levels = []
    for k in range(len(beats) - 1):
        b0, b1 = beats[k], beats[k + 1]
        span = b1 - b0
        if span <= 0:
            continue
        grid_times.append(b0)
        grid_levels.append(1)
        grid_times.append(b0 + span * 0.5)
        grid_levels.append(2)
        for f in [0.25, 0.5, 0.75]:
            grid_times.append(b0 + span * f)
            grid_levels.append(4)
        if swing_ratio != 1.0:
            long_8 = span * swing_ratio / (1.0 + swing_ratio)
            short_8 = span / (1.0 + swing_ratio)
            grid_times.extend([b0 + long_8, b0 + long_8 + short_8])
            grid_levels.extend([8, 8])
        else:
            for f in [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]:
                grid_times.append(b0 + span * f)
                grid_levels.append(8)
        for f in np.arange(0.0625, 1.0, 0.0625):
            grid_times.append(b0 + span * f)
            grid_levels.append(16)
    grid_times.append(beats[-1])
    grid_levels.append(1)
    return np.array(grid_times), np.array(grid_levels)


def _bandpass(y: np.ndarray, sr: int, f_lo: float, f_hi: float, order: int = 2) -> np.ndarray:
    nyq = sr / 2.0
    low = max(f_lo / nyq, 0.001)
    high = min(f_hi / nyq, 0.999)
    if low >= high:
        return np.zeros_like(y)
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, y)


def filter_y_into_bands(
    y: np.ndarray,
    sr: int,
    band_hz: list[tuple[float, float]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    band_hz: [(low_lo, low_hi), (mid_lo, mid_hi), (high_lo, high_hi)].
    반환: (y_low, y_mid, y_high).
    """
    if len(band_hz) < 3:
        return y.copy(), y.copy(), y.copy()
    y_low = _bandpass(y, sr, band_hz[0][0], band_hz[0][1])
    y_mid = _bandpass(y, sr, band_hz[1][0], band_hz[1][1])
    y_high = _bandpass(y, sr, band_hz[2][0], band_hz[2][1])
    return y_low, y_mid, y_high


def _attach_band_evidence(
    anchor_times: np.ndarray,
    band_times_list: list[np.ndarray],
    band_strengths_list: list[np.ndarray],
    tol_sec: float,
) -> list[dict]:
    """
    각 anchor에 대해 ±tol_sec 내 가장 가까운 band onset을 evidence로 attach.
    반환: band_evidence[i] = {"low": {present, onset_strength, dt} or None, "mid": ..., "high": ...}
    """
    band_names = ["low", "mid", "high"]
    n = len(anchor_times)
    out = []
    for i in range(n):
        t_a = anchor_times[i]
        ev = {}
        for b, (times_b, strengths_b) in enumerate(zip(band_times_list, band_strengths_list)):
            if len(times_b) == 0:
                ev[band_names[b]] = None
                continue
            in_window = (times_b >= t_a - tol_sec) & (times_b <= t_a + tol_sec)
            if not np.any(in_window):
                ev[band_names[b]] = None
                continue
            idx = np.where(in_window)[0]
            j = idx[np.argmin(np.abs(times_b[idx] - t_a))]
            ev[band_names[b]] = {
                "present": True,
                "onset_strength": float(strengths_b[j]),
                "dt": float(times_b[j] - t_a),
            }
        out.append(ev)
    return out


def build_context_with_band_evidence(
    audio_path: Union[str, Path],
    *,
    hop_length: int = DEFAULT_HOP_LENGTH,
    delta: float = DEFAULT_DELTA,
    wait: int = DEFAULT_WAIT,
    hop_refine: int = DEFAULT_HOP_REFINE,
    win_refine_sec: float = DEFAULT_WIN_REFINE_SEC,
    evidence_tol_sec: float = BAND_EVIDENCE_TOL_SEC,
    include_temporal: bool = True,
) -> OnsetContext:
    """
    Anchor(broadband onset) 1회 검출 후, 대역별 onset을 ±tol 내에서만 해당 anchor에 evidence로 연결.
    merge로 이벤트를 생성하지 않음. 이벤트 수 = anchor 수.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")
    y, sr = librosa.load(path)
    duration = len(y) / sr

    # Anchor: 전대역 onset 1회
    onset_frames, onset_times, onset_env, strengths = detect_onsets(
        y, sr, hop_length=hop_length, delta=delta, wait=wait
    )
    onset_frames, onset_times = refine_onset_times(
        y, sr, onset_frames, onset_times,
        hop_length=hop_length, hop_refine=hop_refine, win_refine_sec=win_refine_sec,
    )
    strengths = onset_env[onset_frames]

    # 대역별 onset (검출만, merge로 합치지 않음)
    y_low, y_mid, y_high = filter_y_into_bands(y, sr, BAND_HZ)
    band_times_list = []
    band_strengths_list = []
    for y_band in (y_low, y_mid, y_high):
        frames_b, times_b, _, strengths_b = detect_onsets(
            y_band, sr, hop_length=hop_length, delta=delta, wait=wait
        )
        band_times_list.append(times_b)
        band_strengths_list.append(strengths_b)

    band_evidence = _attach_band_evidence(
        onset_times, band_times_list, band_strengths_list, tol_sec=evidence_tol_sec
    )

    tempo_global, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    bpm = float(np.asarray(tempo_global).flat[0]) if np.size(tempo_global) > 0 else 90.0

    beats_dynamic = None
    tempo_dynamic = None
    grid_times = None
    grid_levels = None
    bpm_dynamic_used = False
    if include_temporal:
        (
            beats_dynamic,
            tempo_dynamic,
            grid_times,
            grid_levels,
            bpm_dynamic_used,
        ) = _build_temporal_aux(y, sr, onset_env, hop_length, bpm)

    return OnsetContext(
        y=y,
        sr=sr,
        duration=duration,
        onset_times=onset_times,
        onset_frames=onset_frames,
        strengths=strengths,
        bpm=bpm,
        onset_env=onset_env,
        beats_dynamic=beats_dynamic,
        tempo_dynamic=tempo_dynamic,
        grid_times=grid_times,
        grid_levels=grid_levels,
        bpm_dynamic_used=bpm_dynamic_used,
        band_evidence=band_evidence,
    )


def build_context(
    audio_path: Union[str, Path],
    *,
    hop_length: int = DEFAULT_HOP_LENGTH,
    delta: float = DEFAULT_DELTA,
    wait: int = DEFAULT_WAIT,
    hop_refine: int = DEFAULT_HOP_REFINE,
    win_refine_sec: float = DEFAULT_WIN_REFINE_SEC,
    include_temporal: bool = True,
) -> OnsetContext:
    """
    오디오 파일에서 OnsetContext 생성.
    include_temporal=True이면 beats_dynamic, grid_times, grid_levels 등 채움 (temporal 모듈용).
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")
    y, sr = librosa.load(path)
    duration = len(y) / sr

    onset_frames, onset_times, onset_env, strengths = detect_onsets(
        y, sr, hop_length=hop_length, delta=delta, wait=wait
    )
    onset_frames, onset_times = refine_onset_times(
        y,
        sr,
        onset_frames,
        onset_times,
        hop_length=hop_length,
        hop_refine=hop_refine,
        win_refine_sec=win_refine_sec,
    )
    strengths = onset_env[onset_frames]

    tempo_global, _ = librosa.beat.beat_track(
        y=y, sr=sr, hop_length=hop_length
    )
    bpm = float(np.asarray(tempo_global).flat[0]) if np.size(tempo_global) > 0 else 90.0

    beats_dynamic = None
    tempo_dynamic = None
    grid_times = None
    grid_levels = None
    bpm_dynamic_used = False
    if include_temporal:
        (
            beats_dynamic,
            tempo_dynamic,
            grid_times,
            grid_levels,
            bpm_dynamic_used,
        ) = _build_temporal_aux(y, sr, onset_env, hop_length, bpm)

    return OnsetContext(
        y=y,
        sr=sr,
        duration=duration,
        onset_times=onset_times,
        onset_frames=onset_frames,
        strengths=strengths,
        bpm=bpm,
        onset_env=onset_env,
        beats_dynamic=beats_dynamic,
        tempo_dynamic=tempo_dynamic,
        grid_times=grid_times,
        grid_levels=grid_levels,
        bpm_dynamic_used=bpm_dynamic_used,
    )
