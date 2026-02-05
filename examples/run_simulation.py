"""
Example: Run Single Tracking Simulation

Demonstrates complete tracking pipeline:
1. Load configuration
2. Initialize tracker
3. Generate synthetic data
4. Run tracking
5. Evaluate performance
6. Visualize results
"""

import json
import time
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tracker_framework.core.state import StateType
from tracker_framework.models.motion_models import (
    ConstantVelocityModel, ConstantAccelerationModel, CoordinatedTurnModel
)
from tracker_framework.models.measurement_models import RadarMeasurementModel
from tracker_framework.filters.multi_target_tracker import MultiTargetTracker
from tracker_framework.simulation.radar_simulator import RadarSimulator, create_standard_scenarios
from tracker_framework.metrics.performance_metrics import PerformanceEvaluator
from tracker_framework.visualization.plots import TrackingVisualizer


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def create_motion_model(config: dict):
    """Create motion model from configuration."""
    model_type = config['motion_model']['type']
    
    if model_type == 'CV':
        return ConstantVelocityModel(
            process_noise_std=config['motion_model']['cv_process_noise_std']
        )
    elif model_type == 'CA':
        return ConstantAccelerationModel(
            process_noise_std=config['motion_model']['ca_process_noise_std']
        )
    elif model_type == 'CT':
        return CoordinatedTurnModel(
            process_noise_std=config['motion_model']['ct_process_noise_std'],
            turn_rate_noise_std=config['motion_model']['ct_turn_rate_noise_std']
        )
    else:
        raise ValueError(f"Unknown motion model type: {model_type}")


def run_single_simulation(scenario_name: str, config_path: str, 
                         output_dir: str, enable_visualization: bool = True):
    """
    Run single simulation scenario.
    
    Args:
        scenario_name: Scenario name
        config_path: Path to configuration file
        output_dir: Output directory
        enable_visualization: Enable plots
    """
    print(f"\n{'='*60}")
    print(f"Particle Filter Drone Tracking Simulation")
    print(f"{'='*60}\n")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load configuration
    print(f"Loading configuration from {config_path}...")
    config = load_config(config_path)
    
    # Override scenario if specified
    if scenario_name:
        config['simulation']['scenario'] = scenario_name
    
    print(f"Scenario: {config['simulation']['scenario']}")
    print(f"Motion Model: {config['motion_model']['type']}")
    print(f"Number of Particles: {config['tracker']['num_particles']}")
    print(f"Resampling Strategy: {config['tracker']['resampling_strategy']}")
    print()
    
    # Initialize models
    motion_model = create_motion_model(config)
    
    measurement_model = RadarMeasurementModel(
        range_std=config['measurement_model']['range_std'],
        azimuth_std_deg=config['measurement_model']['azimuth_std_deg'],
        elevation_std_deg=config['measurement_model']['elevation_std_deg'],
        range_rate_std=config['measurement_model']['range_rate_std']
    )
    
    # Initialize tracker
    state_type = StateType[config['tracker']['state_type']]
    
    tracker = MultiTargetTracker(
        motion_model=motion_model,
        measurement_model=measurement_model,
        num_particles=config['tracker']['num_particles'],
        gating_threshold=config['tracker']['gating_threshold'],
        confirmation_threshold=config['tracker']['confirmation_threshold'],
        termination_threshold=config['tracker']['termination_threshold'],
        state_type=state_type
    )
    
    # Initialize simulator
    simulator = RadarSimulator(
        measurement_model=measurement_model,
        detection_probability=config['radar']['detection_probability'],
        clutter_density=config['radar']['clutter_density'],
        weather_noise_factor=config['radar']['weather_noise_factor']
    )
    
    # Load scenario
    scenarios = create_standard_scenarios()
    scenario_key = config['simulation']['scenario']
    
    if scenario_key not in scenarios:
        print(f"ERROR: Unknown scenario '{scenario_key}'")
        print(f"Available scenarios: {list(scenarios.keys())}")
        return
    
    trajectories, description = scenarios[scenario_key]
    print(f"Description: {description}\n")
    
    # Generate synthetic data
    print("Generating synthetic radar data...")
    scan_period = 1.0 / config['radar']['scan_rate_hz']
    
    ground_truth_history, measurement_history = simulator.simulate_scenario(
        trajectories, scan_period
    )
    
    num_scans = len(measurement_history)
    print(f"Generated {num_scans} scans ({num_scans * scan_period:.1f} seconds)")
    print(f"Average measurements per scan: "
          f"{np.mean([len(m) for m in measurement_history]):.1f}\n")
    
    # Run tracking
    print("Running particle filter tracking...")
    estimate_history = []
    evaluator = PerformanceEvaluator(
        association_threshold=config['evaluation']['association_threshold']
    )
    
    processing_times = []
    
    for scan_idx in range(num_scans):
        timestamp = scan_idx * scan_period
        measurements = measurement_history[scan_idx]
        ground_truth = ground_truth_history[scan_idx]
        
        # Track
        start_time = time.time()
        tracker.update(measurements, timestamp)
        processing_time = time.time() - start_time
        processing_times.append(processing_time)
        
        # Get estimates
        estimates = tracker.get_track_states()
        estimate_history.append(estimates)
        
        # Evaluate
        evaluator.evaluate_frame(ground_truth, estimates, processing_time)
        
        # Progress
        if (scan_idx + 1) % 50 == 0 or scan_idx == num_scans - 1:
            print(f"  Processed {scan_idx + 1}/{num_scans} scans "
                  f"({(scan_idx + 1) / num_scans * 100:.1f}%)")
    
    print()
    
    # Compute metrics
    print("Computing performance metrics...")
    metrics = evaluator.compute_overall_metrics()
    error_stats = evaluator.get_error_statistics()
    tracker_stats = tracker.get_statistics()
    
    # Print results
    print(f"\n{'='*60}")
    print("Performance Metrics")
    print(f"{'='*60}")
    print(f"\nPosition Tracking:")
    print(f"  RMSE:      {metrics.position_rmse:.2f} m")
    print(f"  Mean:      {error_stats['position']['mean']:.2f} m")
    print(f"  Std Dev:   {error_stats['position']['std']:.2f} m")
    print(f"  Min/Max:   {error_stats['position']['min']:.2f} / {error_stats['position']['max']:.2f} m")
    
    print(f"\nVelocity Tracking:")
    print(f"  RMSE:      {metrics.velocity_rmse:.2f} m/s")
    print(f"  Mean:      {error_stats['velocity']['mean']:.2f} m/s")
    print(f"  Std Dev:   {error_stats['velocity']['std']:.2f} m/s")
    
    print(f"\nTrack Quality:")
    print(f"  Continuity:         {metrics.track_continuity:.3f}")
    print(f"  Purity:             {metrics.track_purity:.3f}")
    print(f"  True Positive Rate: {metrics.true_positive_rate:.3f}")
    print(f"  False Positive Rate:{metrics.false_positive_rate:.3f}")
    print(f"  OSPA Distance:      {metrics.ospa_distance:.2f} m")
    
    print(f"\nComputational Performance:")
    print(f"  Avg Processing Time: {metrics.avg_processing_time*1000:.2f} ms")
    print(f"  Min/Max:            {error_stats['processing_time']['min']*1000:.2f} / "
          f"{error_stats['processing_time']['max']*1000:.2f} ms")
    print(f"  Total Tracks:       {tracker_stats['total_tracks']}")
    print(f"  Confirmed Tracks:   {tracker_stats['confirmed_tracks']}")
    print(f"  Tracks Created:     {tracker_stats['tracks_created']}")
    print(f"  Tracks Terminated:  {tracker_stats['tracks_terminated']}")
    print(f"\n{'='*60}\n")
    
    # Save metrics
    metrics_dict = metrics.to_dict()
    metrics_dict['error_statistics'] = error_stats
    metrics_dict['tracker_statistics'] = tracker_stats
    
    metrics_file = output_path / f"metrics_{scenario_key}.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics_dict, f, indent=4)
    print(f"Metrics saved to {metrics_file}")
    
    # Visualization
    if enable_visualization:
        print("\nGenerating visualizations...")
        visualizer = TrackingVisualizer()
        
        # Organize data by track
        gt_by_track = {}
        est_by_track = {}
        
        for scan_gt in ground_truth_history:
            for i, state in enumerate(scan_gt):
                if i not in gt_by_track:
                    gt_by_track[i] = []
                gt_by_track[i].append(state)
        
        for scan_est in estimate_history:
            for i, state in enumerate(scan_est):
                if i not in est_by_track:
                    est_by_track[i] = []
                est_by_track[i].append(state)
        
        gt_tracks = list(gt_by_track.values())
        est_tracks = list(est_by_track.values())
        
        # 2D trajectories
        fig = visualizer.plot_trajectories_2d(
            gt_tracks, est_tracks, measurement_history, plane='xy',
            save_path=output_path / f"trajectory_xy_{scenario_key}.png"
        )
        print(f"  Saved: trajectory_xy_{scenario_key}.png")
        
        # 3D trajectories
        fig = visualizer.plot_trajectories_3d(
            gt_tracks, est_tracks,
            save_path=output_path / f"trajectory_3d_{scenario_key}.png"
        )
        print(f"  Saved: trajectory_3d_{scenario_key}.png")
        
        # Error plots
        timestamps = [i * scan_period for i in range(len(evaluator.position_errors))]
        fig = visualizer.plot_error_vs_time(
            evaluator.position_errors,
            evaluator.velocity_errors,
            timestamps,
            save_path=output_path / f"errors_{scenario_key}.png"
        )
        print(f"  Saved: errors_{scenario_key}.png")
        
        # RMSE summary
        fig = visualizer.plot_rmse_summary(
            metrics.position_rmse,
            metrics.velocity_rmse,
            evaluator.position_errors,
            evaluator.velocity_errors,
            save_path=output_path / f"rmse_summary_{scenario_key}.png"
        )
        print(f"  Saved: rmse_summary_{scenario_key}.png")
        
        # X, Y, Z vs Time plot
        fig = visualizer.plot_coordinates_vs_time(
            ground_truth_history,
            estimate_history,
            measurement_history,
            timestamps,
            save_path=output_path / f"coordinates_vs_time_{scenario_key}.png"
        )
        print(f"  Saved: coordinates_vs_time_{scenario_key}.png")
        
        print()
    
    print("Simulation complete!\n")


if __name__ == '__main__':
    import sys
    
    scenario = sys.argv[1] if len(sys.argv) > 1 else 'single_straight'
    config_path = sys.argv[2] if len(sys.argv) > 2 else 'tracker_framework/configs/default_config.json'
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'output'
    
    run_single_simulation(scenario, config_path, output_dir)
