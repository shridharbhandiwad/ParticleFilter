# Particle Filter Track Confirmation Algorithm

## Overview

This document describes the proper implementation of the particle filter multi-target tracking algorithm with M/N track confirmation logic.

## Algorithm Components

### 1. Track Initiation

When an unassociated measurement is detected, a new track is initiated with the following steps:

```
FUNCTION InitiateTrack(measurement, current_time):
    1. Convert measurement to Cartesian state
       - Position: from spherical to Cartesian coordinates
       - Velocity: initialized to zero (estimated over time)
    
    2. Create particle filter
       - Initialize particle cloud around measurement with high uncertainty
       - Position std: ~22m (500 variance)
       - Velocity std: ~10 m/s (100 variance)
    
    3. CRITICAL: Immediately update particle filter with initiating measurement
       - Compute likelihood for all particles
       - Update particle weights based on measurement likelihood
       - Resample particles to reduce degeneracy
       - This ensures proper particle weighting from the start
    
    4. Estimate initial state from updated particles
    
    5. Create track with initial statistics:
       - age = 1 (track has existed for 1 scan)
       - hits = 1 (initiating measurement counts as first hit)
       - misses = 0
       - hit_history = [1] (record the initial hit)
       - confirmed = False (not yet confirmed)
    
    6. Compute initial track quality
    
    RETURN track
```

**Key Fix**: The initiating measurement is now properly used to update the particle filter weights, not just initialize particle positions. This was the primary bug preventing track confirmation.

### 2. M/N Track Confirmation

Tracks are confirmed using M/N logic, where a track needs **M hits out of the last N scans** to be confirmed.

**Default Parameters:**
- M = 3 hits (confirmation_threshold)
- N = 4 scans (confirmation_threshold + 1)

```
FUNCTION IsConfirmed(track, m_hits, n_scans):
    1. If track is already confirmed:
       RETURN True (once confirmed, always confirmed)
    
    2. If track age < n_scans:
       RETURN False (need minimum N scans to evaluate)
    
    3. Count recent hits in last N scans:
       recent_hits = sum(track.hit_history[-n_scans:])
    
    4. If recent_hits >= m_hits:
       track.confirmed = True
       RETURN True
    
    5. RETURN False
```

**Examples:**

| Scan | Detection | Hit History | Age | Hits | Recent Hits (last 4) | Confirmed? |
|------|-----------|-------------|-----|------|---------------------|------------|
| 0    | ✓         | [1]         | 1   | 1    | N/A                | No (age < 4) |
| 1    | ✓         | [1,1]       | 2   | 2    | N/A                | No (age < 4) |
| 2    | ✓         | [1,1,1]     | 3   | 3    | N/A                | No (age < 4) |
| 3    | ✓         | [1,1,1,1]   | 4   | 4    | 4/4 = 4            | **YES** ✓    |
| 4    | ✗         | [1,1,1,1,0] | 5   | 4    | 3/4 = 3            | YES (stays) |

**With Missed Detection:**

| Scan | Detection | Hit History | Age | Hits | Recent Hits (last 4) | Confirmed? |
|------|-----------|-------------|-----|------|---------------------|------------|
| 0    | ✓         | [1]         | 1   | 1    | N/A                | No (age < 4) |
| 1    | ✗         | [1,0]       | 2   | 1    | N/A                | No (age < 4) |
| 2    | ✓         | [1,0,1]     | 3   | 2    | N/A                | No (age < 4) |
| 3    | ✓         | [1,0,1,1]   | 4   | 3    | 3/4 = 3            | **YES** ✓    |

### 3. Track Update Process

For each scan:

```
FUNCTION Update(measurements, current_time):
    1. Predict all tracks to current time
       FOR each track:
           track.filter.predict(dt)
           track.state = track.filter.estimate()
    
    2. Measurement gating
       FOR each track:
           FOR each measurement:
               IF measurement passes gate:
                   Add to candidate list
    
    3. Data association (Global Nearest Neighbor)
       - Build cost matrix using measurement likelihoods
       - Solve assignment problem
       - RETURN associations {track_id -> measurement_index}
    
    4. Update tracks
       FOR each track:
           IF track has associated measurement:
               - Update particle filter with measurement
               - Resample particles
               - Increment hits
               - Reset misses to 0
               - Append 1 to hit_history
           ELSE:
               - Increment misses
               - Append 0 to hit_history
           
           - Increment age
           - Update track quality
           - Check confirmation status
           - Update state estimate
    
    5. Track management
       - Initiate new tracks from unassociated measurements
       - Terminate dead tracks (excessive misses or low quality)
```

### 4. Track Quality Assessment

Track quality is computed as a weighted combination of hit ratio and particle filter quality:

```
FUNCTION UpdateTrackQuality(track):
    1. Compute hit ratio:
       hit_ratio = track.hits / track.age
    
    2. Get particle filter quality:
       filter_quality = track.filter.track_quality
       (based on effective sample size and weight entropy)
    
    3. Combine qualities:
       quality = 0.6 * hit_ratio + 0.4 * filter_quality
    
    4. Penalize consecutive misses:
       IF track.misses > 0:
           quality *= 0.85^(track.misses)
    
    track.quality = quality
```

### 5. Track Termination

Tracks are terminated when:

```
FUNCTION IsTerminated(track, max_misses, min_quality):
    1. Confirmed tracks are more tolerant:
       miss_threshold = max_misses * 2 IF confirmed ELSE max_misses
    
    2. Check termination criteria:
       RETURN (track.misses >= miss_threshold) OR 
              (track.quality < min_quality)
```

**Default thresholds:**
- Tentative tracks: 5 consecutive misses
- Confirmed tracks: 10 consecutive misses
- Minimum quality: 0.2

## Benefits of M/N Logic

1. **Robustness to missed detections**: Tracks can miss 1 out of 4 scans and still confirm
2. **Lower false track rate**: Requires consistent detections before confirmation
3. **Faster confirmation**: Confirms in 4 scans (was requiring more with old logic)
4. **Stable confirmed tracks**: Once confirmed, tracks are more tolerant to misses

## Performance Characteristics

- **Confirmation time**: 4 scans minimum (0.4 seconds at 10 Hz)
- **Tentative track lifetime**: Up to 5 missed scans before termination
- **Confirmed track lifetime**: Up to 10 missed scans before termination
- **Particle count**: 500-1000 particles per track (configurable)
- **Processing time**: ~1-2 ms per track per scan (depends on particle count)

## References

- Bar-Shalom, Y., et al. "Estimation with Applications to Tracking and Navigation"
- Ristic, B., et al. "Beyond the Kalman Filter: Particle Filters for Tracking Applications"
- Reid, D. "An Algorithm for Tracking Multiple Targets" (MHT foundation)
