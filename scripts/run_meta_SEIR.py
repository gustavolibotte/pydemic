#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 11 11:37:44 2020

@author: gustavolibotte
"""

import numpy as np
import meta_SEIR as model
from scipy.integrate import solve_ivp
from epi_plot import EpiPlot
from typing import Tuple

def runMetaSEIR() -> None:
    """
    Simulate the metapopulation-based SEIR model with arbitrary parameters
    """
    seed = 12345
    np.random.seed(seed)
    
    # Parameter settings
    nPatches = 2
    mu = 1 / 10
    sigma = 1 / 3
    gamma = 1 / 2
    M = np.array([1.0, 1.0, 1.0, 1.0])
    beta = randInitBetaMatrix(nPatches, isCrossCoupling = True)
    C = randInitMobilityMatrix(nPatches, isMigrating = True)
    
    # Initial conditions
    S0 = np.ones((1, nPatches)) - 1e-6
    E0 = np.zeros((1, nPatches))
    I0 = np.ones((1, nPatches)) * 1e-6
    R0 = np.zeros((1, nPatches))
    initCond = np.reshape([S0, E0, I0, R0], 4 * nPatches)
    
    # Time span
    nEval = 100
    timeSpan = [0, 30]
    tEvalArray = np.linspace(timeSpan[0], timeSpan[1], num = nEval)
    
    # Model instance
    modelObj = model.MetaSEIR(nPatches, beta, C, mu, sigma, gamma, M)
    
    # Solver
    solIVP = solve_ivp(modelObj.metaSEIR, timeSpan, initCond, t_eval = tEvalArray, method = 'LSODA')
    del modelObj

    # Plotting the results
    EpiPlot.plotMetaSEIR(solIVP.t, solIVP.y, 1, nPatches)
    EpiPlot.plotMetaSEIR(solIVP.t, solIVP.y, 2, nPatches)

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
            normVec = np.random.normal(10 * (nPatches - i) / nPatches, 2, nPatches - i)
            for j in range(nPatches - i):
                idx = [idx_diag[0][j], idx_diag[1][j]]
                beta[idx[0]][idx[1]] = np.abs(normVec[j])
    else:
        idx_diag = kth_diag_indices(beta, 0)
        normVec = np.random.normal(10 * nPatches / nPatches, 2, nPatches)
        for j in range(nPatches):
            idx = [idx_diag[0][j], idx_diag[1][j]]
            beta[idx[0]][idx[1]] = np.abs(normVec[j])
    return beta

def randInitMobilityMatrix(nPatches: int, isMigrating: bool) -> np.ndarray:
    """
    Random initialization of the mobility matrix
    
    The elements on the diagonal are negative and denote the outflow of patch
    i. The remaining elements describe the flow of individuals from patch i to
    patch i. Each row of the matrix must sum up to zero.
    
    Parameters
    ----------
    nPatches: int
        Total number of patches
    isMigrating: bool
        Turns the migration either on or off
        
    Return
    ------
    np.ndarray
        Migration matrix
    """
    C = np.zeros((nPatches, nPatches))
    if nPatches > 1 and isMigrating:
        mobDiag = np.random.choice(25, nPatches, replace = True)
        for i in range(nPatches):
            k = 0
            mobRow = np.random.multinomial(mobDiag[i], [1 / float(nPatches - 1)] * (nPatches - 1), size = 1)
            for j in range(nPatches):
                if i == j:
                    C[i][j] = float(-mobDiag[i]) / 100.0
                else:
                    C[i][j] = float(mobRow[0][k]) / 100.0
                    k = k + 1
    return C
        
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
