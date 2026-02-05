"""
State Vector Definitions for Drone Tracking

State representation for multi-model tracking:
- Position (x, y, z) in Cartesian coordinates [meters]
- Velocity (vx, vy, vz) [m/s]
- Acceleration (ax, ay, az) [m/s^2] - for CA model
- Turn rate (omega) [rad/s] - for CT model
"""

import numpy as np
from enum import Enum
from typing import Dict, Any


class StateType(Enum):
    """State vector types for different motion models."""
    CV = "constant_velocity"  # 6D: [x, y, z, vx, vy, vz]
    CA = "constant_acceleration"  # 9D: [x, y, z, vx, vy, vz, ax, ay, az]
    CT = "coordinated_turn"  # 7D: [x, y, z, vx, vy, vz, omega]


class State:
    """
    Unified state representation for particle filter tracking.
    
    Attributes:
        vector: State vector (numpy array)
        type: StateType enum
        timestamp: Time stamp [seconds]
        covariance: State covariance matrix (optional)
    """
    
    def __init__(self, vector: np.ndarray, state_type: StateType, 
                 timestamp: float = 0.0, covariance: np.ndarray = None):
        """
        Initialize state.
        
        Args:
            vector: State vector
            state_type: Type of state (CV, CA, CT)
            timestamp: Time in seconds
            covariance: Covariance matrix (optional)
        """
        self.vector = np.array(vector, dtype=np.float64)
        self.type = state_type
        self.timestamp = timestamp
        self.covariance = covariance
        
    @property
    def position(self) -> np.ndarray:
        """Get position [x, y, z]."""
        return self.vector[:3]
    
    @property
    def velocity(self) -> np.ndarray:
        """Get velocity [vx, vy, vz]."""
        return self.vector[3:6]
    
    @property
    def acceleration(self) -> np.ndarray:
        """Get acceleration [ax, ay, az] (CA model only)."""
        if self.type == StateType.CA:
            return self.vector[6:9]
        return np.zeros(3)
    
    @property
    def turn_rate(self) -> float:
        """Get turn rate omega (CT model only)."""
        if self.type == StateType.CT:
            return self.vector[6]
        return 0.0
    
    @property
    def speed(self) -> float:
        """Get scalar speed."""
        return np.linalg.norm(self.velocity)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'vector': self.vector.tolist(),
            'type': self.type.value,
            'timestamp': self.timestamp,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'speed': self.speed
        }
    
    def copy(self):
        """Create a deep copy of the state."""
        return State(
            vector=self.vector.copy(),
            state_type=self.type,
            timestamp=self.timestamp,
            covariance=self.covariance.copy() if self.covariance is not None else None
        )
    
    def __repr__(self) -> str:
        return (f"State(type={self.type.value}, t={self.timestamp:.2f}s, "
                f"pos=[{self.position[0]:.1f}, {self.position[1]:.1f}, {self.position[2]:.1f}], "
                f"speed={self.speed:.1f}m/s)")


class Measurement:
    """
    Radar measurement in spherical coordinates.
    
    Attributes:
        range: Range [meters]
        azimuth: Azimuth angle [radians]
        elevation: Elevation angle [radians]
        range_rate: Radial velocity [m/s] (optional)
        snr: Signal-to-noise ratio [dB] (optional)
        timestamp: Time stamp [seconds]
        confidence: Detection confidence [0-1]
    """
    
    def __init__(self, range: float, azimuth: float, elevation: float,
                 range_rate: float = None, snr: float = None,
                 timestamp: float = 0.0, confidence: float = 1.0):
        """
        Initialize radar measurement.
        
        Args:
            range: Range in meters
            azimuth: Azimuth in radians
            elevation: Elevation in radians
            range_rate: Radial velocity in m/s (optional)
            snr: Signal-to-noise ratio in dB (optional)
            timestamp: Time in seconds
            confidence: Detection confidence (0-1)
        """
        self.range = range
        self.azimuth = azimuth
        self.elevation = elevation
        self.range_rate = range_rate
        self.snr = snr
        self.timestamp = timestamp
        self.confidence = confidence
        
    def to_cartesian(self) -> np.ndarray:
        """
        Convert spherical to Cartesian coordinates.
        
        Returns:
            Position vector [x, y, z] in meters
        """
        x = self.range * np.cos(self.elevation) * np.cos(self.azimuth)
        y = self.range * np.cos(self.elevation) * np.sin(self.azimuth)
        z = self.range * np.sin(self.elevation)
        return np.array([x, y, z])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        cartesian = self.to_cartesian()
        return {
            'range': self.range,
            'azimuth': np.degrees(self.azimuth),
            'elevation': np.degrees(self.elevation),
            'range_rate': self.range_rate,
            'snr': self.snr,
            'timestamp': self.timestamp,
            'confidence': self.confidence,
            'cartesian': cartesian.tolist()
        }
    
    def __repr__(self) -> str:
        return (f"Measurement(r={self.range:.1f}m, "
                f"az={np.degrees(self.azimuth):.1f}°, "
                f"el={np.degrees(self.elevation):.1f}°, "
                f"t={self.timestamp:.2f}s)")
