#!/usr/bin/env python3
"""
Extract High Score Tickers
Extracts tickers with a score of 8 and above from gpt_ranking.csv
"""

import pandas as pd
import sys
from pathlib import Path

def extract_high_score_tickers(csv_file='ValueInvesting-AI-Analysis/gpt_ranking.csv', min_score=8, output_file=None):
    """
    Extract tickers with scores >= min_score from the CSV file.
    
    Args:
        csv_file: Path to the CSV file containing ticker rankings
        min_score: Minimum score threshold (default: 8)
        output_file: Optional output file to save results
    
    Returns:
        DataFrame with high-scoring tickers
    """
    try:
        # Read the CSV file
        print(f"📊 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        
        # Check if required columns exist
        required_columns = ['ticker', 'score']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Error: Missing required columns: {missing_columns}")
            print(f"Available columns: {list(df.columns)}")
            return None
        
        # Filter for high-scoring tickers
        high_score_df = df[df['score'] >= min_score].copy()
        
        # Sort by score (descending) and then by ticker
        high_score_df = high_score_df.sort_values(['score', 'ticker'], ascending=[False, True])
        
        # Print summary
        print(f"📈 Summary:")
        print(f"   • Total tickers in file: {len(df)}")
        print(f"   • Tickers with score >= {min_score}: {len(high_score_df)}")
        print(f"   • Score distribution:")
        score_counts = df['score'].value_counts().sort_index()
        for score, count in score_counts.items():
            print(f"     - Score {score}: {count} tickers")
        
        # Print high-scoring tickers
        print(f"\n🎯 High-Scoring Tickers (Score >= {min_score}):")
        print("=" * 80)
        for _, row in high_score_df.iterrows():
            print(f"{row['ticker']:<8} | Score: {row['score']} | {row['reason'][:70]}...")
            
        # Return just the tickers as a list
        high_score_tickers = high_score_df['ticker'].tolist()
        
        # Format for backtesting - Python list format
        tickers_formatted = "[" + ", ".join([f"'{ticker}'" for ticker in high_score_tickers]) + "]"
        
        print(f"\n📋 High-score tickers for backtesting ({len(high_score_tickers)} tickers):")
        print("=" * 80)
        print(tickers_formatted)
        print("=" * 80)
        
        # Also save as a simple text file with one ticker per line
        tickers_file = output_file.replace('.csv', '_tickers.txt') if output_file else 'high_score_tickers_8.txt'
        with open(tickers_file, 'w') as f:
            for ticker in high_score_tickers:
                f.write(f"{ticker}\n")
        print(f"\n💾 Tickers saved to: {tickers_file}")
        
        # Save to file if requested
        if output_file:
            high_score_df.to_csv(output_file, index=False)
            print(f"💾 Full results saved to: {output_file}")
        
        return high_score_df
        
    except FileNotFoundError:
        print(f"❌ Error: File '{csv_file}' not found")
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

def main():
    """Main function to run the extraction."""
    # Default values
    csv_file = 'ValueInvesting-AI-Analysis/gpt_ranking.csv'
    min_score = 8
    output_file = 'high_score_tickers_8.csv'
    
    # Check command line arguments
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            min_score = int(sys.argv[2])
        except ValueError:
            print("❌ Error: min_score must be an integer")
            return
    
    print(f"🔍 Extracting tickers with score >= {min_score} from {csv_file}")
    print("=" * 60)
    
    # Run the extraction
    result = extract_high_score_tickers(csv_file, min_score, output_file)
    
    if result is not None:
        print(f"\n✅ Extraction complete!")
        print(f"📊 Found {len(result)} tickers with score >= {min_score}")
    else:
        print(f"\n❌ Extraction failed!")

if __name__ == "__main__":
    main() 