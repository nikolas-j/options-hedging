"""Streamlit dashboard for options hedging analysis."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.data_loader import (
    discover_market_files,
    load_option_data,
    validate_delta_gamma_files,
    check_date_overlap
)
from app.runner import (
    execute_delta_hedge,
    execute_delta_gamma_hedge,
    results_to_dataframe,
    format_summary_metrics
)
from app.visualizations import (
    plot_pnl_evolution,
    plot_portfolio_value,
    plot_hedge_ratio,
    plot_greeks,
    plot_transaction_costs,
    plot_positions,
    plot_underlying_price,
    create_metrics_table
)


# Page configuration
st.set_page_config(
    page_title="Options Hedging Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("📊 Options Hedging Dashboard")
st.markdown("Delta and Delta-Gamma hedging with S&P 500 ETF call options")

# Discover available market files
market_files = discover_market_files("market_2023")

if not market_files:
    st.error("No market data files found in market_2023/ directory")
    st.stop()

# Sidebar: Strategy configuration
st.sidebar.header("Strategy Configuration")

# Strategy type selection
strategy_type = st.sidebar.radio(
    "Select Strategy",
    ["Delta Hedging", "Delta-Gamma Hedging"],
    help="Choose between delta-only or delta-gamma hedging"
)

st.sidebar.markdown("---")

# File selection
st.sidebar.subheader("📁 Data Selection")

if strategy_type == "Delta Hedging":
    # Single file selection for delta hedging
    file_options = [f"{f['filename']} (Exp: {f['expiration_display']})" for f in market_files]
    selected_file_idx = st.sidebar.selectbox(
        "Select Market Data File",
        range(len(market_files)),
        format_func=lambda i: file_options[i]
    )
    
    selected_file = market_files[selected_file_idx]
    
    # Load data and metadata
    df_primary, metadata_primary = load_option_data(selected_file['path'])
    
    st.sidebar.info(f"**Expiration:** {selected_file['expiration']}")
    st.sidebar.info(f"**Date Range:** {metadata_primary['date_range']['start_str']} to {metadata_primary['date_range']['end_str']}")
    st.sidebar.info(f"**Total Trading Days:** {metadata_primary['total_rows']}")
    
    # Strike selection
    st.sidebar.subheader("Strike Selection")
    available_strikes = metadata_primary['available_strikes']
    
    strike_primary = st.sidebar.selectbox(
        "Select Strike Price",
        available_strikes,
        index=len(available_strikes) // 2 if available_strikes else 0,
        help="Select the strike price for the call option"
    )
    
else:  # Delta-Gamma Hedging
    # Two file selection for delta-gamma hedging
    st.sidebar.markdown("**Primary Option (Shorter Maturity)**")
    file_options_primary = [f"{f['filename']} (Exp: {f['expiration_display']})" for f in market_files]
    selected_primary_idx = st.sidebar.selectbox(
        "Select Primary Option File",
        range(len(market_files)),
        format_func=lambda i: file_options_primary[i],
        key="primary_file"
    )
    
    st.sidebar.markdown("**Hedge Option (Longer Maturity)**")
    file_options_hedge = [f"{f['filename']} (Exp: {f['expiration_display']})" for f in market_files]
    selected_hedge_idx = st.sidebar.selectbox(
        "Select Hedge Option File",
        range(len(market_files)),
        format_func=lambda i: file_options_hedge[i],
        key="hedge_file"
    )
    
    selected_file_primary = market_files[selected_primary_idx]
    selected_file_hedge = market_files[selected_hedge_idx]
    
    # Validate file compatibility
    is_valid, validation_msg = validate_delta_gamma_files(selected_file_primary, selected_file_hedge)
    
    if not is_valid:
        st.sidebar.warning(f"⚠️ {validation_msg}")
    
    # Load data
    df_primary, metadata_primary = load_option_data(selected_file_primary['path'])
    df_hedge, metadata_hedge = load_option_data(selected_file_hedge['path'])
    
    # Check date overlap
    has_overlap, overlap_msg, overlap_range = check_date_overlap(df_primary, df_hedge)
    
    if not has_overlap:
        st.sidebar.error(f"❌ {overlap_msg}")
    else:
        st.sidebar.success(f"✅ {overlap_msg}")
    
    # Strike selection for both options
    st.sidebar.subheader("Strike Selection")
    
    st.sidebar.markdown("**Primary Option Strike**")
    available_strikes_primary = metadata_primary['available_strikes']
    strike_primary = st.sidebar.selectbox(
        "Primary Strike",
        available_strikes_primary,
        index=len(available_strikes_primary) // 2 if available_strikes_primary else 0,
        key="strike_primary"
    )
    
    st.sidebar.markdown("**Hedge Option Strike**")
    available_strikes_hedge = metadata_hedge['available_strikes']
    strike_hedge = st.sidebar.selectbox(
        "Hedge Strike",
        available_strikes_hedge,
        index=len(available_strikes_hedge) // 2 if available_strikes_hedge else 0,
        key="strike_hedge"
    )

st.sidebar.markdown("---")

# Date range selection
st.sidebar.subheader("📅 Date Range")

use_custom_dates = st.sidebar.checkbox("Use Custom Date Range", value=False)

if use_custom_dates:
    if strategy_type == "Delta Hedging":
        min_date = pd.to_datetime(metadata_primary['date_range']['start'])
        max_date = pd.to_datetime(metadata_primary['date_range']['end'])
    else:
        if has_overlap and overlap_range:
            min_date = pd.to_datetime(overlap_range[0])
            max_date = pd.to_datetime(overlap_range[1])
        else:
            min_date = pd.to_datetime(metadata_primary['date_range']['start'])
            max_date = pd.to_datetime(metadata_primary['date_range']['end'])
    
    start_date = st.sidebar.date_input(
        "Start Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
else:
    start_date_str = None
    end_date_str = None

st.sidebar.markdown("---")

# Strategy parameters
st.sidebar.subheader("⚙️ Strategy Parameters")

risk_free_rate = st.sidebar.number_input(
    "Risk-Free Rate",
    min_value=0.0,
    max_value=1.0,
    value=0.03,
    step=0.001,
    format="%.3f",
    help="Annual risk-free interest rate"
)

n_options = st.sidebar.number_input(
    "Number of Options",
    min_value=1,
    max_value=10000,
    value=100,
    step=10,
    help="Number of call options to hedge"
)

volatility_mode = st.sidebar.selectbox(
    "Volatility Mode",
    ["implied", "const"],
    help="Use implied volatility or constant volatility"
)

if volatility_mode == "const":
    initial_volatility = st.sidebar.number_input(
        "Constant Volatility",
        min_value=0.01,
        max_value=2.0,
        value=0.2,
        step=0.01,
        format="%.2f",
        help="Constant volatility value (if not using implied volatility)"
    )
else:
    initial_volatility = st.sidebar.number_input(
        "Initial Volatility (for implied calc)",
        min_value=0.01,
        max_value=2.0,
        value=0.2,
        step=0.01,
        format="%.2f",
        help="Initial guess for implied volatility calculation"
    )

hedge_frequency = st.sidebar.slider(
    "Hedge Frequency (days)",
    min_value=1,
    max_value=30,
    value=1,
    help="Number of days between rehedging"
)

share_transaction_cost = st.sidebar.number_input(
    "Share Transaction Cost (%)",
    min_value=0.0,
    max_value=10.0,
    value=0.5,
    step=0.1,
    format="%.2f",
    help="Transaction cost as percentage of trade value"
) / 100  # Convert to decimal

if strategy_type == "Delta-Gamma Hedging":
    option_transaction_cost = st.sidebar.number_input(
        "Option Transaction Cost (%)",
        min_value=0.0,
        max_value=10.0,
        value=1.0,
        step=0.1,
        format="%.2f",
        help="Option transaction cost as percentage of trade value"
    ) / 100  # Convert to decimal

# Build config dictionary
config = {
    'risk_free_rate': risk_free_rate,
    'n_options': n_options,
    'volatility_mode': volatility_mode,
    'initial_volatility': initial_volatility,
    'hedge_frequency': hedge_frequency,
    'share_transaction_cost': share_transaction_cost
}

if strategy_type == "Delta-Gamma Hedging":
    config['option_transaction_cost'] = option_transaction_cost

# Main content area
st.markdown("---")

# Run button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("🚀 Run Hedging Strategy", type="primary", use_container_width=True)

if run_button:
    # Validate for delta-gamma
    if strategy_type == "Delta-Gamma Hedging":
        if not is_valid:
            st.error(f"Cannot run strategy: {validation_msg}")
            st.stop()
        if not has_overlap:
            st.error(f"Cannot run strategy: {overlap_msg}")
            st.stop()
    
    # Execute strategy
    with st.spinner("Running hedging strategy..."):
        if strategy_type == "Delta Hedging":
            success, results, message = execute_delta_hedge(
                df=df_primary,
                strike=strike_primary,
                config=config,
                start_date=start_date_str,
                end_date=end_date_str
            )
        else:  # Delta-Gamma Hedging
            success, results, message = execute_delta_gamma_hedge(
                df_primary=df_primary,
                df_hedge=df_hedge,
                strike_primary=strike_primary,
                strike_hedge=strike_hedge,
                config=config,
                start_date=start_date_str,
                end_date=end_date_str
            )
    
    if success:
        st.success(f"✅ {message}")
        
        # Store results in session state
        st.session_state['results'] = results
        st.session_state['strategy_type'] = strategy_type
        
    else:
        st.error(f"❌ {message}")
        st.stop()

# Display results if available
if 'results' in st.session_state:
    results = st.session_state['results']
    strategy_type_stored = st.session_state.get('strategy_type', strategy_type)
    
    st.markdown("---")
    st.header("📈 Results")
    
    # Summary metrics
    st.subheader("Summary Metrics")
    summary_metrics = format_summary_metrics(results)
    metrics_df = create_metrics_table(summary_metrics)
    
    # Display metrics in columns
    cols = st.columns(3)
    metrics_list = list(summary_metrics.items())
    for idx, (metric, value) in enumerate(metrics_list):
        with cols[idx % 3]:
            st.metric(metric, value)
    
    st.markdown("---")
    
    # Visualizations
    st.subheader("Performance Visualizations")
    
    # Underlying price
    st.plotly_chart(plot_underlying_price(results), use_container_width=True)
    
    # P&L Evolution
    st.plotly_chart(plot_pnl_evolution(results), use_container_width=True)
    
    # Portfolio Value
    st.plotly_chart(plot_portfolio_value(results), use_container_width=True)
    
    # Two columns for additional charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(plot_hedge_ratio(results, results['strategy_type']), use_container_width=True)
    
    with col2:
        st.plotly_chart(plot_transaction_costs(results), use_container_width=True)
    
    # Greeks (if available)
    greeks_fig = plot_greeks(results, results['strategy_type'])
    if greeks_fig:
        st.plotly_chart(greeks_fig, use_container_width=True)
    
    # Positions
    st.plotly_chart(plot_positions(results), use_container_width=True)
    
    st.markdown("---")
    
    # Export results
    st.subheader("📥 Export Results")
    
    # Convert to DataFrame
    results_df = results_to_dataframe(results)
    
    # Show preview
    with st.expander("Preview Export Data"):
        st.dataframe(results_df, use_container_width=True)
    
    # Download button
    csv = results_df.to_csv(index=False)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"hedging_results_{results['strategy_type']}_{timestamp}.csv"
    
    st.download_button(
        label="⬇️ Download Results as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; padding: 20px;'>"
    "Options Hedging Dashboard | Delta & Delta-Gamma Strategies"
    "</div>",
    unsafe_allow_html=True
)
