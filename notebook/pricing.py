"""
Black-Scholes pricing functions for options Greeks calculation.
"""
import numpy as np
from scipy.integrate import quad


def calc_volatility_newton(C, S, E, t, r, initial, tol=1e-6, max_iter=500):
    """
    Calculate implied volatility using Newton's method.
    
    Args:
        C: Call option price
        S: Spot price
        E: Strike price
        t: Time to maturity (years)
        r: Risk-free rate
        initial: Initial volatility guess
        tol: Convergence tolerance
        max_iter: Maximum iterations
    
    Returns:
        Implied volatility (sigma)
    """
    # Return initial guess if too close to maturity (numerical instability)
    if t < 1/365:  # Less than 1 day to maturity
        return initial
    
    vega_limit = 1e-6  # Newton stability limit

    def f(sigma):
        d_pos = (np.log(S / E) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))
        d_neg = d_pos - sigma * np.sqrt(t)
        def integrand(x): 
            return 1 / np.sqrt(2 * np.pi) * np.exp(-0.5 * x ** 2)
        N_d_pos = quad(integrand, -np.inf, d_pos)[0]
        N_d_neg = quad(integrand, -np.inf, d_neg)[0]
        C_calc = S * N_d_pos - N_d_neg * E * np.exp(-r * t)
        return C_calc - C
    
    def df(sigma):
        d_pos = (np.log(S / E) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))
        dN = 1 / np.sqrt(2 * np.pi) * np.exp(-0.5 * d_pos ** 2)
        return S * dN * np.sqrt(t)

    sigma = initial
    for _ in range(max_iter):
        f_val = f(sigma)
        df_val = df(sigma)
        if df_val == 0:
            break
        if abs(df_val) < vega_limit:
            return initial
        sigma_new = sigma - f_val / df_val
        if abs(sigma_new - sigma) < tol:
            return sigma_new
        sigma = sigma_new
    
    return initial


def calc_delta(S, E, t, r, sigma):
    """
    Calculate delta for a call option.
    
    Args:
        S: Spot price
        E: Strike price
        t: Time to maturity (years)
        r: Risk-free rate
        sigma: Volatility
    
    Returns:
        Delta value
    """
    d_pos = (np.log(S / E) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))

    def integrand(x): 
        return 1 / np.sqrt(2 * np.pi) * np.exp(-0.5 * x ** 2)
    delta = quad(integrand, -np.inf, d_pos)[0]

    return delta


def calc_gamma(S, E, t, r, sigma):
    """
    Calculate gamma for a call option.
    
    Args:
        S: Spot price
        E: Strike price
        t: Time to maturity (years)
        r: Risk-free rate
        sigma: Volatility
    
    Returns:
        Gamma value
    """
    d_pos = (np.log(S / E) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))
    dN = 1 / np.sqrt(2 * np.pi) * np.exp(-0.5 * d_pos ** 2)
    return dN / (S * sigma * np.sqrt(t))
