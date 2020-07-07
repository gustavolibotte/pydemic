#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 10:39:29 2020

@author: gustavolibotte
"""

import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
from proj_consts import ProjectConsts

class LoadData:
    
    @staticmethod
    def getBrazilDataframe() -> pd.DataFrame:
        """
        Get updated data on the epidemic in Brazil
        
        Source: Número de casos confirmados de COVID-19 no Brasil (on GitHub)
        https://raw.githubusercontent.com/wcota/covid19br/master/cases-brazil-states.csv
        
        Parameters
        ----------
        None
        
        Return
        ------
        DataFrame
            COVID-19 data (cases, deaths, recoveries) in Brazil per day (in each state).
        """

        df_brazil_states_cases = pd.read_csv(
            ProjectConsts.CASES_BRAZIL_STATES_URL,
            usecols=["date", "state", "totalCases", "deaths", "recovered"],
            parse_dates=["date"],
        )
        df_brazil_states_cases.fillna(value={"recovered": 0}, inplace=True)
        df_brazil_states_cases = df_brazil_states_cases[df_brazil_states_cases.state != "TOTAL"]
        return df_brazil_states_cases
    
    @staticmethod
    def getBrazilStateDataframe(df_brazil: pd.DataFrame, state_name: str,
                                   confirmed_lower_threshold: int = 5) -> pd.DataFrame:
        """
        Data filtering on the epidemic in each state
        
        Parameters
        ----------
        df_brazil: pd.DataFrame
            Data on the epidemic in Brazil
        state_name: str
            State name
        confirmed_lower_threshold: int
            Minimum number of confirmed cases in time series
            
        Return
        ------
        pd.DataFrame
            COVID-19 data (cases, deaths, recoveries) in Brazil per day in a specific state.
        """
        df_brazil = df_brazil.copy()
        df_state_cases = df_brazil[df_brazil.state == state_name]
        df_state_cases.reset_index(inplace=True)
        columns_rename = {"totalCases": "confirmed"}
        df_state_cases.rename(columns=columns_rename, inplace=True)
        df_state_cases["active"] = (
            df_state_cases["confirmed"] - df_state_cases["deaths"] - df_state_cases["recovered"]
        )
    
        df_state_cases = df_state_cases[df_state_cases.confirmed > confirmed_lower_threshold]
        day_range_list = list(range(len(df_state_cases.confirmed)))
        df_state_cases["day"] = day_range_list
        return df_state_cases
    
    @staticmethod
    def getBrazilCasesByDay(source: str, store: bool = False, confirmed_lower_threshold: int = 5) -> pd.DataFrame:
        """
        Get updated data on the number of cumulative cases in Brazil by day
        
        Source: Ministry of Health of Brazil
        https://covid.saude.gov.br/
        
        Parameters
        ----------
        source: str
            "local" (previously saved file) or "web" (most updated file from web)
        store: bool
            determines whether data obtained when source = "web" is saved on the hard drive
        confirmed_lower_threshold: int
            Minimum number of confirmed cases in time series
            
        Return
        ------
        pd.DataFrame
            Cumulative COVID-19 data (cases, deaths, recoveries, active) in Brazil per day (in each state).
        """
        if source.lower() == "local":
            return pd.read_csv(f"{ProjectConsts.DATA_PATH}/brazil_by_day.csv", parse_dates=["date"])
        elif source.lower() == "web":
            try:
                from get_url_brazilian_ministry import run_url_catcher
                url_data_brazil_ministry = run_url_catcher()
            except ImportError as error:
                print(error.__class__.__name__ + ": " + error.message)
            df_brazil_cases_by_day = pd.read_excel(url_data_brazil_ministry,
                                                    usecols=["regiao", "data", "casosAcumulado", "obitosAcumulado", "Recuperadosnovos", "emAcompanhamentoNovos"],
                                                    parse_dates=["data"],)
            df_brazil_cases_by_day = df_brazil_cases_by_day[df_brazil_cases_by_day["regiao"]=="Brasil"]
            df_brazil_cases_by_day = df_brazil_cases_by_day.drop(columns=["regiao"])
            column_names = {"data": "date", "casosAcumulado": "confirmed", "obitosAcumulado": "deaths", "Recuperadosnovos": "recovered", "emAcompanhamentoNovos": "active"}
            df_brazil_cases_by_day = df_brazil_cases_by_day.rename(columns=column_names)
            df_brazil_cases_by_day = df_brazil_cases_by_day.fillna(value={"recovered": 0, "active": 0})
            df_brazil_cases_by_day = df_brazil_cases_by_day[df_brazil_cases_by_day.confirmed > confirmed_lower_threshold]
            df_brazil_cases_by_day = df_brazil_cases_by_day.reset_index(drop=True)
            df_brazil_cases_by_day["day"] = df_brazil_cases_by_day.date.apply(
                lambda x: (x - df_brazil_cases_by_day.date.min()).days + 1
            )
            df_brazil_cases_by_day = df_brazil_cases_by_day[["date", "day", "confirmed", "deaths", "recovered", "active"]]
            if store:
                df_brazil_cases_by_day.to_csv(f"{ProjectConsts.DATA_PATH}/brazil_by_day.csv", index=False)
            return df_brazil_cases_by_day
    
    @staticmethod
    def getLocalCasesByDay(state: str, city: str = "TOTAL", store: bool = False) -> pd.DataFrame:
        """
        Read the statistics for an spacific state or city
        
        Parameters
        ----------
        state: str
            State name (initials, as for example "RJ")
        city: str
            City name ("TOTAL" takes the cummulative number, considering all cities)
        store: bool
            determines whether data obtained is saved on the hard drive
        
        Return
        ------
        pd.DataFrame
            COVID-19 data (cases, deaths, recoveries, active) in Brazil per day
            for a single state or city
        """
        df_local_cases_by_day = pd.read_csv(ProjectConsts.CASES_BRAZIL_STATES_URL,
            usecols=["date", "state", "city", "totalCases", "deaths", "recovered"],
            parse_dates=["date"],
        )
        df_local_cases_by_day = df_local_cases_by_day[df_local_cases_by_day["state"] == state]
        df_local_cases_by_day = df_local_cases_by_day[df_local_cases_by_day["city"] == city]
        df_local_cases_by_day = df_local_cases_by_day.fillna(value={"recovered": 0})
        df_local_cases_by_day = df_local_cases_by_day.reset_index(drop=True)
        df_local_cases_by_day["day"] = df_local_cases_by_day.date.apply(
            lambda x: (x - df_local_cases_by_day.date.min()).days + 1
        )
        df_local_cases_by_day = df_local_cases_by_day.drop(columns=["date", "state", "city"])
        column_names = {"totalCases": "cases", "recovered": "recoveries"}
        df_local_cases_by_day = df_local_cases_by_day.rename(columns=column_names)
        df_local_cases_by_day = df_local_cases_by_day[["day", "cases", "deaths", "recoveries"]]
        if store:
            if city.upper() == "TOTAL":
                filename = state + "_covid19.csv"
            else:
                filename = state + "_" + city + "_covid19.csv"
            df_local_cases_by_day.to_csv(f"{ProjectConsts.DATA_PATH}/" + filename, index=False)
        return df_local_cases_by_day
