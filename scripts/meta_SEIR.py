#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 19:23:26 2020

@author: gustavolibotte
"""

import numpy as np

class MetaSEIR:
    def __init__(self, nPatches: int, beta: np.ndarray, C: np.ndarray,
                 mu: float, sigma: float, gamma: float, M: np.ndarray) -> None:
        """
        Parameters
        ----------
        nPatches: int
            Total number of patches
        beta: np.ndarray
            Cross-coupling matrix
        C: np.ndarray
            Mobility matrix
        mu: float
            death rate
        sigma: float
            incubation period
        gamma: float
            removal rate
        M: np.ndarray
            Relative migration rate 
        """
        self.nPatches = nPatches
        self.beta = beta
        self.C = C
        self.mu = mu
        self.sigma = sigma
        self.gamma = gamma
        self.M = M
    
    def metaSEIR(self, t: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """
        Metapopulation-based SEIR model
        
        Source: A. L. Lloyd and V. A. A. Jansen, "Spatiotemporal dynamics of
        epidemics: synchrony in metapopulation models," vol. 188, pp. 1–16,
        2004, doi: 10.1016/j.mbs.2003.09.003.
        
        Parameters
        ----------
        t: np.ndarray
            Time array
        Y: np.ndarray
            Population array in format [S1, ..., Sn, E1, ..., En, I1, ..., In,
            R1, ..., Rn]
        
        Return
        ------
        np.ndarray
            Population array in format [S1, ..., Sn, E1, ..., En, I1, ..., In,
            R1, ..., Rn]
        """
        nCompart = 4
        Y = np.reshape(Y, (nCompart, self.nPatches))
        S, E, I, R = Y

        dS = np.zeros(self.nPatches)
        dE = np.zeros(self.nPatches)
        dI = np.zeros(self.nPatches)
        dR = np.zeros(self.nPatches)

        transmParam = np.sum(self.beta * I, 1)
        mobS = np.sum(self.C * S[:, np.newaxis], 0)
        mobE = np.sum(self.C * E[:, np.newaxis], 0)
        mobI = np.sum(self.C * I[:, np.newaxis], 0)
        mobR = np.sum(self.C * R[:, np.newaxis], 0)
        
        for i in range(self.nPatches):
            dS[i] = self.mu - self.mu * S[i] - S[i] * transmParam[i] + self.M[0] * mobS[i]
            dE[i] = S[i] * transmParam[i] - (self.mu + self.sigma) * E[i] + self.M[1] * mobE[i]
            dI[i] = self.sigma * E[i] - (self.mu + self.gamma) * I[i] + self.M[2] * mobI[i]
            dR[i] = self.gamma * I[i] - self.mu * R[i] + self.M[3] * mobR[i]
        
        dSEIR = dS, dE, dI, dR
        dSEIR = np.reshape(dSEIR, (nCompart * self.nPatches))
        return dSEIR
