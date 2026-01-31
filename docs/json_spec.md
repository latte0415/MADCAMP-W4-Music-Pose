# JSON 추출 형식 (파일별)

## 01_basic_test 폴더
- **01_explore** → `onset_beats.json` (onset/beat/드럼 onset 시점)
- **02_split_stem** → JSON 없음 (WAV 4개)
- **03_visualize_point** → `onset_events.json` (이벤트: t, strength, texture)

## 02_layered_onset_export 폴더
- **01_energy** → `onset_events_energy.json` (이벤트별 RMS/대역별 에너지)
- **02_clarity** → `onset_events_clarity.json` (이벤트별 어택 명확도)
- **03_temporal** → `onset_events_temporal.json` (이벤트별 박자 기여도/반복성)
- **04_spectral** → `onset_events_spectral.json` (이벤트별 주파수 집중도)
- **05_context** → `onset_events_context.json` (이벤트별 맥락 의존성)

## Web
- 수용 형식: `onset_times_sec`, `events[]`, 배열 직접

---

## 1. 01_explore.ipynb → onset_beats.json

**출력 경로**: `audio_engine/samples/onset_beats.json`

**생성 시점**: Onset + Beat 검출 셀 실행 후 JSON 저장 셀 실행 시

**스키마**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 (예: `sample_ropes_short.mp3`) |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `tempo_bpm` | number | 추정 BPM |
| `onset_times_sec` | number[] | 전체 믹스 onset 시점 리스트 (초, 소수 넷째 자리) |
| `beat_times_sec` | number[] | 박자 그리드 시점 리스트 (초) |
| `drum_onset_times_sec` | number[] | (선택) 드럼 스템 기준 onset 시점 리스트. Demucs drums.wav 존재 시에만 포함 |

**예시**:

```json
{
  "source": "sample_ropes_short.mp3",
  "sr": 22050,
  "duration_sec": 31.11,
  "tempo_bpm": 120.5,
  "onset_times_sec": [0.1234, 0.5678, ...],
  "beat_times_sec": [0.0, 0.5, 1.0, ...],
  "drum_onset_times_sec": [0.12, 0.56, ...]
}
```

---

## 2. 02_split_stem.ipynb

**JSON 출력 없음.**  
산출물은 WAV 파일 4개: `drums.wav`, `bass.wav`, `vocals.wav`, `other.wav` (Demucs 출력 디렉터리: `samples/stems/htdemucs/{트랙명}/`).

---

## 3. 03_visualize_point.ipynb → onset_events.json

**출력 경로**: `audio_engine/samples/onset_events.json`

**생성 시점**: 질감 정의·evaluation 셀 실행 후, JSON 저장 셀 실행 시 (시각화 셀 전)

**용도**: 웹에서 업로드하여 파형 위 이벤트(세기 반영) 시각화.

**스키마** (최상위):

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `texture_min_hz` | number | 질감(Spectral Centroid) 최소값 (Hz) |
| `texture_max_hz` | number | 질감(Spectral Centroid) 최대값 (Hz) |
| `events` | object[] | 이벤트 배열 (아래 events[] 항목 참고) |

**events[] 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `t` | number | 시간(초), 소수 넷째 자리 |
| `strength` | number | 세기 0~1 (onset strength 정규화) |
| `texture` | number | 질감 0~1 (Spectral Centroid min-max 정규화) |
| `texture_hz` | number | 질감 원값 (Hz, Spectral Centroid) |
| `layer` | string | `"onset"` |
| `color` | string | hex 색상 (예: `"#5a9fd4"`) |

**예시**:

```json
{
  "source": "sample_ropes_short.mp3",
  "sr": 22050,
  "duration_sec": 31.11,
  "texture_min_hz": 500.0,
  "texture_max_hz": 4000.0,
  "events": [
    { "t": 0.1234, "strength": 0.8, "texture": 0.7, "texture_hz": 1200.5, "layer": "onset", "color": "#5a9fd4" },
    { "t": 0.5678, "strength": 0.3, "texture": 0.2, "texture_hz": 800.2, "layer": "onset", "color": "#5a9fd4" }
  ]
}
```

- 웹에서 `strength`, `texture`, `texture_hz`, `texture_min_hz`, `texture_max_hz` 등 필요한 필드만 골라 사용하면 됨.

---

## 4. 01_energy.py → onset_events_energy.json

**출력 경로**: `audio_engine/samples/onset_events_energy.json`

**생성 시점**: 에너지 계산 후 JSON 저장 셀 실행 시

**용도**: 웹에서 이벤트별 RMS 에너지 및 대역별 에너지 시각화.

**스키마** (최상위):

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `energy_rms_min` | number | RMS 최소값 |
| `energy_rms_max` | number | RMS 최대값 |
| `hop_length` | number | hop length (기본 256) |
| `bpm` | number | 추정 BPM |
| `total_events` | number | 총 이벤트 수 |
| `events` | object[] | 이벤트 배열 |

**events[] 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `t` | number | 시간(초), 소수 넷째 자리 |
| `time` | number | 시간(초), t와 동일 |
| `strength` | number | 에너지 점수 0~1 (energy_score) |
| `texture` | number | 고역 에너지 0~1 (E_norm_high) |
| `color` | string | hex 색상 (예: `"#5a9fd4"`) |
| `rms` | number | RMS 원값 |
| `e_norm` | number | 정규화된 에너지 점수 |
| `band_low` | number | 저역(20-150Hz) 에너지 0~1 |
| `band_mid` | number | 중역(150-2kHz) 에너지 0~1 |
| `band_high` | number | 고역(2k-10kHz) 에너지 0~1 |
| `index` | number | 이벤트 인덱스 |
| `frame` | number | 프레임 번호 |
| `onset_strength` | number | onset strength 원값 |
| `log_rms` | number | log RMS 값 |
| `energy_score` | number | 최종 에너지 점수 0~1 |
| `left_sec` | number | 이전 onset까지 거리 (초) |
| `right_sec` | number | 다음 onset까지 거리 (초) |
| `overlap_prev` | boolean | 이전 onset과 윈도우 겹침 여부 |

**예시**:

```json
{
  "source": "drums.wav",
  "sr": 22050,
  "duration_sec": 31.11,
  "energy_rms_min": 0.001,
  "energy_rms_max": 0.5,
  "hop_length": 256,
  "bpm": 120.5,
  "total_events": 100,
  "events": [
    { "t": 0.1234, "time": 0.1234, "strength": 0.8, "texture": 0.7, "color": "#5a9fd4", "rms": 0.3, "e_norm": 0.8, "band_low": 0.6, "band_mid": 0.7, "band_high": 0.7, "index": 0, "frame": 10, "onset_strength": 5.2, "log_rms": -1.2, "energy_score": 0.8, "left_sec": 0.1, "right_sec": 0.2, "overlap_prev": false }
  ]
}
```

---

## 5. 02_clarity.py → onset_events_clarity.json

**출력 경로**: `audio_engine/samples/onset_events_clarity.json`

**생성 시점**: 어택 명확도 계산 후 JSON 저장 셀 실행 시

**용도**: 웹에서 이벤트별 어택 시간 및 명확도 점수 시각화.

**스키마** (최상위):

| 필드 | 타입 | 설명 |
|------|------|------|
| `metadata` | object | 메타데이터 객체 |
| `events` | object[] | 이벤트 배열 |

**metadata 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `hop_length` | number | hop length (기본 256) |
| `bpm` | number | 추정 BPM |
| `total_events` | number | 총 이벤트 수 |

**events[] 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `index` | number | 이벤트 인덱스 |
| `time` | number | 시간(초), 소수 넷째 자리 |
| `frame` | number | 프레임 번호 |
| `strength` | number | onset strength |
| `attack_time_ms` | number | 어택 시간 (ms), 10%→90% 도달 시간 |
| `clarity_score` | number | 명확도 점수 0~1 |

**예시**:

```json
{
  "metadata": {
    "source": "sample_ropes_short.mp3",
    "sr": 22050,
    "hop_length": 256,
    "bpm": 120.5,
    "total_events": 100
  },
  "events": [
    { "index": 0, "time": 0.1234, "frame": 10, "strength": 5.2, "attack_time_ms": 3.5, "clarity_score": 0.85 }
  ]
}
```

---

## 6. 03_temporal.py → onset_events_temporal.json

**출력 경로**: `audio_engine/samples/onset_events_temporal.json`

**생성 시점**: 박자 기여도/반복성 계산 후 JSON 저장 셀 실행 시

**용도**: 웹에서 이벤트별 그리드 정렬도 및 반복성 점수 시각화.

**스키마** (최상위):

| 필드 | 타입 | 설명 |
|------|------|------|
| `metadata` | object | 메타데이터 객체 |
| `events` | object[] | 이벤트 배열 |

**metadata 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `hop_length` | number | hop length (기본 256) |
| `bpm` | number | 글로벌 BPM |
| `bpm_dynamic_used` | boolean | 로컬 템포 사용 여부 |
| `total_events` | number | 총 이벤트 수 |

**events[] 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `index` | number | 이벤트 인덱스 |
| `time` | number | 시간(초), 소수 넷째 자리 |
| `frame` | number | 프레임 번호 |
| `strength` | number | onset strength |
| `grid_align_score` | number | 그리드 정렬 점수 0~1 (비트 그리드와의 거리 기반) |
| `repetition_score` | number | 반복성 점수 0~1 (IOI 주기성 기반) |
| `temporal_score` | number | 최종 박자 기여도 0~1 (grid_align × repetition) |
| `ioi_prev` | number | (선택) 이전 이벤트와의 간격 (초) |
| `ioi_next` | number | (선택) 다음 이벤트와의 간격 (초) |

**예시**:

```json
{
  "metadata": {
    "source": "drums.wav",
    "sr": 22050,
    "duration_sec": 31.11,
    "hop_length": 256,
    "bpm": 120.5,
    "bpm_dynamic_used": true,
    "total_events": 100
  },
  "events": [
    { "index": 0, "time": 0.1234, "frame": 10, "strength": 5.2, "grid_align_score": 0.95, "repetition_score": 0.8, "temporal_score": 0.76, "ioi_prev": 0.5, "ioi_next": 0.5 }
  ]
}
```

---

## 7. 04_spectral.py → onset_events_spectral.json

**출력 경로**: `audio_engine/samples/onset_events_spectral.json`

**생성 시점**: 주파수 집중도 계산 후 JSON 저장 셀 실행 시

**용도**: 웹에서 이벤트별 스펙트럴 중심/대역폭/플랫니스 및 포커스 점수 시각화.

**스키마** (최상위):

| 필드 | 타입 | 설명 |
|------|------|------|
| `metadata` | object | 메타데이터 객체 |
| `events` | object[] | 이벤트 배열 |

**metadata 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `hop_length` | number | hop length (기본 256) |
| `n_fft` | number | FFT 크기 (기본 2048) |
| `bpm` | number | 추정 BPM |
| `total_events` | number | 총 이벤트 수 |

**events[] 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `index` | number | 이벤트 인덱스 |
| `time` | number | 시간(초), 소수 넷째 자리 |
| `frame` | number | 프레임 번호 |
| `strength` | number | onset strength |
| `spectral_centroid_hz` | number \| null | 스펙트럴 중심 (Hz), 유효하지 않으면 null |
| `spectral_bandwidth_hz` | number \| null | 스펙트럴 대역폭 (Hz), 유효하지 않으면 null |
| `spectral_flatness` | number \| null | 스펙트럴 플랫니스 0~1, 유효하지 않으면 null |
| `focus_score` | number | 주파수 집중도 0~1 (플랫니스·대역폭 낮을수록 높음) |

**예시**:

```json
{
  "metadata": {
    "source": "sample_ropes_short.mp3",
    "sr": 22050,
    "duration_sec": 31.11,
    "hop_length": 256,
    "n_fft": 2048,
    "bpm": 120.5,
    "total_events": 100
  },
  "events": [
    { "index": 0, "time": 0.1234, "frame": 10, "strength": 5.2, "spectral_centroid_hz": 1200.5, "spectral_bandwidth_hz": 800.2, "spectral_flatness": 0.3, "focus_score": 0.75 }
  ]
}
```

---

## 8. 05_context.py → onset_events_context.json

**출력 경로**: `audio_engine/samples/onset_events_context.json`

**생성 시점**: 맥락 의존성 계산 후 JSON 저장 셀 실행 시

**용도**: 웹에서 이벤트별 Local SNR 및 대역별 마스킹, 맥락 의존성 점수 시각화.

**스키마** (최상위):

| 필드 | 타입 | 설명 |
|------|------|------|
| `metadata` | object | 메타데이터 객체 |
| `events` | object[] | 이벤트 배열 |

**metadata 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `source` | string | 입력 오디오 파일명 |
| `sr` | number | 샘플링 레이트 (Hz) |
| `duration_sec` | number | 오디오 길이 (초) |
| `hop_length` | number | hop length (기본 256) |
| `n_fft` | number | FFT 크기 (기본 2048) |
| `bpm` | number | 추정 BPM |
| `event_win_sec` | number | 이벤트 윈도우 크기 (초, 기본 0.05) |
| `bg_win_sec` | number | 배경 윈도우 크기 (초, 기본 0.1) |
| `total_events` | number | 총 이벤트 수 |

**events[] 항목**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `index` | number | 이벤트 인덱스 |
| `time` | number | 시간(초), 소수 넷째 자리 |
| `frame` | number | 프레임 번호 |
| `strength` | number | onset strength |
| `snr_db` | number | 이벤트-배경 SNR (dB) |
| `masking_low` | number | 저역(20-150Hz) 마스킹 비율 0~1 |
| `masking_mid` | number | 중역(150-2kHz) 마스킹 비율 0~1 |
| `masking_high` | number | 고역(2k-10kHz) 마스킹 비율 0~1 |
| `dependency_score` | number | 맥락 의존성 점수 0~1 (높을수록 의존적) |

**예시**:

```json
{
  "metadata": {
    "source": "sample_ropes_short.mp3",
    "sr": 22050,
    "duration_sec": 31.11,
    "hop_length": 256,
    "n_fft": 2048,
    "bpm": 120.5,
    "event_win_sec": 0.05,
    "bg_win_sec": 0.1,
    "total_events": 100
  },
  "events": [
    { "index": 0, "time": 0.1234, "frame": 10, "strength": 5.2, "snr_db": 12.5, "masking_low": 0.2, "masking_mid": 0.3, "masking_high": 0.1, "dependency_score": 0.35 }
  ]
}
```

---

## 9. Web (시각화) — 수용 JSON 형식

**용도**: `JsonUploader` / `parseEventsFromJson`으로 로드해 파형 위 이벤트 포인트 표시.

**수용 형식** (우선순위 순):

### 9-1. onset_times_sec (audio_engine 호환)

```json
{
  "onset_times_sec": [0.12, 0.56, 1.0, ...]
}
```

- `onset_times_sec` 배열만 있으면 각 요소를 `t`(초)로 하는 이벤트로 변환.
- `strength`=0.7, `layer`="onset", 기본 색상 적용.

### 9-2. events 배열 (레이어/세기/색상/질감 포함)

```json
{
  "events": [
    { "t": 0.12, "strength": 0.8, "texture": 0.7, "texture_hz": 1200, "color": "#ff0000", "layer": "kick" },
    { "t": 0.56, "strength": 0.5, "color": "#00ff00", "layer": "snare" }
  ]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `t` | number | O | 시간(초). `time` 별칭 가능 |
| `strength` | number | X | 세기 0~1. 기본 0.7 |
| `texture` | number | X | 질감 0~1 (03_visualize_point 출력 호환) |
| `texture_hz` | number | X | 질감 원값 Hz (03 출력 호환) |
| `color` | string | X | hex 색상. 없으면 기본색 |
| `layer` | string | X | 레이어명. 기본 "default" |

### 9-3. 배열 직접 (events 래퍼 없이)

```json
[
  { "t": 0.12, "strength": 0.7, "layer": "onset" },
  { "t": 0.56, "time": 0.56 }
]
```

- 최상위가 배열이면 각 요소를 `normalizeEvent`로 `EventPoint` 변환.

**EventPoint 타입** (web/src/types/event.ts):

- `t`: number (초)
- `strength`: number (0~1)
- `color`: string (hex)
- `layer`: string

(웹에서 `texture`/`texture_hz` 사용 시 타입 확장 가능. 03의 `onset_events.json`에는 위 필드 + `texture`, `texture_hz` 포함.)
