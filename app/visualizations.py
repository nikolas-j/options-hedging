"""Visualization functions for hedging dashboard."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional


def plot_pnl_evolution(results: Dict) -> go.Figure:
    """
    Plot P&L evolution over time.
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        Plotly figure
    """
    dates = results.get('dates', [])
    pnl = results.get('pnl', [])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=pnl,
        mode='lines',
        name='P&L',
        line=dict(color='#2E86AB', width=2),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.2)'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title='Portfolio P&L Evolution',
        xaxis_title='Date',
        yaxis_title='P&L ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def plot_portfolio_value(results: Dict) -> go.Figure:
    """
    Plot portfolio value components over time.
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        Plotly figure
    """
    dates = results.get('dates', [])
    
    fig = go.Figure()
    
    # Option value
    if 'option_values' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['option_values'],
            mode='lines',
            name='Option Value',
            line=dict(color='#A23B72', width=2)
        ))
    
    # Stock position value
    if 'stock_position_values' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['stock_position_values'],
            mode='lines',
            name='Stock Position',
            line=dict(color='#F18F01', width=2)
        ))
    
    # Portfolio value
    if 'portfolio_values' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['portfolio_values'],
            mode='lines',
            name='Total Portfolio',
            line=dict(color='#2E86AB', width=2.5)
        ))
    
    fig.update_layout(
        title='Portfolio Value Components',
        xaxis_title='Date',
        yaxis_title='Value ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def plot_hedge_ratio(results: Dict, strategy_type: str) -> go.Figure:
    """
    Plot hedge ratios over time.
    
    Args:
        results: Strategy results dictionary
        strategy_type: 'delta_hedge' or 'delta_gamma_hedge'
        
    Returns:
        Plotly figure
    """
    dates = results.get('dates', [])
    
    fig = go.Figure()
    
    if strategy_type == 'delta_hedge':
        # Delta hedging: show stock hedge ratio
        if 'hedge_ratios' in results:
            fig.add_trace(go.Scatter(
                x=dates,
                y=results['hedge_ratios'],
                mode='lines',
                name='Delta (Stock Hedge Ratio)',
                line=dict(color='#06A77D', width=2)
            ))
    
    elif strategy_type == 'delta_gamma_hedge':
        # Delta-gamma hedging: show both stock and option hedge ratios
        if 'stock_hedge_ratios' in results:
            fig.add_trace(go.Scatter(
                x=dates,
                y=results['stock_hedge_ratios'],
                mode='lines',
                name='Stock Hedge Ratio',
                line=dict(color='#06A77D', width=2)
            ))
        
        if 'option_hedge_ratios' in results:
            fig.add_trace(go.Scatter(
                x=dates,
                y=results['option_hedge_ratios'],
                mode='lines',
                name='Option Hedge Ratio',
                line=dict(color='#D62246', width=2)
            ))
    
    fig.update_layout(
        title='Hedge Ratios Over Time',
        xaxis_title='Date',
        yaxis_title='Hedge Ratio',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def plot_greeks(results: Dict, strategy_type: str) -> Optional[go.Figure]:
    """
    Plot option Greeks over time.
    
    Args:
        results: Strategy results dictionary
        strategy_type: 'delta_hedge' or 'delta_gamma_hedge'
        
    Returns:
        Plotly figure or None if Greeks not available
    """
    dates = results.get('dates', [])
    
    # Check if we have Greeks data
    has_delta = 'deltas' in results
    has_gamma = 'gammas' in results
    
    if not (has_delta or has_gamma):
        return None
    
    # Create subplot figure
    if has_delta and has_gamma:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Delta', 'Gamma'),
            vertical_spacing=0.12
        )
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['deltas'],
            mode='lines',
            name='Delta',
            line=dict(color='#2E86AB', width=2)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['gammas'],
            mode='lines',
            name='Gamma',
            line=dict(color='#A23B72', width=2)
        ), row=2, col=1)
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Delta", row=1, col=1)
        fig.update_yaxes(title_text="Gamma", row=2, col=1)
        
        fig.update_layout(
            title='Option Greeks Over Time',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            showlegend=False
        )
    else:
        # Single plot
        fig = go.Figure()
        
        if has_delta:
            fig.add_trace(go.Scatter(
                x=dates,
                y=results['deltas'],
                mode='lines',
                name='Delta',
                line=dict(color='#2E86AB', width=2)
            ))
            ylabel = 'Delta'
        else:
            fig.add_trace(go.Scatter(
                x=dates,
                y=results['gammas'],
                mode='lines',
                name='Gamma',
                line=dict(color='#A23B72', width=2)
            ))
            ylabel = 'Gamma'
        
        fig.update_layout(
            title='Option Greeks Over Time',
            xaxis_title='Date',
            yaxis_title=ylabel,
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
    
    return fig


def plot_transaction_costs(results: Dict) -> go.Figure:
    """
    Plot cumulative transaction costs over time.
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        Plotly figure
    """
    dates = results.get('dates', [])
    
    fig = go.Figure()
    
    # Cumulative share transaction costs
    if 'cumulative_tx_costs' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['cumulative_tx_costs'],
            mode='lines',
            name='Share Transaction Costs',
            line=dict(color='#F18F01', width=2),
            fill='tozeroy',
            fillcolor='rgba(241, 143, 1, 0.2)'
        ))
    
    # Cumulative option transaction costs (for delta-gamma)
    if 'cumulative_option_tx_costs' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['cumulative_option_tx_costs'],
            mode='lines',
            name='Option Transaction Costs',
            line=dict(color='#D62246', width=2),
            fill='tozeroy',
            fillcolor='rgba(214, 34, 70, 0.2)'
        ))
    
    fig.update_layout(
        title='Cumulative Transaction Costs',
        xaxis_title='Date',
        yaxis_title='Cumulative Cost ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def plot_positions(results: Dict) -> go.Figure:
    """
    Plot hedge positions over time (shares or options).
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        Plotly figure
    """
    dates = results.get('dates', [])
    
    fig = go.Figure()
    
    # Stock positions
    if 'stock_positions' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['stock_positions'],
            mode='lines',
            name='Stock Position (Shares)',
            line=dict(color='#06A77D', width=2)
        ))
    
    # Option positions (for delta-gamma)
    if 'option_positions' in results:
        fig.add_trace(go.Scatter(
            x=dates,
            y=results['option_positions'],
            mode='lines',
            name='Option B Position',
            line=dict(color='#D62246', width=2)
        ))
    
    fig.update_layout(
        title='Hedge Positions Over Time',
        xaxis_title='Date',
        yaxis_title='Position Size',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def plot_underlying_price(results: Dict) -> go.Figure:
    """
    Plot underlying asset price over time.
    
    Args:
        results: Strategy results dictionary
        
    Returns:
        Plotly figure
    """
    dates = results.get('dates', [])
    spot_prices = results.get('spot', [])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=spot_prices,
        mode='lines',
        name='S&P 500 ETF Price',
        line=dict(color='#1f77b4', width=2.5)
    ))
    
    fig.update_layout(
        title='Underlying Asset Price (S&P 500 ETF)',
        xaxis_title='Date',
        yaxis_title='Price ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_metrics_table(summary_metrics: Dict) -> pd.DataFrame:
    """
    Create a formatted DataFrame for displaying summary metrics.
    
    Args:
        summary_metrics: Dictionary of formatted metrics
        
    Returns:
        DataFrame with two columns: Metric and Value
    """
    df = pd.DataFrame([
        {'Metric': metric, 'Value': value}
        for metric, value in summary_metrics.items()
    ])
    
    return df
