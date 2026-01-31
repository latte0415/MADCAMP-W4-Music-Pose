"""
08. Context Dependency (맥락 의존성)
"혼자 있을 때만 들리는가? 다른 소리에 묻히는가?"
psychoacoustic masking 관점에서 이벤트의 맥락 의존성을 측정합니다.

측정:
- Local SNR: 이벤트 윈도우 에너지 vs 배경 윈도우 에너지
- 대역별 마스킹: 이벤트/배경 스펙트럼을 Low/Mid/High 대역별로 비교
- dependency_score = 1 - norm(SNR) (SNR 낮으면 의존성 높음)
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

# 입력 오디오 경로
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

# 대역 정의 (Hz)
band_hz = [(20, 150), (150, 2000), (2000, 10000)]
band_names = ["low", "mid", "high"]

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

# --- Helper functions ---
def hz_to_bin(f_hz, sr, n_fft):
    return int(f_hz * n_fft / sr)

def get_band_energy(S, sr, n_fft, band_hz):
    """스펙트럼 S에서 대역별 에너지 계산"""
    n_bins = S.shape[0]
    energies = {}
    for (f_lo, f_hi), name in zip(band_hz, band_names):
        b_lo = min(hz_to_bin(f_lo, sr, n_fft), n_bins - 1)
        b_hi = min(hz_to_bin(f_hi, sr, n_fft), n_bins)
        energies[name] = np.sum(S[b_lo:b_hi])
    return energies

def robust_norm(x, valid_mask=None):
    """0~1 정규화 (percentile 기반)"""
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

# --- Context Dependency 계산 ---
n_events = len(onset_times)
snr_db_arr = []
masking_low_arr = []
masking_mid_arr = []
masking_high_arr = []

# 이벤트 윈도우: onset 중심 ±event_win_sec
# 배경 윈도우: 이벤트 윈도우 직전/직후 구간
event_win_sec = 0.05  # 이벤트 윈도우 (±50ms = 100ms total)
bg_win_sec = 0.1      # 배경 윈도우 길이 (100ms)

for i in range(n_events):
    t = onset_times[i]
    
    # 이벤트 윈도우 (onset 중심 ±event_win_sec)
    ev_start = max(0, int(round((t - event_win_sec) * sr)))
    ev_end = min(len(y), int(round((t + event_win_sec) * sr)))
    seg_event = y[ev_start:ev_end]
    
    # 배경 윈도우 (이벤트 윈도우 직전)
    bg_end = ev_start
    bg_start = max(0, bg_end - int(round(bg_win_sec * sr)))
    seg_bg_prev = y[bg_start:bg_end] if bg_end > bg_start else np.array([])
    
    # 배경 윈도우 (이벤트 윈도우 직후)
    bg_start_after = ev_end
    bg_end_after = min(len(y), bg_start_after + int(round(bg_win_sec * sr)))
    seg_bg_next = y[bg_start_after:bg_end_after] if bg_end_after > bg_start_after else np.array([])
    
    # 배경 합치기 (직전 + 직후)
    if len(seg_bg_prev) > 0 and len(seg_bg_next) > 0:
        seg_bg = np.concatenate([seg_bg_prev, seg_bg_next])
    elif len(seg_bg_prev) > 0:
        seg_bg = seg_bg_prev
    elif len(seg_bg_next) > 0:
        seg_bg = seg_bg_next
    else:
        seg_bg = np.array([0.0])
    
    # --- Local SNR ---
    E_event = np.mean(seg_event ** 2) if len(seg_event) > 0 else 1e-10
    E_bg = np.mean(seg_bg ** 2) if len(seg_bg) > 0 else 1e-10
    E_event = max(E_event, 1e-10)
    E_bg = max(E_bg, 1e-10)
    snr_db = 10 * np.log10(E_event / E_bg)
    snr_db_arr.append(snr_db)
    
    # --- 대역별 마스킹 ---
    # 이벤트 스펙트럼
    if len(seg_event) < n_fft // 4:
        masking_low_arr.append(0.5)
        masking_mid_arr.append(0.5)
        masking_high_arr.append(0.5)
        continue
    
    if len(seg_event) < n_fft:
        seg_event_padded = np.pad(seg_event, (0, n_fft - len(seg_event)), mode="constant")
    else:
        seg_event_padded = seg_event[:n_fft]
    
    S_event = np.abs(np.fft.rfft(seg_event_padded)) ** 2
    
    # 배경 스펙트럼
    if len(seg_bg) < n_fft:
        seg_bg_padded = np.pad(seg_bg, (0, n_fft - len(seg_bg)), mode="constant")
    else:
        seg_bg_padded = seg_bg[:n_fft]
    
    S_bg = np.abs(np.fft.rfft(seg_bg_padded)) ** 2
    
    # 대역별 에너지
    E_event_bands = get_band_energy(S_event, sr, n_fft, band_hz)
    E_bg_bands = get_band_energy(S_bg, sr, n_fft, band_hz)
    
    # 마스킹 비율: E_bg / E_event (배경이 클수록 마스킹 높음)
    # 0~1로 클리핑 (1이면 완전히 마스킹됨)
    def masking_ratio(e_bg, e_ev):
        if e_ev < 1e-10:
            return 1.0
        ratio = e_bg / (e_ev + 1e-10)
        return min(1.0, ratio)
    
    masking_low_arr.append(masking_ratio(E_bg_bands["low"], E_event_bands["low"]))
    masking_mid_arr.append(masking_ratio(E_bg_bands["mid"], E_event_bands["mid"]))
    masking_high_arr.append(masking_ratio(E_bg_bands["high"], E_event_bands["high"]))

snr_db_arr = np.array(snr_db_arr)
masking_low_arr = np.array(masking_low_arr)
masking_mid_arr = np.array(masking_mid_arr)
masking_high_arr = np.array(masking_high_arr)

print(f"SNR (dB): min={snr_db_arr.min():.2f}, max={snr_db_arr.max():.2f}, mean={snr_db_arr.mean():.2f}")
print(f"masking_low: min={masking_low_arr.min():.4f}, max={masking_low_arr.max():.4f}")
print(f"masking_mid: min={masking_mid_arr.min():.4f}, max={masking_mid_arr.max():.4f}")
print(f"masking_high: min={masking_high_arr.min():.4f}, max={masking_high_arr.max():.4f}")

# --- Dependency Score ---
# SNR 낮을수록 의존성 높음 → dependency = 1 - norm(SNR)
snr_norm = robust_norm(snr_db_arr)
dependency_score = 1.0 - snr_norm
dependency_score = np.clip(dependency_score, 0, 1)

print(f"dependency_score: min={dependency_score.min():.4f}, max={dependency_score.max():.4f}")

# --- JSON 내보내기 ---
out = {
    "metadata": {
        "source": os.path.basename(audio_path),
        "sr": int(sr),
        "duration_sec": round(float(duration), 4),
        "hop_length": int(hop_length),
        "n_fft": int(n_fft),
        "bpm": round(float(bpm), 2),
        "event_win_sec": event_win_sec,
        "bg_win_sec": bg_win_sec,
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
        "snr_db": round(float(snr_db_arr[i]), 2),
        "masking_low": round(float(masking_low_arr[i]), 4),
        "masking_mid": round(float(masking_mid_arr[i]), 4),
        "masking_high": round(float(masking_high_arr[i]), 4),
        "dependency_score": round(float(dependency_score[i]), 4),
    }
    out["events"].append(ev)

samples_dir = os.path.join(project_root, "audio_engine", "samples")
os.makedirs(samples_dir, exist_ok=True)
json_path = os.path.join(samples_dir, "onset_events_context.json")

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

web_public = os.path.join(project_root, "web", "public")
if os.path.isdir(web_public):
    shutil.copy(json_path, os.path.join(web_public, "onset_events_context.json"))
    print("웹 public 복사 완료: web/public/onset_events_context.json")

print(f"저장 완료: {json_path}")
