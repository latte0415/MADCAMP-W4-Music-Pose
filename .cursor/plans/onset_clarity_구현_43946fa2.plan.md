---
name: Onset Clarity 구현
overview: layering.md의 "2) Onset Clarity (어택 명확도)"를 notebooks/02_layered_onset_export에 구현한다. 측정 제안 A/B/C의 장단점을 정리하고, 선택 제안 후 해당 방식으로 노트북을 작성한다.
todos: []
isProject: false
---

# Onset Clarity (어택 명확도) 구현 계획

## 배경

- **목표**: "타격이 또렷하게 ‘툭’ 하고 박히는지"를 수치화 (이벤트 단위).
- **기존 파이프라인**: [01_energy.ipynb](audio_engine/notebooks/02_layered_onset_export/01_energy.ipynb)에서 `y`, `sr`, `onset_env`, `onset_frames`, `onset_times`, `hop_length`, BPM 기반 `half_win_frames` 등이 이미 계산됨. 새 노트북은 동일 오디오·동일 onset 이벤트를 전제로 clarity만 추가 계산.

---

## 측정 제안별 장단점

### A: Spectral Flux 기반

- **방식**: `onset_env`(= flux 기반)를 그대로 사용. 이벤트 `t_i` 근방에서 **피크 높이/주변 평균(peak-to-mean)** 및 **피크의 급격함(피크 폭, 상승 시간)**으로 clarity 지표 구성.
- **장점**
- 이미 쓰는 `onset_strength`(spectral flux)와 동일 소스라 추가 STFT/멜 계산 없음.
- `01_energy.ipynb`와 변수 공유만 하면 되어 구현이 빠름.
- 피크 대비 주변 평균, 피크 폭 등으로 "또렷함"을 직접 수치화 가능.
- **단점**
- onset strength와 개념이 겹쳐, "에너지 vs 클래리티" 구분이 다소 모호해질 수 있음.
- peak-to-mean·피크 폭 등 세부 정의(윈도우 크기, 기준 구간)를 정해야 함.

### B: Attack time / Rise time

- **방식**: 각 이벤트 구간에서 **amplitude envelope**를 구한 뒤, **10% → 90% 도달 시간(attack time)**을 측정. 짧을수록 명확한 어택.
- **장점**
- 문서 정의("10%→90% 도달 시간, 짧을수록 명확")와 정확히 일치.
- 해석이 직관적: "얼마나 빨리 툭 올라오는가".
- envelope만으로 구현 가능 (librosa에는 10%–90% 직접 함수는 없어, envelope 후 보간으로 구간 찾기).
- **단점**
- envelope 추출 시 hop/윈도우 길이 선택에 따라 값이 달라짐.
- 매우 짧은 타격은 샘플/프레임 해상도 한계로 상한이 있음.

### C: Phase deviation / Transientness (HPSS 기반)

- **방식**: **HPSS**(`librosa.effects.hpss` 또는 `librosa.decompose.hpss`)로 하모닉/퍼커시브 분리 후, 이벤트 윈도우에서 **퍼커시브 성분 비율**이 높을수록 명확한 온셋으로 점수화.
- **장점**
- 이론적으로 "퍼커시브 = 타격성"과 잘 맞음.
- 잔향/하모닉이 많은 소스에서도 타격 성분만 골라 낼 수 있음.
- **단점**
- 연산 비용이 큼 (전체 오디오 HPSS).
- `margin`, `kernel_size` 등 파라미터 튜닝 필요.
- 문서에 "고급"으로 표시되어 있고, 구현·검증 부담이 가장 큼.

---

## 선택 제안

- **우선 구현 권장: B (Attack time / Rise time)**  
- 문서 스펙과 일치하고, 설명이 쉽으며, 01_energy와 독립적인 지표로 쓰기 좋음.  
- 구현 시 envelope는 `hop_length`를 작게(또는 샘플 단위) 잡아 이벤트 근처만 잘라서 계산하면 해상도·일관성 확보에 유리.

- **대안으로 A (Spectral Flux)**  
- 이미 있는 `onset_env`/`onset_frames`만 활용해 "peak salience + 피크 폭"으로 clarity를 만들고 싶다면 A가 적합.  
- 에너지(01_energy)와 다른 각도(피크 대비 대비·급격함)로 해석하면 중복을 줄일 수 있음.

- **C (HPSS)**  
- 첫 단계에서는 제외하고, B(또는 A)로 파이프라인을 맞춘 뒤, "고급 실험"으로 나중에 추가하는 것을 권장.

**정리**: 사용자가 B와 A 중 하나를 선택하면, 그에 맞춰 아래 구현 단계를 적용한다. 선택이 없으면 **B 기준**으로 계획을 세움.

---

## 구현 단계 (B: Attack time 기준)

1. **노트북 파일**  

- `02_clarity.ipynb` 생성 (또는 `02_onset_clarity.ipynb`).  
- 위치: [audio_engine/notebooks/02_layered_onset_export/](audio_engine/notebooks/02_layered_onset_export/).

2. **공통 부분 (01_energy와 동일)**  

- 프로젝트 루트/경로, `librosa`, `numpy`, `matplotlib` import 및 한글 폰트.  
- `audio_path` 로드 → `y`, `sr`.  
- `hop_length=256`, `onset_env`, `onset_frames`, `onset_times`, `strengths`, BPM·`half_win_frames` 계산 (또는 01_energy와 동일한 식으로 재계산).  
- 이벤트 윈도우: onset 프레임 ± `half_win_frames` (또는 attack 측정용으로 약간 더 넓은 윈도우, 예: ±50–80 ms).

3. **Attack time 계산 (B 선택 시)**  

- 각 `onset_frames[i]`에 대해 해당 구간의 **amplitude envelope** 계산 (예: `np.abs(y)`의 프레임별 max 또는 RMS, hop은 작게).  
- 윈도우 내 peak amplitude 기준으로 **10%·90% 레벨** 정의.  
- 시간 축에서 10% 도달 시점과 90% 도달 시점을 보간으로 찾아 **attack_time = t_90 - t_10**.  
- 상한/하한 처리: 너무 짧으면 해상도 한계로 클리핑, 너무 길면(어택 없음) NaN 또는 상한값으로 대체.

4. **점수화**  

- 문서: `Clarity = peak_salience * (1 / attack_time)` (정규화 포함).  
- B만 쓰는 경우: `peak_salience`는 해당 이벤트의 `onset_env[onset_frames[i]]` 또는 envelope peak로 통일.  
- 곡 전체에서 **robust 정규화**(예: 01_energy의 `robust_norm`처럼 percentile 기반) 적용해 `clarity_score` (0~1) 생성.

5. **시각화**  

- 이벤트별 `attack_time`(ms), `clarity_score` 분포.  
- 필요 시 `onset_times` vs `clarity_score` 또는 phase(박자 내 위치) vs clarity.

6. **내보내기**  

- 01_energy와 동일한 형식으로 JSON export (이벤트 인덱스, `time`, `frame`, `attack_time_ms`, `clarity_score` 등).  
- 파일명 예: `onset_events_clarity.json`, 웹용이면 `web/public/` 복사.

7. **주의점 반영**  

- layering.md: "잔향이 큰 소스는 어택가 뭉개질 수 있음 → 5번 Context Dependency와 같이 봐야 함."  
- 노트북에 짧은 주의 문구만 넣고, 실제 Context Dependency 구현은 별도 노트북으로 둠.

---

## A (Spectral Flux) 선택 시 변경점

- **3번**을 다음으로 교체:  
- 이벤트 근방 `onset_env` 슬라이스에서 **피크 값 / 주변 평균(peak-to-mean)** 및 **피크 폭**(예: half-max width) 또는 **상승 시간**(피크 직전 구간 기울기) 계산.  
- `peak_salience = peak_to_mean`, `attack_time ∝ peak_width` 또는 `1/rise_slope` 형태로 두고, 동일한 `Clarity = peak_salience * (1 / attack_time)` 식 사용.
- **4–6번**은 동일: 정규화 → `clarity_score`, 시각화, JSON export.

---

## 의존성

- 현재 [requirements.txt](requirements.txt): `librosa`, `numpy`, `matplotlib` 등으로 B 또는 A 구현 가능.  
- C(HPSS)는 `librosa.effects.hpss` / `librosa.decompose.hpss`로 가능하며 추가 패키지 없음.

---

## 요약

| 항목 | 내용 |
|------|------|
| **제안** | **B (Attack time)** 우선 구현, 대안 **A (Spectral Flux)** |
| **산출물** | `02_clarity.ipynb` (또는 `02_onset_clarity.ipynb`) + `onset_events_clarity.json` |
| **재사용** | 01_energy와 동일한 오디오·onset 파이프라인, 동일 export/시각화 스타일 |

사용자가 **A / B / C** 중 어떤 방식으로 구현할지 선택하면, 그에 맞춰 위 단계만 적용하여 구현하면 됨.