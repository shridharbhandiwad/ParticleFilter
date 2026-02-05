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
                                 QTableWidgetItem, QSplitter, QProgressBar, QFrame)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import QFont, QColor, QPalette
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
            self.timestamps = []
            self.evaluator = PerformanceEvaluator()
            
            # Timer for simulation
            self.sim_timer = QTimer()
            self.sim_timer.timeout.connect(self._simulation_step)
            self.sim_step = 0
            self.total_steps = 0
            
            # Particle filter status
            self.particle_status = {
                'effective_sample_size': 0,
                'num_particles': 0,
                'num_tracks': 0
            }
            
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
            
            # Simulation Status Panel
            status_group = QGroupBox("Simulation Status")
            status_layout = QVBoxLayout()
            status_group.setLayout(status_layout)
            
            # Status indicator
            self.status_indicator = QLabel("⚫ Ready to Start")
            self.status_indicator.setFont(QFont('Arial', 12, QFont.Bold))
            self.status_indicator.setAlignment(Qt.AlignCenter)
            status_layout.addWidget(self.status_indicator)
            
            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            status_layout.addWidget(self.progress_bar)
            
            # Step counter
            self.step_label = QLabel("Step: 0 / 0")
            self.step_label.setAlignment(Qt.AlignCenter)
            status_layout.addWidget(self.step_label)
            
            layout.addWidget(status_group)
            
            # Particle Filter Status Panel
            pf_status_group = QGroupBox("Particle Filter Status")
            pf_status_layout = QVBoxLayout()
            pf_status_group.setLayout(pf_status_layout)
            
            self.pf_status_label = QLabel(
                "Particles: --\n"
                "Active Tracks: --\n"
                "Eff. Sample Size: --"
            )
            self.pf_status_label.setFont(QFont('Courier', 9))
            pf_status_layout.addWidget(self.pf_status_label)
            
            layout.addWidget(pf_status_group)
            
            # Control buttons
            button_layout = QHBoxLayout()
            
            self.start_button = QPushButton("▶ Start Simulation")
            self.start_button.clicked.connect(self._start_simulation)
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.start_button.setToolTip("Click to start the particle filter simulation with current parameters")
            button_layout.addWidget(self.start_button)
            
            self.stop_button = QPushButton("⏸ Stop")
            self.stop_button.clicked.connect(self._stop_simulation)
            self.stop_button.setEnabled(False)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            button_layout.addWidget(self.stop_button)
            
            self.reset_button = QPushButton("⟲ Reset")
            self.reset_button.clicked.connect(self._reset_simulation)
            self.reset_button.setToolTip("Reset simulation to initial state")
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
            
            # Quick Start Instructions
            instructions_group = QGroupBox("Quick Start")
            instructions_layout = QVBoxLayout()
            instructions_group.setLayout(instructions_layout)
            
            instructions = QLabel(
                "1. Select a scenario (Scenario tab)\n"
                "2. Adjust parameters if desired\n"
                "3. Click 'Start Simulation'\n"
                "4. Watch real-time tracking!\n\n"
                "💡 Default settings work well for most scenarios"
            )
            instructions.setWordWrap(True)
            instructions.setStyleSheet("QLabel { color: #555; font-size: 11px; }")
            instructions_layout.addWidget(instructions)
            
            layout.addWidget(instructions_group)
            
            # Status display
            self.status_text = QTextEdit()
            self.status_text.setReadOnly(True)
            self.status_text.setMaximumHeight(120)
            layout.addWidget(QLabel("Log:"))
            layout.addWidget(self.status_text)
            
            # Initial welcome message
            self._log("👋 Welcome to Particle Filter Drone Tracker!")
            self._log("Click 'Start Simulation' to begin tracking with the particle filter.")
            
            return panel
        
        def _create_pf_params_tab(self) -> QWidget:
            """Create particle filter parameters tab."""
            widget = QWidget()
            layout = QVBoxLayout()
            widget.setLayout(layout)
            
            # Number of particles
            self.num_particles_spinner = self._create_param_spinner(
                layout, "Number of Particles", 100, 5000, 1000, 100,
                tooltip="More particles = better accuracy but slower. 1000 is good for most cases."
            )
            
            # Resampling strategy
            layout.addWidget(QLabel("Resampling Strategy:"))
            self.resampling_combo = QComboBox()
            self.resampling_combo.addItems([
                "systematic", "stratified", "residual", "multinomial"
            ])
            self.resampling_combo.setToolTip("Systematic is recommended for most applications")
            layout.addWidget(self.resampling_combo)
            
            # Resampling threshold
            self.resample_threshold_spinner = self._create_param_spinner(
                layout, "Resampling Threshold", 0.1, 1.0, 0.5, 0.1, decimals=2,
                tooltip="Trigger resampling when effective sample size drops below this ratio (0.5 recommended)"
            )
            
            # Gating threshold
            self.gating_threshold_spinner = self._create_param_spinner(
                layout, "Gating Threshold (chi-sq)", 1.0, 20.0, 9.21, 0.5, decimals=2,
                tooltip="Chi-squared threshold for measurement gating. 9.21 = 99% confidence for 3D"
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
            self.motion_model_combo.setToolTip("CV=Constant Velocity, CA=Constant Acceleration, CT=Coordinated Turn")
            layout.addWidget(self.motion_model_combo)
            
            # Process noise std
            self.process_noise_spinner = self._create_param_spinner(
                layout, "Process Noise Std [m/s²]", 0.1, 10.0, 1.0, 0.1, decimals=2,
                tooltip="Models uncertainty in target motion. Higher = more erratic motion expected."
            )
            
            # Turn rate noise (for CT model)
            self.turn_rate_noise_spinner = self._create_param_spinner(
                layout, "Turn Rate Noise [rad/s²]", 0.01, 1.0, 0.1, 0.01, decimals=3,
                tooltip="Turn rate uncertainty (only used for Coordinated Turn model)"
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
                layout, "Range Std [m]", 1.0, 10.0, 4.0, 0.5, decimals=1,
                tooltip="Radar range measurement standard deviation"
            )
            
            # Azimuth accuracy
            self.azimuth_std_spinner = self._create_param_spinner(
                layout, "Azimuth Std [deg]", 0.1, 1.0, 0.3, 0.05, decimals=2,
                tooltip="Radar azimuth (horizontal angle) measurement standard deviation"
            )
            
            # Elevation accuracy
            self.elevation_std_spinner = self._create_param_spinner(
                layout, "Elevation Std [deg]", 0.1, 1.0, 0.3, 0.05, decimals=2,
                tooltip="Radar elevation (vertical angle) measurement standard deviation"
            )
            
            # Detection probability
            self.detection_prob_spinner = self._create_param_spinner(
                layout, "Detection Probability", 0.5, 1.0, 0.95, 0.05, decimals=2,
                tooltip="Probability that radar detects a target when present (0.95 = 95%)"
            )
            
            # Clutter density
            self.clutter_density_spinner = self._create_param_spinner(
                layout, "Clutter Density (log10)", -8.0, -3.0, -6.0, 0.5, decimals=1,
                tooltip="False alarm density (log scale). -6 means 10^-6 false alarms per m³"
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
            self.scenario_combo.setToolTip("Choose a target scenario to track")
            layout.addWidget(self.scenario_combo)
            
            # Scan rate
            self.scan_rate_spinner = self._create_param_spinner(
                layout, "Scan Rate [Hz]", 1, 20, 10, 1,
                tooltip="Radar update rate. Higher = more frequent updates but faster playback."
            )
            
            layout.addStretch()
            return widget
        
        def _create_param_spinner(self, layout, label, min_val, max_val, default, step, decimals=0, tooltip=None):
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
            
            if tooltip:
                spinner.setToolTip(tooltip)
            
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
            
            # Create tab widget for different visualizations
            viz_tabs = QTabWidget()
            layout.addWidget(viz_tabs)
            
            # Tab 1: 2D Trajectory
            traj_widget = QWidget()
            traj_layout = QVBoxLayout()
            traj_widget.setLayout(traj_layout)
            self.trajectory_canvas = FigureCanvas(Figure(figsize=(8, 6)))
            traj_layout.addWidget(self.trajectory_canvas)
            viz_tabs.addTab(traj_widget, "2D Trajectory")
            
            # Tab 2: X, Y, Z vs Time
            xyz_widget = QWidget()
            xyz_layout = QVBoxLayout()
            xyz_widget.setLayout(xyz_layout)
            self.xyz_canvas = FigureCanvas(Figure(figsize=(8, 8)))
            xyz_layout.addWidget(self.xyz_canvas)
            viz_tabs.addTab(xyz_widget, "X, Y, Z vs Time")
            
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
            self.timestamps = []
            self.evaluator.reset()
            self.sim_step = 0
            self.total_steps = len(self.measurement_history)
            
            # Update status indicators
            self.status_indicator.setText("🟢 Running...")
            self.status_indicator.setStyleSheet("QLabel { color: green; }")
            self.progress_bar.setValue(0)
            self.progress_bar.setRange(0, self.total_steps)
            self.step_label.setText(f"Step: 0 / {self.total_steps}")
            
            # Update particle filter status
            self.particle_status['num_particles'] = self.config['num_particles']
            self.particle_status['num_tracks'] = 0
            self._update_pf_status()
            
            # Start timer
            self.is_running = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            timer_interval = int(scan_period * 1000)  # milliseconds
            self.sim_timer.start(timer_interval)
            
            self._log(f"🚀 Simulation started: {description}")
            self._log(f"📊 Total steps: {self.total_steps}, Particles: {self.config['num_particles']}")
            self._log(f"⚙️  Motion Model: {self.config['motion_model']}, Scan Rate: {self.config['scan_rate_hz']} Hz")
        
        def _stop_simulation(self):
            """Stop simulation."""
            self.is_running = False
            self.sim_timer.stop()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # Update status
            if self.sim_step >= self.total_steps:
                self.status_indicator.setText("✅ Completed")
                self.status_indicator.setStyleSheet("QLabel { color: blue; }")
                self._log("✅ Simulation completed successfully!")
            else:
                self.status_indicator.setText("⏸ Stopped")
                self.status_indicator.setStyleSheet("QLabel { color: orange; }")
                self._log("⏸ Simulation stopped by user")
            
            # Compute final metrics
            self._display_final_metrics()
        
        def _reset_simulation(self):
            """Reset simulation."""
            self.is_running = False
            self.sim_timer.stop()
            self.sim_step = 0
            self.total_steps = 0
            self.ground_truth_history = []
            self.estimate_history = []
            self.measurement_history = []
            self.timestamps = []
            self.evaluator.reset()
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # Reset status indicators
            self.status_indicator.setText("⚫ Ready to Start")
            self.status_indicator.setStyleSheet("QLabel { color: black; }")
            self.progress_bar.setValue(0)
            self.step_label.setText("Step: 0 / 0")
            
            # Reset particle filter status
            self.particle_status = {
                'effective_sample_size': 0,
                'num_particles': 0,
                'num_tracks': 0
            }
            self._update_pf_status()
            
            # Clear visualizations
            self.trajectory_canvas.figure.clear()
            self.trajectory_canvas.draw()
            self.xyz_canvas.figure.clear()
            self.xyz_canvas.draw()
            
            # Reset metrics table
            for i in range(6):
                self.metrics_table.item(i, 1).setText("--")
            
            self._log("🔄 Simulation reset")
        
        def _simulation_step(self):
            """Execute one simulation step."""
            if self.sim_step >= len(self.measurement_history):
                self._stop_simulation()
                return
            
            # Get current data
            measurements = self.measurement_history[self.sim_step]
            ground_truth = self.ground_truth_history[self.sim_step]
            timestamp = self.sim_step / self.config['scan_rate_hz']
            self.timestamps.append(timestamp)
            
            # Track
            start_time = time.time()
            self.tracker.update(measurements, timestamp)
            processing_time = time.time() - start_time
            
            # Get estimates
            estimates = self.tracker.get_track_states()
            self.estimate_history.append(estimates)
            
            # Update particle filter status
            self._update_particle_filter_status()
            
            # Evaluate
            frame_metrics = self.evaluator.evaluate_frame(
                ground_truth, estimates, processing_time
            )
            
            # Update progress indicators
            self.sim_step += 1
            self.progress_bar.setValue(self.sim_step)
            self.step_label.setText(f"Step: {self.sim_step} / {self.total_steps}")
            progress_pct = (self.sim_step / self.total_steps) * 100
            self.status_indicator.setText(f"🟢 Running... ({progress_pct:.0f}%)")
            
            # Update visualizations
            self._update_visualization()
            self._update_xyz_visualization()
            self._update_metrics_table(frame_metrics)
            
            # Log every 10 steps to avoid clutter
            if self.sim_step % 10 == 0 or self.sim_step == 1:
                self._log(f"Step {self.sim_step}/{self.total_steps}: {len(estimates)} tracks, "
                         f"{len(measurements)} meas, {processing_time*1000:.1f}ms")
        
        def _update_visualization(self):
            """Update trajectory visualization."""
            # Clear and redraw
            self.trajectory_canvas.figure.clear()
            ax = self.trajectory_canvas.figure.add_subplot(111)
            
            # Plot particles for current tracks (show particle cloud)
            if self.tracker and hasattr(self.tracker, 'tracks'):
                particle_label_added = False
                for track in self.tracker.tracks.values():
                    if hasattr(track.filter, 'particles') and len(track.filter.particles) > 0:
                        particles = track.filter.particles
                        # Sample particles for visualization (max 200 per track)
                        num_to_plot = min(200, len(particles))
                        if len(particles) > 200:
                            sample_indices = np.random.choice(len(particles), 200, replace=False)
                            particles_to_plot = [particles[i] for i in sample_indices]
                        else:
                            particles_to_plot = particles
                        
                        # Extract positions from State objects
                        positions = np.array([p.position[0:2] for p in particles_to_plot])
                        ax.plot(positions[:, 0], positions[:, 1], 'c.', 
                               markersize=1, alpha=0.2, 
                               label='Particles' if not particle_label_added else '')
                        particle_label_added = True
            
            # Plot ground truth
            for gt_track in self.ground_truth_history[:self.sim_step+1]:
                for state in gt_track:
                    ax.plot(state.position[0], state.position[1], 'go', 
                           markersize=4, alpha=0.6, label='Ground Truth' if state == gt_track[0] else '')
            
            # Plot estimates (track history)
            for est_list in self.estimate_history:
                for state in est_list:
                    ax.plot(state.position[0], state.position[1], 'r-', 
                           marker='*', markersize=6, linewidth=2, 
                           label='Estimate' if state == est_list[0] and est_list == self.estimate_history[0] else '')
            
            # Plot current measurements
            if self.sim_step < len(self.measurement_history):
                current_meas = self.measurement_history[self.sim_step]
                for meas in current_meas:
                    cart = meas.to_cartesian()
                    ax.plot(cart[0], cart[1], 'kx', markersize=3, alpha=0.5,
                           label='Measurements' if meas == current_meas[0] else '')
            
            ax.set_xlabel('X [m]', fontsize=12)
            ax.set_ylabel('Y [m]', fontsize=12)
            ax.set_title(f'Tracking: {self.current_scenario_name} (Step {self.sim_step}/{self.total_steps})',
                        fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.axis('equal')
            
            # Add legend (avoid duplicates)
            handles, labels = ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            if by_label:
                ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=9)
            
            self.trajectory_canvas.draw()
        
        def _update_xyz_visualization(self):
            """Update X, Y, Z vs Time visualization."""
            # Only update if we have data
            if not self.estimate_history or not self.timestamps:
                return
            
            # Clear and redraw
            self.xyz_canvas.figure.clear()
            
            # Create three subplots
            axes = [
                self.xyz_canvas.figure.add_subplot(3, 1, 1),
                self.xyz_canvas.figure.add_subplot(3, 1, 2),
                self.xyz_canvas.figure.add_subplot(3, 1, 3)
            ]
            
            coord_names = ['X', 'Y', 'Z']
            coord_indices = [0, 1, 2]
            
            for coord_idx, ax, coord_name in zip(coord_indices, axes, coord_names):
                # Plot ground truth
                gt_plotted = False
                for scan_idx in range(len(self.ground_truth_history[:self.sim_step+1])):
                    scan_gt = self.ground_truth_history[scan_idx]
                    for state in scan_gt:
                        t = self.timestamps[scan_idx] if scan_idx < len(self.timestamps) else 0
                        ax.plot(t, state.position[coord_idx], 'go', markersize=6, 
                               alpha=0.7, label='Ground Truth' if not gt_plotted else '')
                        gt_plotted = True
                
                # Plot measurements (convert from spherical to cartesian)
                meas_plotted = False
                for scan_idx in range(len(self.measurement_history[:self.sim_step+1])):
                    scan_meas = self.measurement_history[scan_idx]
                    for meas in scan_meas:
                        cart = meas.to_cartesian()
                        t = self.timestamps[scan_idx] if scan_idx < len(self.timestamps) else 0
                        ax.plot(t, cart[coord_idx], 'kx', markersize=4, 
                               alpha=0.3, label='Measurements' if not meas_plotted else '')
                        meas_plotted = True
                
                # Plot filtered estimates
                est_plotted = False
                for scan_idx in range(len(self.estimate_history)):
                    scan_est = self.estimate_history[scan_idx]
                    for state in scan_est:
                        t = self.timestamps[scan_idx] if scan_idx < len(self.timestamps) else 0
                        ax.plot(t, state.position[coord_idx], 'r*', markersize=7, 
                               alpha=0.8, label='Filtered' if not est_plotted else '')
                        est_plotted = True
                
                # Connect filtered estimates with lines for each track
                if self.estimate_history:
                    num_tracks = max(len(scan_est) for scan_est in self.estimate_history if scan_est)
                    for track_idx in range(num_tracks):
                        track_times = []
                        track_coords = []
                        for scan_idx, scan_est in enumerate(self.estimate_history):
                            if track_idx < len(scan_est):
                                t = self.timestamps[scan_idx] if scan_idx < len(self.timestamps) else 0
                                track_times.append(t)
                                track_coords.append(scan_est[track_idx].position[coord_idx])
                        
                        if track_times:
                            ax.plot(track_times, track_coords, 'r--', linewidth=1.5, alpha=0.6)
                
                ax.set_ylabel(f'{coord_name} [m]', fontsize=10)
                ax.grid(True, alpha=0.3)
                
                # Only show legend on first subplot to avoid clutter
                if coord_idx == 0:
                    ax.legend(loc='best', fontsize=8)
            
            axes[-1].set_xlabel('Time [s]', fontsize=10)
            axes[0].set_title(f'Position vs Time (Step {self.sim_step}/{self.total_steps})', 
                             fontsize=12, fontweight='bold')
            
            self.xyz_canvas.figure.tight_layout()
            self.xyz_canvas.draw()
        
        def _update_metrics_table(self, frame_metrics):
            """Update metrics table."""
            metrics = self.evaluator.compute_overall_metrics()
            
            self.metrics_table.item(0, 1).setText(f"{metrics.position_rmse:.2f}")
            self.metrics_table.item(1, 1).setText(f"{metrics.velocity_rmse:.2f}")
            self.metrics_table.item(2, 1).setText(f"{metrics.track_purity:.3f}")
            self.metrics_table.item(3, 1).setText(f"{metrics.true_positive_rate:.3f}")
            self.metrics_table.item(4, 1).setText(f"{metrics.false_positive_rate:.3f}")
            self.metrics_table.item(5, 1).setText(f"{frame_metrics['processing_time']*1000:.2f}")
        
        def _update_particle_filter_status(self):
            """Update particle filter status from tracker."""
            if self.tracker:
                stats = self.tracker.get_statistics()
                self.particle_status['num_tracks'] = stats['total_tracks']
                
                # Calculate effective sample size (ESS)
                total_ess = 0
                num_tracks = 0
                for track in self.tracker.tracks.values():
                    if hasattr(track.filter, 'weights'):
                        weights = track.filter.weights
                        if weights is not None and len(weights) > 0:
                            ess = 1.0 / np.sum(weights ** 2)
                            total_ess += ess
                            num_tracks += 1
                
                if num_tracks > 0:
                    avg_ess = total_ess / num_tracks
                    self.particle_status['effective_sample_size'] = avg_ess
                else:
                    self.particle_status['effective_sample_size'] = 0
                
                self._update_pf_status()
        
        def _update_pf_status(self):
            """Update particle filter status display."""
            num_particles = self.particle_status.get('num_particles', 0)
            num_tracks = self.particle_status.get('num_tracks', 0)
            ess = self.particle_status.get('effective_sample_size', 0)
            
            status_text = f"Particles: {num_particles}\n"
            status_text += f"Active Tracks: {num_tracks}\n"
            
            if ess > 0:
                ess_ratio = ess / num_particles if num_particles > 0 else 0
                status_text += f"Eff. Sample Size: {ess:.0f} ({ess_ratio:.1%})"
            else:
                status_text += "Eff. Sample Size: --"
            
            self.pf_status_label.setText(status_text)
        
        def _display_final_metrics(self):
            """Display final performance metrics."""
            metrics = self.evaluator.compute_overall_metrics()
            
            self._log("\n📊 === Final Performance Metrics ===")
            self._log(f"Position RMSE: {metrics.position_rmse:.2f} m")
            self._log(f"Velocity RMSE: {metrics.velocity_rmse:.2f} m/s")
            self._log(f"Track Continuity: {metrics.track_continuity:.3f}")
            self._log(f"Track Purity: {metrics.track_purity:.3f}")
            self._log(f"True Positive Rate: {metrics.true_positive_rate:.3f}")
            self._log(f"False Positive Rate: {metrics.false_positive_rate:.3f}")
            self._log(f"Avg Processing Time: {metrics.avg_processing_time*1000:.2f} ms")
            self._log("====================================\n")
        
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
