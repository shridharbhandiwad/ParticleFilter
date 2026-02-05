"""
Realistic Radar Data Simulator

Generates synthetic radar measurements with:
- Multiple drone trajectories (straight, zigzag, maneuver, hover)
- Realistic measurement noise
- Clutter and false alarms
- Missed detections
- Cloud/weather disturbance
- Multi-target scenarios
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from enum import Enum
from ..core.state import State, Measurement, StateType
from ..models.measurement_models import RadarMeasurementModel, ClutterModel


class TrajectoryType(Enum):
    """Drone trajectory patterns."""
    STRAIGHT = "straight"
    ZIGZAG = "zigzag"
    CIRCULAR = "circular"
    HOVER = "hover"
    AGGRESSIVE_MANEUVER = "aggressive"
    HOVER_AND_BURST = "hover_burst"


class DroneTrajectory:
    """
    Drone trajectory generator.
    
    Generates ground truth state sequences for various motion patterns.
    """
    
    def __init__(self, 
                 trajectory_type: TrajectoryType,
                 start_position: np.ndarray,
                 start_velocity: np.ndarray,
                 duration: float,
                 dt: float = 0.1):
        """
        Initialize trajectory generator.
        
        Args:
            trajectory_type: Type of trajectory
            start_position: Starting position [x, y, z] in meters
            start_velocity: Starting velocity [vx, vy, vz] in m/s
            duration: Trajectory duration [seconds]
            dt: Time step [seconds]
        """
        self.trajectory_type = trajectory_type
        self.start_position = np.array(start_position, dtype=float)
        self.start_velocity = np.array(start_velocity, dtype=float)
        self.duration = duration
        self.dt = dt
        
        self.num_steps = int(duration / dt)
        self.ground_truth: List[State] = []
        
        # Generate trajectory
        self._generate()
    
    def _generate(self):
        """Generate ground truth trajectory."""
        if self.trajectory_type == TrajectoryType.STRAIGHT:
            self._generate_straight()
        elif self.trajectory_type == TrajectoryType.ZIGZAG:
            self._generate_zigzag()
        elif self.trajectory_type == TrajectoryType.CIRCULAR:
            self._generate_circular()
        elif self.trajectory_type == TrajectoryType.HOVER:
            self._generate_hover()
        elif self.trajectory_type == TrajectoryType.AGGRESSIVE_MANEUVER:
            self._generate_aggressive()
        elif self.trajectory_type == TrajectoryType.HOVER_AND_BURST:
            self._generate_hover_burst()
    
    def _generate_straight(self):
        """Straight line trajectory with constant velocity."""
        position = self.start_position.copy()
        velocity = self.start_velocity.copy()
        
        for step in range(self.num_steps):
            timestamp = step * self.dt
            
            state = State(
                vector=np.concatenate([position, velocity]),
                state_type=StateType.CV,
                timestamp=timestamp
            )
            self.ground_truth.append(state)
            
            # Update position
            position = position + velocity * self.dt
    
    def _generate_zigzag(self):
        """Zigzag trajectory with periodic direction changes."""
        position = self.start_position.copy()
        velocity = self.start_velocity.copy()
        
        zigzag_period = 5.0  # Change direction every 5 seconds
        zigzag_angle = np.radians(30)  # 30 degree turns
        
        for step in range(self.num_steps):
            timestamp = step * self.dt
            
            state = State(
                vector=np.concatenate([position, velocity]),
                state_type=StateType.CV,
                timestamp=timestamp
            )
            self.ground_truth.append(state)
            
            # Check if direction change needed
            if timestamp % zigzag_period < self.dt:
                # Rotate velocity in horizontal plane
                speed = np.linalg.norm(velocity[:2])
                current_heading = np.arctan2(velocity[1], velocity[0])
                
                # Alternate left/right
                turn_dir = 1 if (int(timestamp / zigzag_period) % 2) == 0 else -1
                new_heading = current_heading + turn_dir * zigzag_angle
                
                velocity[0] = speed * np.cos(new_heading)
                velocity[1] = speed * np.sin(new_heading)
            
            # Update position
            position = position + velocity * self.dt
    
    def _generate_circular(self):
        """Circular trajectory (coordinated turn)."""
        position = self.start_position.copy()
        velocity = self.start_velocity.copy()
        
        # Turn rate for circular motion
        speed = np.linalg.norm(velocity[:2])
        radius = 200.0  # 200m radius
        omega = speed / radius  # Angular velocity
        
        for step in range(self.num_steps):
            timestamp = step * self.dt
            
            state = State(
                vector=np.concatenate([position, velocity, [omega]]),
                state_type=StateType.CT,
                timestamp=timestamp
            )
            self.ground_truth.append(state)
            
            # Coordinated turn dynamics
            vx, vy, vz = velocity
            
            # Rotate velocity
            cos_omega_dt = np.cos(omega * self.dt)
            sin_omega_dt = np.sin(omega * self.dt)
            
            vx_new = vx * cos_omega_dt - vy * sin_omega_dt
            vy_new = vy * cos_omega_dt + vx * sin_omega_dt
            
            velocity = np.array([vx_new, vy_new, vz])
            
            # Update position
            position = position + velocity * self.dt
    
    def _generate_hover(self):
        """Hovering with small random drift."""
        position = self.start_position.copy()
        
        for step in range(self.num_steps):
            timestamp = step * self.dt
            
            # Small random drift
            drift = np.random.randn(3) * 0.5  # 0.5 m/s drift
            
            state = State(
                vector=np.concatenate([position, drift]),
                state_type=StateType.CV,
                timestamp=timestamp
            )
            self.ground_truth.append(state)
            
            # Update position with drift
            position = position + drift * self.dt
    
    def _generate_aggressive(self):
        """Aggressive maneuvering with high accelerations."""
        position = self.start_position.copy()
        velocity = self.start_velocity.copy()
        acceleration = np.zeros(3)
        
        maneuver_period = 3.0  # Change every 3 seconds
        
        for step in range(self.num_steps):
            timestamp = step * self.dt
            
            state = State(
                vector=np.concatenate([position, velocity, acceleration]),
                state_type=StateType.CA,
                timestamp=timestamp
            )
            self.ground_truth.append(state)
            
            # Random acceleration changes
            if timestamp % maneuver_period < self.dt:
                acceleration = np.random.randn(3) * 5.0  # Up to 5 m/s^2
                acceleration[2] *= 0.5  # Less vertical acceleration
            
            # Update velocity and position
            velocity = velocity + acceleration * self.dt
            position = position + velocity * self.dt + 0.5 * acceleration * self.dt**2
    
    def _generate_hover_burst(self):
        """Hover with sudden burst movements."""
        position = self.start_position.copy()
        velocity = np.zeros(3)
        
        hover_duration = 5.0
        burst_duration = 2.0
        burst_speed = 30.0  # m/s
        
        phase = 0  # 0: hover, 1: burst
        phase_start_time = 0.0
        burst_direction = None
        
        for step in range(self.num_steps):
            timestamp = step * self.dt
            
            # Phase switching
            if phase == 0 and (timestamp - phase_start_time) >= hover_duration:
                # Start burst
                phase = 1
                phase_start_time = timestamp
                burst_direction = np.random.randn(3)
                burst_direction[2] *= 0.3  # Mostly horizontal
                burst_direction = burst_direction / np.linalg.norm(burst_direction)
                velocity = burst_direction * burst_speed
            
            elif phase == 1 and (timestamp - phase_start_time) >= burst_duration:
                # Back to hover
                phase = 0
                phase_start_time = timestamp
                velocity = np.zeros(3)
            
            state = State(
                vector=np.concatenate([position, velocity]),
                state_type=StateType.CV,
                timestamp=timestamp
            )
            self.ground_truth.append(state)
            
            # Update position
            if phase == 0:
                # Hover with small drift
                velocity = np.random.randn(3) * 0.5
            
            position = position + velocity * self.dt
    
    def get_ground_truth(self) -> List[State]:
        """Get ground truth state sequence."""
        return self.ground_truth


class RadarSimulator:
    """
    Realistic radar measurement simulator.
    
    Simulates radar measurements with noise, clutter, and missed detections.
    """
    
    def __init__(self,
                 measurement_model: RadarMeasurementModel = None,
                 detection_probability: float = 0.95,
                 clutter_density: float = 1e-6,
                 snr_threshold: float = 10.0,
                 weather_noise_factor: float = 1.0):
        """
        Initialize radar simulator.
        
        Args:
            measurement_model: Radar measurement model
            detection_probability: Probability of detecting target (Pd)
            clutter_density: Clutter spatial density [detections/m^3]
            snr_threshold: SNR threshold for detection [dB]
            weather_noise_factor: Weather noise multiplier (1.0 = nominal)
        """
        self.measurement_model = measurement_model or RadarMeasurementModel()
        self.detection_probability = detection_probability
        self.clutter_density = clutter_density
        self.snr_threshold = snr_threshold
        self.weather_noise_factor = weather_noise_factor
        
        # Clutter model
        self.clutter_model = ClutterModel(clutter_density=clutter_density)
    
    def simulate_scan(self,
                     ground_truth_states: List[State],
                     timestamp: float,
                     range_limits: Tuple[float, float] = (100.0, 5000.0)) -> List[Measurement]:
        """
        Simulate single radar scan.
        
        Args:
            ground_truth_states: List of true target states
            timestamp: Scan timestamp
            range_limits: (min_range, max_range) in meters
            
        Returns:
            List of measurements (true detections + clutter)
        """
        measurements = []
        
        # Generate true detections
        for state in ground_truth_states:
            # Check if target is within range
            target_range = np.linalg.norm(state.position)
            if target_range < range_limits[0] or target_range > range_limits[1]:
                continue
            
            # Detection probability (range-dependent)
            pd = self._compute_detection_probability(state)
            
            if np.random.rand() < pd:
                # Generate measurement with noise
                measurement = self.measurement_model.predict_measurement(
                    state, add_noise=True
                )
                
                # Add weather noise
                if self.weather_noise_factor > 1.0:
                    measurement.range += np.random.normal(
                        0, 
                        self.measurement_model.range_std * (self.weather_noise_factor - 1.0)
                    )
                
                # Compute SNR
                measurement.snr = self._compute_snr(state)
                measurement.timestamp = timestamp
                measurement.confidence = min(pd, 0.99)
                
                measurements.append(measurement)
        
        # Generate clutter
        num_clutter = np.random.poisson(self.clutter_model.lambda_c * 0.01)  # Scale for scan
        clutter_measurements = self.clutter_model.generate_clutter(
            num_clutter,
            range_limits[0],
            range_limits[1],
            timestamp
        )
        measurements.extend(clutter_measurements)
        
        return measurements
    
    def _compute_detection_probability(self, state: State) -> float:
        """
        Compute detection probability based on target state.
        
        Factors:
        - Range (decreases with range)
        - RCS (assumed constant for drones)
        - Weather conditions
        """
        target_range = np.linalg.norm(state.position)
        
        # Range-dependent Pd (simple model)
        pd_range = self.detection_probability * np.exp(-(target_range / 5000.0)**2)
        
        # Weather degradation
        pd_weather = pd_range / self.weather_noise_factor
        
        return max(0.5, min(0.98, pd_weather))
    
    def _compute_snr(self, state: State) -> float:
        """
        Compute signal-to-noise ratio.
        
        Simple range-dependent model.
        """
        target_range = np.linalg.norm(state.position)
        
        # SNR decreases with range (radar equation: SNR ~ 1/R^4)
        snr_db = 40.0 - 40 * np.log10(target_range / 1000.0)
        
        # Add noise
        snr_db += np.random.normal(0, 2.0)
        
        return snr_db
    
    def simulate_scenario(self,
                         trajectories: List[DroneTrajectory],
                         scan_period: float = 0.1) -> Tuple[List[List[State]], List[List[Measurement]]]:
        """
        Simulate complete multi-target scenario.
        
        Args:
            trajectories: List of drone trajectories
            scan_period: Time between scans [seconds]
            
        Returns:
            (ground_truth_history, measurement_history)
            - ground_truth_history: List of state lists per time step
            - measurement_history: List of measurement lists per time step
        """
        # Determine scenario duration
        max_duration = max(traj.duration for traj in trajectories)
        num_scans = int(max_duration / scan_period)
        
        ground_truth_history = []
        measurement_history = []
        
        for scan_idx in range(num_scans):
            timestamp = scan_idx * scan_period
            
            # Collect ground truth states at this time
            current_states = []
            for traj in trajectories:
                gt_states = traj.get_ground_truth()
                time_idx = int(timestamp / traj.dt)
                
                if time_idx < len(gt_states):
                    current_states.append(gt_states[time_idx])
            
            ground_truth_history.append(current_states)
            
            # Generate measurements
            measurements = self.simulate_scan(current_states, timestamp)
            measurement_history.append(measurements)
        
        return ground_truth_history, measurement_history


def create_standard_scenarios() -> Dict[str, Tuple[List[DroneTrajectory], str]]:
    """
    Create standard test scenarios.
    
    Returns:
        Dictionary of scenario_name -> (trajectories, description)
    """
    scenarios = {}
    
    # Scenario 1: Single straight-line target
    scenarios['single_straight'] = (
        [DroneTrajectory(
            trajectory_type=TrajectoryType.STRAIGHT,
            start_position=np.array([1000.0, 0.0, 500.0]),
            start_velocity=np.array([30.0, 0.0, 0.0]),
            duration=30.0
        )],
        "Single drone, straight trajectory, 30 m/s"
    )
    
    # Scenario 2: Zigzag maneuver
    scenarios['single_zigzag'] = (
        [DroneTrajectory(
            trajectory_type=TrajectoryType.ZIGZAG,
            start_position=np.array([500.0, -500.0, 400.0]),
            start_velocity=np.array([25.0, 25.0, 0.0]),
            duration=40.0
        )],
        "Single drone, zigzag maneuvers"
    )
    
    # Scenario 3: Circular turn
    scenarios['single_circular'] = (
        [DroneTrajectory(
            trajectory_type=TrajectoryType.CIRCULAR,
            start_position=np.array([1000.0, 0.0, 600.0]),
            start_velocity=np.array([0.0, 30.0, 0.0]),
            duration=35.0
        )],
        "Single drone, circular trajectory"
    )
    
    # Scenario 4: Aggressive maneuver
    scenarios['single_aggressive'] = (
        [DroneTrajectory(
            trajectory_type=TrajectoryType.AGGRESSIVE_MANEUVER,
            start_position=np.array([800.0, 800.0, 500.0]),
            start_velocity=np.array([20.0, -10.0, 5.0]),
            duration=25.0
        )],
        "Single drone, aggressive maneuvers"
    )
    
    # Scenario 5: Hover and burst
    scenarios['hover_burst'] = (
        [DroneTrajectory(
            trajectory_type=TrajectoryType.HOVER_AND_BURST,
            start_position=np.array([1200.0, 0.0, 400.0]),
            start_velocity=np.array([0.0, 0.0, 0.0]),
            duration=30.0
        )],
        "Single drone, hover with burst movements"
    )
    
    # Scenario 6: Two targets - parallel
    scenarios['two_parallel'] = (
        [
            DroneTrajectory(
                trajectory_type=TrajectoryType.STRAIGHT,
                start_position=np.array([1000.0, -200.0, 500.0]),
                start_velocity=np.array([30.0, 0.0, 0.0]),
                duration=30.0
            ),
            DroneTrajectory(
                trajectory_type=TrajectoryType.STRAIGHT,
                start_position=np.array([1000.0, 200.0, 500.0]),
                start_velocity=np.array([30.0, 0.0, 0.0]),
                duration=30.0
            )
        ],
        "Two drones, parallel trajectories"
    )
    
    # Scenario 7: Track crossing
    scenarios['crossing'] = (
        [
            DroneTrajectory(
                trajectory_type=TrajectoryType.STRAIGHT,
                start_position=np.array([500.0, -500.0, 500.0]),
                start_velocity=np.array([25.0, 25.0, 0.0]),
                duration=30.0
            ),
            DroneTrajectory(
                trajectory_type=TrajectoryType.STRAIGHT,
                start_position=np.array([500.0, 500.0, 500.0]),
                start_velocity=np.array([25.0, -25.0, 0.0]),
                duration=30.0
            )
        ],
        "Two drones, crossing trajectories"
    )
    
    # Scenario 8: Complex multi-target
    scenarios['multi_complex'] = (
        [
            DroneTrajectory(
                trajectory_type=TrajectoryType.STRAIGHT,
                start_position=np.array([1000.0, 0.0, 500.0]),
                start_velocity=np.array([30.0, 0.0, 0.0]),
                duration=35.0
            ),
            DroneTrajectory(
                trajectory_type=TrajectoryType.CIRCULAR,
                start_position=np.array([800.0, 800.0, 600.0]),
                start_velocity=np.array([0.0, 25.0, 0.0]),
                duration=35.0
            ),
            DroneTrajectory(
                trajectory_type=TrajectoryType.ZIGZAG,
                start_position=np.array([1200.0, -400.0, 400.0]),
                start_velocity=np.array([20.0, 20.0, 0.0]),
                duration=35.0
            )
        ],
        "Three drones, mixed trajectories"
    )
    
    return scenarios
