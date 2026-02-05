"""
Motion Models for Drone Tracking

Implements:
1. Constant Velocity (CV) Model
2. Constant Acceleration (CA) Model  
3. Coordinated Turn (CT) Model
4. Adaptive IMM-style model switching

Each model provides:
- State transition matrix F(dt)
- Process noise covariance Q(dt)
- State propagation function
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple
from ..core.state import State, StateType


class MotionModel(ABC):
    """Abstract base class for motion models."""
    
    @abstractmethod
    def propagate(self, state: State, dt: float, process_noise: bool = True) -> State:
        """
        Propagate state forward by dt seconds.
        
        Args:
            state: Current state
            dt: Time step [seconds]
            process_noise: Add process noise if True
            
        Returns:
            Propagated state
        """
        pass
    
    @abstractmethod
    def get_process_noise_covariance(self, dt: float) -> np.ndarray:
        """
        Get process noise covariance matrix Q for time step dt.
        
        Args:
            dt: Time step [seconds]
            
        Returns:
            Process noise covariance matrix Q
        """
        pass
    
    @abstractmethod
    def get_state_dim(self) -> int:
        """Get state vector dimension."""
        pass


class ConstantVelocityModel(MotionModel):
    """
    Constant Velocity (CV) Motion Model
    
    State: [x, y, z, vx, vy, vz]
    
    Dynamics:
        x(t+dt) = x(t) + vx*dt
        vx(t+dt) = vx(t) + noise
    
    Process noise: White noise acceleration
    """
    
    def __init__(self, process_noise_std: float = 1.0):
        """
        Initialize CV model.
        
        Args:
            process_noise_std: Process noise standard deviation [m/s^2]
        """
        self.process_noise_std = process_noise_std
        self.state_type = StateType.CV
        
    def get_state_dim(self) -> int:
        return 6
    
    def get_transition_matrix(self, dt: float) -> np.ndarray:
        """
        Get state transition matrix F for CV model.
        
        F = [I3  dt*I3]
            [0   I3   ]
        """
        F = np.eye(6)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt
        return F
    
    def get_process_noise_covariance(self, dt: float) -> np.ndarray:
        """
        Discrete white noise acceleration model.
        
        Q = sigma^2 * [dt^3/3*I3  dt^2/2*I3]
                      [dt^2/2*I3  dt*I3    ]
        """
        q = self.process_noise_std ** 2
        dt2 = dt * dt
        dt3 = dt2 * dt
        
        Q = np.zeros((6, 6))
        
        # Position-position block
        Q[0:3, 0:3] = np.eye(3) * (dt3 / 3.0) * q
        
        # Position-velocity block
        Q[0:3, 3:6] = np.eye(3) * (dt2 / 2.0) * q
        Q[3:6, 0:3] = np.eye(3) * (dt2 / 2.0) * q
        
        # Velocity-velocity block
        Q[3:6, 3:6] = np.eye(3) * dt * q
        
        return Q
    
    def propagate(self, state: State, dt: float, process_noise: bool = True) -> State:
        """Propagate state using CV model."""
        F = self.get_transition_matrix(dt)
        new_vector = F @ state.vector[:6]
        
        if process_noise:
            Q = self.get_process_noise_covariance(dt)
            noise = np.random.multivariate_normal(np.zeros(6), Q)
            new_vector += noise
        
        return State(
            vector=new_vector,
            state_type=self.state_type,
            timestamp=state.timestamp + dt
        )


class ConstantAccelerationModel(MotionModel):
    """
    Constant Acceleration (CA) Motion Model
    
    State: [x, y, z, vx, vy, vz, ax, ay, az]
    
    Dynamics:
        x(t+dt) = x(t) + vx*dt + 0.5*ax*dt^2
        vx(t+dt) = vx(t) + ax*dt
        ax(t+dt) = ax(t) + noise
    
    Better for maneuvering targets.
    """
    
    def __init__(self, process_noise_std: float = 2.0):
        """
        Initialize CA model.
        
        Args:
            process_noise_std: Process noise standard deviation [m/s^3]
        """
        self.process_noise_std = process_noise_std
        self.state_type = StateType.CA
        
    def get_state_dim(self) -> int:
        return 9
    
    def get_transition_matrix(self, dt: float) -> np.ndarray:
        """
        Get state transition matrix F for CA model.
        
        F = [I3  dt*I3  0.5*dt^2*I3]
            [0   I3     dt*I3      ]
            [0   0      I3         ]
        """
        F = np.eye(9)
        dt2 = dt * dt
        
        # Position-velocity coupling
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt
        
        # Position-acceleration coupling
        F[0, 6] = 0.5 * dt2
        F[1, 7] = 0.5 * dt2
        F[2, 8] = 0.5 * dt2
        
        # Velocity-acceleration coupling
        F[3, 6] = dt
        F[4, 7] = dt
        F[5, 8] = dt
        
        return F
    
    def get_process_noise_covariance(self, dt: float) -> np.ndarray:
        """
        Discrete white noise jerk model.
        
        Process noise affects acceleration states.
        """
        q = self.process_noise_std ** 2
        dt2 = dt * dt
        dt3 = dt2 * dt
        dt4 = dt3 * dt
        
        Q = np.zeros((9, 9))
        
        # Position block
        Q[0:3, 0:3] = np.eye(3) * (dt4 / 4.0) * q
        Q[0:3, 3:6] = np.eye(3) * (dt3 / 2.0) * q
        Q[0:3, 6:9] = np.eye(3) * (dt2 / 2.0) * q
        
        # Velocity block
        Q[3:6, 0:3] = np.eye(3) * (dt3 / 2.0) * q
        Q[3:6, 3:6] = np.eye(3) * dt2 * q
        Q[3:6, 6:9] = np.eye(3) * dt * q
        
        # Acceleration block
        Q[6:9, 0:3] = np.eye(3) * (dt2 / 2.0) * q
        Q[6:9, 3:6] = np.eye(3) * dt * q
        Q[6:9, 6:9] = np.eye(3) * q
        
        return Q
    
    def propagate(self, state: State, dt: float, process_noise: bool = True) -> State:
        """Propagate state using CA model."""
        # Ensure state is 9D
        if len(state.vector) == 6:
            # Convert from CV to CA
            state_vector = np.concatenate([state.vector, np.zeros(3)])
        else:
            state_vector = state.vector[:9]
        
        F = self.get_transition_matrix(dt)
        new_vector = F @ state_vector
        
        if process_noise:
            Q = self.get_process_noise_covariance(dt)
            noise = np.random.multivariate_normal(np.zeros(9), Q)
            new_vector += noise
        
        return State(
            vector=new_vector,
            state_type=self.state_type,
            timestamp=state.timestamp + dt
        )


class CoordinatedTurnModel(MotionModel):
    """
    Coordinated Turn (CT) Motion Model
    
    State: [x, y, z, vx, vy, vz, omega]
    
    Dynamics (horizontal plane):
        x(t+dt) = x(t) + (vx/omega)*sin(omega*dt) + (vy/omega)*(cos(omega*dt)-1)
        vx(t+dt) = vx*cos(omega*dt) - vy*sin(omega*dt)
        omega(t+dt) = omega + noise
    
    Vertical motion uses CV model.
    
    Excellent for banking turns and circular motion.
    """
    
    def __init__(self, process_noise_std: float = 1.0, 
                 turn_rate_noise_std: float = 0.1):
        """
        Initialize CT model.
        
        Args:
            process_noise_std: Process noise for velocity [m/s^2]
            turn_rate_noise_std: Process noise for turn rate [rad/s^2]
        """
        self.process_noise_std = process_noise_std
        self.turn_rate_noise_std = turn_rate_noise_std
        self.state_type = StateType.CT
        
    def get_state_dim(self) -> int:
        return 7
    
    def get_process_noise_covariance(self, dt: float) -> np.ndarray:
        """Process noise covariance for CT model."""
        Q = np.zeros((7, 7))
        
        # Position and velocity noise (simplified)
        q_vel = self.process_noise_std ** 2
        Q[0:3, 0:3] = np.eye(3) * (dt**3 / 3.0) * q_vel
        Q[3:6, 3:6] = np.eye(3) * dt * q_vel
        
        # Turn rate noise
        Q[6, 6] = self.turn_rate_noise_std ** 2 * dt
        
        return Q
    
    def propagate(self, state: State, dt: float, process_noise: bool = True) -> State:
        """
        Propagate state using CT model with non-linear dynamics.
        """
        # Ensure state is 7D
        if len(state.vector) == 6:
            # Convert from CV to CT (assume zero turn rate initially)
            state_vector = np.concatenate([state.vector, [0.0]])
        else:
            state_vector = state.vector[:7].copy()
        
        x, y, z, vx, vy, vz, omega = state_vector
        
        # Small turn rate threshold (switch to CV model)
        omega_threshold = 1e-4
        
        if abs(omega) > omega_threshold:
            # Non-linear coordinated turn
            sin_omega_dt = np.sin(omega * dt)
            cos_omega_dt = np.cos(omega * dt)
            
            # Update position (horizontal plane)
            x_new = x + (vx / omega) * sin_omega_dt - (vy / omega) * (1 - cos_omega_dt)
            y_new = y + (vy / omega) * sin_omega_dt + (vx / omega) * (1 - cos_omega_dt)
            z_new = z + vz * dt  # Vertical uses CV
            
            # Update velocity (rotation in horizontal plane)
            vx_new = vx * cos_omega_dt - vy * sin_omega_dt
            vy_new = vy * cos_omega_dt + vx * sin_omega_dt
            vz_new = vz
            
        else:
            # Fall back to CV model for near-zero turn rate
            x_new = x + vx * dt
            y_new = y + vy * dt
            z_new = z + vz * dt
            vx_new = vx
            vy_new = vy
            vz_new = vz
        
        omega_new = omega
        
        new_vector = np.array([x_new, y_new, z_new, vx_new, vy_new, vz_new, omega_new])
        
        if process_noise:
            Q = self.get_process_noise_covariance(dt)
            noise = np.random.multivariate_normal(np.zeros(7), Q)
            new_vector += noise
        
        return State(
            vector=new_vector,
            state_type=self.state_type,
            timestamp=state.timestamp + dt
        )


class AdaptiveMotionModel:
    """
    Adaptive motion model that switches between CV, CA, and CT
    based on motion characteristics.
    
    Uses a simple IMM-like approach for model selection.
    """
    
    def __init__(self):
        self.cv_model = ConstantVelocityModel(process_noise_std=1.0)
        self.ca_model = ConstantAccelerationModel(process_noise_std=2.0)
        self.ct_model = CoordinatedTurnModel(process_noise_std=1.0)
        
        # Model probabilities (uniform initially)
        self.model_probs = {
            StateType.CV: 0.33,
            StateType.CA: 0.33,
            StateType.CT: 0.34
        }
        
    def select_model(self, state: State) -> MotionModel:
        """
        Select best motion model based on state characteristics.
        
        Heuristics:
        - High speed change -> CA
        - Lateral acceleration -> CT
        - Steady motion -> CV
        """
        # Simple heuristic: use acceleration magnitude
        if state.type == StateType.CA:
            acc_mag = np.linalg.norm(state.acceleration)
            if acc_mag > 5.0:  # High acceleration
                return self.ca_model
        
        # Check for turning (if CT state)
        if state.type == StateType.CT:
            if abs(state.turn_rate) > 0.1:  # Significant turn
                return self.ct_model
        
        # Default to CV for steady state
        return self.cv_model
    
    def propagate(self, state: State, dt: float, 
                  model_type: StateType = None) -> State:
        """
        Propagate using specified or auto-selected model.
        """
        if model_type is None:
            model = self.select_model(state)
        else:
            if model_type == StateType.CV:
                model = self.cv_model
            elif model_type == StateType.CA:
                model = self.ca_model
            else:
                model = self.ct_model
        
        return model.propagate(state, dt, process_noise=True)
