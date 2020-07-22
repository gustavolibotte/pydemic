#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:55:56 2020

@author: gustavolibotte
"""

import numpy as np
import meta_SEIRPDQ as model
from scipy.integrate import solve_ivp
from epi_plot import EpiPlot
from typing import Tuple

def runMetaSEIRPDQ() -> None:
    """
    Simulate the metapopulation-based SEIRPDQ model with arbitrary parameters
    """
    seed = 12345
    np.random.seed(seed)
    
    # Parameter settings
    nPatches = 4
    beta = randInitBetaMatrix(nPatches, isCrossCoupling = False)
    mu = 1e-7
    gamma_I = 0.65
    gamma_A = 0.95
    gamma_P = 0.4
    d_I = 2e-4
    d_P = 0.3
    omega = 0.0
    epsilon_I = 1/3
    rho = 0.85
    eta = 0.0
    sigma = 1/5
    # N = 211.8e6 * np.ones(nPatches)
    N = np.array([6.32e6, 1.85e5, 1.80e5, 1.13e5])
    
    # Initial conditions
    E0 = 70 * np.ones((1, nPatches))
    A0 = 7 * np.ones((1, nPatches))
    I0 = 35 * np.ones((1, nPatches))
    P0 = 7 * np.ones((1, nPatches))
    R0 = np.zeros((1, nPatches))
    D0 = np.zeros((1, nPatches))
    C0 = 7 * np.ones((1, nPatches))
    H0 = np.zeros((1, nPatches))
    S0 = N - (E0 + A0 + I0 + R0 + P0 + D0)
    initCond = np.reshape([S0, E0, A0, I0, P0, R0, D0, C0, H0], 9 * nPatches)
    
    # Time span
    nEval = 1000
    timeSpan = [0, 100]
    tEvalArray = np.linspace(timeSpan[0], timeSpan[1], num = nEval)
    
    # Model instance
    modelObj = model.MetaSEIRPDQ(nPatches, beta, mu, gamma_I, gamma_A, gamma_P, d_I, d_P, omega, epsilon_I, rho, eta, sigma, N)
    
    # Solver
    solIVP = solve_ivp(modelObj.metaSEIRPDQ, timeSpan, initCond, t_eval = tEvalArray, method = 'LSODA')
    
    EpiPlot.plotMetaSEIR(solIVP.t, solIVP.y, 1, nPatches)
    EpiPlot.plotMetaSEIR(solIVP.t, solIVP.y, 2, nPatches)
    EpiPlot.plotMetaSEIR(solIVP.t, solIVP.y, 3, nPatches)
    EpiPlot.plotMetaSEIR(solIVP.t, solIVP.y, 4, nPatches)

def randInitBetaMatrix(nPatches: int, isCrossCoupling: bool = False) -> np.ndarray:
    """
    Random initialization of the cross-coupling matrix
    
    Denotes the contact rate of susceptible and infected individuals on patches
    i and j, respectively. Values tend to be higher on the main diagonal and
    decrease gradually further away from the main diagonal. Cross-coupling
    between patches is avoided when the off-diagonal elements are set to zero
    (this is done by defining isCrossCoupling = True).
    
    Parameters
    ----------
    nPatches: int
        Total number of patches
    isCrossCoupling: bool
        Turns the cross-coupling either on or off
        
    Return
    ------
    np.ndarray
        Cross-coupling matrix
    """
    beta = np.zeros((nPatches, nPatches))
    if isCrossCoupling:
        for i in range(nPatches):
            idx_diag = kth_diag_indices(beta, i)
            normVec = np.random.normal(10 * (nPatches - np.abs(i)) / nPatches, 2, nPatches - np.abs(i))
            for j in range(nPatches - np.abs(i)):
                idx = [idx_diag[0][j], idx_diag[1][j]]
                beta[idx[0]][idx[1]] = np.abs(normVec[j])
    else:
        idx_diag = kth_diag_indices(beta, 0)
        normVec = np.random.normal(10 * nPatches / nPatches, 2, nPatches)
        for j in range(nPatches):
            idx = [idx_diag[0][j], idx_diag[1][j]]
            beta[idx[0]][idx[1]] = np.abs(normVec[j])
    return beta
        
def kth_diag_indices(a: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Gets the indexes (rows and columns) of the kth diagonal of a matrix
    
    Parameters
    ----------
    a: np.ndarray
        Matrix
    k: int
        Index referring to the diagonal
    
    Return
    ------
    Tuple[np.ndarray, np.ndarray]
        Indexes for rows and columns
    """
    rows, cols = np.diag_indices_from(a)
    if k < 0:
        return rows[-k:], cols[:k]
    elif k > 0:
        return rows[:-k], cols[k:]
    else:
        return rows, cols
