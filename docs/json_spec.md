# JSON 추출 형식 (파일별)

- **01_explore** → `onset_beats.json` (onset/beat/드럼 onset 시점)
- **02_split_stem** → JSON 없음 (WAV 4개)
- **03_visualize_point** → `onset_events.json` (이벤트: t, strength, texture)
- **Web** → 수용 형식: `onset_times_sec`, `events[]`, 배열 직접

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

## 4. Web (시각화) — 수용 JSON 형식

**용도**: `JsonUploader` / `parseEventsFromJson`으로 로드해 파형 위 이벤트 포인트 표시.

**수용 형식** (우선순위 순):

### 4-1. onset_times_sec (audio_engine 호환)

```json
{
  "onset_times_sec": [0.12, 0.56, 1.0, ...]
}
```

- `onset_times_sec` 배열만 있으면 각 요소를 `t`(초)로 하는 이벤트로 변환.
- `strength`=0.7, `layer`="onset", 기본 색상 적용.

### 4-2. events 배열 (레이어/세기/색상/질감 포함)

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

### 4-3. 배열 직접 (events 래퍼 없이)

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
