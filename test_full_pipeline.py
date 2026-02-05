"""
Quick end-to-end test with reduced complexity
"""

import json
import time
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from tracker_framework.core.state import StateType
from tracker_framework.models.motion_models import ConstantVelocityModel
from tracker_framework.models.measurement_models import RadarMeasurementModel
from tracker_framework.filters.multi_target_tracker import MultiTargetTracker
from tracker_framework.simulation.radar_simulator import RadarSimulator, create_standard_scenarios
from tracker_framework.metrics.performance_metrics import PerformanceEvaluator
from tracker_framework.visualization.plots import TrackingVisualizer


def run_quick_test():
    """Run a quick test with minimal configuration."""
    print("="*60)
    print("Quick Test: X, Y, Z vs Time Plots")
    print("="*60)
    
    # Create output directory
    output_path = Path('output')
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Minimal configuration
    print("\nConfiguration:")
    print("  Particles: 100 (reduced for speed)")
    print("  Duration: 5 seconds")
    print("  Scan rate: 5 Hz")
    
    # Initialize models
    motion_model = ConstantVelocityModel(process_noise_std=1.0)
    measurement_model = RadarMeasurementModel(
        range_std=4.0,
        azimuth_std_deg=0.3,
        elevation_std_deg=0.3
    )
    
    # Initialize tracker with fewer particles
    tracker = MultiTargetTracker(
        motion_model=motion_model,
        measurement_model=measurement_model,
        num_particles=100,  # Reduced from 1000
        gating_threshold=9.21,
        state_type=StateType.CV
    )
    
    # Initialize simulator
    simulator = RadarSimulator(
        measurement_model=measurement_model,
        detection_probability=0.95,
        clutter_density=1e-6
    )
    
    # Load simple scenario
    scenarios = create_standard_scenarios()
    trajectories, description = scenarios['single_straight']
    
    print(f"\nScenario: {description}")
    
    # Generate synthetic data (short duration)
    print("\nGenerating data...")
    scan_period = 0.2  # 5 Hz
    
    ground_truth_history, measurement_history = simulator.simulate_scenario(
        trajectories, scan_period
    )
    
    num_scans = len(measurement_history)
    print(f"  Generated {num_scans} scans")
    
    # Run tracking
    print("\nRunning particle filter...")
    estimate_history = []
    evaluator = PerformanceEvaluator()
    
    for scan_idx in range(num_scans):
        timestamp = scan_idx * scan_period
        measurements = measurement_history[scan_idx]
        ground_truth = ground_truth_history[scan_idx]
        
        # Track
        start_time = time.time()
        tracker.update(measurements, timestamp)
        processing_time = time.time() - start_time
        
        # Get estimates
        estimates = tracker.get_track_states()
        estimate_history.append(estimates)
        
        # Evaluate
        evaluator.evaluate_frame(ground_truth, estimates, processing_time)
        
        print(f"  Scan {scan_idx+1}/{num_scans}: {len(estimates)} tracks, "
              f"{len(measurements)} measurements, {processing_time*1000:.1f}ms")
    
    # Compute metrics
    print("\nComputing metrics...")
    metrics = evaluator.compute_overall_metrics()
    
    print(f"\nPerformance:")
    print(f"  Position RMSE: {metrics.position_rmse:.2f} m")
    print(f"  Velocity RMSE: {metrics.velocity_rmse:.2f} m/s")
    print(f"  Avg Processing Time: {metrics.avg_processing_time*1000:.2f} ms")
    
    # Generate visualizations
    print("\nGenerating plots...")
    visualizer = TrackingVisualizer()
    
    timestamps = [i * scan_period for i in range(len(ground_truth_history))]
    
    # X, Y, Z vs Time plot (NEW FEATURE)
    print("  Generating X, Y, Z vs time plot...")
    fig = visualizer.plot_coordinates_vs_time(
        ground_truth_history,
        estimate_history,
        measurement_history,
        timestamps,
        save_path=output_path / "test_coordinates_vs_time.png"
    )
    print("  ✓ Saved: test_coordinates_vs_time.png")
    
    # Verify the file was created
    plot_file = output_path / "test_coordinates_vs_time.png"
    if plot_file.exists():
        print(f"\n✓ SUCCESS: Plot created ({plot_file.stat().st_size} bytes)")
        return True
    else:
        print("\n✗ ERROR: Plot file not created!")
        return False


if __name__ == '__main__':
    success = run_quick_test()
    print("\n" + "="*60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Tests failed!")
    print("="*60 + "\n")
    sys.exit(0 if success else 1)
