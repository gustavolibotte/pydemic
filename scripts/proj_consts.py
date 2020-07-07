#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 10:42:32 2020

@author: gustavolibotte
"""

class ProjectConsts:
    """Container of constants"""
    
    # %% Values
    BRAZIL_POPULATION = float(210147125)  # gathered from IBGE 2019
    RJ_CITY_POPULATION = float(6718903)    # gathered from IBGE 2019
    SP_STATE_POPULATION = float(45919049) # gathered from IBGE 2019
    RJ_STATE_POPULATION = float(17264943) # gathered from IBGE 2019
    CE_STATE_POPULATION = float(9132078)  # gathered from IBGE 2019
    
    # %% Paths
    DATA_PATH = "../pydemic/data"
    
    # %% URLs
    CASES_BRAZIL_STATES_URL = "https://raw.githubusercontent.com/wcota/covid19br/master/cases-brazil-states.csv"
    BRAZIL_HEALTH_MINISTRY_URL = "https://covid.saude.gov.br/"
