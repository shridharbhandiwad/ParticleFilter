"""
Performance Metrics for Tracking Evaluation

Implements:
- Position RMSE
- Velocity error
- Track continuity
- Track fragmentation
- False track rate
- Track purity
- OSPA metric
- Processing latency
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from ..core.state import State


@dataclass
class TrackingMetrics:
    """Container for tracking performance metrics."""
    
    # Position and velocity errors
    position_rmse: float = 0.0
    velocity_rmse: float = 0.0
    
    # Track quality metrics
    track_continuity: float = 0.0
    track_purity: float = 0.0
    track_fragmentation: float = 0.0
    
    # Detection metrics
    true_positive_rate: float = 0.0
    false_positive_rate: float = 0.0
    false_track_rate: float = 0.0
    
    # OSPA metric
    ospa_distance: float = 0.0
    
    # Computational metrics
    avg_processing_time: float = 0.0
    particle_efficiency: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'position_rmse': self.position_rmse,
            'velocity_rmse': self.velocity_rmse,
            'track_continuity': self.track_continuity,
            'track_purity': self.track_purity,
            'track_fragmentation': self.track_fragmentation,
            'true_positive_rate': self.true_positive_rate,
            'false_positive_rate': self.false_positive_rate,
            'false_track_rate': self.false_track_rate,
            'ospa_distance': self.ospa_distance,
            'avg_processing_time': self.avg_processing_time,
            'particle_efficiency': self.particle_efficiency
        }


class PerformanceEvaluator:
    """
    Evaluate tracking performance against ground truth.
    """
    
    def __init__(self, association_threshold: float = 50.0):
        """
        Initialize evaluator.
        
        Args:
            association_threshold: Maximum distance for track-truth association [meters]
        """
        self.association_threshold = association_threshold
        
        # History
        self.position_errors = []
        self.velocity_errors = []
        self.processing_times = []
        
        # Track statistics
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        
        # OSPA history
        self.ospa_history = []
    
    def evaluate_frame(self,
                      ground_truth: List[State],
                      estimates: List[State],
                      processing_time: float = 0.0) -> Dict:
        """
        Evaluate single frame.
        
        Args:
            ground_truth: Ground truth states
            estimates: Estimated states
            processing_time: Processing time for this frame [seconds]
            
        Returns:
            Frame-level metrics dictionary
        """
        # Associate estimates to ground truth
        associations, unmatched_gt, unmatched_est = self._associate_tracks(
            ground_truth, estimates
        )
        
        # Compute errors for matched tracks
        frame_position_errors = []
        frame_velocity_errors = []
        
        for gt_idx, est_idx in associations:
            gt_state = ground_truth[gt_idx]
            est_state = estimates[est_idx]
            
            # Position error
            pos_error = np.linalg.norm(gt_state.position - est_state.position)
            frame_position_errors.append(pos_error)
            self.position_errors.append(pos_error)
            
            # Velocity error
            vel_error = np.linalg.norm(gt_state.velocity - est_state.velocity)
            frame_velocity_errors.append(vel_error)
            self.velocity_errors.append(vel_error)
        
        # Update statistics
        self.true_positives += len(associations)
        self.false_negatives += len(unmatched_gt)
        self.false_positives += len(unmatched_est)
        
        # Processing time
        if processing_time > 0:
            self.processing_times.append(processing_time)
        
        # Compute OSPA
        ospa = self._compute_ospa(ground_truth, estimates)
        self.ospa_history.append(ospa)
        
        # Frame metrics
        frame_metrics = {
            'position_errors': frame_position_errors,
            'velocity_errors': frame_velocity_errors,
            'avg_position_error': np.mean(frame_position_errors) if frame_position_errors else 0.0,
            'avg_velocity_error': np.mean(frame_velocity_errors) if frame_velocity_errors else 0.0,
            'true_positives': len(associations),
            'false_positives': len(unmatched_est),
            'false_negatives': len(unmatched_gt),
            'ospa': ospa,
            'processing_time': processing_time
        }
        
        return frame_metrics
    
    def compute_overall_metrics(self) -> TrackingMetrics:
        """
        Compute overall metrics from accumulated history.
        
        Returns:
            TrackingMetrics object
        """
        metrics = TrackingMetrics()
        
        # Position and velocity RMSE
        if self.position_errors:
            metrics.position_rmse = np.sqrt(np.mean(np.array(self.position_errors) ** 2))
        
        if self.velocity_errors:
            metrics.velocity_rmse = np.sqrt(np.mean(np.array(self.velocity_errors) ** 2))
        
        # Detection rates
        total_detections = self.true_positives + self.false_negatives
        if total_detections > 0:
            metrics.true_positive_rate = self.true_positives / total_detections
        
        total_estimates = self.true_positives + self.false_positives
        if total_estimates > 0:
            metrics.false_positive_rate = self.false_positives / total_estimates
        
        # Track continuity (inverse of false negative rate)
        if total_detections > 0:
            metrics.track_continuity = self.true_positives / total_detections
        
        # Track purity (inverse of false positive rate)
        if total_estimates > 0:
            metrics.track_purity = self.true_positives / total_estimates
        
        # False track rate
        if total_estimates > 0:
            metrics.false_track_rate = self.false_positives / total_estimates
        
        # Average OSPA
        if self.ospa_history:
            metrics.ospa_distance = np.mean(self.ospa_history)
        
        # Processing time
        if self.processing_times:
            metrics.avg_processing_time = np.mean(self.processing_times)
        
        return metrics
    
    def _associate_tracks(self,
                         ground_truth: List[State],
                         estimates: List[State]) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Associate estimated tracks to ground truth using nearest neighbor.
        
        Returns:
            (associations, unmatched_gt, unmatched_est)
            - associations: List of (gt_idx, est_idx) pairs
            - unmatched_gt: Indices of unmatched ground truth
            - unmatched_est: Indices of unmatched estimates
        """
        if not ground_truth or not estimates:
            return [], list(range(len(ground_truth))), list(range(len(estimates)))
        
        # Build distance matrix
        num_gt = len(ground_truth)
        num_est = len(estimates)
        
        dist_matrix = np.full((num_gt, num_est), np.inf)
        
        for i, gt_state in enumerate(ground_truth):
            for j, est_state in enumerate(estimates):
                dist = np.linalg.norm(gt_state.position - est_state.position)
                if dist < self.association_threshold:
                    dist_matrix[i, j] = dist
        
        # Greedy assignment (for production, use Hungarian algorithm)
        associations = []
        matched_gt = set()
        matched_est = set()
        
        for _ in range(min(num_gt, num_est)):
            min_dist = np.inf
            min_i, min_j = -1, -1
            
            for i in range(num_gt):
                if i in matched_gt:
                    continue
                for j in range(num_est):
                    if j in matched_est:
                        continue
                    if dist_matrix[i, j] < min_dist:
                        min_dist = dist_matrix[i, j]
                        min_i, min_j = i, j
            
            if min_dist < self.association_threshold:
                associations.append((min_i, min_j))
                matched_gt.add(min_i)
                matched_est.add(min_j)
            else:
                break
        
        unmatched_gt = [i for i in range(num_gt) if i not in matched_gt]
        unmatched_est = [j for j in range(num_est) if j not in matched_est]
        
        return associations, unmatched_gt, unmatched_est
    
    def _compute_ospa(self,
                     ground_truth: List[State],
                     estimates: List[State],
                     c: float = 100.0,
                     p: int = 2) -> float:
        """
        Compute Optimal Subpattern Assignment (OSPA) metric.
        
        OSPA handles both localization and cardinality errors.
        
        Args:
            ground_truth: Ground truth states
            estimates: Estimated states
            c: Cutoff parameter [meters]
            p: Order parameter
            
        Returns:
            OSPA distance
        """
        m = len(ground_truth)
        n = len(estimates)
        
        if m == 0 and n == 0:
            return 0.0
        
        # Build distance matrix (capped at c)
        max_size = max(m, n)
        
        if m == 0 or n == 0:
            # Cardinality error only
            return c * ((abs(m - n) / max_size) ** (1.0 / p))
        
        # Compute pairwise distances
        dist_matrix = np.full((m, n), c)
        
        for i, gt_state in enumerate(ground_truth):
            for j, est_state in enumerate(estimates):
                dist = np.linalg.norm(gt_state.position - est_state.position)
                dist_matrix[i, j] = min(dist, c)
        
        # Find optimal assignment (greedy approximation)
        # For exact solution, use scipy.optimize.linear_sum_assignment
        total_cost = 0.0
        
        if m <= n:
            # More estimates than truth
            used_est = set()
            for i in range(m):
                min_dist = c
                min_j = -1
                for j in range(n):
                    if j not in used_est and dist_matrix[i, j] < min_dist:
                        min_dist = dist_matrix[i, j]
                        min_j = j
                
                if min_j >= 0:
                    used_est.add(min_j)
                    total_cost += min_dist ** p
            
            # Cardinality penalty for extra estimates
            total_cost += (n - m) * (c ** p)
        else:
            # More truth than estimates
            used_gt = set()
            for j in range(n):
                min_dist = c
                min_i = -1
                for i in range(m):
                    if i not in used_gt and dist_matrix[i, j] < min_dist:
                        min_dist = dist_matrix[i, j]
                        min_i = i
                
                if min_i >= 0:
                    used_gt.add(min_i)
                    total_cost += min_dist ** p
            
            # Cardinality penalty for missed truth
            total_cost += (m - n) * (c ** p)
        
        # OSPA distance
        ospa = (total_cost / max_size) ** (1.0 / p)
        
        return ospa
    
    def get_error_statistics(self) -> Dict:
        """Get detailed error statistics."""
        stats = {}
        
        if self.position_errors:
            stats['position'] = {
                'mean': np.mean(self.position_errors),
                'std': np.std(self.position_errors),
                'min': np.min(self.position_errors),
                'max': np.max(self.position_errors),
                'median': np.median(self.position_errors),
                'rmse': np.sqrt(np.mean(np.array(self.position_errors) ** 2))
            }
        
        if self.velocity_errors:
            stats['velocity'] = {
                'mean': np.mean(self.velocity_errors),
                'std': np.std(self.velocity_errors),
                'min': np.min(self.velocity_errors),
                'max': np.max(self.velocity_errors),
                'median': np.median(self.velocity_errors),
                'rmse': np.sqrt(np.mean(np.array(self.velocity_errors) ** 2))
            }
        
        if self.processing_times:
            stats['processing_time'] = {
                'mean': np.mean(self.processing_times),
                'std': np.std(self.processing_times),
                'min': np.min(self.processing_times),
                'max': np.max(self.processing_times),
                'median': np.median(self.processing_times)
            }
        
        return stats
    
    def reset(self):
        """Reset evaluator state."""
        self.position_errors = []
        self.velocity_errors = []
        self.processing_times = []
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.ospa_history = []
