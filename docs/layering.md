
## 0) 전제: 단위는 “이벤트(타격)”

먼저 onset detection으로 타격 이벤트를 잡고(시간 `t_i`), 각 이벤트마다 아래 지표를 계산해 점수화합니다.
이벤트 단위로 하면 “타격 포인트”와 직결됩니다.

---

## 1) Energy (타격 에너지)

### 측정 제안

* **이벤트 윈도우 에너지**: `E = RMS` 또는 `log-energy`

  * `t_i` 기준 ±(예: 10–50ms) 구간 RMS 계산
* **대역별 에너지**(권장): 킥/스네어/햇 분리용

  * Low(예: 20–150Hz), Mid(150–2k), High(2k–10k) 대역 에너지
  * STFT 또는 필터뱅크로 계산

### 점수화

* 곡 전체 에너지 분포 대비 **퍼센타일(rank)** 로 정규화

  * `E_norm = percentile(E)`
    → 믹스 크기/마스터링 차이 덜 탐.

### 주의점

* 브러쉬는 에너지가 낮아도 중요한 경우가 많음 → Energy는 **단독 결정 변수로 쓰지 말고** 다른 지표와 결합.

---

## 2) Onset Clarity (어택 명확도)

“타격이 또렷하게 ‘툭’ 하고 박히는지”를 수치로 만듭니다.

### 측정 제안 A: Spectral Flux 기반

* `flux(t)` = 프레임 간 스펙트럼 변화량
* 이벤트 `t_i` 근방에서

  * **피크 높이 / 주변 평균**(peak-to-mean)
  * **피크의 급격함**(피크 폭, 상승 시간)
    을 사용

### 측정 제안 B: Attack time / Rise time

* amplitude envelope에서

  * `10% → 90%` 도달 시간(Attack time)
  * 짧을수록 명확한 어택

### 측정 제안 C: Phase deviation / Transientness (고급)

* HPSS(하모닉-퍼커시브 분리) 후 퍼커시브 성분 비율이 높을수록 명확한 온셋

### 점수화

* `Clarity = peak_salience * (1 / attack_time)` 형태(정규화 포함)

### 주의점

* 잔향이 큰 소스는 어택이 뭉개질 수 있음. 그래서 5번 Context Dependency와 같이 봐야 함.

---

## 3) Temporal Salience (박자 기여도 / 반복성)

“이 이벤트가 그루브/박자 인식에 얼마나 기여하는가”

### 측정 제안 A: 비트 그리드 정렬도

1. tempo/beat tracking으로 비트 시퀀스 `B = {b_k}` 추정
2. 이벤트 `t_i`가 가장 가까운 비트/서브비트(예: 1/2, 1/4, 1/8, 1/16)에 얼마나 잘 붙는지

   * `distance = min_k |t_i - grid_k|`
   * 작을수록 salience ↑

### 측정 제안 B: 반복성/주기성

* `IOI`(Inter-Onset Interval) 분포에서

  * 특정 간격이 반복되면 salience ↑
* 또는 onset 함수의 autocorrelation에서 강한 주기 성분에 기여하는 이벤트를 높게

### 측정 제안 C: 다운비트 가중치

* 다운비트/강박(1박, 3박 등)에 정렬되면 더 높은 가중치

### 점수화

* `Temporal = grid_align_score * repetition_score * downbeat_weight`

### 주의점

* 스윙/셔플/루바토에서는 그리드 기반이 흔들림 → “가변 그리드(스윙 비율)” 또는 “로컬 템포” 적용 필요.

---

## 4) Spectral Focus (주파수 집중도)

“주파수 에너지가 한 대역에 뭉쳐 또렷한가, 아니면 넓게 퍼져 텍스처인가”

### 측정 제안

이벤트 구간의 스펙트럼에서:

* **Spectral Centroid** (무게중심)
* **Spectral Bandwidth/Spread** (퍼짐 정도)
* **Spectral Flatness** (노이즈성/평탄성)

  * flatness 높음 = 노이즈(브러쉬, 쉐이커, 룸노이즈) 성격

### 직관적 해석

* 킥: centroid 낮고, spread 낮거나 특정 구조
* 스네어: 중고역 존재하지만 transient가 뚜렷
* 브러쉬: flatness 높고 spread 넓음 (노이즈)

### 점수화(예시 방향)

* “포커스”는 spread/flatness가 낮을수록 ↑

  * `Focus = 1 - norm(flatness) - norm(spread)` (적당히 가중)

### 주의점

* 크래시 심벌은 spread 넓지만 메인 악기일 수 있음 → Temporal/Clarity와 함께 판단해야 함.

---

## 5) Context Dependency (맥락 의존성)

“혼자 있을 때만 들리는가? 다른 소리에 묻히는가?”
즉, **마스킹(psychoacoustic masking)** 관점입니다.

### 측정 제안 A: Local SNR / Event-to-Background Ratio

* 이벤트 윈도우 에너지 `E_event`
* 직전/직후 배경 윈도우 에너지 `E_bg`
* `SNR = 10*log10(E_event / E_bg)`

  * 낮을수록 “맥락 의존적”(혼잡하면 안 들림)

### 측정 제안 B: 대역별 마스킹 추정 (권장)

* 이벤트 스펙트럼과 배경 스펙트럼을 대역별로 비교
* 해당 이벤트의 주요 대역에서 배경이 더 크면 마스킹 ↑

### 측정 제안 C: 분리 후 잔차 기반(고급)

* HPSS 또는 source separation(드럼/기타/보컬) 후
* “해당 소스에서만 살아남는 정도”를 의존성 지표로 사용

### 점수화

* `Dependency = 1 - norm(SNR)` (SNR 낮으면 의존성 높음)
* 최종 Precision 레이어에서

  * 의존성이 높을수록 **고정밀(P2) 쪽**으로 이동시키는 가중치

### 주의점

* 믹스가 이미 분리돼 있으면(스텀) Dependency 의미가 달라짐. 원 믹스 기준이 가장 현실적.

---

## 6) (보너스) 안정성 높이려면 추가할 지표 2개

### A. Event Type Confidence (악기/타격 종류 확신도)

* 킥/스네어/햇 분류기(간단한 룰 기반도 가능)
* 분류 확신도가 낮으면 P2로 보내는 전략이 안정적

### B. Micro-variability (미세 변주)

* 동일 패턴 내에서 어택/스펙트럼이 얼마나 달라지는지
* 브러쉬/고스트 노트/사람 연주 뉘앙스에 유리

---

## 7) 최종적으로 Precision을 어떻게 합칠지(실무형)

### 방향성

* **P0(저정밀)**: Energy↑ + Temporal↑ + Clarity↑
* **P1(중정밀)**: Temporal↑ + (Energy 중간) + 패턴성↑
* **P2(고정밀)**: Dependency↑ + Flatness↑(텍스처) + Energy↓(가능) + Type confidence↓

### 간단한 스코어 예시(개념)

* `P0_score = w1*Energy + w2*Temporal + w3*Clarity - w4*Dependency`
* `P2_score = v1*Dependency + v2*Flatness + v3*(1-Clarity) + v4*(1-Energy)`

그리고 `argmax(P0, P1, P2)`로 레이어 할당.
