#!/usr/bin/env python3
"""
Checkpoint and Resume Demo
Demonstrates how the system saves progress and can resume from interruptions.
"""

import sys
import os
import time
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.value_analysis import run_stock_analysis

def demo_checkpoint_resume():
    """Demonstrate checkpoint and resume functionality."""
    
    print("🧪 CHECKPOINT & RESUME DEMO")
    print("=" * 50)
    
    # Test with a small list of stocks
    test_stocks = [
        'AAPL', 'MSFT', 'GOOGL', 'BRK-B', 'JNJ', 
        'XOM', 'JPM', 'PG', 'KO', 'WMT',
        'META', 'NVDA', 'TSLA', 'UNH', 'HD'
    ]
    
    output_file = "checkpoint_demo_results.csv"
    
    print(f"📋 Testing with {len(test_stocks)} stocks")
    print(f"💾 Output file: {output_file}")
    print(f"🔄 Checkpoint interval: Every 2 qualifying stocks")
    print()
    
    # Check if file already exists
    if os.path.exists(output_file):
        print(f"📂 Found existing file: {output_file}")
        df_existing = pd.read_csv(output_file)
        print(f"📊 Already processed: {len(df_existing)} stocks")
        print(f"🎯 Qualifying stocks: {df_existing['symbol'].tolist()}")
        print()
        
        # Ask user if they want to resume or start fresh
        response = input("🔄 Resume from existing file? (y/n): ").lower().strip()
        if response != 'y':
            print("🗑️  Removing existing file and starting fresh...")
            os.remove(output_file)
            print()
    
    print("🚀 Starting analysis...")
    print("💡 Tip: You can interrupt this with Ctrl+C to test resume functionality")
    print()
    
    try:
        # Run analysis with frequent checkpoints
        df_results = run_stock_analysis(
            symbol_list=test_stocks,
            output_path=output_file,
            criteria_level="relaxed",  # Use relaxed criteria to get more qualifying stocks
            batch_size=3,  # Small batches for demo
            max_openai_calls=0,  # No AI calls for faster demo
            checkpoint_interval=2  # Save every 2 qualifying stocks
        )
        
        print("\n✅ Analysis completed successfully!")
        print(f"📊 Final results: {len(df_results)} qualifying stocks")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Analysis interrupted by user!")
        print("💾 Progress has been saved to checkpoint file")
        print("🔄 You can resume by running this script again")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        print("💾 Any progress up to this point has been saved")

def show_checkpoint_info():
    """Show information about checkpoint functionality."""
    
    print("📋 CHECKPOINT SYSTEM OVERVIEW")
    print("=" * 50)
    print()
    print("🔄 AUTOMATIC RESUME:")
    print("   • System checks for existing output file")
    print("   • Skips already processed tickers")
    print("   • Continues from where it left off")
    print()
    print("💾 PERIODIC SAVING:")
    print("   • Saves every N qualifying stocks (default: 10)")
    print("   • Uses atomic file operations for safety")
    print("   • Fallback save mechanism if primary fails")
    print()
    print("🛡️  SAFETY FEATURES:")
    print("   • Temporary file creation before final save")
    print("   • Atomic file replacement (os.replace)")
    print("   • Error handling with fallback saves")
    print("   • Progress tracking in monitoring dashboard")
    print()
    print("📁 FILE MANAGEMENT:")
    print("   • Creates .tmp files during saves")
    print("   • Automatically cleans up temporary files")
    print("   • Preserves original file if save fails")
    print()

if __name__ == "__main__":
    show_checkpoint_info()
    print("-" * 50)
    demo_checkpoint_resume() 