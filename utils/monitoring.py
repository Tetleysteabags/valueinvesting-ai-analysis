#!/usr/bin/env python3
"""
Monitoring System for Value Investing AI Pipeline
Provides real-time progress tracking and status updates.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys

class PipelineMonitor:
    """Real-time monitoring system for the value investing pipeline."""
    
    def __init__(self, total_stocks: int, batch_size: int = 50):
        self.total_stocks = total_stocks
        self.batch_size = batch_size
        self.processed_stocks = 0
        self.qualifying_stocks = 0
        self.failed_stocks = 0
        self.current_batch = 0
        self.start_time = None
        self.last_update_time = None
        self.qualifying_list = []
        self.failed_list = []
        self.current_stock = ""
        self.status = "idle"
        self.lock = threading.Lock()
        
        # Performance tracking
        self.batch_times = []
        self.api_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
    def start(self):
        """Start the monitoring system."""
        with self.lock:
            self.start_time = datetime.now()
            self.last_update_time = self.start_time
            self.status = "running"
            self._print_header()
    
    def update_progress(self, processed: int, qualifying: int, failed: int, 
                       current_stock: str = "", batch_num: int = 0,
                       api_calls: int = 0, cache_hits: int = 0, cache_misses: int = 0):
        """Update progress metrics."""
        with self.lock:
            self.processed_stocks = processed
            self.qualifying_stocks = qualifying
            self.failed_stocks = failed
            self.current_stock = current_stock
            self.current_batch = batch_num
            self.api_calls = api_calls
            self.cache_hits = cache_hits
            self.cache_misses = cache_misses
            self._print_progress()
    
    def add_qualifying_stock(self, ticker: str):
        """Add a qualifying stock to the list."""
        with self.lock:
            if ticker not in self.qualifying_list:
                self.qualifying_list.append(ticker)
    
    def add_failed_stock(self, ticker: str, reason: str = ""):
        """Add a failed stock to the list."""
        with self.lock:
            if ticker not in [f[0] for f in self.failed_list]:
                self.failed_list.append((ticker, reason))
    
    def record_batch_time(self, batch_time: float):
        """Record the time taken for a batch."""
        with self.lock:
            self.batch_times.append(batch_time)
    
    def complete(self):
        """Mark the pipeline as completed."""
        with self.lock:
            self.status = "completed"
            self._print_final_summary()
    
    def error(self, error_msg: str):
        """Handle pipeline errors."""
        with self.lock:
            self.status = "error"
            self._print_error(error_msg)
    
    def _print_header(self):
        """Print the monitoring header."""
        print("\n" + "="*80)
        print("🚀 VALUE INVESTING AI PIPELINE - MONITORING DASHBOARD")
        print("="*80)
        print(f"📅 Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total Stocks: {self.total_stocks:,}")
        print(f"📦 Batch Size: {self.batch_size}")
        print(f"🔄 Total Batches: {(self.total_stocks + self.batch_size - 1) // self.batch_size}")
        print("-"*80)
    
    def _print_progress(self):
        """Print current progress."""
        if not self.start_time:
            return
            
        current_time = datetime.now()
        elapsed = current_time - self.start_time
        
        # Calculate progress percentages
        progress_pct = (self.processed_stocks / self.total_stocks) * 100 if self.total_stocks > 0 else 0
        success_rate = (self.qualifying_stocks / self.processed_stocks) * 100 if self.processed_stocks > 0 else 0
        
        # Calculate ETA
        if self.processed_stocks > 0:
            avg_time_per_stock = elapsed.total_seconds() / self.processed_stocks
            remaining_stocks = self.total_stocks - self.processed_stocks
            eta_seconds = remaining_stocks * avg_time_per_stock
            eta = timedelta(seconds=int(eta_seconds))
        else:
            eta = timedelta(0)
        
        # Calculate API efficiency
        total_api_calls = self.cache_hits + self.cache_misses
        cache_efficiency = (self.cache_hits / total_api_calls * 100) if total_api_calls > 0 else 0
        
        # Clear previous lines and print progress
        print(f"\r{' ' * 100}", end='\r')  # Clear line
        
        print(f"📈 PROGRESS: {self.processed_stocks:,}/{self.total_stocks:,} ({progress_pct:.1f}%)")
        print(f"⏱️  Elapsed: {str(elapsed).split('.')[0]} | ETA: {str(eta).split('.')[0]}")
        print(f"🎯 Qualifying: {self.qualifying_stocks} | Failed: {self.failed_stocks} | Success Rate: {success_rate:.1f}%")
        print(f"📦 Batch: {self.current_batch} | Current: {self.current_stock}")
        print(f"🌐 API Calls: {self.api_calls} | Cache: {cache_efficiency:.1f}% hit rate")
        
        # Progress bar
        bar_length = 50
        filled_length = int(bar_length * progress_pct / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f"📊 [{bar}] {progress_pct:.1f}%")
        
        # Recent qualifying stocks
        if self.qualifying_list:
            recent = self.qualifying_list[-5:]  # Last 5
            print(f"✅ Recent Qualifiers: {', '.join(recent)}")
        
        print("-" * 80)
    
    def _print_final_summary(self):
        """Print final summary when pipeline completes."""
        if not self.start_time:
            return
            
        end_time = datetime.now()
        total_time = end_time - self.start_time
        
        print("\n" + "="*80)
        print("🎉 PIPELINE COMPLETED!")
        print("="*80)
        print(f"⏱️  Total Time: {str(total_time).split('.')[0]}")
        print(f"📊 Processed: {self.processed_stocks:,} stocks")
        print(f"✅ Qualifying: {self.qualifying_stocks} stocks")
        print(f"❌ Failed: {self.failed_stocks} stocks")
        print(f"📈 Success Rate: {(self.qualifying_stocks/self.processed_stocks*100):.2f}%" if self.processed_stocks > 0 else "N/A")
        
        if self.batch_times:
            avg_batch_time = sum(self.batch_times) / len(self.batch_times)
            print(f"📦 Avg Batch Time: {avg_batch_time:.2f}s")
        
        total_api_calls = self.cache_hits + self.cache_misses
        if total_api_calls > 0:
            print(f"🌐 Total API Calls: {total_api_calls}")
            print(f"🔥 Cache Hits: {self.cache_hits} ({self.cache_hits/total_api_calls*100:.1f}%)")
            print(f"❄️  Cache Misses: {self.cache_misses} ({self.cache_misses/total_api_calls*100:.1f}%)")
        
        if self.qualifying_list:
            print(f"\n🎯 All Qualifying Stocks ({len(self.qualifying_list)}):")
            print(f"   {', '.join(self.qualifying_list)}")
        
        print("="*80)
    
    def _print_error(self, error_msg: str):
        """Print error message."""
        print(f"\n❌ PIPELINE ERROR: {error_msg}")
        print(f"⏱️  Failed after: {str(datetime.now() - self.start_time).split('.')[0]}")
        print(f"📊 Processed: {self.processed_stocks:,}/{self.total_stocks:,} stocks")
        print("="*80)

class ProgressTracker:
    """Simple progress tracker for individual operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, increment: int = 1):
        """Update progress."""
        self.current += increment
        self._print_progress()
    
    def _print_progress(self):
        """Print current progress."""
        progress = (self.current / self.total) * 100
        elapsed = time.time() - self.start_time
        
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
        else:
            eta = 0
        
        print(f"\r{self.description}: {self.current}/{self.total} ({progress:.1f}%) | "
              f"Elapsed: {elapsed:.1f}s | ETA: {eta:.1f}s", end='', flush=True)
    
    def complete(self):
        """Mark as completed."""
        total_time = time.time() - self.start_time
        print(f"\n✅ {self.description} completed in {total_time:.2f}s")

def create_monitor(total_stocks: int, batch_size: int = 50) -> PipelineMonitor:
    """Create a new pipeline monitor."""
    return PipelineMonitor(total_stocks, batch_size) 