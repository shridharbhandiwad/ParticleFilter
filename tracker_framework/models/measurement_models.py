"""
Measurement Models for Radar Tracking

Implements:
1. Cartesian to Spherical conversion
2. Measurement likelihood computation
3. Measurement gating
4. Clutter rejection

Radar accuracies:
- Azimuth: < 0.3°
- Elevation: < 0.3°
- Range: 3-5 meters
"""

import numpy as np
from typing import Tuple, Optional
from ..core.state import State, Measurement


class RadarMeasurementModel:
    """
    Radar measurement model in spherical coordinates.
    
    h(x) = [r, az, el, r_dot]^T
    
    where:
        r = sqrt(x^2 + y^2 + z^2)
        az = atan2(y, x)
        el = atan2(z, sqrt(x^2 + y^2))
        r_dot = (x*vx + y*vy + z*vz) / r
    """
    
    def __init__(self, 
                 range_std: float = 4.0,
                 azimuth_std_deg: float = 0.3,
                 elevation_std_deg: float = 0.3,
                 range_rate_std: float = 1.0):
        """
        Initialize radar measurement model.
        
        Args:
            range_std: Range measurement standard deviation [meters]
            azimuth_std_deg: Azimuth standard deviation [degrees]
            elevation_std_deg: Elevation standard deviation [degrees]
            range_rate_std: Range rate standard deviation [m/s]
        """
        self.range_std = range_std
        self.azimuth_std = np.radians(azimuth_std_deg)
        self.elevation_std = np.radians(elevation_std_deg)
        self.range_rate_std = range_rate_std
        
        # Measurement noise covariance matrix
        self.R = np.diag([
            range_std ** 2,
            self.azimuth_std ** 2,
            self.elevation_std ** 2,
            range_rate_std ** 2
        ])
        
        # Measurement noise in Cartesian (approximate)
        self.R_cartesian = self._compute_cartesian_covariance(1000.0)  # At 1km range
        
    def _compute_cartesian_covariance(self, range_val: float) -> np.ndarray:
        """
        Compute approximate Cartesian measurement covariance.
        
        Linearized approximation of spherical->Cartesian transformation.
        """
        # Simplified: position covariance in Cartesian
        # sigma_x ≈ sigma_r, sigma_y ≈ r*sigma_az, sigma_z ≈ r*sigma_el
        
        sigma_x = self.range_std
        sigma_y = range_val * self.azimuth_std
        sigma_z = range_val * self.elevation_std
        
        R_cart = np.diag([sigma_x**2, sigma_y**2, sigma_z**2])
        return R_cart
    
    def predict_measurement(self, state: State, 
                           add_noise: bool = False) -> Measurement:
        """
        Predict measurement from state (forward model).
        
        h(x): state -> measurement
        
        Args:
            state: Current state
            add_noise: Add measurement noise if True
            
        Returns:
            Predicted measurement
        """
        pos = state.position
        vel = state.velocity
        
        # Range
        r = np.linalg.norm(pos)
        
        # Avoid division by zero
        if r < 1e-6:
            r = 1e-6
        
        # Azimuth
        az = np.arctan2(pos[1], pos[0])
        
        # Elevation
        el = np.arctan2(pos[2], np.sqrt(pos[0]**2 + pos[1]**2))
        
        # Range rate (radial velocity)
        r_dot = np.dot(pos, vel) / r
        
        if add_noise:
            # Add measurement noise
            r += np.random.normal(0, self.range_std)
            az += np.random.normal(0, self.azimuth_std)
            el += np.random.normal(0, self.elevation_std)
            r_dot += np.random.normal(0, self.range_rate_std)
        
        return Measurement(
            range=r,
            azimuth=az,
            elevation=el,
            range_rate=r_dot,
            timestamp=state.timestamp
        )
    
    def compute_likelihood(self, measurement: Measurement, 
                          state: State) -> float:
        """
        Compute measurement likelihood p(z|x).
        
        Uses Gaussian likelihood in measurement space.
        
        Args:
            measurement: Observed measurement
            state: Predicted state
            
        Returns:
            Likelihood value (not normalized)
        """
        # Predict measurement from state
        predicted = self.predict_measurement(state, add_noise=False)
        
        # Innovation (measurement residual)
        innovation = np.array([
            measurement.range - predicted.range,
            self._angle_diff(measurement.azimuth, predicted.azimuth),
            self._angle_diff(measurement.elevation, predicted.elevation),
            (measurement.range_rate or 0.0) - predicted.range_rate
        ])
        
        # Mahalanobis distance
        try:
            R_inv = np.linalg.inv(self.R)
            mahalanobis_dist_sq = innovation.T @ R_inv @ innovation
            
            # Gaussian likelihood (unnormalized)
            likelihood = np.exp(-0.5 * mahalanobis_dist_sq)
            
        except np.linalg.LinAlgError:
            # Fallback: use simple Euclidean distance
            dist_sq = np.sum(innovation ** 2)
            likelihood = np.exp(-0.5 * dist_sq)
        
        return likelihood
    
    def compute_likelihood_cartesian(self, measurement: Measurement,
                                    state: State) -> float:
        """
        Compute likelihood in Cartesian space (alternative).
        
        Sometimes more numerically stable than spherical.
        """
        meas_pos = measurement.to_cartesian()
        pred_pos = state.position
        
        diff = meas_pos - pred_pos
        
        # Use range-dependent covariance
        R_cart = self._compute_cartesian_covariance(measurement.range)
        
        try:
            R_inv = np.linalg.inv(R_cart)
            mahalanobis_dist_sq = diff.T @ R_inv @ diff
            likelihood = np.exp(-0.5 * mahalanobis_dist_sq)
        except np.linalg.LinAlgError:
            dist_sq = np.sum(diff ** 2)
            likelihood = np.exp(-0.5 * dist_sq / (self.range_std ** 2))
        
        return likelihood
    
    def gate_measurement(self, measurement: Measurement, 
                        state: State, 
                        gate_threshold: float = 9.21) -> bool:
        """
        Measurement gating using chi-squared test.
        
        Args:
            measurement: Observed measurement
            state: Predicted state
            gate_threshold: Chi-squared threshold (default: 95% confidence, 4 DOF)
            
        Returns:
            True if measurement passes gate
        """
        predicted = self.predict_measurement(state, add_noise=False)
        
        innovation = np.array([
            measurement.range - predicted.range,
            self._angle_diff(measurement.azimuth, predicted.azimuth),
            self._angle_diff(measurement.elevation, predicted.elevation),
            (measurement.range_rate or 0.0) - predicted.range_rate
        ])
        
        try:
            R_inv = np.linalg.inv(self.R)
            mahalanobis_dist_sq = innovation.T @ R_inv @ innovation
            
            return mahalanobis_dist_sq < gate_threshold
        except np.linalg.LinAlgError:
            # Fallback: use simple distance
            return np.linalg.norm(innovation[:3]) < 3 * self.range_std
    
    def innovation_vector(self, measurement: Measurement,
                         state: State) -> np.ndarray:
        """
        Compute innovation (residual) vector.
        
        nu = z - h(x)
        """
        predicted = self.predict_measurement(state, add_noise=False)
        
        innovation = np.array([
            measurement.range - predicted.range,
            self._angle_diff(measurement.azimuth, predicted.azimuth),
            self._angle_diff(measurement.elevation, predicted.elevation),
            (measurement.range_rate or 0.0) - predicted.range_rate
        ])
        
        return innovation
    
    @staticmethod
    def _angle_diff(angle1: float, angle2: float) -> float:
        """
        Compute smallest angle difference (wrap around).
        
        Returns difference in [-pi, pi].
        """
        diff = angle1 - angle2
        while diff > np.pi:
            diff -= 2 * np.pi
        while diff < -np.pi:
            diff += 2 * np.pi
        return diff
    
    def get_measurement_covariance(self) -> np.ndarray:
        """Get measurement noise covariance matrix."""
        return self.R.copy()


class ClutterModel:
    """
    Clutter and false alarm model.
    
    Models random false detections in the surveillance volume.
    """
    
    def __init__(self, 
                 clutter_density: float = 1e-6,
                 surveillance_volume: float = 1e9):
        """
        Initialize clutter model.
        
        Args:
            clutter_density: Clutter spatial density [detections/m^3]
            surveillance_volume: Surveillance volume [m^3]
        """
        self.clutter_density = clutter_density
        self.surveillance_volume = surveillance_volume
        
        # Expected number of clutter returns per scan
        self.lambda_c = clutter_density * surveillance_volume
    
    def get_clutter_likelihood(self) -> float:
        """
        Get likelihood of measurement being clutter.
        
        Assumes uniform spatial distribution.
        """
        return self.clutter_density
    
    def generate_clutter(self, num_clutter: int,
                        range_min: float = 100.0,
                        range_max: float = 5000.0,
                        timestamp: float = 0.0) -> list:
        """
        Generate random clutter measurements.
        
        Args:
            num_clutter: Number of clutter returns
            range_min: Minimum range [m]
            range_max: Maximum range [m]
            timestamp: Time stamp
            
        Returns:
            List of clutter Measurements
        """
        clutter_list = []
        
        for _ in range(num_clutter):
            r = np.random.uniform(range_min, range_max)
            az = np.random.uniform(-np.pi, np.pi)
            el = np.random.uniform(-np.pi/4, np.pi/4)  # +/- 45 degrees
            
            meas = Measurement(
                range=r,
                azimuth=az,
                elevation=el,
                timestamp=timestamp,
                confidence=0.3  # Low confidence for clutter
            )
            clutter_list.append(meas)
        
        return clutter_list
