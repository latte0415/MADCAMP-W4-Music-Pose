# JSON 추출 형식 (파일별)

## 01_basic_test 폴더
- **01_explore** → `onset_beats.json` (onset/beat/드럼 onset 시점)
- **02_split_stem** → JSON 없음 (WAV 4개)
- **03_visualize_point** → `onset_events.json` (이벤트: t, strength, texture)

## 02_layered_onset_export 폴더
- **01_energy** → `onset_events_energy.json`
- **02_clarity** → `onset_events_clarity.json`
- **03_temporal** → `onset_events_temporal.json`
- **04_spectral** → `onset_events_spectral.json`
- **05_context** → `onset_events_context.json`
- **06_layered_export** → `onset_events_layered.json`

## Web
- 수용 형식: `onset_times_sec`, `events[]`, 배열 직접

---

## 1. 01_explore → onset_beats.json

**출력 경로**: `audio_engine/samples/onset_beats.json`

**스키마**: `source`, `sr`, `duration_sec`, `tempo_bpm`, `onset_times_sec`, `beat_times_sec`, (선택) `drum_onset_times_sec`.

---

## 2. 02_split_stem

**JSON 없음.** 산출물: `samples/stems/htdemucs/{트랙명}/` — drums, bass, vocals, other.wav.

---

## 3. 03_visualize_point → onset_events.json

**출력 경로**: `audio_engine/samples/onset_events.json`

**스키마 (최상위)**: `source`, `sr`, `duration_sec`, `texture_min_hz`, `texture_max_hz`, `events[]`.  
**events[]**: `t`, `strength`, `texture`, `texture_hz`, `layer`, `color`.

---

## 4. 01_energy.py → onset_events_energy.json

**출력 경로**: `audio_engine/samples/onset_events_energy.json`

**스키마 (최상위)**: `source`, `sr`, `duration_sec`, `energy_rms_min`, `energy_rms_max`, `hop_length`, `bpm`, `total_events`, `events[]`.  
**events[]**: `t`, `time`, `strength`, `texture`, `color`, `rms`, `e_norm`, `band_low`, `band_mid`, `band_high`, `index`, `frame`, `onset_strength`, `log_rms`, `energy_score`, `left_sec`, `right_sec`, `overlap_prev`.

---

## 5. 02_clarity.py → onset_events_clarity.json

**스키마**: `metadata` (source, sr, hop_length, bpm, total_events), `events[]` (index, time, frame, strength, attack_time_ms, clarity_score).

---

## 6. 03_temporal.py → onset_events_temporal.json

**스키마**: `metadata` (source, sr, duration_sec, hop_length, bpm, bpm_dynamic_used, total_events), `events[]` (index, time, frame, strength, grid_align_score, repetition_score, temporal_score, ioi_prev, ioi_next).

---

## 7. 04_spectral.py → onset_events_spectral.json

**스키마**: `metadata`, `events[]` (index, time, frame, strength, spectral_centroid_hz, spectral_bandwidth_hz, spectral_flatness, focus_score).

---

## 8. 05_context.py → onset_events_context.json

**스키마**: `metadata` (event_win_sec, bg_win_sec 포함), `events[]` (index, time, frame, strength, snr_db, masking_low, masking_mid, masking_high, dependency_score).

---

## 9. 06_layered_export.py → onset_events_layered.json

**출력 경로**: `audio_engine/samples/onset_events_layered.json`  
**생성**: `write_layered_json()` (L5 export). 스크립트 `06_layered_export.py`.

**스키마 (최상위)**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `total_events` | number | 총 이벤트 수 |
| `layer_counts` | object | `{"P0": n, "P1": n, "P2": n}` |
| `events` | object[] | 이벤트 배열 |

**events[] 항목** (실제 `export.write_layered_json` 출력 기준):

| 필드 | 타입 | 설명 |
|------|------|------|
| `time` | number | 시간(초) |
| `t` | number | time과 동일 |
| `layer` | string | `"P0"` \| `"P1"` \| `"P2"` |
| `strength` | number | onset strength |
| `color` | string | hex (P0=#2ecc71, P1=#f39c12, P2=#3498db) |
| `energy_score` | number | 0~1 |
| `clarity_score` | number | 0~1 |
| `temporal_score` | number | 0~1 |
| `focus_score` | number | 0~1 |
| `dependency_score` | number | 0~1 |

---

## 10. Web (시각화) — 수용 JSON 형식

**수용 형식**: `onset_times_sec` 단일 배열, `events[]` 배열, 최상위 배열 직접.  
필드: `t`/`time`, `strength`, `color`, `layer`, (선택) `texture`, `texture_hz`.  
EventPoint: `t`, `strength`, `color`, `layer`.
