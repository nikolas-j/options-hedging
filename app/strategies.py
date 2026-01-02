"""
Hedging strategy implementations for delta and gamma hedging.
"""
import pandas as pd
import numpy as np
from pricing import calc_volatility_newton, calc_delta, calc_gamma


def run_delta_hedge(data, strike, config, start_date=None, end_date=None):
    """
    Run delta hedging backtest.
    
    Args:
        data: DataFrame with Date, Underlying, and C{strike} columns
        strike: Strike price
        config: Dictionary with hedging configuration
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
    
    Returns:
        Dictionary with results
    """
    # Extract parameters
    E = strike
    
    maturity_date = pd.Timestamp(data['Date'].iloc[-1])
    
    subset = data[['Date', 'Underlying', f'C{E}']].copy()
    if start_date:
        mask = subset['Date'] >= pd.to_datetime(start_date)
        subset = subset[mask].reset_index(drop=True)
    if end_date:
        mask = subset['Date'] <= pd.to_datetime(end_date)
        subset = subset[mask].reset_index(drop=True)
    
    dates_all = subset['Date']
    spot = subset['Underlying']
    call = subset[f'C{E}']
    
    T = (maturity_date - dates_all).dt.days / 365.0
    
    # Extract config parameters
    r = config['risk_free_rate']
    N_options = config['n_options']
    volatility_mode = config['volatility_mode']
    initial_volatility = config['initial_volatility']
    hedge_frequency_d = config['hedge_frequency']
    share_transaction_cost = config['share_transaction_cost']
    
    # Track metrics
    initial_premium = -call.iloc[0] * N_options
    current_shares = 0
    cumulative_cash = initial_premium
    initial_wealth = None
    
    # Lists to track daily metrics
    dates = []
    delta_pnl = []
    unhedged_pnl = []
    short_shares_held = []
    traded_shares = []
    trade_cash_flows = []
    deltas = []
    volatilities = []
    transaction_costs = []
    spot_prices = []
    call_prices = []
    time_to_maturity = []
    
    for i in range(len(dates_all)):
        S = spot.iloc[i]
        C = call.iloc[i]
        t = T.iloc[i]
        
        # Calculate Greeks and volatility every day
        if volatility_mode == 'const':
            vol = initial_volatility
        elif volatility_mode == 'implied':
            vol = calc_volatility_newton(C, S, E, t, r, volatilities[-1] if volatilities else initial_volatility)
        else:
            raise ValueError("Invalid volatility mode. Choose 'const' or 'implied'.")
        
        delta_i = calc_delta(S, E, t, r, vol)
        
        # Rebalance only every hedge_frequency_d days
        if (i % hedge_frequency_d) == 0:
            target_shares = delta_i * N_options
            shares_to_trade = target_shares - current_shares
            
            cash_flow = shares_to_trade * S
            transaction_cost = share_transaction_cost * abs(cash_flow)
            
            cumulative_cash += cash_flow - transaction_cost
            
            # Update position
            current_shares = target_shares
        else:
            # No rebalancing on this day
            shares_to_trade = 0
            transaction_cost = 0
            cash_flow = 0
        
        # Calculate portfolio value every day
        long_call_value = N_options * C
        short_stock_value = -current_shares * S
        wealth = long_call_value + short_stock_value + cumulative_cash
        
        if initial_wealth is None:
            initial_wealth = wealth
        
        pnl = wealth - initial_wealth
        
        # Track metrics
        dates.append(dates_all.iloc[i])
        delta_pnl.append(pnl)
        unhedged_pnl.append((C * N_options) - (call.iloc[0] * N_options))
        deltas.append(delta_i)
        volatilities.append(vol)
        short_shares_held.append(current_shares)
        traded_shares.append(shares_to_trade)
        trade_cash_flows.append(cash_flow)
        transaction_costs.append(transaction_cost)
        spot_prices.append(S)
        call_prices.append(C)
        time_to_maturity.append(t)

    trade_volume = [np.abs(s) for s in traded_shares]
    transaction_costs[0] = 0
    cumulative_transaction_cost = np.cumsum(transaction_costs)
    
    # Count number of rehedges (when shares_traded != 0)
    rehedge_count = sum(1 for s in traded_shares if s != 0)
    
    return {
        'dates': dates,
        'pnl': delta_pnl,
        'unhedged_pnl': unhedged_pnl,
        'deltas': deltas,
        'vol': volatilities,
        'shares_held': short_shares_held,
        'shares_traded': traded_shares,
        'cash_flows': trade_cash_flows,
        'transaction_costs': transaction_costs,
        'cumulative_transaction_cost': cumulative_transaction_cost.tolist(),
        'trade_volume': trade_volume,
        'spot': spot_prices,
        'call_prices': call_prices,
        'time_to_maturity': time_to_maturity,
        'maturity_date': maturity_date,
        'strike': E,
        'rehedge_count': rehedge_count
    }



def run_gamma_hedge(data_A, data_B, strike_A, strike_B, config, start_date=None, end_date=None):
    """
    Run gamma hedging backtest.
    
    Args:
        data_A: DataFrame for primary option
        data_B: DataFrame for hedging option
        strike_A: Strike price for primary option
        strike_B: Strike price for hedging option
        config: Dictionary with hedging configuration
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
    
    Returns:
        Dictionary with results
    """
    # Extract and align data
    E_A = strike_A
    E_B = strike_B
    
    # Extract maturity dates from original datasets (before any filtering)
    maturity_date_A = pd.Timestamp(data_A['Date'].iloc[-1])
    maturity_date_B = pd.Timestamp(data_B['Date'].iloc[-1])
    
    subset_A = data_A[['Date', 'Underlying', f'C{E_A}']].copy()
    subset_B = data_B[['Date', f'C{E_B}']].copy()
    
    # Filter by date range
    if start_date:
        start_dt = pd.to_datetime(start_date)
        subset_A = subset_A[subset_A['Date'] >= start_dt].reset_index(drop=True)
        subset_B = subset_B[subset_B['Date'] >= start_dt].reset_index(drop=True)
    if end_date:
        end_dt = pd.to_datetime(end_date)
        subset_A = subset_A[subset_A['Date'] <= end_dt].reset_index(drop=True)
        subset_B = subset_B[subset_B['Date'] <= end_dt].reset_index(drop=True)
    
    # Ensure both datasets have exactly the same dates
    common_dates_filtered = pd.merge(subset_A[['Date']], subset_B[['Date']], on='Date', how='inner')['Date']
    subset_A = subset_A[subset_A['Date'].isin(common_dates_filtered)].reset_index(drop=True)
    subset_B = subset_B[subset_B['Date'].isin(common_dates_filtered)].reset_index(drop=True)
    
    dates_all = subset_A['Date']
    spot = subset_A['Underlying']
    call_A = subset_A[f'C{E_A}']
    call_B = subset_B[f'C{E_B}']
    
    T_A = (maturity_date_A - dates_all).dt.days / 365.0
    T_B = (maturity_date_B - dates_all).dt.days / 365.0
    
    # Extract parameters
    r = config['risk_free_rate']
    N_options = config['n_options']
    volatility_mode = config['volatility_mode']
    initial_volatility = config['initial_volatility']
    hedge_frequency_d = config['hedge_frequency']
    share_transaction_cost = config['share_transaction_cost']
    option_transaction_cost = config['option_transaction_cost']
    
    # Track metrics
    initial_premium = -call_A.iloc[0] * N_options
    current_shares = 0
    current_calls_B = 0
    cumulative_cash = initial_premium
    initial_wealth = None
    
    # Lists to track daily metrics
    trade_dates = []
    gamma_pnl = []
    unhedged_pnl = []
    shares_held = []
    shares_traded = []
    calls_B_held = []
    calls_B_traded = []
    cash_flows = []
    delta_A = []
    delta_B = []
    gamma_A = []
    gamma_B = []
    vol_A = []
    vol_B = []
    transaction_costs = []
    spot_prices = []
    call_A_prices = []
    call_B_prices = []
    time_to_maturity_A = []
    time_to_maturity_B = []
    
    for i in range(len(dates_all)):
        S = spot.iloc[i]
        C_A = call_A.iloc[i]
        C_B = call_B.iloc[i]
        t_A = T_A.iloc[i]
        t_B = T_B.iloc[i]
        
        # Calculate Greeks and volatility every day
        if volatility_mode == 'const':
            vol_A_i = vol_B_i = initial_volatility
        elif volatility_mode == 'implied':
            vol_A_i = calc_volatility_newton(C_A, S, E_A, t_A, r, vol_A[-1] if vol_A else initial_volatility)
            vol_B_i = calc_volatility_newton(C_B, S, E_B, t_B, r, vol_B[-1] if vol_B else initial_volatility)
        else:
            raise ValueError("Invalid volatility mode. Choose 'const' or 'implied'.")

        delta_A_i = calc_delta(S, E_A, t_A, r, vol_A_i)
        delta_B_i = calc_delta(S, E_B, t_B, r, vol_B_i)
        gamma_A_i = calc_gamma(S, E_A, t_A, r, vol_A_i)
        gamma_B_i = calc_gamma(S, E_B, t_B, r, vol_B_i)
        
        # Rebalance only every hedge_frequency_d days
        if (i % hedge_frequency_d) == 0:
            # Solution to linear equations:
            target_calls_B = -(gamma_A_i / gamma_B_i) * N_options
            target_shares = -delta_A_i * N_options - delta_B_i * target_calls_B

            shares_to_trade = target_shares - current_shares
            calls_B_to_trade = target_calls_B - current_calls_B

            # Cash flow from trading
            cash_flow_stock = shares_to_trade * S
            cash_flow_opt = calls_B_to_trade * C_B
            cash_flow = -cash_flow_stock - cash_flow_opt
            
            # Transaction cost as percentage of dollar amount
            cost_stock = share_transaction_cost * abs(cash_flow_stock)
            cost_opt = option_transaction_cost * abs(cash_flow_opt)
            transaction_cost = cost_stock + cost_opt

            cumulative_cash += cash_flow - transaction_cost
            
            # Update positions
            current_shares = target_shares
            current_calls_B = target_calls_B
        else:
            # No rebalancing on this day
            shares_to_trade = 0
            calls_B_to_trade = 0
            transaction_cost = 0
            cash_flow = 0
        
        # Calculate portfolio value every day
        call_A_value = N_options * C_A
        call_B_value = current_calls_B * C_B
        stock_value = current_shares * S
        wealth = call_A_value + call_B_value + stock_value + cumulative_cash

        if initial_wealth is None:
            initial_wealth = wealth
        
        pnl = wealth - initial_wealth
        
        # Track metrics
        trade_dates.append(dates_all.iloc[i])
        gamma_pnl.append(pnl)
        unhedged_pnl.append((C_A * N_options) - (call_A.iloc[0] * N_options))
        delta_A.append(delta_A_i)
        delta_B.append(delta_B_i)
        gamma_A.append(gamma_A_i)
        gamma_B.append(gamma_B_i)
        vol_A.append(vol_A_i)
        vol_B.append(vol_B_i)
        shares_held.append(current_shares)
        shares_traded.append(shares_to_trade)
        calls_B_held.append(current_calls_B)
        calls_B_traded.append(calls_B_to_trade)
        cash_flows.append(cash_flow)
        transaction_costs.append(transaction_cost)
        spot_prices.append(S)
        call_A_prices.append(C_A)
        call_B_prices.append(C_B)
        time_to_maturity_A.append(t_A)
        time_to_maturity_B.append(t_B)

    
    trade_volume = [np.abs(s) + np.abs(c) for s, c in zip(shares_traded, calls_B_traded)]
    transaction_costs[0] = 0
    cumulative_transaction_cost = np.cumsum(transaction_costs)
    
    
    # Count number of rehedges (when shares_traded != 0 or calls_B_traded != 0)
    rehedge_count = sum(1 for s, c in zip(shares_traded, calls_B_traded) if s != 0 or c != 0)
    
    return {
        'dates': trade_dates,
        'pnl': gamma_pnl,
        'unhedged_pnl': unhedged_pnl,
        'delta_A': delta_A,
        'delta_B': delta_B,
        'gamma_A': gamma_A,
        'gamma_B': gamma_B,
        'vol_A': vol_A,
        'vol_B': vol_B,
        'shares_held': shares_held,
        'shares_traded': shares_traded,
        'calls_B_held': calls_B_held,
        'calls_B_traded': calls_B_traded,
        'cash_flows': cash_flows,
        'transaction_costs': transaction_costs,
        'cumulative_transaction_cost': cumulative_transaction_cost.tolist(),
        'trade_volume': trade_volume,
        'spot': spot_prices,
        'call_A_prices': call_A_prices,
        'call_B_prices': call_B_prices,
        'time_to_maturity_A': time_to_maturity_A,
        'time_to_maturity_B': time_to_maturity_B,
        'maturity_date_A': maturity_date_A,
        'maturity_date_B': maturity_date_B,
        'strike_A': E_A,
        'strike_B': E_B,
        'rehedge_count': rehedge_count
    }

