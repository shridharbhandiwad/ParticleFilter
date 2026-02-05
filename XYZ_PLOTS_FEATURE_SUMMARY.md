# X, Y, Z vs Time Plots - Feature Implementation Summary

## Overview
Added three new plots showing x, y, and z coordinates vs time for ground truth (GT), measured, and filtered values in the particle filter tracking system.

## Changes Made

### 1. New Plot Method in `TrackingVisualizer`
**File:** `tracker_framework/visualization/plots.py`

Added `plot_coordinates_vs_time()` method that creates a 3-subplot figure showing:
- **X Position vs Time**: Ground truth, measurements, and filtered estimates
- **Y Position vs Time**: Ground truth, measurements, and filtered estimates  
- **Z Position vs Time**: Ground truth, measurements, and filtered estimates

#### Method Signature:
```python
def plot_coordinates_vs_time(self,
                            ground_truth: List[List[State]],
                            estimates: List[List[State]],
                            measurements: List[List[Measurement]],
                            timestamps: List[float],
                            save_path: Optional[str] = None) -> Figure
```

#### Features:
- Ground truth plotted as green circles (`go`)
- Measurements plotted as black crosses (`kx`) after conversion from spherical to Cartesian
- Filtered estimates plotted as red stars (`r*`) with connecting dashed lines
- Separate subplot for each coordinate (X, Y, Z)
- Shared time axis for easy comparison
- Grid and legend for clarity

### 2. Integration into Example Simulation
**File:** `examples/run_simulation.py`

Added call to generate the new plot as part of the standard visualization pipeline:
```python
# X, Y, Z vs Time plot
fig = visualizer.plot_coordinates_vs_time(
    ground_truth_history,
    estimate_history,
    measurement_history,
    timestamps,
    save_path=output_path / f"coordinates_vs_time_{scenario_key}.png"
)
```

### 3. Matplotlib Backend Fix
**File:** `tracker_framework/visualization/plots.py`

Set matplotlib to use non-interactive backend (`Agg`) to prevent hanging when running in headless environments:
```python
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
```

### 4. Test Scripts
Created two test scripts to verify functionality:

#### `test_xyz_plots.py`
- Quick test with synthetic dummy data
- Verifies basic plotting functionality
- Fast execution (< 2 seconds)

#### `test_full_pipeline.py`
- Full end-to-end test with particle filter
- Reduced configuration (100 particles, 5 seconds)
- Tests complete integration
- Execution time: ~35 seconds

## Usage Examples

### Using in Your Code
```python
from tracker_framework.visualization.plots import TrackingVisualizer

# After running tracking simulation
visualizer = TrackingVisualizer()

fig = visualizer.plot_coordinates_vs_time(
    ground_truth_history,  # List of ground truth states per scan
    estimate_history,      # List of filtered estimates per scan
    measurement_history,   # List of measurements per scan
    timestamps,            # List of timestamps (seconds)
    save_path='output/xyz_vs_time.png'
)
```

### Running the Tests
```bash
# Quick functionality test
python3 test_xyz_plots.py

# Full pipeline test
python3 test_full_pipeline.py

# Original example (with new plot included)
python3 examples/run_simulation.py single_straight
```

## Output
The plots show:
- **Time series comparison** of all three position coordinates
- **Measurement noise** visible as scattered points around ground truth
- **Filtering effectiveness** shown by filtered estimates tracking ground truth
- **Track continuity** via connecting lines between filtered estimates

### Example Output Files:
- `output/test_xyz_plot.png` (282 KB) - Simple test
- `output/test_coordinates_vs_time.png` (415 KB) - Full pipeline test

## Visual Elements

### Plot Legend:
- 🟢 **Green circles**: Ground Truth positions
- ✖️ **Black crosses**: Radar Measurements (after conversion to Cartesian)
- 🔴 **Red stars**: Filtered Estimates
- **Red dashed lines**: Track continuity (connecting filtered estimates)

### Plot Layout:
```
┌─────────────────────────────────────────┐
│  X Position vs Time                     │
│  (GT: green, Measured: black, Red: est) │
├─────────────────────────────────────────┤
│  Y Position vs Time                     │
│  (GT: green, Measured: black, Red: est) │
├─────────────────────────────────────────┤
│  Z Position vs Time                     │
│  (GT: green, Measured: black, Red: est) │
└─────────────────────────────────────────┘
```

## Testing Results

### Quick Test (`test_xyz_plots.py`)
✅ **Status:** PASSED
- Plot generated successfully
- File size: 282 KB
- Execution time: ~1 second

### Full Pipeline Test (`test_full_pipeline.py`)
✅ **Status:** PASSED
- 150 scans processed
- 100 particles per filter
- Position RMSE: 23.86 m
- Velocity RMSE: 17.73 m/s
- Avg Processing Time: 192.84 ms
- Plot generated successfully
- File size: 415 KB
- Execution time: ~35 seconds

## Git Commits
1. **03604e0**: Add X, Y, Z vs time plots for GT, measured, and filtered values
2. **2c12faa**: Add test script and fix matplotlib backend for non-interactive plotting
3. **a84466e**: Add full pipeline test demonstrating X, Y, Z vs time plots

## Branch
All changes are on branch: `cursor/x-y-z-value-plots-a59e`

## Benefits
1. **Better insight** into tracking performance over time
2. **Easy comparison** between GT, measurements, and estimates
3. **Coordinate-specific analysis** (identify which axis has more error)
4. **Track continuity visualization** via connecting lines
5. **Integration** with existing visualization pipeline

## Compatibility
- Works with all existing scenarios
- Compatible with all motion models (CV, CA, CT)
- No breaking changes to existing code
- Backward compatible with existing visualization methods
