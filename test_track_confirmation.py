#!/usr/bin/env python3
"""
Quick test to verify track confirmation logic
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tracker_framework.core.state import StateType, Measurement
from tracker_framework.models.motion_models import ConstantVelocityModel
from tracker_framework.models.measurement_models import RadarMeasurementModel
from tracker_framework.filters.multi_target_tracker import MultiTargetTracker


def test_track_confirmation():
    """Test that tracks get confirmed properly with M/N logic."""
    
    print("\n" + "="*60)
    print("Testing Particle Filter Track Confirmation")
    print("="*60 + "\n")
    
    # Create tracker with confirmation_threshold = 3 (means 3/4 M/N logic)
    tracker = MultiTargetTracker(
        motion_model=ConstantVelocityModel(),
        measurement_model=RadarMeasurementModel(),
        num_particles=500,  # Fewer particles for faster testing
        confirmation_threshold=3,
        termination_threshold=5,
        state_type=StateType.CV
    )
    
    # Simulate a target moving in a straight line
    # Position: (1000, 500, 100) moving at (10, 5, 0) m/s
    
    scan_period = 0.1  # 10 Hz
    
    print("Simulating target track over 10 scans...")
    print("-" * 60)
    
    for scan_idx in range(10):
        timestamp = scan_idx * scan_period
        
        # Generate measurement for the target
        # Target position at this time
        pos_x = 1000 + 10 * timestamp
        pos_y = 500 + 5 * timestamp
        pos_z = 100
        
        # Convert to spherical
        r = np.sqrt(pos_x**2 + pos_y**2 + pos_z**2)
        az = np.arctan2(pos_y, pos_x)
        el = np.arcsin(pos_z / r)
        
        # Add small noise
        r += np.random.normal(0, 2.0)
        az += np.random.normal(0, np.radians(0.2))
        el += np.random.normal(0, np.radians(0.2))
        
        measurement = Measurement(
            range=r,
            azimuth=az,
            elevation=el,
            timestamp=timestamp
        )
        
        # Update tracker
        tracker.update([measurement], timestamp)
        
        # Get statistics
        stats = tracker.get_statistics()
        confirmed_tracks = tracker.get_confirmed_tracks()
        
        print(f"Scan {scan_idx:2d} (t={timestamp:.2f}s):")
        print(f"  Total tracks: {stats['total_tracks']}")
        print(f"  Confirmed tracks: {stats['confirmed_tracks']}")
        print(f"  Tentative tracks: {stats['tentative_tracks']}")
        
        # Check individual tracks
        for track_id, track in tracker.tracks.items():
            print(f"    Track {track_id}: age={track.age}, hits={track.hits}, "
                  f"misses={track.misses}, hit_history={track.hit_history}, "
                  f"confirmed={track.confirmed}, quality={track.quality:.3f}")
        
        print()
    
    # Final verification
    print("="*60)
    print("FINAL RESULTS:")
    print("="*60)
    
    final_stats = tracker.get_statistics()
    confirmed_tracks = tracker.get_confirmed_tracks()
    
    print(f"Total tracks created: {final_stats['tracks_created']}")
    print(f"Confirmed tracks: {final_stats['confirmed_tracks']}")
    print(f"Average quality: {final_stats['average_quality']:.3f}")
    
    # Verify that we have at least one confirmed track
    if final_stats['confirmed_tracks'] > 0:
        print("\n✅ SUCCESS: Particle filter successfully created confirmed track(s)!")
        
        # Show confirmed track details
        print("\nConfirmed Track Details:")
        for track in confirmed_tracks:
            print(f"  Track {track.track_id}:")
            print(f"    Age: {track.age} scans")
            print(f"    Hits: {track.hits}")
            print(f"    Hit history: {track.hit_history}")
            print(f"    Quality: {track.quality:.3f}")
            print(f"    Position: [{track.state.position[0]:.1f}, "
                  f"{track.state.position[1]:.1f}, {track.state.position[2]:.1f}]")
            print(f"    Velocity: [{track.state.velocity[0]:.1f}, "
                  f"{track.state.velocity[1]:.1f}, {track.state.velocity[2]:.1f}]")
        
        return True
    else:
        print("\n❌ FAILED: No confirmed tracks created!")
        return False


if __name__ == '__main__':
    success = test_track_confirmation()
    sys.exit(0 if success else 1)
