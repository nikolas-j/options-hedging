"""Strategy execution wrappers for hedging dashboard."""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from app.strategies import run_delta_hedge, run_gamma_hedge
from app.data_loader import prepare_strategy_data, get_common_dates


def execute_delta_hedge(
    df: pd.DataFrame,
    strike: int,
    config: Dict,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[bool, Optional[Dict], str]:
    """
    Execute delta hedging strategy.
    
    Args:
        df: Option data DataFrame
        strike: Selected strike price
        config: Strategy configuration dict
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        
    Returns:
        Tuple of (success, results_dict, message)
    """
    try:
        # Prepare data
        strategy_data = prepare_strategy_data(df, strike, start_date, end_date)
        
        if len(strategy_data) == 0:
            return False, None, "No data available after filtering"
        
        # Run delta hedging
        results = run_delta_hedge(
            data=strategy_data,
            strike=strike,
            config=config,
            start_date=start_date,
            end_date=end_date
        )
        
        # Compute summary metrics from lists
        pnl_list = results['pnl']
        results['final_pnl'] = pnl_list[-1]
        results['mse_pnl'] = sum(p**2 for p in pnl_list) / len(pnl_list)
        initial_opt_val = results['call_prices'][0] * config['n_options']
        results['normalized_mse'] = results['mse_pnl'] / (initial_opt_val ** 2) if initial_opt_val > 0 else 0
        results['total_tx_cost'] = sum(results['transaction_costs'])
        results['total_volume'] = sum(results['trade_volume'])
        results['trading_days'] = len(results['dates'])
        results['avg_daily_trades'] = results['total_volume'] / results['trading_days'] if results['trading_days'] > 0 else 0
        results['pnl_std'] = (sum((p - sum(pnl_list)/len(pnl_list))**2 for p in pnl_list) / len(pnl_list)) ** 0.5
        results['pnl_min'] = min(pnl_list)
        results['pnl_max'] = max(pnl_list)
        results['initial_option_value'] = initial_opt_val
        
        # Add field mappings for visualizations
        results['hedge_ratios'] = results['deltas']
        results['stock_positions'] = results['shares_held']
        results['option_values'] = [c * config['n_options'] for c in results['call_prices']]
        results['stock_position_values'] = [s * spot for s, spot in zip(results['shares_held'], results['spot'])]
        results['portfolio_values'] = [ov + sv for ov, sv in zip(results['option_values'], results['stock_position_values'])]
        results['cumulative_tx_costs'] = results['cumulative_transaction_cost']
        
        # Add metadata
        results['strike'] = strike
        results['start_date'] = strategy_data['Date'].min().strftime('%Y-%m-%d')
        results['end_date'] = strategy_data['Date'].max().strftime('%Y-%m-%d')
        results['strategy_type'] = 'delta_hedge'
        
        return True, results, "Delta hedging completed successfully"
        
    except Exception as e:
        return False, None, f"Error executing delta hedge: {str(e)}"


def execute_delta_gamma_hedge(
    df_primary: pd.DataFrame,
    df_hedge: pd.DataFrame,
    strike_primary: int,
    strike_hedge: int,
    config: Dict,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[bool, Optional[Dict], str]:
    """
    Execute delta-gamma hedging strategy.
    
    Args:
        df_primary: Primary option data DataFrame
        df_hedge: Hedge option data DataFrame
        strike_primary: Primary option strike
        strike_hedge: Hedge option strike
        config: Strategy configuration dict
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        
    Returns:
        Tuple of (success, results_dict, message)
    """
    try:
        # Prepare data for both options
        data_a = prepare_strategy_data(df_primary, strike_primary, start_date, end_date)
        data_b = prepare_strategy_data(df_hedge, strike_hedge, start_date, end_date)
        
        if len(data_a) == 0 or len(data_b) == 0:
            return False, None, "Insufficient data after filtering"
        
        # Check for common dates
        common_dates = get_common_dates(data_a, data_b)
        if len(common_dates) == 0:
            return False, None, "No overlapping dates between the two options"
        
        # Run delta-gamma hedging
        results = run_gamma_hedge(
            data_A=data_a,
            data_B=data_b,
            strike_A=strike_primary,
            strike_B=strike_hedge,
            config=config,
            start_date=start_date,
            end_date=end_date
        )
        
        # Compute summary metrics from lists
        pnl_list = results['pnl']
        results['final_pnl'] = pnl_list[-1]
        results['mse_pnl'] = sum(p**2 for p in pnl_list) / len(pnl_list)
        initial_opt_val = results['call_A_prices'][0] * config['n_options']
        results['normalized_mse'] = results['mse_pnl'] / (initial_opt_val ** 2) if initial_opt_val > 0 else 0
        results['total_tx_cost'] = sum(results['transaction_costs'])
        
        # Volume metrics - separate share and option volumes
        share_volume = sum(abs(s) for s in results['shares_traded'])
        option_volume = sum(abs(c) for c in results['calls_B_traded'])
        results['total_volume'] = share_volume + option_volume
        results['total_share_volume'] = share_volume
        results['total_option_volume'] = option_volume
        
        results['trading_days'] = len(results['dates'])
        results['avg_daily_trades'] = results['total_volume'] / results['trading_days'] if results['trading_days'] > 0 else 0
        results['pnl_std'] = (sum((p - sum(pnl_list)/len(pnl_list))**2 for p in pnl_list) / len(pnl_list)) ** 0.5
        results['pnl_min'] = min(pnl_list)
        results['pnl_max'] = max(pnl_list)
        results['initial_option_value'] = initial_opt_val
        
        # Transaction cost breakdown (approximate from total costs and volumes)
        total_vol = results['total_volume']
        if total_vol > 0:
            share_ratio = share_volume / total_vol
            option_ratio = option_volume / total_vol
            results['total_share_tx_cost'] = results['total_tx_cost'] * share_ratio
            results['total_option_tx_cost'] = results['total_tx_cost'] * option_ratio
        else:
            results['total_share_tx_cost'] = 0
            results['total_option_tx_cost'] = 0
        
        # Add field mappings for visualizations
        results['stock_hedge_ratios'] = results['shares_held']
        results['option_hedge_ratios'] = results['calls_B_held']
        results['stock_positions'] = results['shares_held']
        results['option_positions'] = results['calls_B_held']
        results['deltas'] = results['delta_A']
        results['gammas'] = results['gamma_A']
        
        # Portfolio values
        option_A_values = [c * config['n_options'] for c in results['call_A_prices']]
        option_B_values = [c * ob for c, ob in zip(results['call_B_prices'], results['calls_B_held'])]
        stock_values = [s * spot for s, spot in zip(results['shares_held'], results['spot'])]
        results['option_values'] = option_A_values
        results['stock_position_values'] = stock_values
        results['portfolio_values'] = [oa + ob + sv for oa, ob, sv in zip(option_A_values, option_B_values, stock_values)]
        results['cumulative_tx_costs'] = results['cumulative_transaction_cost']
        
        # Add metadata
        results['strike_primary'] = strike_primary
        results['strike_hedge'] = strike_hedge
        results['start_date'] = common_dates.min().strftime('%Y-%m-%d')
        results['end_date'] = common_dates.max().strftime('%Y-%m-%d')
        results['strategy_type'] = 'delta_gamma_hedge'
        
        return True, results, "Delta-gamma hedging completed successfully"
        
    except Exception as e:
        return False, None, f"Error executing delta-gamma hedge: {str(e)}"


def results_to_dataframe(results: Dict) -> pd.DataFrame:
    """
    Convert results dictionary to DataFrame for CSV export.
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        DataFrame with all metrics and time series data
    """
    # Start with summary metrics
    summary_data = {}
    
    # Identify time series columns (these are lists/arrays)
    time_series_cols = []
    scalar_cols = []
    
    for key, value in results.items():
        if isinstance(value, (list, pd.Series)):
            time_series_cols.append(key)
        else:
            scalar_cols.append(key)
    
    # Create DataFrame from time series data
    if time_series_cols:
        df_dict = {}
        max_len = 0
        
        for col in time_series_cols:
            data = results[col]
            if isinstance(data, pd.Series):
                df_dict[col] = data.values
            else:
                df_dict[col] = data
            max_len = max(max_len, len(df_dict[col]))
        
        df = pd.DataFrame(df_dict)
    else:
        df = pd.DataFrame()
    
    # Add scalar metrics as metadata columns (repeated for all rows)
    for col in scalar_cols:
        if len(df) > 0:
            df[col] = results[col]
        else:
            # If no time series, create single-row DataFrame with scalars
            summary_data[col] = [results[col]]
    
    if len(df) == 0 and summary_data:
        df = pd.DataFrame(summary_data)
    
    return df


def format_summary_metrics(results: Dict) -> Dict[str, any]:
    """
    Extract and format key summary metrics for display.
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        Dictionary with formatted summary metrics
    """
    summary = {}
    
    # Common metrics
    if 'final_pnl' in results:
        summary['Final P&L'] = f"${results['final_pnl']:,.2f}"
    if 'mse_pnl' in results:
        summary['MSE P&L'] = f"{results['mse_pnl']:,.2f}"
    if 'normalized_mse' in results:
        summary['Normalized MSE'] = f"{results['normalized_mse']:.6f}"
    if 'total_tx_cost' in results:
        summary['Total Transaction Cost'] = f"${results['total_tx_cost']:,.2f}"
    if 'trading_days' in results:
        summary['Trading Days'] = f"{results['trading_days']}"
    if 'avg_daily_trades' in results:
        summary['Avg Daily Trades'] = f"{results['avg_daily_trades']:.2f}"
    if 'pnl_std' in results:
        summary['P&L Std Dev'] = f"${results['pnl_std']:,.2f}"
    if 'pnl_min' in results:
        summary['Min P&L'] = f"${results['pnl_min']:,.2f}"
    if 'pnl_max' in results:
        summary['Max P&L'] = f"${results['pnl_max']:,.2f}"
    if 'initial_option_value' in results:
        summary['Initial Option Value'] = f"${results['initial_option_value']:,.2f}"
    
    # Delta-specific volume
    if 'total_volume' in results and 'strategy_type' in results and results['strategy_type'] == 'delta_hedge':
        summary['Total Share Volume'] = f"{results['total_volume']:,.0f}"
    
    # Delta-gamma specific
    if 'total_share_volume' in results:
        summary['Total Share Volume'] = f"{results['total_share_volume']:,.0f}"
    if 'total_option_volume' in results:
        summary['Total Option Volume'] = f"{results['total_option_volume']:,.0f}"
    if 'total_share_tx_cost' in results:
        summary['Share Transaction Cost'] = f"${results['total_share_tx_cost']:,.2f}"
    if 'total_option_tx_cost' in results:
        summary['Option Transaction Cost'] = f"${results['total_option_tx_cost']:,.2f}"
    
    return summary
