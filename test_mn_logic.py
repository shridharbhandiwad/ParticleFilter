#!/usr/bin/env python3
"""
Test M/N track confirmation logic with missed detections
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tracker_framework.core.state import StateType, Measurement
from tracker_framework.models.motion_models import ConstantVelocityModel
from tracker_framework.models.measurement_models import RadarMeasurementModel
from tracker_framework.filters.multi_target_tracker import MultiTargetTracker


def test_mn_with_misses():
    """Test M/N logic: 3 hits out of 4 scans with one missed detection."""
    
    print("\n" + "="*70)
    print("Testing M/N Confirmation Logic (3/4) with Missed Detection")
    print("="*70 + "\n")
    
    tracker = MultiTargetTracker(
        motion_model=ConstantVelocityModel(),
        measurement_model=RadarMeasurementModel(),
        num_particles=500,
        confirmation_threshold=3,  # M = 3 hits out of N = 4 scans
        termination_threshold=5,
        state_type=StateType.CV
    )
    
    scan_period = 0.1
    
    # Test pattern: Hit, Miss, Hit, Hit -> Should confirm on scan 3
    detection_pattern = [True, False, True, True, True, True]
    
    print("Detection pattern: Hit, Miss, Hit, Hit, Hit, Hit")
    print("Expected: Track confirmed at scan 3 (age=4)\n")
    print("-" * 70)
    
    for scan_idx, should_detect in enumerate(detection_pattern):
        timestamp = scan_idx * scan_period
        
        measurements = []
        
        if should_detect:
            # Generate measurement
            pos_x = 1000 + 10 * timestamp
            pos_y = 500 + 5 * timestamp
            pos_z = 100
            
            r = np.sqrt(pos_x**2 + pos_y**2 + pos_z**2)
            az = np.arctan2(pos_y, pos_x)
            el = np.arcsin(pos_z / r)
            
            r += np.random.normal(0, 2.0)
            az += np.random.normal(0, np.radians(0.2))
            el += np.random.normal(0, np.radians(0.2))
            
            measurements.append(Measurement(
                range=r, azimuth=az, elevation=el, timestamp=timestamp
            ))
        
        # Update tracker
        tracker.update(measurements, timestamp)
        
        stats = tracker.get_statistics()
        
        detection_str = "HIT " if should_detect else "MISS"
        print(f"Scan {scan_idx} ({detection_str}): Total={stats['total_tracks']}, "
              f"Confirmed={stats['confirmed_tracks']}, Tentative={stats['tentative_tracks']}")
        
        for track_id, track in tracker.tracks.items():
            print(f"  Track {track_id}: age={track.age}, hits={track.hits}, "
                  f"history={track.hit_history[-4:]}, confirmed={track.confirmed}")
    
    print("\n" + "="*70)
    
    # Verify results
    final_stats = tracker.get_statistics()
    if final_stats['confirmed_tracks'] > 0:
        print("✅ SUCCESS: Track confirmed despite missed detection!")
        print(f"   M/N logic (3/4) working correctly")
        return True
    else:
        print("❌ FAILED: Track not confirmed")
        return False


def test_no_confirmation_insufficient_hits():
    """Test that track doesn't confirm with only 2/4 hits."""
    
    print("\n" + "="*70)
    print("Testing M/N Logic: Track should NOT confirm with 2/4 hits")
    print("="*70 + "\n")
    
    tracker = MultiTargetTracker(
        motion_model=ConstantVelocityModel(),
        measurement_model=RadarMeasurementModel(),
        num_particles=500,
        confirmation_threshold=3,
        termination_threshold=5,
        state_type=StateType.CV
    )
    
    scan_period = 0.1
    
    # Test pattern: Hit, Miss, Hit, Miss -> Should NOT confirm (only 2/4)
    detection_pattern = [True, False, True, False]
    
    print("Detection pattern: Hit, Miss, Hit, Miss")
    print("Expected: Track NOT confirmed (only 2/4 hits)\n")
    print("-" * 70)
    
    for scan_idx, should_detect in enumerate(detection_pattern):
        timestamp = scan_idx * scan_period
        
        measurements = []
        
        if should_detect:
            pos_x = 1000 + 10 * timestamp
            pos_y = 500 + 5 * timestamp
            pos_z = 100
            
            r = np.sqrt(pos_x**2 + pos_y**2 + pos_z**2)
            az = np.arctan2(pos_y, pos_x)
            el = np.arcsin(pos_z / r)
            
            r += np.random.normal(0, 2.0)
            az += np.random.normal(0, np.radians(0.2))
            el += np.random.normal(0, np.radians(0.2))
            
            measurements.append(Measurement(
                range=r, azimuth=az, elevation=el, timestamp=timestamp
            ))
        
        tracker.update(measurements, timestamp)
        
        stats = tracker.get_statistics()
        detection_str = "HIT " if should_detect else "MISS"
        print(f"Scan {scan_idx} ({detection_str}): Total={stats['total_tracks']}, "
              f"Confirmed={stats['confirmed_tracks']}, Tentative={stats['tentative_tracks']}")
        
        for track_id, track in tracker.tracks.items():
            print(f"  Track {track_id}: age={track.age}, hits={track.hits}, "
                  f"history={track.hit_history}, confirmed={track.confirmed}")
    
    print("\n" + "="*70)
    
    # Verify results
    final_stats = tracker.get_statistics()
    if final_stats['confirmed_tracks'] == 0:
        print("✅ SUCCESS: Track correctly NOT confirmed with only 2/4 hits")
        return True
    else:
        print("❌ FAILED: Track incorrectly confirmed")
        return False


if __name__ == '__main__':
    test1 = test_mn_with_misses()
    test2 = test_no_confirmation_insufficient_hits()
    
    print("\n" + "="*70)
    print("OVERALL TEST RESULTS")
    print("="*70)
    print(f"Test 1 (3/4 with miss): {'PASS' if test1 else 'FAIL'}")
    print(f"Test 2 (2/4 no confirm): {'PASS' if test2 else 'FAIL'}")
    print()
    
    sys.exit(0 if (test1 and test2) else 1)
