"""
07. Spectral Focus (주파수 집중도)
주파수 에너지가 한 대역에 뭉쳐 또렷한가, 아니면 넓게 퍼져 텍스처인가
Spectral Centroid, Bandwidth, Flatness -> focus_score
"""
import sys
import os
import json
import shutil

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

# audio_path = os.path.join(
#     project_root, 'audio_engine', 'samples', 'stems', 'htdemucs', 'sample_ropes_short', 'drums.wav'
# )
audio_path = os.path.join(project_root, 'audio_engine', 'samples', 'sample_ropes_short.mp3')

if not os.path.exists(audio_path):
    raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")

y, sr = librosa.load(audio_path)
duration = len(y) / sr
print(f"파일: {os.path.basename(audio_path)}")
print(f"샘플링 레이트: {sr} Hz, 길이: {duration:.2f} 초")

# Onset 검출 + refine (01_energy와 동일)
hop_length = 256
hop_refine = 64
win_refine_sec = 0.08
n_fft = 2048

onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
onset_frames = librosa.onset.onset_detect(
    onset_envelope=onset_env, sr=sr, hop_length=hop_length,
    delta=0.07, wait=4, backtrack=False,
)
onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
strengths = onset_env[onset_frames]

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

# Phase 3: 이벤트 구간 [mid_prev, mid_next] 정의 (01_energy와 동일)
n_events = len(onset_times)
centroids = []
bandwidths = []
flatnesses = []

for i in range(n_events):
    mid_prev = 0.0 if i == 0 else (onset_times[i - 1] + onset_times[i]) / 2
    mid_next = duration if i == n_events - 1 else (onset_times[i] + onset_times[i + 1]) / 2
    start_sample = max(0, int(round(mid_prev * sr)))
    end_sample = min(len(y), int(round(mid_next * sr)))
    seg = y[start_sample:end_sample]

    if len(seg) < n_fft // 4:
        centroids.append(np.nan)
        bandwidths.append(np.nan)
        flatnesses.append(np.nan)
        continue

    if len(seg) < n_fft:
        seg = np.pad(seg, (0, n_fft - len(seg)), mode="constant", constant_values=0)

    S = np.abs(librosa.stft(seg[:n_fft], n_fft=n_fft, hop_length=n_fft // 2)) ** 2
    if S.size == 0:
        centroids.append(np.nan)
        bandwidths.append(np.nan)
        flatnesses.append(np.nan)
        continue

    cent = librosa.feature.spectral_centroid(S=S, sr=sr)
    bw = librosa.feature.spectral_bandwidth(S=S, sr=sr, centroid=cent)
    flat = librosa.feature.spectral_flatness(S=S)

    centroids.append(float(np.nanmean(cent)))
    bandwidths.append(float(np.nanmean(bw)))
    flatnesses.append(float(np.nanmean(flat)))

centroids = np.array(centroids)
bandwidths = np.array(bandwidths)
flatnesses = np.array(flatnesses)

valid = np.isfinite(centroids) & np.isfinite(bandwidths) & np.isfinite(flatnesses)
print(f"centroid (Hz): min={np.nanmin(centroids):.0f}, max={np.nanmax(centroids):.0f}")
print(f"bandwidth (Hz): min={np.nanmin(bandwidths):.0f}, max={np.nanmax(bandwidths):.0f}")
print(f"flatness: min={np.nanmin(flatnesses):.4f}, max={np.nanmax(flatnesses):.4f}")

# Focus = 1 - norm(flatness) - norm(spread) (적당히 가중)
# flatness, bandwidth 낮을수록 "포커스" 높음 -> 또렷한 타격
def robust_norm(x, valid_mask=None):
    if valid_mask is not None:
        arr = x[valid_mask]
    else:
        arr = x[np.isfinite(x)]
    if len(arr) < 2:
        return np.clip(np.nan_to_num(x, nan=0.5), 0, 1)
    p1, p99 = np.percentile(arr, [1, 99])
    if p99 <= p1:
        return np.clip(np.nan_to_num(x, nan=0.5), 0, 1)
    out = (x - p1) / (p99 - p1)
    out = np.clip(out, 0, 1)
    out = np.nan_to_num(out, nan=0.5)
    return out

flat_norm = robust_norm(flatnesses, valid)
bw_norm = robust_norm(bandwidths, valid)

# Focus = 1 - 0.5*flat - 0.5*spread (가중 합)
# 0~1 유지
focus_score = 1.0 - 0.5 * flat_norm - 0.5 * bw_norm
focus_score = np.clip(focus_score, 0, 1)

print(f"focus_score: min={focus_score.min():.4f}, max={focus_score.max():.4f}")

# JSON 내보내기
out = {
    "metadata": {
        "source": os.path.basename(audio_path),
        "sr": int(sr),
        "duration_sec": round(float(duration), 4),
        "hop_length": int(hop_length),
        "n_fft": int(n_fft),
        "bpm": round(float(bpm), 2),
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
        "spectral_centroid_hz": round(float(centroids[i]), 2) if np.isfinite(centroids[i]) else None,
        "spectral_bandwidth_hz": round(float(bandwidths[i]), 2) if np.isfinite(bandwidths[i]) else None,
        "spectral_flatness": round(float(flatnesses[i]), 4) if np.isfinite(flatnesses[i]) else None,
        "focus_score": round(float(focus_score[i]), 4),
    }
    out["events"].append(ev)

samples_dir = os.path.join(project_root, "audio_engine", "samples")
os.makedirs(samples_dir, exist_ok=True)
json_path = os.path.join(samples_dir, "onset_events_spectral.json")

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

web_public = os.path.join(project_root, "web", "public")
if os.path.isdir(web_public):
    shutil.copy(json_path, os.path.join(web_public, "onset_events_spectral.json"))
    print("웹 public 복사 완료: web/public/onset_events_spectral.json")

print(f"저장 완료: {json_path}")
