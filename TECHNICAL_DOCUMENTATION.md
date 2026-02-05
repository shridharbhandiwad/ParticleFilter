# Technical Documentation

## System Architecture Overview

### Design Philosophy

This particle filter drone tracking framework follows a **modular, production-ready architecture** designed for:

1. **Research Flexibility**: Easy algorithm swapping and parameter tuning
2. **Operational Scalability**: Efficient implementation for real-time tracking
3. **Code Maintainability**: Clear separation of concerns with well-defined interfaces
4. **C++ Portability**: Minimal Python-specific dependencies for future porting

---

## Mathematical Foundation

### 1. State Representation

#### Constant Velocity (CV) Model
```
State vector: x = [x, y, z, vx, vy, vz]^T  (6D)

Dynamics:
  x(k+1) = x(k) + vx*dt
  vx(k+1) = vx(k) + w_vx

Process noise: w ~ N(0, Q_cv)
```

#### Constant Acceleration (CA) Model
```
State vector: x = [x, y, z, vx, vy, vz, ax, ay, az]^T  (9D)

Dynamics:
  x(k+1) = x(k) + vx*dt + 0.5*ax*dt²
  vx(k+1) = vx(k) + ax*dt
  ax(k+1) = ax(k) + w_ax

Process noise: w ~ N(0, Q_ca)
```

#### Coordinated Turn (CT) Model
```
State vector: x = [x, y, z, vx, vy, vz, ω]^T  (7D)

Dynamics (horizontal plane):
  x(k+1) = x(k) + (vx/ω)*sin(ω*dt) - (vy/ω)*(1-cos(ω*dt))
  y(k+1) = y(k) + (vy/ω)*sin(ω*dt) + (vx/ω)*(1-cos(ω*dt))
  z(k+1) = z(k) + vz*dt  (vertical: constant velocity)
  
  vx(k+1) = vx*cos(ω*dt) - vy*sin(ω*dt)
  vy(k+1) = vy*cos(ω*dt) + vx*sin(ω*dt)
  ω(k+1) = ω(k) + w_ω

Process noise: w ~ N(0, Q_ct)
```

### 2. Measurement Model

#### Radar Spherical Coordinates
```
Measurement vector: z = [r, az, el, ṙ]^T

Measurement function h(x):
  r = sqrt(x² + y² + z²)
  az = atan2(y, x)
  el = atan2(z, sqrt(x² + y²))
  ṙ = (x*vx + y*vy + z*vz) / r

Measurement noise: v ~ N(0, R)

R = diag([σ_r², σ_az², σ_el², σ_ṙ²])
where:
  σ_r = 3-5 meters
  σ_az = 0.3 degrees
  σ_el = 0.3 degrees
  σ_ṙ = 1.0 m/s
```

#### Cartesian Conversion
```
x = r * cos(el) * cos(az)
y = r * cos(el) * sin(az)
z = r * sin(el)
```

### 3. Particle Filter Algorithm

#### Sequential Importance Resampling (SIR)

**Initialization (k=0):**
```
For i = 1 to N:
  x⁽ⁱ⁾₀ ~ p(x₀)     # Sample from initial distribution
  w⁽ⁱ⁾₀ = 1/N        # Uniform weights
```

**Prediction Step (k=k+1):**
```
For i = 1 to N:
  x⁽ⁱ⁾ₖ ~ p(xₖ | x⁽ⁱ⁾ₖ₋₁)    # Propagate using motion model
```

**Update Step:**
```
For i = 1 to N:
  w̃⁽ⁱ⁾ₖ = w⁽ⁱ⁾ₖ₋₁ * p(zₖ | x⁽ⁱ⁾ₖ)    # Importance weight

Normalize:
  w⁽ⁱ⁾ₖ = w̃⁽ⁱ⁾ₖ / Σⱼ w̃⁽ʲ⁾ₖ
```

**Resampling:**
```
Compute ESS = 1 / Σᵢ (w⁽ⁱ⁾ₖ)²

If ESS < N_threshold:
  Resample particles according to weights
  Reset weights: w⁽ⁱ⁾ₖ = 1/N
```

**Estimation:**
```
x̂ₖ = Σᵢ w⁽ⁱ⁾ₖ * x⁽ⁱ⁾ₖ    # Weighted mean
```

### 4. Likelihood Function

#### Gaussian Likelihood in Measurement Space
```
p(z | x) = (2π)^(-n/2) |R|^(-1/2) exp(-½ ν^T R^(-1) ν)

where:
  ν = z - h(x)           # Innovation
  R = measurement covariance
  n = measurement dimension
```

#### Mahalanobis Distance
```
d² = ν^T R^(-1) ν

Likelihood:
  L(x) = exp(-½ d²)      # Unnormalized
```

#### Clutter Model (PDAF-inspired)
```
p_total(z | x) = Pd * p_true(z | x) + (1-Pd) * λc * V^(-1)

where:
  Pd = detection probability
  λc = clutter density [returns/m³]
  V = surveillance volume [m³]
```

### 5. Resampling Strategies

#### Systematic Resampling (Recommended)
```
Algorithm:
  u₀ ~ Uniform(0, 1/N)
  For i = 1 to N:
    uᵢ = u₀ + (i-1)/N
    Find j such that Σₖ₌₁ʲ wₖ ≥ uᵢ
    x'⁽ⁱ⁾ = x⁽ʲ⁾

Complexity: O(N)
Variance: Low
```

#### Stratified Resampling
```
Algorithm:
  For i = 1 to N:
    uᵢ ~ Uniform((i-1)/N, i/N)
    Find j such that Σₖ₌₁ʲ wₖ ≥ uᵢ
    x'⁽ⁱ⁾ = x⁽ʲ⁾

Complexity: O(N)
Variance: Low
```

#### Residual Resampling
```
Algorithm:
  # Deterministic replication
  For i = 1 to N:
    Nᵢ = floor(N * wᵢ)
    Replicate x⁽ⁱ⁾ Nᵢ times
  
  # Stochastic residual
  N_residual = N - Σᵢ Nᵢ
  w'ᵢ = (N*wᵢ - Nᵢ) / N_residual
  Resample N_residual particles using w'ᵢ

Complexity: O(N)
Variance: Lowest
```

### 6. Multi-Target Data Association

#### Global Nearest Neighbor (GNN)

**Problem:** Associate M measurements to N tracks

**Cost Matrix:**
```
C[i,j] = -log(p(zⱼ | xᵢ))    # i: track, j: measurement
```

**Gating:**
```
Gate measurement j for track i if:
  (zⱼ - h(xᵢ))^T R^(-1) (zⱼ - h(xᵢ)) < γ

where γ = chi-squared threshold (e.g., 9.21 for 95%, 4 DOF)
```

**Assignment:**
Solve assignment problem to minimize total cost subject to:
- Each measurement assigned to at most one track
- Each track assigned to at most one measurement

**Complexity:** O(N³) for Hungarian algorithm, O(NM log N) for greedy

---

## Performance Metrics

### 1. Position/Velocity RMSE

```
RMSE_pos = sqrt(1/K Σₖ ||x̂ₖ - xₖ||²)
RMSE_vel = sqrt(1/K Σₖ ||v̂ₖ - vₖ||²)
```

### 2. OSPA Metric

Optimal Subpattern Assignment handles both localization and cardinality errors.

```
OSPA(X, Y) = [1/n (min_π Σᵢ d(xᵢ, yπ(i))^p + c^p * |m-n|)]^(1/p)

where:
  X = {x₁, ..., xₘ} = ground truth set
  Y = {y₁, ..., yₙ} = estimate set
  π = permutation
  d(x,y) = min(||x-y||, c)  # Capped distance
  c = cutoff parameter [meters]
  p = order parameter
  
Standard: c=100m, p=2
```

### 3. Track Quality Metrics

**Track Continuity:**
```
TC = TP / (TP + FN)    # Detection rate
where:
  TP = true positives (correct associations)
  FN = false negatives (missed detections)
```

**Track Purity:**
```
TP_purity = TP / (TP + FP)    # Precision
where:
  FP = false positives (false tracks)
```

**Effective Sample Size:**
```
ESS = 1 / Σᵢ (wᵢ)²

Interpretation:
  ESS ≈ N: particles have similar weights (good)
  ESS << N: particle degeneracy (bad, need resampling)
```

---

## Implementation Details

### 1. Process Noise Covariance

#### CV Model (Discrete White Noise Acceleration)
```
Q_cv = σ² * [Q_pos  Q_pv ]
              [Q_pv  Q_vel]

Q_pos = (dt³/3) * I₃
Q_pv = (dt²/2) * I₃
Q_vel = dt * I₃

where σ = process noise std [m/s²]
```

#### CA Model (Discrete White Noise Jerk)
```
Q_ca = σ² * [Q_pos  Q_pv   Q_pa  ]
              [Q_pv   Q_vel  Q_va  ]
              [Q_pa   Q_va   Q_acc ]

Q_pos = (dt⁴/4) * I₃
Q_pv = (dt³/2) * I₃
Q_pa = (dt²/2) * I₃
Q_vel = dt² * I₃
Q_va = dt * I₃
Q_acc = I₃

where σ = process noise std [m/s³]
```

### 2. Numerical Stability

**Log-Space Computations:**
For very small likelihoods, use log-space to prevent underflow:
```
log(w) = log(w_old) + log(p(z|x))
w = exp(log(w) - log_sum_exp(all log weights))
```

**Angle Wrapping:**
```
angle_diff(θ₁, θ₂):
  diff = θ₁ - θ₂
  while diff > π: diff -= 2π
  while diff < -π: diff += 2π
  return diff
```

**Covariance Matrix Regularization:**
```
R_inv = inv(R + ε*I)    # Add small diagonal term
where ε = 1e-6
```

### 3. Computational Complexity

**Per Frame:**
- Prediction: O(N) where N = number of particles
- Update: O(N*M) where M = number of measurements
- Resampling: O(N)
- Estimation: O(N)

**Multi-Target:**
- Data Association: O(T*M) for greedy, O(T³) for optimal
- Total: O(T*N*M) where T = number of tracks

**Memory:**
- O(T*N*D) where D = state dimension

---

## Parameter Tuning Guidelines

### Decision Tree for Parameter Selection

```
START
│
├─ Dense Clutter?
│  ├─ YES → num_particles ≥ 2000
│  │       gating_threshold = 12-15
│  │       clutter_density = 1e-5
│  └─ NO  → num_particles = 1000
│          gating_threshold = 9.21
│          clutter_density = 1e-6
│
├─ Maneuvering Target?
│  ├─ YES → motion_model = CA or CT
│  │       process_noise_std = 2-3 m/s²
│  └─ NO  → motion_model = CV
│          process_noise_std = 1 m/s²
│
├─ Tracking Performance Issue?
│  ├─ High False Tracks → Increase confirmation_threshold
│  │                     Increase gating_threshold
│  ├─ Lost Tracks → Decrease process_noise_std
│  │                Increase termination_threshold
│  └─ Noisy Estimates → Increase num_particles
│                      Increase resampling_threshold
```

### Radar-Specific Tuning

**High SNR Environment (SNR > 15 dB):**
```
range_std = 3.0 m
azimuth_std = 0.2°
detection_probability = 0.98
```

**Low SNR Environment (SNR < 10 dB):**
```
range_std = 5.0 m
azimuth_std = 0.4°
detection_probability = 0.85
```

**Weather Degradation:**
```
weather_noise_factor = 1.5-2.5
detection_probability *= 0.9
```

---

## Code Architecture

### Class Hierarchy

```
State
├─ position: np.ndarray [x, y, z]
├─ velocity: np.ndarray [vx, vy, vz]
├─ acceleration: np.ndarray [ax, ay, az] (CA only)
└─ turn_rate: float (CT only)

Measurement
├─ range: float
├─ azimuth: float (radians)
├─ elevation: float (radians)
├─ range_rate: float (optional)
├─ snr: float (optional)
└─ to_cartesian() → np.ndarray

MotionModel (Abstract)
├─ propagate(state, dt) → state
└─ get_process_noise_covariance(dt) → Q
    ├─ ConstantVelocityModel
    ├─ ConstantAccelerationModel
    └─ CoordinatedTurnModel

RadarMeasurementModel
├─ predict_measurement(state) → measurement
├─ compute_likelihood(measurement, state) → float
├─ gate_measurement(measurement, state) → bool
└─ innovation_vector(measurement, state) → np.ndarray

ParticleFilter
├─ particles: List[State]
├─ weights: np.ndarray
├─ predict(dt)
├─ update(measurement)
├─ resample()
└─ estimate() → State

MultiTargetTracker
├─ tracks: Dict[int, Track]
├─ predict(time)
├─ update(measurements, time)
└─ get_track_states() → List[State]
```

### Data Flow

```
Ground Truth → Radar Simulator → Measurements
                                      ↓
                            Multi-Target Tracker
                                   ↓
                        ┌──────────┴──────────┐
                   Prediction            Update
                        │                   │
                  Motion Model      Measurement Model
                        │                   │
                   Particle Filter   Data Association
                        │                   │
                  Resampling          Track Management
                        └──────────┬──────────┘
                                   ↓
                            State Estimates
                                   ↓
                         Performance Evaluator
                                   ↓
                              Visualization
```

---

## Testing Strategy

### Unit Tests
- State propagation correctness
- Measurement conversion accuracy
- Likelihood computation
- Resampling algorithms
- Data association logic

### Integration Tests
- Single-target tracking scenarios
- Multi-target tracking scenarios
- Clutter rejection
- Track initiation/termination

### Performance Tests
- Computational latency benchmarks
- Memory usage profiling
- Scalability tests (number of particles, targets)

### Validation Tests
- RMSE convergence
- OSPA metric validation
- Comparison with ground truth

---

## Future Enhancements

### Algorithm Improvements
1. **IMM (Interacting Multiple Model):** Adaptive motion model switching
2. **JPDA (Joint Probabilistic Data Association):** Probabilistic multi-target association
3. **PHD Filter:** Unknown number of targets
4. **Rao-Blackwellized Particle Filter:** Exploit linear substructure

### Implementation Optimizations
1. **GPU Acceleration:** CUDA kernel for particle propagation
2. **SIMD Vectorization:** AVX/SSE for likelihood computation
3. **Parallel Processing:** Multi-threading for multiple tracks
4. **C++ Port:** High-performance implementation

### Feature Additions
1. **Sensor Fusion:** Multi-radar, radar+EO/IR
2. **Terrain Constraints:** Ground elevation models
3. **Flight Dynamics:** Physical constraints on maneuvers
4. **Classification:** Drone type identification

---

## References

1. Arulampalam, M. S., et al. (2002). "A tutorial on particle filters for online nonlinear/non-Gaussian Bayesian tracking." *IEEE TSP*.

2. Bar-Shalom, Y., Li, X. R., & Kirubarajan, T. (2001). *Estimation with Applications to Tracking and Navigation*. Wiley.

3. Ristic, B., Arulampalam, S., & Gordon, N. (2004). *Beyond the Kalman Filter: Particle Filters for Tracking Applications*. Artech House.

4. Schuhmacher, D., et al. (2008). "A consistent metric for performance evaluation of multi-object filters." *IEEE TSP*.

5. Doucet, A., & Johansen, A. M. (2009). "A tutorial on particle filtering and smoothing: Fifteen years later." *Handbook of Nonlinear Filtering*.
