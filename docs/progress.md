# 작업 내용 및 핵심 요약 (파일별)

## 오디오 엔진 (audio_engine)

### 01_explore.ipynb

**역할**: 음악 파형 탐색 + Onset/Beat 기본 테스트 (Step 1).

**작업 내용**:
- 오디오 로드 및 전체/확대 파형 시각화 (10~15초 줌).
- **Onset 검출**: `librosa.onset.onset_detect` (delta=0.05, wait=2, backtrack=True, hop_length=256).
- **Beat 검출**: `librosa.beat.beat_track` → 박자 그리드 + BPM.
- **드럼 스템 선택 사용**: `stems/htdemucs/{트랙명}/drums.wav` 존재 시 해당 파일로 onset 재계산(드럼 타격 더 많이 검출).
- **JSON 저장**: `audio_engine/samples/onset_beats.json` — source, sr, duration_sec, tempo_bpm, onset_times_sec, beat_times_sec, (선택) drum_onset_times_sec.
- **시각화**: 파형 위 beat(주황), onset(빨강), 드럼 onset(초록) 세로선.

**핵심**: Step 1 산출물(onset/beat 리스트 + JSON) 확보. 드럼 스템 사용 시 타격점 검출 개수 증가.

---

### 02_split_stem.ipynb

**역할**: Stem 분리 검증 (Step 2).

**작업 내용**:
- Demucs(htdemucs)로 원본 오디오를 4 stem으로 분리.
- **출력**: `samples/stems/htdemucs/{트랙명}/` 아래 `drums.wav`, `bass.wav`, `vocals.wav`, `other.wav`.
- 엔진은 `audio_engine/engine/stems.py`의 `separate()` 사용 (필요 시 MP3→WAV 변환 후 Demucs 호출).

**핵심**: drums stem 확보 → 01_explore 드럼 onset, 03_visualize_point 드럼 입력으로 활용.

---

### 03_visualize_point.ipynb

**역할**: 타격점 세기·질감 시각화 (Step 1 확장).

**작업 내용**:
- **입력**: 원본 또는 드럼 스템 경로 한 개 (`audio_path`).
- **Onset + 세기**: `onset_strength` → `onset_detect` → `strengths = onset_env[onset_frames]`.
- **질감 정의**: Spectral Centroid (Hz) — `librosa.feature.spectral_centroid`로 프레임별 계산 후 `textures = centroid[0, onset_frames]`.
- **Evaluation**: 질감 min/max/mean 출력 + 질감(Hz) 분포 히스토그램.
- **시각화**: (1) 파형 + scatter(시간, 진폭, 점 크기=세기), (2) 시간–질감 scatter(시간, 질감 Hz, 점 크기=세기) 전체, (3) 동일 시간–질감 확대(12초). 세기는 모든 scatter에서 30~500 선형 스케일 유지.
- **JSON 출력**: `audio_engine/samples/onset_events.json` — `events` 배열 (t, strength 0~1, layer, color, texture_hz). 웹에서 업로드하여 파형 위 이벤트 시각화 가능.

**핵심**: 세기=점 크기, y축=질감(Hz)로 “어두운 타격 vs 밝은 타격” 구분 가능. 웹 시각화용 events JSON 출력.

---

### audio_engine/engine/

| 파일 | 역할 | 핵심 |
|------|------|------|
| **stems.py** | Demucs 래퍼 | MP3 등 비-WAV는 WAV로 변환 후 Demucs 실행, stem별 wav 경로 반환. |
| **schemas.py** | 결과 스키마 | 스텁(주석만). |
| **keypoints.py** | 키포인트 추출 | 스텁(주석만). |
| **viz.py** | 시각화 유틸 | 스텁(주석만). |

---

## 웹 (web)

**역할**: 파형 + 이벤트 포인트 오버레이 시각화.

**작업 내용**:
- **JsonUploader**: JSON 파일 업로드 → `parseEventsFromJson` → `EventPoint[]` 전달.
- **WaveformWithOverlay**: 오디오 파형 + 이벤트 포인트(세로선/마커), 레이어별 토글.
- **parseEvents.ts**: (1) `onset_times_sec` 단일 배열 → onset 이벤트로 변환, (2) `events` 배열 또는 최상위 배열 → `{ t, strength?, color?, layer? }` 정규화.

**핵심**: `onset_beats.json`(onset_times_sec) 또는 `events` 배열 JSON 업로드 시 파형 위에 타격점 표시 가능.

---

## 문서

| 파일 | 내용 |
|------|------|
| **docs/personal.md** | 테스트/검증 로드맵(Step 0~7), 산출물 정리, 우선순위. |
| **docs/json_spec.md** | 파일별 JSON 추출 형식 및 Web 수용 형식 정리. |
| **docs/progress.md** | 본 문서 — 파일별 작업 내용 및 핵심 요약. |
