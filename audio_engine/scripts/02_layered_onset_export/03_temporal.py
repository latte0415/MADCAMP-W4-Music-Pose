# %% [markdown]
# # 06. Temporal Salience (박자 기여도 / 반복성)
#
# 가변 그리드 + 로컬 템포 기반으로 "이 이벤트가 그루브/박자 인식에 얼마나 기여하는가"를 수치화합니다.
# 다운비트 가중치는 제외하여 장르 독립적으로 동작합니다.
#

# %%
import sys
import os
import json
import shutil

# 프로젝트 루트
def find_project_root():
    cwd = os.path.abspath(os.getcwd())
    while cwd:
        if os.path.isdir(os.path.join(cwd, 'audio_engine')) and os.path.isdir(os.path.join(cwd, 'web')):
            return cwd
        cwd = os.path.dirname(cwd)
    return os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), '..', '..'))

project_root = find_project_root()
sys.path.insert(0, project_root)

import librosa
import numpy as np

print(f"프로젝트 루트: {project_root}")
print(f"Librosa 버전: {librosa.__version__}")

# %%
# 입력 오디오 경로 (01_energy, 02_clarity와 동일)
# audio_path = os.path.join(
#     project_root, 'audio_engine', 'samples', 'stems', 'htdemucs', 'sample_ropes_short', 'drums.wav'
# )
# audio_path = os.path.join(project_root, 'audio_engine', 'samples', 'sample_ropes_short.mp3')
audio_path = os.path.join(project_root, 'audio_engine', 'samples', 'sample_cardmani.mp3')

if not os.path.exists(audio_path):
    raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")

y, sr = librosa.load(audio_path)
duration = len(y) / sr
print(f"파일: {os.path.basename(audio_path)}")
print(f"샘플링 레이트: {sr} Hz, 길이: {duration:.2f} 초")

# %%
# Onset 검출 + refine (01_energy와 동일)
hop_length = 256
hop_refine = 64
win_refine_sec = 0.08

onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
onset_frames = librosa.onset.onset_detect(
    onset_envelope=onset_env, sr=sr, hop_length=hop_length,
    delta=0.07, wait=4, backtrack=False,
)
onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
strengths = onset_env[onset_frames]

# 글로벌 BPM (fallback용)
tempo_global, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
bpm = float(np.asarray(tempo_global).flat[0]) if np.size(tempo_global) > 0 else 90.0

def refine_onset_times(y, sr, onset_frames, onset_times, hop_length=256, hop_refine=64, win_refine_sec=0.08):
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
        env_local = librosa.onset.onset_strength(y=seg, sr=sr, hop_length=hop_refine)
        if len(env_local) == 0:
            onset_frames_refined.append(onset_frames[i])
            onset_times_refined.append(onset_times[i])
            continue
        peak_local = np.argmax(env_local)
        t_refined = start_s / sr + librosa.frames_to_time(peak_local, sr=sr, hop_length=hop_refine)
        frame_refined = librosa.time_to_frames(t_refined, sr=sr, hop_length=hop_length)
        onset_frames_refined.append(frame_refined)
        onset_times_refined.append(t_refined)
    return np.array(onset_frames_refined), np.array(onset_times_refined)

onset_frames, onset_times = refine_onset_times(
    y, sr, onset_frames, onset_times,
    hop_length=hop_length, hop_refine=hop_refine, win_refine_sec=win_refine_sec
)
strengths = onset_env[onset_frames]

print(f"검출된 타격점 수: {len(onset_times)}")
print(f"글로벌 BPM: {bpm:.1f}")

# %%
# 로컬 템포 (Local Tempo)
std_bpm = 4  # 루바토/템포 변화가 큰 곡에 대응
tempo_dynamic = librosa.feature.tempo(y=y, sr=sr, aggregate=None, std_bpm=std_bpm)
tempo_times = librosa.times_like(tempo_dynamic, sr=sr)
# beat_track은 onset_envelope과 같은 길이의 bpm 배열 필요 → 보간
onset_env_times = librosa.times_like(onset_env, sr=sr, hop_length=hop_length)
tempo_dynamic = np.interp(onset_env_times, tempo_times, np.nan_to_num(tempo_dynamic, nan=bpm))
bpm_dynamic_used = True
print(f"로컬 템포: min={float(np.nanmin(tempo_dynamic)):.1f} BPM, max={float(np.nanmax(tempo_dynamic)):.1f} BPM")

# %%
# 비트 시퀀스 (가변 템포 적용)
_, beats_dynamic = librosa.beat.beat_track(
    y=y, sr=sr, hop_length=hop_length,
    bpm=tempo_dynamic, units='time', trim=False
)
beats_dynamic = np.asarray(beats_dynamic).flatten()

# beat가 너무 적으면 글로벌 BPM으로 fallback
if len(beats_dynamic) < 4:
    _, beats_dynamic = librosa.beat.beat_track(
        y=y, sr=sr, hop_length=hop_length,
        units='time', trim=False
    )
    beats_dynamic = np.asarray(beats_dynamic).flatten()
    bpm_dynamic_used = False

beats_dynamic = np.sort(beats_dynamic)
print(f"비트 수: {len(beats_dynamic)}")

# %%
# 가변 그리드 생성: beat 구간 [b_k, b_{k+1}]을 1/2, 1/4, 1/8, 1/16으로 분할
# swing_ratio=1.0 → straight (장르 중립)
swing_ratio = 1.0

def build_variable_grid_with_levels(beats, swing_ratio=1.0):
    """비트 시퀀스로부터 서브비트 그리드 생성. (time, level) 반환. level=4가 1/4, 8이 1/8, 16이 1/16."""
    grid_times = []
    grid_levels = []
    for k in range(len(beats) - 1):
        b0, b1 = beats[k], beats[k + 1]
        span = b1 - b0
        if span <= 0:
            continue
        # beat boundary (level 1)
        grid_times.append(b0)
        grid_levels.append(1)
        # 1/2
        grid_times.append(b0 + span * 0.5)
        grid_levels.append(2)
        # 1/4
        for f in [0.25, 0.5, 0.75]:
            grid_times.append(b0 + span * f)
            grid_levels.append(4)
        # 1/8
        if swing_ratio != 1.0:
            long_8 = span * swing_ratio / (1.0 + swing_ratio)
            short_8 = span / (1.0 + swing_ratio)
            grid_times.extend([b0 + long_8, b0 + long_8 + short_8])
            grid_levels.extend([8, 8])
        else:
            for f in [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]:
                grid_times.append(b0 + span * f)
                grid_levels.append(8)
        # 1/16
        for f in np.arange(0.0625, 1.0, 0.0625):
            grid_times.append(b0 + span * f)
            grid_levels.append(16)
    grid_times.append(beats[-1])
    grid_levels.append(1)
    return np.array(grid_times), np.array(grid_levels)

grid_times, grid_levels = build_variable_grid_with_levels(beats_dynamic, swing_ratio=swing_ratio)
print(f"그리드 포인트 수: {len(grid_times)}")

# %%
# 그리드 정렬 점수 (grid_align_score) — 계층적 가중치
# 1/4 정렬 > 1/8 > 1/16. tau를 타이트하게 해서 변별력 확보.
beat_length = 60.0 / max(bpm, 40)
tau_tight = beat_length * 0.06   # 약 40ms (1/4 정렬에 엄격)
tau_loose = beat_length * 0.12   # 1/8 이하 정렬용

level_weight = {1: 1.0, 2: 0.95, 4: 0.9, 8: 0.75, 16: 0.6}  # 굵은 그리드일수록 높은 가중치

grid_align_scores = []
for t in onset_times:
    dists = np.abs(t - grid_times)
    idx = np.argmin(dists)
    d = dists[idx]
    level = grid_levels[idx]
    w = level_weight.get(level, 0.5)
    # 거리가 가까울수록 높은 점수, 계층 가중치 적용
    base = np.exp(-d / tau_tight)
    grid_align_scores.append(base * w)

grid_align_score = np.array(grid_align_scores)
grid_align_score = np.clip(grid_align_score, 0, 1)

# %%
# 반복성 점수 (repetition_score)
# IOI를 beat 단위로 정규화 후, 그리드 배수(0.25, 0.5, 1, 1.5...)에 가까우면 높은 점수
MIN_IOI_SEC = 0.05  # 50ms 미만: 이중탐지/노이즈 → 중립

deltas = np.diff(onset_times)
ioi_prev = np.concatenate([[np.nan], deltas])
ioi_next = np.concatenate([deltas, [np.nan]])

# 이벤트 i의 대표 IOI (prev, next 중 짧은 쪽 제외 — 비정상 IOI 필터)
def get_repr_ioi(prev, next_):
    if np.isfinite(prev) and np.isfinite(next_):
        if prev < MIN_IOI_SEC and next_ < MIN_IOI_SEC:
            return np.nan
        if prev < MIN_IOI_SEC:
            return next_
        if next_ < MIN_IOI_SEC:
            return prev
        return (prev + next_) / 2
    return prev if np.isfinite(prev) else next_

ioi_per_event = np.array([get_repr_ioi(ioi_prev[i], ioi_next[i]) for i in range(len(onset_times))])

# Beat 정규화: ioi_beat = ioi / (60/bpm)
beat_len = 60.0 / max(bpm, 40)
# 그리드 배수 (1/16 ~ 2비트)
grid_multiples = np.array([0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0])
sigma_beat = 0.08  # beat 단위 허용 오차

def repetition_score_single(ioi_val):
    if not np.isfinite(ioi_val) or ioi_val < MIN_IOI_SEC:
        return 0.5
    ioi_beat = ioi_val / beat_len
    if ioi_beat > 2.5:  # 너무 긴 간격
        return 0.5
    best = 0.0
    for mult in grid_multiples:
        s = np.exp(-np.abs(ioi_beat - mult) / sigma_beat)
        best = max(best, s)
    return float(best)

repetition_score = np.array([repetition_score_single(v) for v in ioi_per_event])
repetition_score = np.clip(repetition_score, 0, 1)

# %%
# 최종 Temporal 점수: grid_align * repetition * strength_weight (다운비트 가중치 없음)
# Onset strength 반영: 뚜렷한 타격이 그루브 인식에 더 기여 (고스트 노트 과도 페널티 방지)
strength_norm = np.clip((strengths - strengths.min()) / (strengths.max() - strengths.min() + 1e-8), 0, 1)
strength_weight = 0.85 + 0.15 * strength_norm  # 0.85~1.0 범위

temporal_score_raw = grid_align_score * repetition_score * strength_weight

def robust_norm(x):
    """0~1 정규화"""
    p1, p99 = np.percentile(x, [1, 99])
    if p99 == p1 or np.isnan(p99 - p1):
        return np.clip(x, 0, 1)
    x_norm = (x - p1) / (p99 - p1)
    return np.clip(x_norm, 0, 1)

temporal_score = robust_norm(temporal_score_raw)

print(f"grid_align_score: min={grid_align_score.min():.4f}, max={grid_align_score.max():.4f}")
print(f"repetition_score: min={repetition_score.min():.4f}, max={repetition_score.max():.4f}")
print(f"temporal_score: min={temporal_score.min():.4f}, max={temporal_score.max():.4f}")

# %%
# JSON 내보내기
out = {
    "metadata": {
        "source": os.path.basename(audio_path),
        "sr": int(sr),
        "duration_sec": round(float(duration), 4),
        "hop_length": int(hop_length),
        "bpm": round(float(bpm), 2),
        "bpm_dynamic_used": bpm_dynamic_used,
        "total_events": len(onset_times),
    },
    "events": []
}

for i in range(len(onset_times)):
    ev = {
        "index": i,
        "time": round(float(onset_times[i]), 4),
        "frame": int(onset_frames[i]),
        "strength": round(float(strengths[i]), 4),
        "grid_align_score": round(float(grid_align_score[i]), 4),
        "repetition_score": round(float(repetition_score[i]), 4),
        "temporal_score": round(float(temporal_score[i]), 4),
    }
    if np.isfinite(ioi_prev[i]):
        ev["ioi_prev"] = round(float(ioi_prev[i]), 4)
    if np.isfinite(ioi_next[i]):
        ev["ioi_next"] = round(float(ioi_next[i]), 4)
    out["events"].append(ev)

samples_dir = os.path.join(project_root, "audio_engine", "samples")
os.makedirs(samples_dir, exist_ok=True)
json_path = os.path.join(samples_dir, "onset_events_temporal.json")

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

web_public = os.path.join(project_root, "web", "public")
if os.path.isdir(web_public):
    shutil.copy(json_path, os.path.join(web_public, "onset_events_temporal.json"))
    print("웹 public 복사 완료: web/public/onset_events_temporal.json")

print(f"저장 완료: {json_path}")
