"""
Particle Filter Implementation for Drone Tracking

Core particle filter with:
- Sequential Importance Resampling (SIR)
- Multiple resampling strategies
- Adaptive particle count
- Degeneracy detection and mitigation
- Track quality assessment
"""

import numpy as np
from typing import List, Optional, Tuple
from enum import Enum
from ..core.state import State, Measurement, StateType
from ..models.motion_models import MotionModel, ConstantVelocityModel
from ..models.measurement_models import RadarMeasurementModel, ClutterModel


class ResamplingStrategy(Enum):
    """Resampling strategies for particle filter."""
    MULTINOMIAL = "multinomial"
    SYSTEMATIC = "systematic"
    STRATIFIED = "stratified"
    RESIDUAL = "residual"


class ParticleFilter:
    """
    Sequential Importance Resampling (SIR) Particle Filter.
    
    Algorithm:
    1. Prediction: Propagate particles using motion model
    2. Update: Compute importance weights from measurements
    3. Resampling: Resample particles based on weights
    4. Estimation: Compute state estimate from particles
    """
    
    def __init__(self,
                 num_particles: int = 1000,
                 motion_model: MotionModel = None,
                 measurement_model: RadarMeasurementModel = None,
                 resampling_strategy: ResamplingStrategy = ResamplingStrategy.SYSTEMATIC,
                 resampling_threshold: float = 0.5,
                 state_type: StateType = StateType.CV):
        """
        Initialize particle filter.
        
        Args:
            num_particles: Number of particles
            motion_model: Motion model for prediction
            measurement_model: Measurement model for update
            resampling_strategy: Resampling method
            resampling_threshold: Threshold for effective sample size
            state_type: State vector type
        """
        self.num_particles = num_particles
        self.state_type = state_type
        
        # Models
        self.motion_model = motion_model or ConstantVelocityModel()
        self.measurement_model = measurement_model or RadarMeasurementModel()
        
        # Resampling
        self.resampling_strategy = resampling_strategy
        self.resampling_threshold = resampling_threshold
        
        # Particles: list of State objects
        self.particles: List[State] = []
        
        # Weights: normalized importance weights
        self.weights = np.ones(num_particles) / num_particles
        
        # State estimate
        self.state_estimate: Optional[State] = None
        
        # Track quality metrics
        self.effective_sample_size = num_particles
        self.track_quality = 1.0
        self.consecutive_misses = 0
        
        # Clutter model
        self.clutter_model = ClutterModel()
        
    def initialize(self, initial_state: State, 
                  initial_covariance: np.ndarray = None):
        """
        Initialize particle cloud around initial state.
        
        Args:
            initial_state: Initial state estimate
            initial_covariance: Initial covariance (for particle spread)
        """
        state_dim = len(initial_state.vector)
        
        if initial_covariance is None:
            # Default covariance
            initial_covariance = np.eye(state_dim)
            initial_covariance[0:3, 0:3] *= 100.0  # 10m position std
            initial_covariance[3:6, 3:6] *= 25.0   # 5 m/s velocity std
        
        # Generate particles from Gaussian distribution
        self.particles = []
        for _ in range(self.num_particles):
            noise = np.random.multivariate_normal(
                np.zeros(state_dim), 
                initial_covariance
            )
            particle_vector = initial_state.vector + noise
            
            particle = State(
                vector=particle_vector,
                state_type=self.state_type,
                timestamp=initial_state.timestamp
            )
            self.particles.append(particle)
        
        # Uniform weights initially
        self.weights = np.ones(self.num_particles) / self.num_particles
        
        # Set initial estimate
        self.state_estimate = initial_state.copy()
        
    def predict(self, dt: float):
        """
        Prediction step: Propagate particles using motion model.
        
        x_k|k-1 = f(x_k-1|k-1, w_k)
        
        Args:
            dt: Time step [seconds]
        """
        for i in range(len(self.particles)):
            self.particles[i] = self.motion_model.propagate(
                self.particles[i], 
                dt, 
                process_noise=True
            )
    
    def update(self, measurement: Measurement,
              detection_probability: float = 0.95,
              use_cartesian: bool = False):
        """
        Update step: Compute importance weights based on measurement.
        
        w_k = w_k-1 * p(z_k | x_k)
        
        Args:
            measurement: Radar measurement
            detection_probability: Probability of detection (Pd)
            use_cartesian: Use Cartesian likelihood if True
        """
        # Compute likelihoods for all particles
        likelihoods = np.zeros(self.num_particles)
        
        for i, particle in enumerate(self.particles):
            if use_cartesian:
                likelihood = self.measurement_model.compute_likelihood_cartesian(
                    measurement, particle
                )
            else:
                likelihood = self.measurement_model.compute_likelihood(
                    measurement, particle
                )
            
            likelihoods[i] = likelihood
        
        # Incorporate detection probability and clutter
        # PDAF-like update: p(z|x) = Pd * p_true(z|x) + (1-Pd) * p_clutter(z)
        p_clutter = self.clutter_model.get_clutter_likelihood()
        
        # Update weights (element-wise multiplication)
        self.weights *= (detection_probability * likelihoods + 
                        (1 - detection_probability) * p_clutter)
        
        # Normalize weights
        weight_sum = np.sum(self.weights)
        if weight_sum > 1e-15:
            self.weights /= weight_sum
            self.consecutive_misses = 0
        else:
            # All weights near zero - measurement very unlikely
            # Reset to uniform
            self.weights = np.ones(self.num_particles) / self.num_particles
            self.consecutive_misses += 1
        
        # Compute effective sample size
        self.effective_sample_size = 1.0 / np.sum(self.weights ** 2)
        
        # Update track quality
        self._update_track_quality()
        
    def resample(self, force: bool = False):
        """
        Resample particles based on importance weights.
        
        Resampling triggered when effective sample size drops below threshold.
        
        Args:
            force: Force resampling regardless of ESS
        """
        # Check if resampling needed
        ess_ratio = self.effective_sample_size / self.num_particles
        
        if not force and ess_ratio > self.resampling_threshold:
            return  # No resampling needed
        
        # Perform resampling based on strategy
        if self.resampling_strategy == ResamplingStrategy.MULTINOMIAL:
            indices = self._multinomial_resample()
        elif self.resampling_strategy == ResamplingStrategy.SYSTEMATIC:
            indices = self._systematic_resample()
        elif self.resampling_strategy == ResamplingStrategy.STRATIFIED:
            indices = self._stratified_resample()
        elif self.resampling_strategy == ResamplingStrategy.RESIDUAL:
            indices = self._residual_resample()
        else:
            indices = self._systematic_resample()
        
        # Resample particles
        self.particles = [self.particles[i].copy() for i in indices]
        
        # Reset weights to uniform
        self.weights = np.ones(self.num_particles) / self.num_particles
        
        # Reset effective sample size
        self.effective_sample_size = self.num_particles
    
    def estimate(self) -> State:
        """
        Compute state estimate from particle cloud.
        
        Uses weighted mean of particles.
        
        Returns:
            Estimated state
        """
        # Weighted mean
        state_dim = len(self.particles[0].vector)
        mean_vector = np.zeros(state_dim)
        
        for i, particle in enumerate(self.particles):
            mean_vector += self.weights[i] * particle.vector
        
        # Create state estimate
        self.state_estimate = State(
            vector=mean_vector,
            state_type=self.state_type,
            timestamp=self.particles[0].timestamp
        )
        
        return self.state_estimate
    
    def estimate_covariance(self) -> np.ndarray:
        """
        Estimate state covariance from particle cloud.
        
        Returns:
            Covariance matrix
        """
        state_dim = len(self.particles[0].vector)
        mean_vector = self.state_estimate.vector
        
        covariance = np.zeros((state_dim, state_dim))
        
        for i, particle in enumerate(self.particles):
            diff = particle.vector - mean_vector
            covariance += self.weights[i] * np.outer(diff, diff)
        
        return covariance
    
    # ========== Resampling Algorithms ==========
    
    def _multinomial_resample(self) -> np.ndarray:
        """
        Multinomial resampling (simple but high variance).
        
        Draw N samples from categorical distribution defined by weights.
        """
        indices = np.random.choice(
            self.num_particles,
            size=self.num_particles,
            replace=True,
            p=self.weights
        )
        return indices
    
    def _systematic_resample(self) -> np.ndarray:
        """
        Systematic resampling (low variance, recommended).
        
        Deterministic selection with single random offset.
        """
        indices = np.zeros(self.num_particles, dtype=int)
        
        # Cumulative sum of weights
        cumsum = np.cumsum(self.weights)
        
        # Starting point
        u0 = np.random.uniform(0, 1.0 / self.num_particles)
        
        j = 0
        for i in range(self.num_particles):
            u = u0 + i / self.num_particles
            
            # Find first index where cumsum >= u
            while j < self.num_particles and cumsum[j] < u:
                j += 1
            
            indices[i] = min(j, self.num_particles - 1)
        
        return indices
    
    def _stratified_resample(self) -> np.ndarray:
        """
        Stratified resampling (low variance).
        
        Random sample within each stratum.
        """
        indices = np.zeros(self.num_particles, dtype=int)
        cumsum = np.cumsum(self.weights)
        
        j = 0
        for i in range(self.num_particles):
            # Random sample in stratum
            u = np.random.uniform(i / self.num_particles, 
                                 (i + 1) / self.num_particles)
            
            while j < self.num_particles and cumsum[j] < u:
                j += 1
            
            indices[i] = min(j, self.num_particles - 1)
        
        return indices
    
    def _residual_resample(self) -> np.ndarray:
        """
        Residual resampling (lowest variance).
        
        Deterministic component + residual stochastic.
        """
        indices = []
        
        # Deterministic replication based on integer part
        N_weights = self.weights * self.num_particles
        N_int = N_weights.astype(int)
        
        for i in range(self.num_particles):
            indices.extend([i] * N_int[i])
        
        # Residual resampling for fractional part
        N_residual = self.num_particles - len(indices)
        if N_residual > 0:
            residual_weights = N_weights - N_int
            residual_weights /= np.sum(residual_weights)
            
            residual_indices = np.random.choice(
                self.num_particles,
                size=N_residual,
                replace=True,
                p=residual_weights
            )
            indices.extend(residual_indices)
        
        return np.array(indices)
    
    # ========== Track Quality Management ==========
    
    def _update_track_quality(self):
        """
        Update track quality score based on ESS and weights.
        
        Quality in [0, 1]:
        - 1.0: Perfect track
        - 0.0: Lost track
        """
        # ESS-based quality
        ess_ratio = self.effective_sample_size / self.num_particles
        
        # Weight entropy (higher = more uncertain)
        entropy = -np.sum(self.weights * np.log(self.weights + 1e-15))
        max_entropy = np.log(self.num_particles)
        normalized_entropy = entropy / max_entropy
        
        # Combined quality score
        self.track_quality = 0.7 * ess_ratio + 0.3 * (1.0 - normalized_entropy)
        
        # Penalize consecutive misses
        if self.consecutive_misses > 0:
            self.track_quality *= (0.9 ** self.consecutive_misses)
    
    def is_track_valid(self, quality_threshold: float = 0.3) -> bool:
        """
        Check if track is still valid.
        
        Args:
            quality_threshold: Minimum quality for valid track
            
        Returns:
            True if track is valid
        """
        return (self.track_quality > quality_threshold and 
                self.consecutive_misses < 5)
    
    def get_particles_array(self) -> np.ndarray:
        """
        Get particles as numpy array for visualization.
        
        Returns:
            Array of shape (num_particles, state_dim)
        """
        state_dim = len(self.particles[0].vector)
        particles_array = np.zeros((self.num_particles, state_dim))
        
        for i, particle in enumerate(self.particles):
            particles_array[i] = particle.vector
        
        return particles_array
    
    def adapt_particle_count(self, min_particles: int = 100,
                            max_particles: int = 5000):
        """
        Adaptive particle count based on track quality and uncertainty.
        
        Increase particles when uncertainty is high.
        Decrease when tracking is confident.
        
        Args:
            min_particles: Minimum number of particles
            max_particles: Maximum number of particles
        """
        # Estimate uncertainty from covariance
        covariance = self.estimate_covariance()
        position_uncertainty = np.trace(covariance[:3, :3])
        
        # Heuristic: more particles for higher uncertainty
        if position_uncertainty > 1000:  # High uncertainty
            target_particles = min(self.num_particles * 2, max_particles)
        elif position_uncertainty < 100:  # Low uncertainty
            target_particles = max(self.num_particles // 2, min_particles)
        else:
            return  # Keep current count
        
        if target_particles != self.num_particles:
            self._resize_particle_cloud(target_particles)
    
    def _resize_particle_cloud(self, new_count: int):
        """Resize particle cloud by resampling or replication."""
        if new_count > self.num_particles:
            # Increase: replicate particles
            indices = np.random.choice(
                self.num_particles,
                size=new_count - self.num_particles,
                p=self.weights
            )
            for idx in indices:
                self.particles.append(self.particles[idx].copy())
        else:
            # Decrease: resample
            indices = self._systematic_resample()
            self.particles = [self.particles[i].copy() for i in indices[:new_count]]
        
        self.num_particles = new_count
        self.weights = np.ones(new_count) / new_count
