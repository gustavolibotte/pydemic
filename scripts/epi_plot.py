#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 11 14:50:19 2020

@author: gustavolibotte
"""

import matplotlib.pyplot as plt

class EpiPlot:
    
    @staticmethod
    def plotMetaSEIR(t, Y, patch, nPatches):
        # TODO: generic implementation for plotting purpose
        for i in range(patch - 1, nPatches * 4, nPatches):
            plt.plot(t, Y[i, :])
        plt.xlabel("Dias")
        plt.ylabel("População")
        plt.legend(['S', 'E', 'I', 'R'])
        plt.show()
