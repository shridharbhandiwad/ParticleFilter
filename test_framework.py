#!/usr/bin/env python3
"""
Quick test script to verify framework functionality.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("Testing Particle Filter Drone Tracking Framework...")
print("=" * 60)

# Test 1: Import core modules
print("\n[1/8] Testing core imports...")
try:
    from tracker_framework.core.state import State, Measurement, StateType
    from tracker_framework.models.motion_models import (
        ConstantVelocityModel, ConstantAccelerationModel, CoordinatedTurnModel
    )
    from tracker_framework.models.measurement_models import RadarMeasurementModel, ClutterModel
    from tracker_framework.filters.particle_filter import ParticleFilter, ResamplingStrategy
    from tracker_framework.filters.multi_target_tracker import MultiTargetTracker
    from tracker_framework.simulation.radar_simulator import RadarSimulator, create_standard_scenarios
    from tracker_framework.metrics.performance_metrics import PerformanceEvaluator
    from tracker_framework.visualization.plots import TrackingVisualizer
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Create state and measurement
print("\n[2/8] Testing state and measurement creation...")
try:
    state = State(
        vector=np.array([1000.0, 500.0, 400.0, 30.0, 0.0, 0.0]),
        state_type=StateType.CV,
        timestamp=0.0
    )
    print(f"✓ State created: {state}")
    
    measurement = Measurement(
        range=1200.0,
        azimuth=np.radians(30.0),
        elevation=np.radians(20.0),
        timestamp=0.0
    )
    print(f"✓ Measurement created: {measurement}")
    cart = measurement.to_cartesian()
    print(f"  Cartesian: [{cart[0]:.1f}, {cart[1]:.1f}, {cart[2]:.1f}]")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 3: Motion models
print("\n[3/8] Testing motion models...")
try:
    cv_model = ConstantVelocityModel(process_noise_std=1.0)
    ca_model = ConstantAccelerationModel(process_noise_std=2.0)
    ct_model = CoordinatedTurnModel(process_noise_std=1.0)
    
    # Test propagation
    new_state = cv_model.propagate(state, dt=0.1, process_noise=False)
    print(f"✓ CV model propagation: position change = "
          f"{np.linalg.norm(new_state.position - state.position):.2f}m")
    
    print("✓ All motion models working")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 4: Measurement model
print("\n[4/8] Testing measurement model...")
try:
    meas_model = RadarMeasurementModel(
        range_std=4.0,
        azimuth_std_deg=0.3,
        elevation_std_deg=0.3
    )
    
    predicted_meas = meas_model.predict_measurement(state, add_noise=False)
    print(f"✓ Predicted measurement: r={predicted_meas.range:.1f}m, "
          f"az={np.degrees(predicted_meas.azimuth):.1f}°")
    
    likelihood = meas_model.compute_likelihood(measurement, state)
    print(f"✓ Likelihood computed: {likelihood:.6f}")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 5: Particle filter
print("\n[5/8] Testing particle filter...")
try:
    pf = ParticleFilter(
        num_particles=500,
        motion_model=cv_model,
        measurement_model=meas_model,
        resampling_strategy=ResamplingStrategy.SYSTEMATIC,
        state_type=StateType.CV
    )
    
    pf.initialize(state)
    print(f"✓ Particle filter initialized with {pf.num_particles} particles")
    
    pf.predict(dt=0.1)
    print(f"✓ Prediction step completed")
    
    pf.update(measurement)
    print(f"✓ Update step completed, ESS = {pf.effective_sample_size:.0f}")
    
    pf.resample()
    estimate = pf.estimate()
    print(f"✓ Resampling and estimation completed")
    print(f"  Estimated position: [{estimate.position[0]:.1f}, {estimate.position[1]:.1f}, {estimate.position[2]:.1f}]")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 6: Multi-target tracker
print("\n[6/8] Testing multi-target tracker...")
try:
    tracker = MultiTargetTracker(
        motion_model=cv_model,
        measurement_model=meas_model,
        num_particles=500,
        state_type=StateType.CV
    )
    
    # Simulate a few measurements
    measurements = [
        Measurement(1000.0, np.radians(0), np.radians(20), timestamp=0.0),
        Measurement(1500.0, np.radians(45), np.radians(15), timestamp=0.0)
    ]
    
    tracker.update(measurements, 0.0)
    stats = tracker.get_statistics()
    print(f"✓ Tracker initialized: {stats['total_tracks']} tracks")
    
    # Update again
    tracker.update(measurements, 0.1)
    stats = tracker.get_statistics()
    print(f"✓ Tracker updated: {stats['confirmed_tracks']} confirmed tracks")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 7: Simulation
print("\n[7/8] Testing radar simulator...")
try:
    simulator = RadarSimulator(
        measurement_model=meas_model,
        detection_probability=0.95,
        clutter_density=1e-6
    )
    
    scenarios = create_standard_scenarios()
    print(f"✓ Created {len(scenarios)} standard scenarios")
    
    # Test one scenario
    trajectories, description = scenarios['single_straight']
    print(f"✓ Testing scenario: {description}")
    
    gt_history, meas_history = simulator.simulate_scenario(trajectories, scan_period=0.1)
    print(f"✓ Simulation complete: {len(gt_history)} scans, "
          f"avg {np.mean([len(m) for m in meas_history]):.1f} measurements/scan")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 8: Metrics
print("\n[8/8] Testing performance metrics...")
try:
    evaluator = PerformanceEvaluator()
    
    # Create dummy data
    gt_states = [State(np.array([1000, 0, 500, 30, 0, 0]), StateType.CV, 0.0)]
    est_states = [State(np.array([1005, 2, 498, 29, 1, 0]), StateType.CV, 0.0)]
    
    frame_metrics = evaluator.evaluate_frame(gt_states, est_states, processing_time=0.01)
    print(f"✓ Frame evaluation: pos_error={frame_metrics['avg_position_error']:.2f}m")
    
    overall_metrics = evaluator.compute_overall_metrics()
    print(f"✓ Overall metrics computed: RMSE={overall_metrics.position_rmse:.2f}m")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All tests passed! Framework is working correctly.")
print("=" * 60)
