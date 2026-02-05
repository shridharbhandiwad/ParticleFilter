"""
Multi-Target Tracker with Data Association

Implements:
- Track management (initiation, maintenance, termination)
- Measurement-to-track association
- Global Nearest Neighbor (GNN)
- Track quality scoring
- Clutter rejection
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from ..core.state import State, Measurement, StateType
from ..models.motion_models import MotionModel, ConstantVelocityModel
from ..models.measurement_models import RadarMeasurementModel
from .particle_filter import ParticleFilter


@dataclass
class Track:
    """
    Track representation for multi-target tracking.
    
    Implements M/N track confirmation logic:
    - Track is confirmed if it gets M hits out of last N scans
    - Track is tentative until confirmed
    - Track is deleted if quality drops or too many misses
    
    Attributes:
        track_id: Unique track identifier
        filter: Particle filter for this track
        last_update_time: Time of last measurement update
        age: Track age [number of scans since creation]
        hits: Total number of measurement associations
        misses: Number of consecutive missed detections
        quality: Track quality score [0-1]
        state: Current state estimate
        hit_history: Recent hit/miss history for M/N confirmation [1=hit, 0=miss]
        confirmed: Whether track is confirmed
    """
    track_id: int
    filter: ParticleFilter
    last_update_time: float
    age: int = 0
    hits: int = 0
    misses: int = 0
    quality: float = 1.0
    state: Optional[State] = None
    hit_history: List[int] = field(default_factory=list)
    confirmed: bool = False
    
    def update_quality(self):
        """Update track quality based on hit/miss ratio and filter quality."""
        hit_ratio = self.hits / max(self.age, 1)
        filter_quality = self.filter.track_quality
        
        # Combined quality (60% hit ratio, 40% filter quality)
        self.quality = 0.6 * hit_ratio + 0.4 * filter_quality
        
        # Penalize consecutive misses exponentially
        if self.misses > 0:
            self.quality *= (0.85 ** self.misses)
    
    def is_confirmed(self, m_hits: int = 3, n_scans: int = 4) -> bool:
        """
        Check if track is confirmed using M/N logic.
        
        Track is confirmed if it has M hits in the last N scans.
        
        Args:
            m_hits: Minimum hits required
            n_scans: Window of scans to check
            
        Returns:
            True if track is confirmed
        """
        # Once confirmed, stay confirmed
        if self.confirmed:
            return True
        
        # Need at least N scans to confirm
        if self.age < n_scans:
            return False
        
        # Check M/N criterion
        recent_hits = sum(self.hit_history[-n_scans:])
        if recent_hits >= m_hits:
            self.confirmed = True
            return True
        
        return False
    
    def is_terminated(self, max_misses: int = 5, min_quality: float = 0.2) -> bool:
        """
        Check if track should be terminated.
        
        Confirmed tracks are more tolerant to misses.
        
        Args:
            max_misses: Maximum consecutive misses
            min_quality: Minimum quality threshold
            
        Returns:
            True if track should be terminated
        """
        # Confirmed tracks can tolerate more misses
        miss_threshold = max_misses * 2 if self.confirmed else max_misses
        
        # Terminate on excessive misses or low quality
        return self.misses >= miss_threshold or self.quality < min_quality


class MultiTargetTracker:
    """
    Multi-target tracker with measurement association.
    
    Manages multiple tracks and performs data association.
    """
    
    def __init__(self,
                 motion_model: MotionModel = None,
                 measurement_model: RadarMeasurementModel = None,
                 num_particles: int = 1000,
                 gating_threshold: float = 9.21,
                 confirmation_threshold: int = 3,
                 termination_threshold: int = 5,
                 state_type: StateType = StateType.CV):
        """
        Initialize multi-target tracker.
        
        Args:
            motion_model: Motion model for tracks
            measurement_model: Measurement model
            num_particles: Number of particles per track
            gating_threshold: Chi-squared gating threshold
            confirmation_threshold: Hits needed for confirmation
            termination_threshold: Misses before termination
            state_type: State vector type
        """
        self.motion_model = motion_model or ConstantVelocityModel()
        self.measurement_model = measurement_model or RadarMeasurementModel()
        self.num_particles = num_particles
        self.gating_threshold = gating_threshold
        self.confirmation_threshold = confirmation_threshold
        self.termination_threshold = termination_threshold
        self.state_type = state_type
        
        # Track management
        self.tracks: Dict[int, Track] = {}
        self.next_track_id = 1
        
        # Association history
        self.association_history: List[Dict] = []
        
        # Statistics
        self.total_tracks_created = 0
        self.total_tracks_terminated = 0
        
    def predict(self, current_time: float):
        """
        Predict all tracks to current time.
        
        Args:
            current_time: Current time [seconds]
        """
        for track_id, track in self.tracks.items():
            dt = current_time - track.last_update_time
            
            if dt > 0:
                # Predict particle filter
                track.filter.predict(dt)
                
                # Update state estimate
                track.state = track.filter.estimate()
                track.last_update_time = current_time
    
    def update(self, measurements: List[Measurement], current_time: float):
        """
        Update tracks with measurements.
        
        Performs:
        1. Prediction to current time
        2. Measurement gating
        3. Data association
        4. Track updates
        5. Track management
        
        Args:
            measurements: List of measurements
            current_time: Current time [seconds]
        """
        # Step 1: Predict tracks
        self.predict(current_time)
        
        # Step 2: Measurement gating
        gated_measurements = self._gate_measurements(measurements)
        
        # Step 3: Data association
        associations = self._associate_measurements(measurements, gated_measurements)
        
        # Step 4: Update tracks
        self._update_tracks(associations, measurements, current_time)
        
        # Step 5: Track management
        self._manage_tracks(associations, measurements, current_time)
        
        # Store association history
        self.association_history.append({
            'time': current_time,
            'associations': associations.copy(),
            'num_measurements': len(measurements)
        })
    
    def _gate_measurements(self, measurements: List[Measurement]) -> Dict[int, List[int]]:
        """
        Gate measurements for each track.
        
        Returns:
            Dictionary mapping track_id -> list of measurement indices
        """
        gated = {}
        
        for track_id, track in self.tracks.items():
            gated[track_id] = []
            
            for meas_idx, measurement in enumerate(measurements):
                # Check if measurement passes gate
                if self.measurement_model.gate_measurement(
                    measurement, 
                    track.state, 
                    self.gating_threshold
                ):
                    gated[track_id].append(meas_idx)
        
        return gated
    
    def _associate_measurements(self, 
                               measurements: List[Measurement],
                               gated_measurements: Dict[int, List[int]]) -> Dict[int, Optional[int]]:
        """
        Perform measurement-to-track association using Global Nearest Neighbor.
        
        Uses likelihood-based assignment.
        
        Returns:
            Dictionary mapping track_id -> measurement_index (or None)
        """
        associations = {}
        
        # Initialize all tracks to no association
        for track_id in self.tracks.keys():
            associations[track_id] = None
        
        # Build cost matrix
        track_ids = list(self.tracks.keys())
        num_tracks = len(track_ids)
        num_measurements = len(measurements)
        
        if num_tracks == 0 or num_measurements == 0:
            return associations
        
        # Cost matrix: negative log-likelihood
        cost_matrix = np.full((num_tracks, num_measurements), np.inf)
        
        for i, track_id in enumerate(track_ids):
            track = self.tracks[track_id]
            
            # Only consider gated measurements
            for meas_idx in gated_measurements.get(track_id, []):
                measurement = measurements[meas_idx]
                
                # Compute likelihood
                likelihood = self.measurement_model.compute_likelihood(
                    measurement, track.state
                )
                
                # Cost = negative log-likelihood
                if likelihood > 1e-15:
                    cost_matrix[i, meas_idx] = -np.log(likelihood)
        
        # Solve assignment problem (greedy nearest neighbor for simplicity)
        # For production, use Hungarian algorithm (scipy.optimize.linear_sum_assignment)
        used_measurements = set()
        
        for _ in range(min(num_tracks, num_measurements)):
            # Find minimum cost
            min_cost = np.inf
            min_track_idx = -1
            min_meas_idx = -1
            
            for i in range(num_tracks):
                for j in range(num_measurements):
                    if j not in used_measurements and cost_matrix[i, j] < min_cost:
                        min_cost = cost_matrix[i, j]
                        min_track_idx = i
                        min_meas_idx = j
            
            # Check if valid association found
            if min_cost < 10.0:  # Threshold on negative log-likelihood
                track_id = track_ids[min_track_idx]
                associations[track_id] = min_meas_idx
                used_measurements.add(min_meas_idx)
            else:
                break
        
        return associations
    
    def _update_tracks(self, 
                      associations: Dict[int, Optional[int]],
                      measurements: List[Measurement],
                      current_time: float):
        """
        Update tracks based on associations.
        
        Args:
            associations: Track-to-measurement associations
            measurements: List of measurements
            current_time: Current time
        """
        for track_id, meas_idx in associations.items():
            track = self.tracks[track_id]
            
            if meas_idx is not None:
                # Update with measurement
                measurement = measurements[meas_idx]
                track.filter.update(measurement, detection_probability=0.95)
                track.filter.resample()
                
                # Update track statistics
                track.hits += 1
                track.misses = 0
                track.hit_history.append(1)  # Record hit
                track.last_update_time = current_time
                
            else:
                # No measurement - missed detection
                track.misses += 1
                track.hit_history.append(0)  # Record miss
            
            # Update age and quality
            track.age += 1
            track.update_quality()
            
            # Check confirmation status
            track.is_confirmed(self.confirmation_threshold, self.confirmation_threshold + 1)
            
            # Update state estimate
            track.state = track.filter.estimate()
    
    def _manage_tracks(self,
                      associations: Dict[int, Optional[int]],
                      measurements: List[Measurement],
                      current_time: float):
        """
        Manage track lifecycle: initiation and termination.
        
        Args:
            associations: Track-to-measurement associations
            measurements: List of measurements
            current_time: Current time
        """
        # Identify unassociated measurements
        associated_meas_indices = set(
            meas_idx for meas_idx in associations.values() 
            if meas_idx is not None
        )
        
        unassociated_measurements = [
            measurements[i] for i in range(len(measurements))
            if i not in associated_meas_indices
        ]
        
        # Initiate new tracks from unassociated measurements
        for measurement in unassociated_measurements:
            self._initiate_track(measurement, current_time)
        
        # Terminate dead tracks
        tracks_to_terminate = []
        for track_id, track in self.tracks.items():
            if track.is_terminated(self.termination_threshold):
                tracks_to_terminate.append(track_id)
        
        for track_id in tracks_to_terminate:
            self._terminate_track(track_id)
    
    def _initiate_track(self, measurement: Measurement, current_time: float):
        """
        Initiate new track from measurement.
        
        Implements proper track initiation:
        1. Create initial state from measurement
        2. Initialize particle filter with high uncertainty
        3. Immediately update particle filter with initiating measurement
        4. Start track with hits=1 (since we have one measurement)
        
        Args:
            measurement: Initial measurement
            current_time: Current time
        """
        # Convert measurement to state
        position = measurement.to_cartesian()
        
        # Initialize velocity to zero (will be estimated over time)
        if self.state_type == StateType.CV:
            initial_vector = np.concatenate([position, np.zeros(3)])
        elif self.state_type == StateType.CA:
            initial_vector = np.concatenate([position, np.zeros(6)])
        elif self.state_type == StateType.CT:
            initial_vector = np.concatenate([position, np.zeros(4)])
        else:
            initial_vector = np.concatenate([position, np.zeros(3)])
        
        initial_state = State(
            vector=initial_vector,
            state_type=self.state_type,
            timestamp=current_time
        )
        
        # Create particle filter
        pf = ParticleFilter(
            num_particles=self.num_particles,
            motion_model=self.motion_model,
            measurement_model=self.measurement_model,
            state_type=self.state_type
        )
        
        # Initialize with high uncertainty (tentative track)
        state_dim = len(initial_vector)
        initial_cov = np.eye(state_dim)
        initial_cov[0:3, 0:3] *= 500.0  # 22.4m position std
        initial_cov[3:6, 3:6] *= 100.0  # 10 m/s velocity std
        
        pf.initialize(initial_state, initial_cov)
        
        # CRITICAL: Immediately update particle filter with initiating measurement
        # This properly weights the particles based on the measurement
        pf.update(measurement, detection_probability=0.95)
        pf.resample()
        
        # Estimate state after update
        updated_state = pf.estimate()
        
        # Create track with initial hit recorded
        track = Track(
            track_id=self.next_track_id,
            filter=pf,
            last_update_time=current_time,
            state=updated_state,
            age=1,  # Track starts at age 1
            hits=1,  # Track starts with 1 hit (the initiating measurement)
            misses=0,
            hit_history=[1],  # Record the initial hit
            confirmed=False  # Not confirmed yet
        )
        
        # Update track quality
        track.update_quality()
        
        self.tracks[self.next_track_id] = track
        self.next_track_id += 1
        self.total_tracks_created += 1
    
    def _terminate_track(self, track_id: int):
        """Terminate track."""
        if track_id in self.tracks:
            del self.tracks[track_id]
            self.total_tracks_terminated += 1
    
    def get_confirmed_tracks(self) -> List[Track]:
        """
        Get list of confirmed tracks.
        
        Uses M/N confirmation logic:
        - M = confirmation_threshold (default 3)
        - N = confirmation_threshold + 1 (default 4)
        - Track needs 3 hits out of last 4 scans to be confirmed
        
        Returns:
            List of confirmed tracks
        """
        m_hits = self.confirmation_threshold
        n_scans = self.confirmation_threshold + 1
        
        return [
            track for track in self.tracks.values()
            if track.is_confirmed(m_hits, n_scans)
        ]
    
    def get_track_states(self) -> List[State]:
        """Get current state estimates for all confirmed tracks."""
        confirmed = self.get_confirmed_tracks()
        return [track.state for track in confirmed if track.state is not None]
    
    def get_statistics(self) -> Dict:
        """Get tracker statistics."""
        confirmed_tracks = self.get_confirmed_tracks()
        
        return {
            'total_tracks': len(self.tracks),
            'confirmed_tracks': len(confirmed_tracks),
            'tentative_tracks': len(self.tracks) - len(confirmed_tracks),
            'tracks_created': self.total_tracks_created,
            'tracks_terminated': self.total_tracks_terminated,
            'average_quality': np.mean([t.quality for t in self.tracks.values()]) 
                               if self.tracks else 0.0
        }
