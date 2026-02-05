#!/usr/bin/env python3
"""
Main Entry Point for Particle Filter Drone Tracker

Usage:
    python main.py --mode gui                    # Launch GUI
    python main.py --mode sim --scenario single_straight   # Run simulation
    python main.py --mode batch --config configs/  # Batch parameter study
"""

import argparse
import sys
from pathlib import Path

# Add tracker_framework to path
sys.path.insert(0, str(Path(__file__).parent))

from tracker_framework.gui.main_window import launch_gui, PYQT_AVAILABLE


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Particle Filter Drone Tracking Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch interactive GUI
  python main.py --mode gui
  
  # Run single simulation
  python main.py --mode sim --scenario single_straight --config configs/default_config.json
  
  # Run batch parameter study
  python main.py --mode batch --study-config configs/parameter_study.json
  
  # Show available scenarios
  python main.py --list-scenarios
        """
    )
    
    parser.add_argument('--mode', type=str, default='gui',
                       choices=['gui', 'sim', 'batch'],
                       help='Execution mode: gui, sim, or batch')
    
    parser.add_argument('--scenario', type=str, default='single_straight',
                       help='Scenario name (for sim mode)')
    
    parser.add_argument('--config', type=str, default='tracker_framework/configs/default_config.json',
                       help='Configuration file path')
    
    parser.add_argument('--study-config', type=str,
                       help='Parameter study configuration (for batch mode)')
    
    parser.add_argument('--list-scenarios', action='store_true',
                       help='List available scenarios')
    
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for results')
    
    parser.add_argument('--no-visualization', action='store_true',
                       help='Disable visualization (faster)')
    
    args = parser.parse_args()
    
    # List scenarios
    if args.list_scenarios:
        from tracker_framework.simulation.radar_simulator import create_standard_scenarios
        scenarios = create_standard_scenarios()
        print("\n=== Available Scenarios ===")
        for name, (_, description) in scenarios.items():
            print(f"  {name}: {description}")
        print()
        return
    
    # Execute based on mode
    if args.mode == 'gui':
        print("Launching GUI...")
        if not PYQT_AVAILABLE:
            print("ERROR: PyQt5 not installed. Install with: pip install PyQt5")
            return
        launch_gui()
    
    elif args.mode == 'sim':
        print(f"Running simulation: {args.scenario}")
        from examples.run_simulation import run_single_simulation
        run_single_simulation(args.scenario, args.config, args.output_dir, 
                            not args.no_visualization)
    
    elif args.mode == 'batch':
        print("Running batch parameter study...")
        from examples.parameter_study import run_parameter_study
        run_parameter_study(args.study_config or args.config, args.output_dir)


if __name__ == '__main__':
    main()
