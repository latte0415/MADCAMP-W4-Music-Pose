# 같은 비트·다른 값 문제 — 수정 계획안

Energy/Clarity가 “같은 비트(MIDI·청각 동일)인데 다른 값”으로 나오는 원인(프레임 양자화, backtrack, 인접 타격 겹침)을 줄이기 위한 수정 계획.  
**측정 정의**를 바꿔서 기준 시점·윈도우에 덜 민감하게 만드는 방향으로 정리함.

---

## 적용 대상

| 파일 | 역할 |
|------|------|
| [01_energy.ipynb](audio_engine/notebooks/02_layered_onset_export/01_energy.ipynb) | Energy(RMS·대역별), energy_score |
| [02_clarity.ipynb](audio_engine/notebooks/02_layered_onset_export/02_clarity.ipynb) | Attack time, clarity_score |

두 노트북이 **동일한 onset 파이프라인**(`onset_frames`, `onset_times`)을 쓰므로, **0단계·1단계·2단계**는 한 번 적용하면 둘 다 이득.

---

## Phase 0: 즉시 패치 (우선 적용)

### 0-1) `backtrack=False`로 통일

**목적**: valley까지 당기는 backtrack이 타격마다 기준 시점을 흔들어서, 같은 비트가 다른 값으로 나오는 것을 완화.

**수정 위치**

- **01_energy.ipynb** — Onset 검출 셀  
  - `onset_detect(..., backtrack=True)` → `backtrack=False`
- **02_clarity.ipynb** — Onset 검출 셀  
  - 동일하게 `backtrack=False`

**선택**: 나중에 “제한 backtrack”(±1~2프레임 이내 local minimum만)을 쓰고 싶으면, `librosa.onset.onset_backtrack` 대신 직접 짧은 구간만 검색하는 함수를 만들어서 적용.

---

### 0-2) 샘플 변환은 `round` 사용

**목적**: `int(t*sr)`는 항상 내림이라 편향이 생김. `round`로 바꿔 분산 완화.

**수정 위치**

- **02_clarity.ipynb** — Attack time 계산 루프  
  - `center_sample = int(t * sr)`  
  - → `center_sample = int(round(t * sr))`  
  - (또는 `np.round(onset_times * sr).astype(int)`로 벡터화 가능)

**01_energy**: 프레임 기준 `(f ± half_win_frames) * hop_length`만 쓰므로 샘플 변환은 없음.  
나중에 **onset_times 기반** 구간을 쓰게 되면 그때부터 `round(onset_times * sr)` 사용.

---

### 0-3) 윈도우를 “이웃 onset 기반” 가변으로 변경 (겹침 방지)

**목적**: 인접 타격이 한 윈도우에 섞이지 않게 해서, “같은 비트인데 옆 타격 때문에 값이 튀는” 현상 감소.

**공통 전제**

- `onset_times` (길이 N)가 이미 계산된 상태.
- `t_0 = 0` 또는 첫 onset 이전 구간 시작, `t_{N} = duration` 또는 마지막 onset 이후 구간 끝으로 두고,  
  `gap_prev[i] = t_i - t_{i-1}`, `gap_next[i] = t_{i+1} - t_i` (경계는 `np.inf` 등으로 처리).

**01_energy.ipynb**

- 현재: `start_sample = (f - half_win_frames) * hop_length`, `end_sample = (f + half_win_frames + 1) * hop_length` (고정 프레임 윈도우).
- 변경: **시간 기준 가변 half-win**  
  - `half_win_sec_fixed = (2 * half_win_frames + 1) * hop_length / sr / 2` (기존 윈도우의 절반 길이, 초).  
  - 이벤트 i에 대해  
    - `left_sec = min(half_win_sec_fixed, 0.45 * gap_prev[i])`  
    - `right_sec = min(half_win_sec_fixed, 0.45 * gap_next[i])`  
  - `start_sample = round((onset_times[i] - left_sec) * sr)`, `end_sample = round((onset_times[i] + right_sec) * sr)` (경계는 `max(0, ...)`, `min(len(y), ...)`).
- **대역별 에너지** 셀도 동일한 `start_sample`, `end_sample`을 쓰도록 변경 (프레임 `f` 대신 `onset_times[i]` + 위 left/right 사용).
- **win_total_sec** 등 겹침 분석은 “이벤트별로 다른 윈도우 길이”가 되므로, “겹침” 정의를  
  `(onset_times[i] - left_sec) < (onset_times[i-1] + right_prev)` 형태로 재정의하거나, 단순히 `gap_prev[i] < (left_sec + right_prev)` 로 계산.

**02_clarity.ipynb**

- 현재: `pre_onset_ms = 50`, `post_onset_ms = 20` 고정.  
  `center_sample = int(t*sr)` 기준으로 `[center - pre_samples, center + post_samples]`.
- 변경:  
  - `pre_sec = min(0.05, 0.45 * gap_prev[i])`, `post_sec = min(0.02, 0.45 * gap_next[i])` (단위 초).  
  - `center_sample = round(onset_times[i] * sr)`  
  - `start_sample = max(0, round((onset_times[i] - pre_sec) * sr))`  
  - `end_sample = min(len(y), round((onset_times[i] + post_sec) * sr))`  
  - `gap_prev`/`gap_next`는 `np.diff(onset_times)`와 앞뒤 패딩으로 생성.

이렇게 하면 빠른 연주 구간에서 윈도우가 자동으로 짧아져, 두 타격이 한 윈도우에 같이 들어가는 경우가 크게 줄어듦.

---

## Phase 1: 프레임 양자화 줄이기

### 1-1) hop_length 축소 (선택)

- 현재 `hop_length=256` (sr=22050이면 약 11.6 ms).
- 128 또는 64로 줄이면 “같은 비트인데 프레임이 달라서” 생기는 윈도우 어긋남이 감소.
- **비용**: onset_strength·beat_track 등 연산량 증가 (대략 2x~4x).
- **적용**: 01_energy·02_clarity 공통으로 onset 검출 셀에서 `hop_length=256` → `128`(또는 64)로 변경.  
  BPM/beat_duration 기반 `half_win_frames` 등은 그대로 두면 됨 (프레임 수는 자동으로 더 촘촘해짐).

### 1-2) 멀티해상도 로컬 리파인 (권장)

- 전체는 기존 `hop_length=256`으로 onset 검출.
- 각 `onset_frames[i]` (또는 `onset_times[i]`) 주변 **±80 ms 정도만** `hop_length=64`(또는 128)로 onset_strength를 다시 계산하고,  
  그 구간에서 **피크 프레임**을 찾아서 해당 프레임을 “정제된 onset”으로 사용.
- 정제된 onset을 `onset_frames_refined`, `onset_times_refined`로 두고, 이후 Energy/Clarity는 **이 정제된 시점** 기준으로 계산.
- **적용**:  
  - 01_energy·02_clarity **앞단**에 공통 셀 하나 추가:  
    `refine_onset_times(y, sr, onset_frames, onset_times, hop_length=256, hop_refine=64, win_refine_sec=0.08)`  
    → `onset_times_refined`, (필요 시) `onset_frames_refined`.  
  - 기존 `onset_times` 대신 `onset_times_refined`를 쓰도록 두 노트북의 Energy/Clarity 셀을 수정.

---

## Phase 2: 서브프레임 기준점 추정

### 2-1) Onset envelope peak의 parabolic interpolation

- `onset_strength`(프레임 시퀀스)에서 각 검출된 peak 주변 3점으로 포물선 보간해,  
  peak 위치를 **프레임 인덱스 소수**로 추정 → `frames_to_time`으로 변환하면 ms 단위 기준 시점 획득.
- **적용**:  
  - Phase 1-2의 “로컬 리파인” 셀 안에서, 또는 별도 셀에서  
    `onset_times_refined = parabolic_peak_to_time(onset_frames, onset_env, sr, hop_length)`  
  - 이후 모든 윈도우 계산은 `onset_times_refined` 기준.

### 2-2) 로컬 파형/에너지 기반 미세 정렬 (선택)

- Onset 근처(예: ±30 ms)에서 band-limited envelope(예: 60–200 Hz 킥, 1–4 kHz 스네어/하이햇) 또는 짧은 RMS의 **상승 구간(derivative peak)**을 찾아 onset을 재정의.
- 드럼처럼 transient가 뚜렷한 소스에 유리. 구현 난이도는 2-1보다 높음.

---

## Phase 3: Energy/Clarity 정의를 “구간 안정형”으로 변경

### 3-1) Energy: “온셋 간 구간” 집계

- **현재**: center 기준 고정(또는 가변) 윈도우에서 RMS.
- **변경**: 이벤트 i의 구간을  
  `[mid(t_{i-1}, t_i), mid(t_i, t_{i+1})]`  
  로 정의하고, **그 구간**에서 RMS(및 대역별 에너지) 계산.  
  “center가 몇 ms 흔들림”이 결과에 거의 반영되지 않고, 인접 타격과의 구간이 명확히 갈림.
- **적용**:  
  - 01_energy에서 `start_sample`/`end_sample`을  
    `mid_prev = (onset_times[i-1] + onset_times[i]) / 2`, `mid_next = (onset_times[i] + onset_times[i+1]) / 2`  
    로 두고, `[round(mid_prev*sr), round(mid_next*sr)]` 구간으로 segment 잘라서 RMS·대역 에너지 계산.  
  - 첫/끝 이벤트는 `mid_prev=0` 또는 `mid_next=duration` 등으로 예외 처리.

### 3-2) Clarity: “로컬 최소 → 로컬 최대” 구간에서 10–90%

- **현재**: onset 기준 고정(또는 가변) 윈도우에서 envelope를 만들고, 그 구간 전체의 peak 기준 10%–90%로 attack time 계산.  
  → 윈도우가 조금만 어긋나도 “어택 구간”이 달라져 값이 흔들림.
- **변경**:  
  - Onset i 주변에서 envelope를 만든 뒤,  
    **해당 이벤트의 로컬 최소( valley ) → 로컬 최대( peak )** 구간만 잘라서,  
    그 구간 내에서 10%–90% 도달 시간을 계산.  
  - 즉 “이 이벤트의 어택 구간”을 **이벤트 단위 로컬 min–max**로 규정해, center 기준 윈도우 위치에 덜 민감하게 함.
- **적용**:  
  - 02_clarity의 `get_attack_time` (또는 이벤트 루프 안)에서:  
    segment의 envelope를 구한 뒤, **peak 이전**에서 **직전 로컬 최소**를 찾고,  
    `pre_peak_env = env[local_min_idx : peak_idx+1]`  
    처럼 잘라서 10%–90%를 계산.  
  - 로컬 최소가 없으면 기존처럼 segment 시작~peak 사용.

---

## Phase 4: 드럼 stem artefact 대응 (선택)

- HPSS(percussive 강화), 대역별 energy 분리(킥/스네어/하이햇), log + robust normalize 등은 01_energy에 이미 일부 있음.
- Demucs 등 분리 artefact로 에너지가 흔들릴 때만 추가로:  
  band 제한 envelope, HPSS 후 퍼커시브만으로 Energy/Clarity 재계산 등을 검토.

---

## MVP 적용 순서 (권장)

1. **Phase 0 전부**  
   - `backtrack=False` (0-1)  
   - 02_clarity에서 `round(t*sr)` (0-2)  
   - 01_energy·02_clarity 모두 **이웃 onset 기반 가변 윈도우** (0-3)  
   → 구현 부담 작고, “같은 비트 다른 값”이 체감상 많이 줄어듦.

2. **Phase 1-2 (로컬 리파인)**  
   - 정제된 `onset_times_refined`를 두 노트북에 공통 적용.  
   → 프레임 양자화 영향 추가 감소.

3. **Phase 3**  
   - 01_energy: **온셋 간 구간** RMS/대역 에너지 (3-1)  
   - 02_clarity: **로컬 min→max** 구간에서 10–90% (3-2)  
   → 기준 시점에 덜 민감한 “구간 안정형” 정의로 전환.

4. **Phase 2-1 (parabolic)**  
   - 로컬 리파인과 결합해 서브프레임 시점 추정.  
   (Phase 1-2만 해도 효과 크므로, 2-1은 선택.)

5. **Phase 1-1, 2-2, 4**  
   - 필요 시 hop 축소, 로컬 파형 정렬, stem artefact 대응 추가.

---

## 수정 시 주의사항

- **01_energy**의 `win_total_sec`, 겹침 분석 셀은 “가변 윈도우”로 바뀌면 **이벤트별 left/right**가 다르므로,  
  겹침 조건을 위 0-3에 맞게 다시 정의해야 함.
- **02_clarity**의 `strengths = onset_env[onset_frames]`는 그대로 두어도 됨.  
  정제된 시점을 쓰면 `onset_frames_refined`로 인덱싱하거나, `onset_times_refined`에 대응하는 프레임 인덱스를 구해 사용.
- JSON export 시 `onset_times`를 정제된 값으로 내보내면, 이후 파이프라인(웹 시각화 등)과 호환 유지.

이 순서대로 적용하면 “같은 비트인데 다른 값”은 크게 줄고, 남는 차이는 실제 오디오 컨텍스트(잔향·누설·믹싱)로 해석하기 쉬워짐.
