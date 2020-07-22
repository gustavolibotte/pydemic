#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 15:11:06 2020

@author: gustavolibotte
"""

import numpy as np

class MetaSEIRPDQ(object):
    def __init__(self, nPatches, beta, mu, gamma_I, gamma_A, gamma_P, d_I, d_P, omega,
                 epsilon_I, rho, eta, sigma, N):
        self.nPatches = nPatches
        self.beta = beta
        self.mu = mu
        self.gamma_I = gamma_I
        self.gamma_A = gamma_A
        self.gamma_P = gamma_P
        self.d_I = d_I
        self.d_P = d_P
        self.omega = omega
        self.epsilon_I = epsilon_I
        self.rho = rho
        self.eta = eta
        self.sigma = sigma
        self.N = N
    
    def metaSEIRPDQ(self, t: np.ndarray, Y: np.ndarray) -> np.ndarray:
        nCompart = 9
        Y = np.reshape(Y, (nCompart, self.nPatches))
        S, E, A, I, P, R, D, C, H = Y
        
        dS = np.zeros(self.nPatches)
        dE = np.zeros(self.nPatches)
        dA = np.zeros(self.nPatches)
        dI = np.zeros(self.nPatches)
        dP = np.zeros(self.nPatches)
        dR = np.zeros(self.nPatches)
        dD = np.zeros(self.nPatches)
        dC = np.zeros(self.nPatches)
        dH = np.zeros(self.nPatches)
        
        transmParam = np.sum(self.beta * I, 1)
        
        for i in range(self.nPatches):
            dS[i] = -transmParam[i] * S[i] / self.N[i] - self.mu / self.N[i] * S[i] * A[i] - self.omega * S[i] + self.eta * R[i]
            dE[i] = transmParam[i] * S[i] / self.N[i] + self.mu / self.N[i] * S[i] * A[i] - self.sigma * E[i] - self.omega * E[i]
            dA[i] = self.sigma * (1 - self.rho) * E[i] - self.gamma_A * A[i] - self.omega * A[i]
            dI[i] = self.sigma * self.rho * E[i] - self.gamma_I * I[i] - self.d_I * I[i] - self.omega * I[i] - self.epsilon_I * I[i]
            dP[i] = self.epsilon_I * I[i] - self.gamma_P * P[i] - self.d_P * P[i]
            dR[i] = self.gamma_A * A[i] + self.gamma_I * I[i] + self.gamma_P * P[i] + self.omega * (S[i] + E[i] + A[i] + I[i]) - self.eta * R[i]
            dD[i] = self.d_I * I[i] + self.d_P * P[i]
            dC[i] = self.epsilon_I * I[i]
            dH[i] = self.gamma_P * P[i]
        
        dSEIRPDQ = dS, dE, dA, dI, dP, dR, dD, dC, dH
        dSEIRPDQ = np.reshape(dSEIRPDQ, (nCompart * self.nPatches))
        return dSEIRPDQ
