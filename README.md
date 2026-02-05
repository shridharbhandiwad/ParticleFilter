# Particle Filter Drone Tracking Framework

A production-ready particle filter implementation for radar-based drone tracking in dense clutter environments. Designed for defense radar signal processing, multi-target tracking, and algorithm research.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🎯 Overview

This framework provides a complete solution for tracking maneuvering drones using radar measurements with:

- **Particle Filter Implementation**: Sequential Importance Resampling (SIR) with multiple resampling strategies
- **Multi-Target Tracking**: Automatic track initiation, maintenance, and termination with data association
- **Motion Models**: Constant Velocity (CV), Constant Acceleration (CA), Coordinated Turn (CT)
- **Realistic Simulation**: Radar measurements with noise, clutter, false alarms, and missed detections
- **Interactive GUI**: Real-time parameter tuning and visualization
- **Performance Metrics**: RMSE, OSPA, track quality, computational efficiency
- **Parameter Study Tools**: Automated batch testing for optimization

---

## 🚀 Features

### Core Tracking Capabilities

- ✅ **Particle Filter Algorithm**
  - Sequential Importance Resampling (SIR)
  - Multiple resampling strategies: Systematic, Stratified, Residual, Multinomial
  - Adaptive particle count
  - Degeneracy detection and mitigation
  - Track quality assessment

- ✅ **Multi-Target Tracking**
  - Automatic track initiation and termination
  - Global Nearest Neighbor (GNN) data association
  - Measurement gating
  - Track confirmation logic
  - Clutter rejection

- ✅ **Motion Models**
  - Constant Velocity (CV): 6D state [x, y, z, vx, vy, vz]
  - Constant Acceleration (CA): 9D state with accelerations
  - Coordinated Turn (CT): 7D state with turn rate
  - Configurable process noise

- ✅ **Measurement Model**
  - Radar spherical coordinates (range, azimuth, elevation, range rate)
  - Realistic measurement noise (range: 3-5m, angles: <0.3°)
  - Likelihood computation
  - Innovation analysis

### Simulation Environment

- ✅ **Realistic Radar Simulator**
  - Multiple drone trajectory patterns: straight, zigzag, circular, aggressive, hover+burst
  - Configurable measurement noise
  - Clutter generation (spatial false alarms)
  - Missed detection probability
  - Weather/cloud disturbance
  - Multi-target scenarios
  - Track crossing scenarios

- ✅ **Standard Test Scenarios**
  - Single target (straight, zigzag, circular, aggressive, hover+burst)
  - Two targets (parallel, crossing)
  - Multi-target complex scenarios

### Visualization & Analysis

- ✅ **Comprehensive Plotting**
  - 2D/3D trajectory visualization
  - Particle cloud visualization
  - Ground truth vs estimates
  - Error plots (position, velocity)
  - RMSE summary with histograms
  - Innovation sequence plots
  - Particle metrics (ESS, weight entropy)

- ✅ **Performance Metrics**
  - Position/Velocity RMSE
  - Track continuity and purity
  - True positive / False positive rates
  - OSPA (Optimal Subpattern Assignment) metric
  - Processing latency
  - Track fragmentation

### User Interface

- ✅ **Interactive GUI** (PyQt5) - **NEWLY ENHANCED!**
  - **Visual Status Indicators**: Color-coded simulation state (Ready/Running/Stopped/Completed)
  - **Progress Tracking**: Real-time progress bar and step counter
  - **Particle Filter Status**: Live monitoring of particle count, active tracks, and effective sample size
  - **Intuitive Controls**: Large styled buttons with helpful tooltips on every parameter
  - **Quick Start Guide**: Built-in instructions for new users
  - **Enhanced Visualization**: Real-time particle cloud display showing filter uncertainty
  - **Smart Logging**: Informative status messages with reduced clutter
  - Real-time parameter adjustment
  - Scenario selection
  - Configuration save/load
  - Performance metrics display

---

## 📋 Requirements

### Core Dependencies
```
numpy >= 1.20.0
scipy >= 1.7.0
matplotlib >= 3.4.0
pandas >= 1.3.0
```

### GUI (Optional)
```
PyQt5 >= 5.15.0
```

---

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd workspace
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install numpy scipy matplotlib pandas

# Optional: For GUI
pip install PyQt5
```

---

## 🎮 Quick Start

### Launch Interactive GUI (Recommended for First-Time Users)
```bash
python main.py --mode gui
```

**New User-Friendly Features:**
- Clear "Ready to Start" status indicator
- Built-in Quick Start instructions in the interface
- Tooltips on all controls explaining what each parameter does
- Real-time particle filter status showing if the simulation is running
- Progress bar tracking simulation completion
- Particle cloud visualization showing filter confidence

**How to Use:**
1. Launch the GUI
2. (Optional) Select a scenario from the "Scenario" tab
3. Click the large green "▶ Start Simulation" button
4. Watch the particle filter track targets in real-time!
5. Monitor the "Particle Filter Status" panel to see the filter working

### Run Single Simulation
```bash
python main.py --mode sim --scenario single_straight --config tracker_framework/configs/default_config.json
```

### List Available Scenarios
```bash
python main.py --list-scenarios
```

### Run Parameter Study
```bash
python main.py --mode batch --study-config tracker_framework/configs/parameter_study_example.json
```

---

## 📁 Project Structure

```
workspace/
├── UI_IMPROVEMENTS_SUMMARY.md   # Detailed documentation of new UI features
├── tracker_framework/           # Main framework package
│   ├── core/                   # Core data structures
│   │   ├── state.py           # State and Measurement classes
│   │   └── __init__.py
│   ├── models/                 # Motion and measurement models
│   │   ├── motion_models.py   # CV, CA, CT motion models
│   │   ├── measurement_models.py  # Radar measurement model
│   │   └── __init__.py
│   ├── filters/                # Filtering algorithms
│   │   ├── particle_filter.py # Particle filter implementation
│   │   ├── multi_target_tracker.py  # Multi-target tracker
│   │   └── __init__.py
│   ├── simulation/             # Data generation
│   │   ├── radar_simulator.py # Radar data simulator
│   │   └── __init__.py
│   ├── metrics/                # Performance evaluation
│   │   ├── performance_metrics.py  # Metrics computation
│   │   └── __init__.py
│   ├── visualization/          # Plotting tools
│   │   ├── plots.py           # Visualization functions
│   │   └── __init__.py
│   ├── gui/                    # Graphical interface
│   │   ├── main_window.py     # PyQt5 GUI
│   │   └── __init__.py
│   ├── configs/                # Configuration files
│   │   ├── default_config.json
│   │   ├── high_clutter_config.json
│   │   └── maneuvering_target_config.json
│   └── __init__.py
├── examples/                    # Example scripts
│   ├── run_simulation.py       # Single simulation runner
│   ├── parameter_study.py      # Batch parameter sweep
│   └── __init__.py
├── main.py                      # Main entry point
└── README.md                    # This file
```

---

## 🔧 Configuration

### Configuration File Format

Configurations are stored in JSON format. Example:

```json
{
    "tracker": {
        "num_particles": 1000,
        "resampling_strategy": "systematic",
        "resampling_threshold": 0.5,
        "gating_threshold": 9.21,
        "state_type": "CV"
    },
    "motion_model": {
        "type": "CV",
        "cv_process_noise_std": 1.0
    },
    "measurement_model": {
        "range_std": 4.0,
        "azimuth_std_deg": 0.3,
        "elevation_std_deg": 0.3
    },
    "radar": {
        "detection_probability": 0.95,
        "clutter_density": 1e-6,
        "scan_rate_hz": 10
    }
}
```

### Key Parameters

**Particle Filter**
- `num_particles`: Number of particles (100-5000, default: 1000)
- `resampling_strategy`: "systematic", "stratified", "residual", "multinomial"
- `resampling_threshold`: ESS threshold for resampling (0.1-1.0, default: 0.5)
- `gating_threshold`: Chi-squared gating threshold (default: 9.21 for 95% confidence)

**Motion Model**
- `type`: "CV", "CA", or "CT"
- `process_noise_std`: Process noise standard deviation [m/s²]

**Radar**
- `range_std`: Range accuracy [meters] (3-5 typical)
- `azimuth_std_deg`: Azimuth accuracy [degrees] (<0.3 typical)
- `elevation_std_deg`: Elevation accuracy [degrees] (<0.3 typical)
- `detection_probability`: Pd (0.8-0.98)
- `clutter_density`: Spatial clutter density [detections/m³]

---

## 📊 Available Scenarios

| Scenario | Description | Duration | Difficulty |
|----------|-------------|----------|------------|
| `single_straight` | Single drone, straight trajectory | 30s | Easy |
| `single_zigzag` | Single drone, zigzag maneuvers | 40s | Medium |
| `single_circular` | Single drone, circular trajectory | 35s | Medium |
| `single_aggressive` | Single drone, aggressive maneuvers | 25s | Hard |
| `hover_burst` | Hover with burst movements | 30s | Hard |
| `two_parallel` | Two drones, parallel trajectories | 30s | Medium |
| `crossing` | Two drones, crossing trajectories | 30s | Hard |
| `multi_complex` | Three drones, mixed trajectories | 35s | Very Hard |

---

## 📈 Performance Metrics

The framework computes comprehensive performance metrics:

### Position and Velocity
- **Position RMSE**: Root Mean Square Error in 3D position [meters]
- **Velocity RMSE**: Root Mean Square Error in velocity [m/s]

### Track Quality
- **Track Continuity**: Ratio of successful associations (1.0 = perfect)
- **Track Purity**: Ratio of true to total tracks (1.0 = no false tracks)
- **True Positive Rate**: Detection rate
- **False Positive Rate**: False alarm rate

### Advanced Metrics
- **OSPA Distance**: Optimal Subpattern Assignment metric (handles localization + cardinality errors)
- **Track Fragmentation**: Number of track breaks
- **Processing Time**: Computational latency per frame

---

## 🧪 Example Usage

### Python API

```python
from tracker_framework.core.state import StateType
from tracker_framework.models.motion_models import ConstantVelocityModel
from tracker_framework.models.measurement_models import RadarMeasurementModel
from tracker_framework.filters.multi_target_tracker import MultiTargetTracker
from tracker_framework.simulation.radar_simulator import RadarSimulator, create_standard_scenarios

# Initialize models
motion_model = ConstantVelocityModel(process_noise_std=1.0)
measurement_model = RadarMeasurementModel(
    range_std=4.0, 
    azimuth_std_deg=0.3, 
    elevation_std_deg=0.3
)

# Create tracker
tracker = MultiTargetTracker(
    motion_model=motion_model,
    measurement_model=measurement_model,
    num_particles=1000,
    state_type=StateType.CV
)

# Load scenario
scenarios = create_standard_scenarios()
trajectories, _ = scenarios['single_straight']

# Generate data
simulator = RadarSimulator(measurement_model=measurement_model)
ground_truth, measurements = simulator.simulate_scenario(trajectories, scan_period=0.1)

# Run tracking
for timestamp, meas_list in enumerate(measurements):
    tracker.update(meas_list, timestamp * 0.1)
    estimates = tracker.get_track_states()
    print(f"Time: {timestamp*0.1:.1f}s, Tracks: {len(estimates)}")
```

---

## 🎓 Algorithm Details

### Particle Filter (SIR)

**Prediction Step**:
```
x_k|k-1 = f(x_k-1|k-1, w_k)
```
Propagate particles using motion model with process noise.

**Update Step**:
```
w_k = w_k-1 * p(z_k | x_k)
w_k = w_k / sum(w_k)  # Normalize
```
Compute likelihood for each particle and update weights.

**Resampling**:
```
if ESS < N * threshold:
    resample()
```
Resample when effective sample size drops below threshold.

**Estimation**:
```
x̂_k = Σ w_k * x_k
```
Weighted mean of particles.

### Motion Models

**Constant Velocity (CV)**:
```
x_k = x_k-1 + vx * dt
vx_k = vx_k-1 + noise
```

**Constant Acceleration (CA)**:
```
x_k = x_k-1 + vx*dt + 0.5*ax*dt²
vx_k = vx_k-1 + ax*dt
ax_k = ax_k-1 + noise
```

**Coordinated Turn (CT)**:
```
x_k = x_k-1 + (vx/ω)*sin(ω*dt) - (vy/ω)*(1-cos(ω*dt))
vx_k = vx*cos(ω*dt) - vy*sin(ω*dt)
ω_k = ω_k-1 + noise
```

### Measurement Model

**Spherical to Cartesian**:
```
x = r * cos(el) * cos(az)
y = r * cos(el) * sin(az)
z = r * sin(el)
```

**Likelihood**:
```
p(z|x) = exp(-0.5 * (z - h(x))ᵀ R⁻¹ (z - h(x)))
```
where R is measurement noise covariance.

---

## 🔍 Parameter Tuning Guidelines

### Number of Particles
- **Low (100-500)**: Fast but lower accuracy
- **Medium (1000-2000)**: Good balance (recommended)
- **High (3000-5000)**: Best accuracy but slower

### Process Noise
- **Too Low**: Filter is too confident, poor maneuver tracking
- **Too High**: Filter is uncertain, noisy estimates
- **Guideline**: Start with 1.0 m/s² for CV, 2.0 m/s² for CA

### Gating Threshold
- **Chi-squared values**: 7.81 (95%, 3 DOF), 9.21 (95%, 4 DOF), 13.28 (99%, 4 DOF)
- **High clutter**: Increase threshold (10-15)
- **Low clutter**: Use standard threshold (9.21)

### Resampling Threshold
- **0.3-0.5**: Aggressive resampling (better for maneuvers)
- **0.5-0.7**: Moderate resampling (general purpose)
- **0.7-0.9**: Conservative resampling (smooth tracking)

---

## 🚀 Performance Optimization

### Computational Efficiency

**Current Performance** (on typical hardware):
- Processing time: 5-20 ms per frame (1000 particles)
- Scalable to 10+ targets
- Real-time capable at 10 Hz

**Optimization Suggestions**:

1. **Reduce Particles**: Use adaptive particle count
2. **Efficient Resampling**: Use systematic resampling (O(N))
3. **Vectorization**: Leverage NumPy operations
4. **Parallel Processing**: Multi-threading for multiple tracks
5. **GPU Acceleration**: CUDA/OpenCL for particle propagation (future)

### C++ Porting

The framework is designed for easy C++ porting:
- Modular class structure
- Clear interfaces
- Minimal Python-specific features
- Well-documented algorithms

---

## 📚 Future Extensions

### Planned Features

- [ ] **Interacting Multiple Model (IMM)**: Automatic motion model switching
- [ ] **Joint Probabilistic Data Association (JPDA)**: Better data association
- [ ] **Probability Hypothesis Density (PHD)**: Unknown number of targets
- [ ] **Multi-sensor Fusion**: Combine multiple radar sources
- [ ] **GPU Acceleration**: CUDA implementation for particle operations
- [ ] **Real-time Data Interface**: Connect to actual radar hardware
- [ ] **Machine Learning Integration**: Learned motion models
- [ ] **Advanced Clutter Models**: Non-uniform spatial distributions

### Research Applications

- Algorithm comparison studies
- Parameter sensitivity analysis
- Motion model performance evaluation
- Sensor fusion experiments
- Real-world radar data validation

---

## 🤝 Contributing

Contributions are welcome! This is a research framework designed for:
- Algorithm experimentation
- Performance benchmarking
- Educational purposes
- Operational prototyping

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👤 Author

Drone Tracking Algorithm Lab

---

## 📞 Support

For questions, issues, or feature requests, please open an issue on the repository.

---

## 🙏 Acknowledgments

This framework implements standard particle filtering and multi-target tracking algorithms from the literature, adapted for defense radar drone tracking applications.

### References

1. Arulampalam, M. S., et al. (2002). "A tutorial on particle filters for online nonlinear/non-Gaussian Bayesian tracking." IEEE Transactions on Signal Processing.

2. Bar-Shalom, Y., & Li, X. R. (1995). "Multitarget-multisensor tracking: Principles and techniques."

3. Schuhmacher, D., et al. (2008). "A consistent metric for performance evaluation of multi-object filters." IEEE Transactions on Signal Processing.

---

**Built for production-ready research and operational deployment.**
