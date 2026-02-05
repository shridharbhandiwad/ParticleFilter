"""
Quick test of X, Y, Z vs time plotting functionality
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tracker_framework.core.state import State, Measurement, StateType
from tracker_framework.visualization.plots import TrackingVisualizer


def create_dummy_data():
    """Create dummy data for testing."""
    # Create a simple trajectory
    timestamps = np.linspace(0, 10, 50)
    
    # Ground truth: sinusoidal motion
    ground_truth_history = []
    estimate_history = []
    measurement_history = []
    
    for t in timestamps:
        # Ground truth state
        x = 100 + 10 * t
        y = 200 + 5 * np.sin(t)
        z = 50 + 2 * t
        
        gt_vector = np.array([x, y, z, 10, 5*np.cos(t), 2])
        gt_state = State(
            vector=gt_vector,
            state_type=StateType.CV,
            timestamp=t
        )
        ground_truth_history.append([gt_state])
        
        # Filtered estimate (with small error)
        est_vector = np.array([
            x + np.random.randn()*2, 
            y + np.random.randn()*2, 
            z + np.random.randn()*1,
            10 + np.random.randn()*0.5, 
            5*np.cos(t) + np.random.randn()*0.5, 
            2 + np.random.randn()*0.3
        ])
        est_state = State(
            vector=est_vector,
            state_type=StateType.CV,
            timestamp=t
        )
        estimate_history.append([est_state])
        
        # Measurements (convert from cartesian to spherical for realism)
        meas_x = x + np.random.randn() * 5
        meas_y = y + np.random.randn() * 5
        meas_z = z + np.random.randn() * 3
        
        # Convert to spherical
        r = np.sqrt(meas_x**2 + meas_y**2 + meas_z**2)
        az = np.arctan2(meas_y, meas_x)
        el = np.arcsin(meas_z / r)
        
        measurement = Measurement(
            range=r,
            azimuth=az,
            elevation=el,
            timestamp=t
        )
        measurement_history.append([measurement])
    
    return ground_truth_history, estimate_history, measurement_history, timestamps


def test_xyz_plot():
    """Test the new X, Y, Z vs time plot."""
    print("Creating test data...")
    gt_history, est_history, meas_history, timestamps = create_dummy_data()
    
    print("Generating X, Y, Z vs time plot...")
    visualizer = TrackingVisualizer()
    
    fig = visualizer.plot_coordinates_vs_time(
        gt_history,
        est_history,
        meas_history,
        timestamps,
        save_path='output/test_xyz_plot.png'
    )
    
    print("✓ Plot generated successfully!")
    print("  Saved to: output/test_xyz_plot.png")
    
    # Verify the plot was created
    output_file = Path('output/test_xyz_plot.png')
    if output_file.exists():
        print(f"✓ Plot file exists and has size: {output_file.stat().st_size} bytes")
        return True
    else:
        print("✗ Plot file was not created!")
        return False


if __name__ == '__main__':
    # Create output directory
    Path('output').mkdir(exist_ok=True)
    
    success = test_xyz_plot()
    sys.exit(0 if success else 1)
