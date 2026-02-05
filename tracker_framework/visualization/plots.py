"""
Visualization and Plotting Tools

Provides:
- Ground truth vs estimated track plots
- Particle cloud visualization
- Innovation/residual plots
- Error plots (RMSE, track loss)
- Particle weight distribution
- Effective sample size
- 3D trajectory visualization
- X, Y, Z coordinates vs time (GT, measured, filtered)
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Dict, Optional, Tuple
from ..core.state import State, Measurement
from ..filters.particle_filter import ParticleFilter


class TrackingVisualizer:
    """
    Visualization tools for tracking results.
    """
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize visualizer.
        
        Args:
            figsize: Default figure size
        """
        self.figsize = figsize
        plt.style.use('seaborn-v0_8-darkgrid')
    
    def plot_trajectories_2d(self,
                            ground_truth: List[List[State]],
                            estimates: List[List[State]],
                            measurements: List[List[Measurement]] = None,
                            plane: str = 'xy',
                            save_path: Optional[str] = None) -> Figure:
        """
        Plot 2D trajectories.
        
        Args:
            ground_truth: Ground truth state history (per track)
            estimates: Estimated state history (per track)
            measurements: Measurement history (optional)
            plane: Projection plane ('xy', 'xz', or 'yz')
            save_path: Path to save figure (optional)
            
        Returns:
            Matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Determine axes
        if plane == 'xy':
            idx1, idx2 = 0, 1
            xlabel, ylabel = 'X [m]', 'Y [m]'
        elif plane == 'xz':
            idx1, idx2 = 0, 2
            xlabel, ylabel = 'X [m]', 'Z [m]'
        else:  # yz
            idx1, idx2 = 1, 2
            xlabel, ylabel = 'Y [m]', 'Z [m]'
        
        # Plot measurements (if provided)
        if measurements:
            all_meas_x = []
            all_meas_y = []
            for meas_list in measurements:
                for meas in meas_list:
                    cart = meas.to_cartesian()
                    all_meas_x.append(cart[idx1])
                    all_meas_y.append(cart[idx2])
            
            if all_meas_x:
                ax.scatter(all_meas_x, all_meas_y, c='gray', s=1, alpha=0.3, 
                          label='Measurements', marker='.')
        
        # Plot ground truth
        for i, gt_track in enumerate(ground_truth):
            if not gt_track:
                continue
            gt_x = [state.position[idx1] for state in gt_track]
            gt_y = [state.position[idx2] for state in gt_track]
            ax.plot(gt_x, gt_y, 'g-', linewidth=2, label=f'GT Track {i+1}' if i < 3 else '')
            ax.plot(gt_x[0], gt_y[0], 'go', markersize=8)  # Start
            ax.plot(gt_x[-1], gt_y[-1], 'gs', markersize=8)  # End
        
        # Plot estimates
        for i, est_track in enumerate(estimates):
            if not est_track:
                continue
            est_x = [state.position[idx1] for state in est_track]
            est_y = [state.position[idx2] for state in est_track]
            ax.plot(est_x, est_y, 'r--', linewidth=2, label=f'Est Track {i+1}' if i < 3 else '')
            ax.plot(est_x[0], est_y[0], 'ro', markersize=8)
            ax.plot(est_x[-1], est_y[-1], 'rs', markersize=8)
        
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(f'Tracking Results - {plane.upper()} Plane', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_trajectories_3d(self,
                            ground_truth: List[List[State]],
                            estimates: List[List[State]],
                            save_path: Optional[str] = None) -> Figure:
        """
        Plot 3D trajectories.
        
        Args:
            ground_truth: Ground truth state history
            estimates: Estimated state history
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot ground truth
        for i, gt_track in enumerate(ground_truth):
            if not gt_track:
                continue
            gt_x = [state.position[0] for state in gt_track]
            gt_y = [state.position[1] for state in gt_track]
            gt_z = [state.position[2] for state in gt_track]
            ax.plot(gt_x, gt_y, gt_z, 'g-', linewidth=2, label=f'GT Track {i+1}')
            ax.scatter(gt_x[0], gt_y[0], gt_z[0], c='g', s=100, marker='o')
        
        # Plot estimates
        for i, est_track in enumerate(estimates):
            if not est_track:
                continue
            est_x = [state.position[0] for state in est_track]
            est_y = [state.position[1] for state in est_track]
            est_z = [state.position[2] for state in est_track]
            ax.plot(est_x, est_y, est_z, 'r--', linewidth=2, label=f'Est Track {i+1}')
            ax.scatter(est_x[0], est_y[0], est_z[0], c='r', s=100, marker='o')
        
        ax.set_xlabel('X [m]', fontsize=12)
        ax.set_ylabel('Y [m]', fontsize=12)
        ax.set_zlabel('Z [m]', fontsize=12)
        ax.set_title('3D Tracking Results', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_particle_cloud(self,
                           particle_filter: ParticleFilter,
                           ground_truth: State = None,
                           plane: str = 'xy',
                           save_path: Optional[str] = None) -> Figure:
        """
        Visualize particle cloud.
        
        Args:
            particle_filter: Particle filter instance
            ground_truth: Ground truth state (optional)
            plane: Projection plane
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Determine axes
        if plane == 'xy':
            idx1, idx2 = 0, 1
            xlabel, ylabel = 'X [m]', 'Y [m]'
        elif plane == 'xz':
            idx1, idx2 = 0, 2
            xlabel, ylabel = 'X [m]', 'Z [m]'
        else:
            idx1, idx2 = 1, 2
            xlabel, ylabel = 'Y [m]', 'Z [m]'
        
        # Get particles
        particles = particle_filter.get_particles_array()
        weights = particle_filter.weights
        
        # Plot particles (color by weight)
        scatter = ax.scatter(particles[:, idx1], particles[:, idx2],
                           c=weights, s=10, cmap='hot', alpha=0.6,
                           vmin=0, vmax=weights.max())
        
        # Plot estimate
        if particle_filter.state_estimate:
            est_pos = particle_filter.state_estimate.position
            ax.plot(est_pos[idx1], est_pos[idx2], 'b*', markersize=20, 
                   label='Estimate', markeredgecolor='white', markeredgewidth=1)
        
        # Plot ground truth
        if ground_truth:
            gt_pos = ground_truth.position
            ax.plot(gt_pos[idx1], gt_pos[idx2], 'go', markersize=15,
                   label='Ground Truth', markeredgecolor='white', markeredgewidth=1)
        
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(f'Particle Cloud - {plane.upper()} Plane\n'
                    f'ESS: {particle_filter.effective_sample_size:.0f}, '
                    f'Quality: {particle_filter.track_quality:.2f}',
                    fontsize=12, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Particle Weight', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_error_vs_time(self,
                          position_errors: List[float],
                          velocity_errors: List[float],
                          timestamps: List[float],
                          save_path: Optional[str] = None) -> Figure:
        """
        Plot tracking errors vs time.
        
        Args:
            position_errors: Position errors [m]
            velocity_errors: Velocity errors [m/s]
            timestamps: Time stamps [s]
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Position error
        ax1.plot(timestamps, position_errors, 'b-', linewidth=1.5, label='Position Error')
        ax1.axhline(np.mean(position_errors), color='r', linestyle='--', 
                   label=f'Mean: {np.mean(position_errors):.2f} m')
        ax1.set_ylabel('Position Error [m]', fontsize=12)
        ax1.set_title('Tracking Error vs Time', fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Velocity error
        ax2.plot(timestamps, velocity_errors, 'g-', linewidth=1.5, label='Velocity Error')
        ax2.axhline(np.mean(velocity_errors), color='r', linestyle='--',
                   label=f'Mean: {np.mean(velocity_errors):.2f} m/s')
        ax2.set_xlabel('Time [s]', fontsize=12)
        ax2.set_ylabel('Velocity Error [m/s]', fontsize=12)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_rmse_summary(self,
                         position_rmse: float,
                         velocity_rmse: float,
                         position_errors: List[float],
                         velocity_errors: List[float],
                         save_path: Optional[str] = None) -> Figure:
        """
        Plot RMSE summary with histograms.
        
        Args:
            position_rmse: Position RMSE [m]
            velocity_rmse: Velocity RMSE [m/s]
            position_errors: Position error history
            velocity_errors: Velocity error history
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Position error histogram
        axes[0, 0].hist(position_errors, bins=50, color='blue', alpha=0.7, edgecolor='black')
        axes[0, 0].axvline(position_rmse, color='r', linestyle='--', linewidth=2,
                          label=f'RMSE: {position_rmse:.2f} m')
        axes[0, 0].set_xlabel('Position Error [m]', fontsize=11)
        axes[0, 0].set_ylabel('Frequency', fontsize=11)
        axes[0, 0].set_title('Position Error Distribution', fontsize=12, fontweight='bold')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Velocity error histogram
        axes[0, 1].hist(velocity_errors, bins=50, color='green', alpha=0.7, edgecolor='black')
        axes[0, 1].axvline(velocity_rmse, color='r', linestyle='--', linewidth=2,
                          label=f'RMSE: {velocity_rmse:.2f} m/s')
        axes[0, 1].set_xlabel('Velocity Error [m/s]', fontsize=11)
        axes[0, 1].set_ylabel('Frequency', fontsize=11)
        axes[0, 1].set_title('Velocity Error Distribution', fontsize=12, fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Position error CDF
        sorted_pos_err = np.sort(position_errors)
        cdf_pos = np.arange(1, len(sorted_pos_err) + 1) / len(sorted_pos_err)
        axes[1, 0].plot(sorted_pos_err, cdf_pos, 'b-', linewidth=2)
        axes[1, 0].axvline(position_rmse, color='r', linestyle='--', linewidth=2,
                          label=f'RMSE: {position_rmse:.2f} m')
        axes[1, 0].set_xlabel('Position Error [m]', fontsize=11)
        axes[1, 0].set_ylabel('CDF', fontsize=11)
        axes[1, 0].set_title('Position Error CDF', fontsize=12, fontweight='bold')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Velocity error CDF
        sorted_vel_err = np.sort(velocity_errors)
        cdf_vel = np.arange(1, len(sorted_vel_err) + 1) / len(sorted_vel_err)
        axes[1, 1].plot(sorted_vel_err, cdf_vel, 'g-', linewidth=2)
        axes[1, 1].axvline(velocity_rmse, color='r', linestyle='--', linewidth=2,
                          label=f'RMSE: {velocity_rmse:.2f} m/s')
        axes[1, 1].set_xlabel('Velocity Error [m/s]', fontsize=11)
        axes[1, 1].set_ylabel('CDF', fontsize=11)
        axes[1, 1].set_title('Velocity Error CDF', fontsize=12, fontweight='bold')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.suptitle('RMSE Summary', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_particle_metrics(self,
                             ess_history: List[float],
                             weight_entropy_history: List[float],
                             timestamps: List[float],
                             save_path: Optional[str] = None) -> Figure:
        """
        Plot particle filter metrics.
        
        Args:
            ess_history: Effective sample size history
            weight_entropy_history: Weight entropy history
            timestamps: Time stamps
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Effective sample size
        ax1.plot(timestamps, ess_history, 'b-', linewidth=1.5)
        ax1.axhline(np.mean(ess_history), color='r', linestyle='--',
                   label=f'Mean: {np.mean(ess_history):.0f}')
        ax1.set_ylabel('Effective Sample Size', fontsize=12)
        ax1.set_title('Particle Filter Metrics', fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Weight entropy
        ax2.plot(timestamps, weight_entropy_history, 'g-', linewidth=1.5)
        ax2.axhline(np.mean(weight_entropy_history), color='r', linestyle='--',
                   label=f'Mean: {np.mean(weight_entropy_history):.2f}')
        ax2.set_xlabel('Time [s]', fontsize=12)
        ax2.set_ylabel('Weight Entropy', fontsize=12)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_innovation_sequence(self,
                                innovations: List[np.ndarray],
                                timestamps: List[float],
                                measurement_names: List[str] = None,
                                save_path: Optional[str] = None) -> Figure:
        """
        Plot innovation (residual) sequence.
        
        Args:
            innovations: Innovation vectors
            timestamps: Time stamps
            measurement_names: Names of measurement components
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        if not innovations:
            return None
        
        innovations_array = np.array(innovations)
        num_components = innovations_array.shape[1]
        
        if measurement_names is None:
            measurement_names = [f'Component {i+1}' for i in range(num_components)]
        
        fig, axes = plt.subplots(num_components, 1, figsize=(12, 3*num_components), 
                                sharex=True)
        
        if num_components == 1:
            axes = [axes]
        
        for i in range(num_components):
            axes[i].plot(timestamps, innovations_array[:, i], 'b-', linewidth=1)
            axes[i].axhline(0, color='r', linestyle='--', linewidth=1)
            axes[i].fill_between(timestamps,
                                -3*np.std(innovations_array[:, i]),
                                3*np.std(innovations_array[:, i]),
                                alpha=0.2, color='gray', label='±3σ')
            axes[i].set_ylabel(measurement_names[i], fontsize=11)
            axes[i].legend(loc='best')
            axes[i].grid(True, alpha=0.3)
        
        axes[-1].set_xlabel('Time [s]', fontsize=12)
        axes[0].set_title('Innovation Sequence', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_coordinates_vs_time(self,
                                ground_truth: List[List[State]],
                                estimates: List[List[State]],
                                measurements: List[List[Measurement]],
                                timestamps: List[float],
                                save_path: Optional[str] = None) -> Figure:
        """
        Plot x, y, z coordinates vs time for ground truth, measurements, and filtered estimates.
        
        Args:
            ground_truth: Ground truth state history (per scan, per track)
            estimates: Estimated state history (per scan, per track)
            measurements: Measurement history (per scan)
            timestamps: Time stamps [s]
            save_path: Path to save figure
            
        Returns:
            Matplotlib Figure
        """
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        
        coord_names = ['X', 'Y', 'Z']
        coord_indices = [0, 1, 2]
        
        for coord_idx, ax, coord_name in zip(coord_indices, axes, coord_names):
            # Plot ground truth
            gt_plotted = False
            for scan_idx, scan_gt in enumerate(ground_truth):
                for state in scan_gt:
                    t = timestamps[scan_idx] if scan_idx < len(timestamps) else scan_idx
                    ax.plot(t, state.position[coord_idx], 'go', markersize=6, 
                           alpha=0.7, label='Ground Truth' if not gt_plotted else '')
                    gt_plotted = True
            
            # Plot measurements (convert from spherical to cartesian)
            meas_plotted = False
            for scan_idx, scan_meas in enumerate(measurements):
                for meas in scan_meas:
                    cart = meas.to_cartesian()
                    t = timestamps[scan_idx] if scan_idx < len(timestamps) else scan_idx
                    ax.plot(t, cart[coord_idx], 'kx', markersize=4, 
                           alpha=0.3, label='Measurements' if not meas_plotted else '')
                    meas_plotted = True
            
            # Plot filtered estimates
            est_plotted = False
            for scan_idx, scan_est in enumerate(estimates):
                for state in scan_est:
                    t = timestamps[scan_idx] if scan_idx < len(timestamps) else scan_idx
                    ax.plot(t, state.position[coord_idx], 'r*', markersize=7, 
                           alpha=0.8, label='Filtered' if not est_plotted else '')
                    est_plotted = True
            
            # Connect filtered estimates with lines for each track
            # Group estimates by track (assume consistent ordering within each scan)
            if estimates:
                num_tracks = max(len(scan_est) for scan_est in estimates)
                for track_idx in range(num_tracks):
                    track_times = []
                    track_coords = []
                    for scan_idx, scan_est in enumerate(estimates):
                        if track_idx < len(scan_est):
                            t = timestamps[scan_idx] if scan_idx < len(timestamps) else scan_idx
                            track_times.append(t)
                            track_coords.append(scan_est[track_idx].position[coord_idx])
                    
                    if track_times:
                        ax.plot(track_times, track_coords, 'r--', linewidth=1.5, alpha=0.6)
            
            ax.set_ylabel(f'{coord_name} Position [m]', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best', fontsize=10)
        
        axes[-1].set_xlabel('Time [s]', fontsize=12)
        axes[0].set_title('Position Coordinates vs Time (GT, Measured, Filtered)', 
                         fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
