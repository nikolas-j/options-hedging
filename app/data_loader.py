"""Data loading and file discovery utilities for options hedging dashboard."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime


def discover_market_files(market_dir: str = "market_2023") -> List[Dict[str, str]]:
    """
    Auto-detect all .feather files in market directory.
    
    Args:
        market_dir: Directory path containing market data files
        
    Returns:
        List of dicts with file metadata: {'path', 'filename', 'expiration'}
    """
    market_path = Path(market_dir)
    if not market_path.exists():
        return []
    
    files = []
    for file_path in sorted(market_path.glob("*.feather")):
        try:
            # Extract expiration date from filename: SPY.P{YYYY-MM-DD}.feather
            expiration_str = file_path.stem.split('SPY.P')[1]
            expiration_date = pd.to_datetime(expiration_str)
            
            files.append({
                'path': str(file_path),
                'filename': file_path.name,
                'expiration': expiration_date.strftime('%Y-%m-%d'),
                'expiration_display': expiration_date.strftime('%b %d, %Y')
            })
        except (IndexError, ValueError):
            # Skip files that don't match expected pattern
            continue
    
    return files


def load_option_data(filepath: str) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """
    Load option data from feather file and extract metadata.
    
    Args:
        filepath: Path to feather file
        
    Returns:
        Tuple of (DataFrame, metadata_dict)
        metadata contains: 'expiration', 'available_strikes', 'date_range'
    """
    # Load data
    df = pd.read_feather(filepath)
    
    # Convert Date column to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Convert numeric columns
    numeric_cols = [col for col in df.columns if col != 'Date']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Extract available strike columns (C followed by digits)
    call_cols = [col for col in df.columns if col.startswith('C') and col[1:].isdigit()]
    available_strikes = sorted([int(col[1:]) for col in call_cols])
    
    # Get date range
    date_range = {
        'start': df['Date'].min(),
        'end': df['Date'].max(),
        'start_str': df['Date'].min().strftime('%Y-%m-%d'),
        'end_str': df['Date'].max().strftime('%Y-%m-%d')
    }
    
    # Extract expiration from filename
    try:
        expiration_str = Path(filepath).stem.split('SPY.P')[1]
        expiration = pd.to_datetime(expiration_str).strftime('%Y-%m-%d')
    except (IndexError, ValueError):
        expiration = date_range['end_str']
    
    metadata = {
        'expiration': expiration,
        'available_strikes': available_strikes,
        'date_range': date_range,
        'total_rows': len(df)
    }
    
    return df, metadata


def prepare_strategy_data(df: pd.DataFrame, strike: int, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Prepare data for strategy execution by selecting strike column and filtering dates.
    
    Args:
        df: Full option data DataFrame
        strike: Selected strike price
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        
    Returns:
        Filtered DataFrame with columns: Date, Underlying, C{strike}
    """
    call_col = f'C{strike}'
    
    if call_col not in df.columns:
        raise ValueError(f"Strike {strike} not available in data")
    
    # Select relevant columns
    strategy_df = df[['Date', 'Underlying', call_col]].copy()
    
    # Drop rows with NA values
    na_count = strategy_df[call_col].isna().sum()
    if na_count > 0:
        strategy_df = strategy_df.dropna(subset=[call_col])
    
    # Apply date filters
    if start_date:
        start_dt = pd.to_datetime(start_date)
        strategy_df = strategy_df[strategy_df['Date'] >= start_dt]
    
    if end_date:
        end_dt = pd.to_datetime(end_date)
        strategy_df = strategy_df[strategy_df['Date'] <= end_dt]
    
    # Reset index
    strategy_df = strategy_df.reset_index(drop=True)
    
    return strategy_df


def get_common_dates(data_a: pd.DataFrame, data_b: pd.DataFrame) -> pd.Series:
    """
    Get common trading dates between two datasets.
    
    Args:
        data_a: First DataFrame with 'Date' column
        data_b: Second DataFrame with 'Date' column
        
    Returns:
        Series of common dates
    """
    common_dates = pd.merge(
        data_a[['Date']], 
        data_b[['Date']], 
        on='Date', 
        how='inner'
    )['Date']
    
    return common_dates.sort_values().reset_index(drop=True)


def validate_delta_gamma_files(primary_file: Dict, hedge_file: Dict) -> Tuple[bool, str]:
    """
    Validate that two files are compatible for delta-gamma hedging.
    
    Args:
        primary_file: Primary option file metadata
        hedge_file: Hedge option file metadata
        
    Returns:
        Tuple of (is_valid, message)
    """
    primary_exp = pd.to_datetime(primary_file['expiration'])
    hedge_exp = pd.to_datetime(hedge_file['expiration'])
    
    if primary_exp >= hedge_exp:
        return False, f"Hedge option must expire after primary option. Primary: {primary_file['expiration']}, Hedge: {hedge_file['expiration']}"
    
    return True, "Files are compatible"


def check_date_overlap(data_a: pd.DataFrame, data_b: pd.DataFrame) -> Tuple[bool, str, Optional[Tuple[str, str]]]:
    """
    Check if two datasets have overlapping dates.
    
    Args:
        data_a: First DataFrame
        data_b: Second DataFrame
        
    Returns:
        Tuple of (has_overlap, message, date_range)
        date_range is (start_date, end_date) if overlap exists, None otherwise
    """
    common_dates = get_common_dates(data_a, data_b)
    
    if len(common_dates) == 0:
        return False, "No overlapping dates between selected files", None
    
    start_date = common_dates.min().strftime('%Y-%m-%d')
    end_date = common_dates.max().strftime('%Y-%m-%d')
    
    message = f"Found {len(common_dates)} common trading days ({start_date} to {end_date})"
    
    return True, message, (start_date, end_date)
