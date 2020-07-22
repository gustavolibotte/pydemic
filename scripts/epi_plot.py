#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 11 14:50:19 2020

@author: gustavolibotte
"""

import matplotlib
import matplotlib.pyplot as plt

class EpiPlot:
    
    @staticmethod
    def plotMetaSEIR(t, Y, patch, nPatches):
        for i in range(patch - 1, nPatches * 4, nPatches):
            plt.plot(t, Y[i, :])
        plt.xlabel("t (dias)")
        plt.ylabel("População")
        plt.legend(['S', 'E', 'I', 'R'])
        plt.show()
    
    @staticmethod
    def plotMetaSEIRPDQ(t, Y, patch, nPatches):
        matplotlib.rcParams['axes.linewidth'] = 0.5
        
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        
        ax1.set_xlabel('t (dias)')
        ax1.set_ylabel('S(t), R(t)')
        ax1.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        ax2.set_ylabel('E(t), A(t), I(t), P(t), D(t)')
        ax2.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        
        k = 0
        for i in range(patch - 1, nPatches * 7, nPatches):
            if k == 0:
                ax1.plot(t, Y[i, :], 'b-', label = 'S', linewidth = 0.5)
            elif k == 1:
                ax2.plot(t, Y[i, :], 'g-', label = 'E', linewidth = 0.5)
            elif k == 2:
                ax2.plot(t, Y[i, :], 'r-', label = 'A', linewidth = 0.5)
            elif k == 3:
                ax2.plot(t, Y[i, :], 'c-', label = 'I', linewidth = 0.5)
            elif k == 4:
                ax2.plot(t, Y[i, :], 'm-', label = 'P', linewidth = 0.5)
            elif k == 5:
                ax1.plot(t, Y[i, :], 'y-', label = 'R', linewidth = 0.5)
            else:
                ax2.plot(t, Y[i, :], 'k-', label = 'D', linewidth = 0.5)
            k = k + 1
        
        fig.tight_layout()
        
        hand1, lab1 = ax1.get_legend_handles_labels()
        ax1.legend(hand1, lab1, frameon=True, loc='upper left', ncol=1, bbox_to_anchor=(0.0, 1.25))
        hand2, lab2 = ax2.get_legend_handles_labels()
        ax2.legend(hand2, lab2, frameon=True, loc='upper right', ncol=3, bbox_to_anchor=(1.0, 1.25))
        
        # matplotlib.rcParams['pdf.fonttype'] = 42
        # matplotlib.rcParams['ps.fonttype'] = 42
        # plt.savefig('/Users/gustavolibotte/Desktop/figs/SEIRPDQsim5-' + str(patch) + '.pdf', dpi = 1000, bbox_extra_artists=([lg1, lg2]), bbox_inches='tight')
        plt.show()
