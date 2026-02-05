"""
Main GUI Window for Particle Filter Parameter Tuning

Features:
- Real-time parameter adjustment
- Scenario selection
- Start/Stop simulation
- Visualization display
- Configuration save/load
- Performance metrics display
"""

import sys
import json
import time
from pathlib import Path
import numpy as np

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QLabel, QSlider, QSpinBox, QDoubleSpinBox,
                                 QComboBox, QPushButton, QGroupBox, QTabWidget,
                                 QTextEdit, QFileDialog, QCheckBox, QTableWidget,
                                 QTableWidgetItem, QSplitter)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("Warning: PyQt5 not available. GUI functionality disabled.")

if PYQT_AVAILABLE:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib
    matplotlib.use('Qt5Agg')

from ..core.state import StateType
from ..models.motion_models import ConstantVelocityModel, ConstantAccelerationModel, CoordinatedTurnModel
from ..models.measurement_models import RadarMeasurementModel
from ..filters.particle_filter import ResamplingStrategy
from ..filters.multi_target_tracker import MultiTargetTracker
from ..simulation.radar_simulator import RadarSimulator, create_standard_scenarios
from ..metrics.performance_metrics import PerformanceEvaluator
from ..visualization.plots import TrackingVisualizer


if not PYQT_AVAILABLE:
    # Stub class for when PyQt5 is not available
    class TrackerGUI:
        def __init__(self):
            raise ImportError("PyQt5 is required for GUI functionality")
else:
    class TrackerGUI(QMainWindow):
        """
        Main GUI window for particle filter tuning.
        """
        
        def __init__(self):
            super().__init__()
            
            self.setWindowTitle("Particle Filter Drone Tracker - Parameter Tuning")
            self.setGeometry(100, 100, 1600, 900)
            
            # Configuration
            self.config = self._default_config()
            
            # Simulation state
            self.is_running = False
            self.tracker = None
            self.simulator = None
            self.scenarios = create_standard_scenarios()
            self.current_scenario_name = 'single_straight'
            
            # Data
            self.ground_truth_history = []
            self.estimate_history = []
            self.measurement_history = []
            self.evaluator = PerformanceEvaluator()
            
            # Timer for simulation
            self.sim_timer = QTimer()
            self.sim_timer.timeout.connect(self._simulation_step)
            self.sim_step = 0
            
            # Setup UI
            self._init_ui()
            
        def _init_ui(self):
            """Initialize user interface."""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            main_layout = QHBoxLayout()
            central_widget.setLayout(main_layout)
            
            # Left panel: Controls
            left_panel = self._create_control_panel()
            main_layout.addWidget(left_panel, stretch=1)
            
            # Right panel: Visualization
            right_panel = self._create_visualization_panel()
            main_layout.addWidget(right_panel, stretch=2)
            
        def _create_control_panel(self) -> QWidget:
            """Create control panel with parameter sliders."""
            panel = QWidget()
            layout = QVBoxLayout()
            panel.setLayout(layout)
            
            # Title
            title = QLabel("Parameter Controls")
            title.setFont(QFont('Arial', 16, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Tab widget for organized controls
            tabs = QTabWidget()
            layout.addWidget(tabs)
            
            # Tab 1: Particle Filter Parameters
            tabs.addTab(self._create_pf_params_tab(), "Particle Filter")
            
            # Tab 2: Motion Model Parameters
            tabs.addTab(self._create_motion_params_tab(), "Motion Model")
            
            # Tab 3: Measurement Parameters
            tabs.addTab(self._create_measurement_params_tab(), "Measurement")
            
            # Tab 4: Scenario Selection
            tabs.addTab(self._create_scenario_tab(), "Scenario")
            
            # Control buttons
            button_layout = QHBoxLayout()
            
            self.start_button = QPushButton("Start")
            self.start_button.clicked.connect(self._start_simulation)
            button_layout.addWidget(self.start_button)
            
            self.stop_button = QPushButton("Stop")
            self.stop_button.clicked.connect(self._stop_simulation)
            self.stop_button.setEnabled(False)
            button_layout.addWidget(self.stop_button)
            
            self.reset_button = QPushButton("Reset")
            self.reset_button.clicked.connect(self._reset_simulation)
            button_layout.addWidget(self.reset_button)
            
            layout.addLayout(button_layout)
            
            # Config buttons
            config_layout = QHBoxLayout()
            
            save_config_btn = QPushButton("Save Config")
            save_config_btn.clicked.connect(self._save_config)
            config_layout.addWidget(save_config_btn)
            
            load_config_btn = QPushButton("Load Config")
            load_config_btn.clicked.connect(self._load_config)
            config_layout.addWidget(load_config_btn)
            
            layout.addLayout(config_layout)
            
            # Status display
            self.status_text = QTextEdit()
            self.status_text.setReadOnly(True)
            self.status_text.setMaximumHeight(150)
            layout.addWidget(QLabel("Status:"))
            layout.addWidget(self.status_text)
            
            return panel
        
        def _create_pf_params_tab(self) -> QWidget:
            """Create particle filter parameters tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            widget.setLayout(layout)
            
            # Number of particles
            self.num_particles_spinner = self._create_param_spinner(
                layout, "Number of Particles", 100, 5000, 1000, 100
            )
            
            # Resampling strategy
            layout.addWidget(QLabel("Resampling Strategy:"))
            self.resampling_combo = QComboBox()
            self.resampling_combo.addItems([
                "systematic", "stratified", "residual", "multinomial"
            ])
            layout.addWidget(self.resampling_combo)
            
            # Resampling threshold
            self.resample_threshold_spinner = self._create_param_spinner(
                layout, "Resampling Threshold", 0.1, 1.0, 0.5, 0.1, decimals=2
            )
            
            # Gating threshold
            self.gating_threshold_spinner = self._create_param_spinner(
                layout, "Gating Threshold (chi-sq)", 1.0, 20.0, 9.21, 0.5, decimals=2
            )
            
            layout.addStretch()
            return widget
        
        def _create_motion_params_tab(self) -> QWidget:
            """Create motion model parameters tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            widget.setLayout(layout)
            
            # Motion model selection
            layout.addWidget(QLabel("Motion Model:"))
            self.motion_model_combo = QComboBox()
            self.motion_model_combo.addItems(["CV", "CA", "CT"])
            layout.addWidget(self.motion_model_combo)
            
            # Process noise std
            self.process_noise_spinner = self._create_param_spinner(
                layout, "Process Noise Std [m/s²]", 0.1, 10.0, 1.0, 0.1, decimals=2
            )
            
            # Turn rate noise (for CT model)
            self.turn_rate_noise_spinner = self._create_param_spinner(
                layout, "Turn Rate Noise [rad/s²]", 0.01, 1.0, 0.1, 0.01, decimals=3
            )
            
            layout.addStretch()
            return widget
        
        def _create_measurement_params_tab(self) -> QWidget:
            """Create measurement model parameters tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            widget.setLayout(layout)
            
            # Range accuracy
            self.range_std_spinner = self._create_param_spinner(
                layout, "Range Std [m]", 1.0, 10.0, 4.0, 0.5, decimals=1
            )
            
            # Azimuth accuracy
            self.azimuth_std_spinner = self._create_param_spinner(
                layout, "Azimuth Std [deg]", 0.1, 1.0, 0.3, 0.05, decimals=2
            )
            
            # Elevation accuracy
            self.elevation_std_spinner = self._create_param_spinner(
                layout, "Elevation Std [deg]", 0.1, 1.0, 0.3, 0.05, decimals=2
            )
            
            # Detection probability
            self.detection_prob_spinner = self._create_param_spinner(
                layout, "Detection Probability", 0.5, 1.0, 0.95, 0.05, decimals=2
            )
            
            # Clutter density
            self.clutter_density_spinner = self._create_param_spinner(
                layout, "Clutter Density (log10)", -8.0, -3.0, -6.0, 0.5, decimals=1
            )
            
            layout.addStretch()
            return widget
        
        def _create_scenario_tab(self) -> QWidget:
            """Create scenario selection tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            widget.setLayout(layout)
            
            layout.addWidget(QLabel("Select Scenario:"))
            
            self.scenario_combo = QComboBox()
            for name, (_, description) in self.scenarios.items():
                self.scenario_combo.addItem(f"{name}: {description}", name)
            layout.addWidget(self.scenario_combo)
            
            # Scan rate
            self.scan_rate_spinner = self._create_param_spinner(
                layout, "Scan Rate [Hz]", 1, 20, 10, 1
            )
            
            layout.addStretch()
            return widget
        
        def _create_param_spinner(self, layout, label, min_val, max_val, default, step, decimals=0):
            """Create parameter spinner with label."""
            layout.addWidget(QLabel(label + ":"))
            
            if decimals > 0:
                spinner = QDoubleSpinBox()
                spinner.setDecimals(decimals)
                spinner.setSingleStep(step)
            else:
                spinner = QSpinBox()
                spinner.setSingleStep(int(step))
            
            spinner.setMinimum(min_val)
            spinner.setMaximum(max_val)
            spinner.setValue(default)
            layout.addWidget(spinner)
            
            return spinner
        
        def _create_visualization_panel(self) -> QWidget:
            """Create visualization panel."""
            panel = QWidget()
            layout = QVBoxLayout()
            panel.setLayout(layout)
            
            # Title
            title = QLabel("Real-Time Tracking Visualization")
            title.setFont(QFont('Arial', 16, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Matplotlib canvases
            self.trajectory_canvas = FigureCanvas(Figure(figsize=(8, 6)))
            layout.addWidget(self.trajectory_canvas)
            
            # Metrics table
            metrics_label = QLabel("Performance Metrics")
            metrics_label.setFont(QFont('Arial', 12, QFont.Bold))
            layout.addWidget(metrics_label)
            
            self.metrics_table = QTableWidget()
            self.metrics_table.setRowCount(6)
            self.metrics_table.setColumnCount(2)
            self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
            self.metrics_table.setMaximumHeight(200)
            
            metrics_names = [
                "Position RMSE [m]",
                "Velocity RMSE [m/s]",
                "Track Quality",
                "True Positive Rate",
                "False Positive Rate",
                "Processing Time [ms]"
            ]
            
            for i, name in enumerate(metrics_names):
                self.metrics_table.setItem(i, 0, QTableWidgetItem(name))
                self.metrics_table.setItem(i, 1, QTableWidgetItem("--"))
            
            layout.addWidget(self.metrics_table)
            
            return panel
        
        def _default_config(self) -> dict:
            """Get default configuration."""
            return {
                'num_particles': 1000,
                'resampling_strategy': 'systematic',
                'resampling_threshold': 0.5,
                'gating_threshold': 9.21,
                'motion_model': 'CV',
                'process_noise_std': 1.0,
                'turn_rate_noise_std': 0.1,
                'range_std': 4.0,
                'azimuth_std_deg': 0.3,
                'elevation_std_deg': 0.3,
                'detection_probability': 0.95,
                'clutter_density_log': -6.0,
                'scenario': 'single_straight',
                'scan_rate_hz': 10
            }
        
        def _read_config_from_ui(self):
            """Read configuration from UI controls."""
            self.config['num_particles'] = self.num_particles_spinner.value()
            self.config['resampling_strategy'] = self.resampling_combo.currentText()
            self.config['resampling_threshold'] = self.resample_threshold_spinner.value()
            self.config['gating_threshold'] = self.gating_threshold_spinner.value()
            self.config['motion_model'] = self.motion_model_combo.currentText()
            self.config['process_noise_std'] = self.process_noise_spinner.value()
            self.config['turn_rate_noise_std'] = self.turn_rate_noise_spinner.value()
            self.config['range_std'] = self.range_std_spinner.value()
            self.config['azimuth_std_deg'] = self.azimuth_std_spinner.value()
            self.config['elevation_std_deg'] = self.elevation_std_spinner.value()
            self.config['detection_probability'] = self.detection_prob_spinner.value()
            self.config['clutter_density_log'] = self.clutter_density_spinner.value()
            self.config['scenario'] = self.scenario_combo.currentData()
            self.config['scan_rate_hz'] = self.scan_rate_spinner.value()
        
        def _start_simulation(self):
            """Start simulation."""
            self._read_config_from_ui()
            self._reset_simulation()
            
            # Initialize tracker
            motion_model = self._create_motion_model()
            measurement_model = self._create_measurement_model()
            
            state_type = StateType.CV
            if self.config['motion_model'] == 'CA':
                state_type = StateType.CA
            elif self.config['motion_model'] == 'CT':
                state_type = StateType.CT
            
            self.tracker = MultiTargetTracker(
                motion_model=motion_model,
                measurement_model=measurement_model,
                num_particles=self.config['num_particles'],
                gating_threshold=self.config['gating_threshold'],
                state_type=state_type
            )
            
            # Initialize simulator
            self.simulator = RadarSimulator(
                measurement_model=measurement_model,
                detection_probability=self.config['detection_probability'],
                clutter_density=10 ** self.config['clutter_density_log']
            )
            
            # Load scenario
            self.current_scenario_name = self.config['scenario']
            trajectories, description = self.scenarios[self.current_scenario_name]
            
            # Simulate scenario
            scan_period = 1.0 / self.config['scan_rate_hz']
            self.ground_truth_history, self.measurement_history = \
                self.simulator.simulate_scenario(trajectories, scan_period)
            
            self.estimate_history = []
            self.evaluator.reset()
            self.sim_step = 0
            
            # Start timer
            self.is_running = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            timer_interval = int(scan_period * 1000)  # milliseconds
            self.sim_timer.start(timer_interval)
            
            self._log(f"Simulation started: {description}")
            self._log(f"Configuration: {self.config}")
        
        def _stop_simulation(self):
            """Stop simulation."""
            self.is_running = False
            self.sim_timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._log("Simulation stopped")
            
            # Compute final metrics
            self._display_final_metrics()
        
        def _reset_simulation(self):
            """Reset simulation."""
            self.is_running = False
            self.sim_timer.stop()
            self.sim_step = 0
            self.ground_truth_history = []
            self.estimate_history = []
            self.measurement_history = []
            self.evaluator.reset()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._log("Simulation reset")
        
        def _simulation_step(self):
            """Execute one simulation step."""
            if self.sim_step >= len(self.measurement_history):
                self._stop_simulation()
                return
            
            # Get current data
            measurements = self.measurement_history[self.sim_step]
            ground_truth = self.ground_truth_history[self.sim_step]
            timestamp = self.sim_step / self.config['scan_rate_hz']
            
            # Track
            start_time = time.time()
            self.tracker.update(measurements, timestamp)
            processing_time = time.time() - start_time
            
            # Get estimates
            estimates = self.tracker.get_track_states()
            self.estimate_history.append(estimates)
            
            # Evaluate
            frame_metrics = self.evaluator.evaluate_frame(
                ground_truth, estimates, processing_time
            )
            
            # Update visualization
            self._update_visualization()
            self._update_metrics_table(frame_metrics)
            
            # Log
            self._log(f"Step {self.sim_step}: {len(ground_truth)} GT, "
                     f"{len(estimates)} Est, {len(measurements)} Meas, "
                     f"Time: {processing_time*1000:.1f}ms")
            
            self.sim_step += 1
        
        def _update_visualization(self):
            """Update trajectory visualization."""
            # Clear and redraw
            self.trajectory_canvas.figure.clear()
            ax = self.trajectory_canvas.figure.add_subplot(111)
            
            # Plot ground truth
            for gt_track in self.ground_truth_history[:self.sim_step]:
                for state in gt_track:
                    ax.plot(state.position[0], state.position[1], 'go', markersize=2)
            
            # Plot estimates
            for est_list in self.estimate_history:
                for state in est_list:
                    ax.plot(state.position[0], state.position[1], 'r*', markersize=4)
            
            # Plot measurements
            for meas_list in self.measurement_history[:self.sim_step]:
                for meas in meas_list:
                    cart = meas.to_cartesian()
                    ax.plot(cart[0], cart[1], 'k.', markersize=1, alpha=0.3)
            
            ax.set_xlabel('X [m]')
            ax.set_ylabel('Y [m]')
            ax.set_title(f'Tracking: {self.current_scenario_name} (Step {self.sim_step})')
            ax.grid(True, alpha=0.3)
            ax.axis('equal')
            
            self.trajectory_canvas.draw()
        
        def _update_metrics_table(self, frame_metrics):
            """Update metrics table."""
            metrics = self.evaluator.compute_overall_metrics()
            
            self.metrics_table.item(0, 1).setText(f"{metrics.position_rmse:.2f}")
            self.metrics_table.item(1, 1).setText(f"{metrics.velocity_rmse:.2f}")
            self.metrics_table.item(2, 1).setText(f"{metrics.track_purity:.3f}")
            self.metrics_table.item(3, 1).setText(f"{metrics.true_positive_rate:.3f}")
            self.metrics_table.item(4, 1).setText(f"{metrics.false_positive_rate:.3f}")
            self.metrics_table.item(5, 1).setText(f"{frame_metrics['processing_time']*1000:.2f}")
        
        def _display_final_metrics(self):
            """Display final performance metrics."""
            metrics = self.evaluator.compute_overall_metrics()
            
            self._log("\n=== Final Performance Metrics ===")
            self._log(f"Position RMSE: {metrics.position_rmse:.2f} m")
            self._log(f"Velocity RMSE: {metrics.velocity_rmse:.2f} m/s")
            self._log(f"Track Continuity: {metrics.track_continuity:.3f}")
            self._log(f"Track Purity: {metrics.track_purity:.3f}")
            self._log(f"True Positive Rate: {metrics.true_positive_rate:.3f}")
            self._log(f"False Positive Rate: {metrics.false_positive_rate:.3f}")
            self._log(f"Avg Processing Time: {metrics.avg_processing_time*1000:.2f} ms")
            self._log("================================\n")
        
        def _create_motion_model(self):
            """Create motion model from config."""
            model_type = self.config['motion_model']
            
            if model_type == 'CV':
                return ConstantVelocityModel(self.config['process_noise_std'])
            elif model_type == 'CA':
                return ConstantAccelerationModel(self.config['process_noise_std'])
            elif model_type == 'CT':
                return CoordinatedTurnModel(
                    self.config['process_noise_std'],
                    self.config['turn_rate_noise_std']
                )
        
        def _create_measurement_model(self):
            """Create measurement model from config."""
            return RadarMeasurementModel(
                range_std=self.config['range_std'],
                azimuth_std_deg=self.config['azimuth_std_deg'],
                elevation_std_deg=self.config['elevation_std_deg']
            )
        
        def _save_config(self):
            """Save configuration to JSON file."""
            self._read_config_from_ui()
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Configuration", "", "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.config, f, indent=4)
                self._log(f"Configuration saved to {filename}")
        
        def _load_config(self):
            """Load configuration from JSON file."""
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Configuration", "", "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'r') as f:
                    self.config = json.load(f)
                
                # Update UI
                self.num_particles_spinner.setValue(self.config['num_particles'])
                self.resampling_combo.setCurrentText(self.config['resampling_strategy'])
                # ... update other controls ...
                
                self._log(f"Configuration loaded from {filename}")
        
        def _log(self, message):
            """Log message to status text."""
            self.status_text.append(message)
            # Auto-scroll to bottom
            scrollbar = self.status_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())


def launch_gui():
    """Launch the GUI application."""
    if not PYQT_AVAILABLE:
        print("ERROR: PyQt5 is not installed. GUI cannot be launched.")
        print("Install with: pip install PyQt5")
        return
    
    app = QApplication(sys.argv)
    window = TrackerGUI()
    window.show()
    sys.exit(app.exec_())
