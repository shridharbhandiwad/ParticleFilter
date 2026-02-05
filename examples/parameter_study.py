"""
Parameter Study and Sensitivity Analysis

Automated batch testing of different parameter configurations
to find optimal settings for various scenarios.
"""

import json
import itertools
import numpy as np
import pandas as pd
from pathlib import Path
import sys
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from tracker_framework.core.state import StateType
from tracker_framework.models.motion_models import ConstantVelocityModel
from tracker_framework.models.measurement_models import RadarMeasurementModel
from tracker_framework.filters.multi_target_tracker import MultiTargetTracker
from tracker_framework.simulation.radar_simulator import RadarSimulator, create_standard_scenarios
from tracker_framework.metrics.performance_metrics import PerformanceEvaluator


def run_parameter_sweep(base_config: dict, param_ranges: dict, 
                       scenario_name: str, output_dir: str):
    """
    Run parameter sweep study.
    
    Args:
        base_config: Base configuration
        param_ranges: Dictionary of parameter ranges to sweep
        scenario_name: Scenario to test
        output_dir: Output directory
    """
    print(f"\n{'='*70}")
    print("Parameter Sweep Study")
    print(f"{'='*70}\n")
    print(f"Scenario: {scenario_name}")
    print(f"Parameters to sweep:")
    for param, values in param_ranges.items():
        print(f"  {param}: {values}")
    print()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load scenario
    scenarios = create_standard_scenarios()
    if scenario_name not in scenarios:
        print(f"ERROR: Unknown scenario '{scenario_name}'")
        return
    
    trajectories, description = scenarios[scenario_name]
    
    # Generate parameter combinations
    param_names = list(param_ranges.keys())
    param_values_lists = [param_ranges[name] for name in param_names]
    param_combinations = list(itertools.product(*param_values_lists))
    
    total_runs = len(param_combinations)
    print(f"Total runs: {total_runs}\n")
    
    # Results storage
    results = []
    
    # Generate test data once (same for all parameter configs)
    base_measurement_model = RadarMeasurementModel(
        range_std=base_config['measurement_model']['range_std'],
        azimuth_std_deg=base_config['measurement_model']['azimuth_std_deg'],
        elevation_std_deg=base_config['measurement_model']['elevation_std_deg']
    )
    
    base_simulator = RadarSimulator(
        measurement_model=base_measurement_model,
        detection_probability=base_config['radar']['detection_probability'],
        clutter_density=base_config['radar']['clutter_density']
    )
    
    scan_period = 1.0 / base_config['radar']['scan_rate_hz']
    ground_truth_history, measurement_history = base_simulator.simulate_scenario(
        trajectories, scan_period
    )
    
    # Run parameter sweep
    for run_idx, param_combo in enumerate(param_combinations):
        print(f"Run {run_idx + 1}/{total_runs}: ", end='')
        
        # Build configuration for this run
        run_config = base_config.copy()
        param_dict = dict(zip(param_names, param_combo))
        
        print(f"{param_dict}")
        
        # Update configuration
        for param_name, param_value in param_dict.items():
            # Parse nested parameter names (e.g., 'tracker.num_particles')
            parts = param_name.split('.')
            config_section = run_config
            for part in parts[:-1]:
                config_section = config_section[part]
            config_section[parts[-1]] = param_value
        
        # Initialize tracker
        motion_model = ConstantVelocityModel(
            process_noise_std=run_config['motion_model']['cv_process_noise_std']
        )
        
        measurement_model = RadarMeasurementModel(
            range_std=run_config['measurement_model']['range_std'],
            azimuth_std_deg=run_config['measurement_model']['azimuth_std_deg'],
            elevation_std_deg=run_config['measurement_model']['elevation_std_deg']
        )
        
        tracker = MultiTargetTracker(
            motion_model=motion_model,
            measurement_model=measurement_model,
            num_particles=run_config['tracker']['num_particles'],
            gating_threshold=run_config['tracker']['gating_threshold'],
            state_type=StateType[run_config['tracker']['state_type']]
        )
        
        # Run tracking
        evaluator = PerformanceEvaluator()
        
        for scan_idx in range(len(measurement_history)):
            timestamp = scan_idx * scan_period
            measurements = measurement_history[scan_idx]
            ground_truth = ground_truth_history[scan_idx]
            
            tracker.update(measurements, timestamp)
            estimates = tracker.get_track_states()
            evaluator.evaluate_frame(ground_truth, estimates, 0.0)
        
        # Collect metrics
        metrics = evaluator.compute_overall_metrics()
        
        # Store results
        result_entry = param_dict.copy()
        result_entry.update({
            'position_rmse': metrics.position_rmse,
            'velocity_rmse': metrics.velocity_rmse,
            'track_continuity': metrics.track_continuity,
            'track_purity': metrics.track_purity,
            'true_positive_rate': metrics.true_positive_rate,
            'false_positive_rate': metrics.false_positive_rate,
            'ospa_distance': metrics.ospa_distance
        })
        results.append(result_entry)
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Save results
    csv_file = output_path / f"parameter_study_{scenario_name}.csv"
    df.to_csv(csv_file, index=False)
    print(f"\nResults saved to {csv_file}")
    
    # Print summary statistics
    print(f"\n{'='*70}")
    print("Summary Statistics")
    print(f"{'='*70}\n")
    
    print("Position RMSE [m]:")
    print(f"  Best:  {df['position_rmse'].min():.2f}")
    print(f"  Worst: {df['position_rmse'].max():.2f}")
    print(f"  Mean:  {df['position_rmse'].mean():.2f}")
    print()
    
    # Find best configuration
    best_idx = df['position_rmse'].idxmin()
    best_config = df.loc[best_idx]
    
    print("Best Configuration (lowest position RMSE):")
    for param in param_names:
        print(f"  {param}: {best_config[param]}")
    print(f"  Position RMSE: {best_config['position_rmse']:.2f} m")
    print(f"  Velocity RMSE: {best_config['velocity_rmse']:.2f} m/s")
    print(f"  Track Purity: {best_config['track_purity']:.3f}")
    print()


def run_parameter_study(study_config_path: str, output_dir: str):
    """
    Run parameter study from configuration file.
    
    Args:
        study_config_path: Path to study configuration JSON
        output_dir: Output directory
    """
    # Load study configuration
    with open(study_config_path, 'r') as f:
        study_config = json.load(f)
    
    base_config = study_config.get('base_config', {})
    scenarios_to_test = study_config.get('scenarios', ['single_straight'])
    param_ranges = study_config.get('parameter_ranges', {})
    
    # Run sweep for each scenario
    for scenario in scenarios_to_test:
        run_parameter_sweep(base_config, param_ranges, scenario, output_dir)


def create_example_study_config():
    """Create example parameter study configuration."""
    config = {
        "base_config": {
            "tracker": {
                "num_particles": 1000,
                "resampling_strategy": "systematic",
                "resampling_threshold": 0.5,
                "gating_threshold": 9.21,
                "confirmation_threshold": 3,
                "termination_threshold": 5,
                "state_type": "CV"
            },
            "motion_model": {
                "type": "CV",
                "cv_process_noise_std": 1.0
            },
            "measurement_model": {
                "range_std": 4.0,
                "azimuth_std_deg": 0.3,
                "elevation_std_deg": 0.3,
                "range_rate_std": 1.0
            },
            "radar": {
                "detection_probability": 0.95,
                "clutter_density": 1e-6,
                "scan_rate_hz": 10
            }
        },
        "scenarios": ["single_straight", "single_zigzag"],
        "parameter_ranges": {
            "tracker.num_particles": [500, 1000, 2000],
            "tracker.gating_threshold": [7.0, 9.21, 12.0],
            "motion_model.cv_process_noise_std": [0.5, 1.0, 2.0]
        }
    }
    
    output_file = Path("tracker_framework/configs/parameter_study_example.json")
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"Example study configuration created: {output_file}")


if __name__ == '__main__':
    # Create example if no config provided
    if len(sys.argv) < 2:
        print("Creating example parameter study configuration...")
        create_example_study_config()
        print("\nRun with: python parameter_study.py tracker_framework/configs/parameter_study_example.json")
    else:
        study_config = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output_parameter_study'
        run_parameter_study(study_config, output_dir)
