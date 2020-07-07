# %% [markdown]
# # COVID-19 SEIRPD-Q model
#
# ## Table of Contents
#
# 1. [Importing libs](#importing)
#
# 2. [Loading data](#loading)
#
# 3. [Data cleaning](#cleaning)
#
# 4. [(Very) Basic EDA](#eda)
#
# 5. [Epidemiology models](#models)
#
# 6. [Programming SEIRPD-Q model in Python](#implementations)
#
# 7. [Least-squares fitting](#least-squares)
#
# 8. [Extrapolation/Predictions](#deterministic-predictions)
#
# 9. [Forward UQ](#uq)
#
# 10. [Bayesian Calibration](#bayes-calibration)
#
# Before analyze the models, we begin having a look at the available data.
# %% [markdown]
# <a id="importing"></a>
# ## Importing libs

# %%
import os
import time

import matplotlib.pyplot as plt
import arviz as az
from arviz.utils import Numba
import numpy as np  # linear algebra
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
import pymc3 as pm  # for uncertainty quantification and model calibration
import theano  # to control better pymc3 backend and write a wrapper
import theano.tensor as t  # for the wrapper to a custom model to pymc3
from numba import jit  # to accelerate ODE system RHS evaluations
from scipy import optimize  # to solve minimization problem from least-squares fitting
from scipy.stats import gaussian_kde  # to calculate MPV from KDE
from scipy.integrate import solve_ivp  # to solve ODE system
from tqdm import tqdm, trange

from proj_consts import ProjectConsts
from get_url_brazilian_ministry import run_url_catcher

seed = 12345  # for the sake of reproducibility :)
np.random.seed(seed)

plt.style.use("seaborn-talk")  # beautify the plots!

THEANO_FLAGS = "optimizer=fast_compile"  # A theano trick

Numba.enable_numba()  # speed-up arviz plots

# DATA_PATH = os.environ["DATA_DIR"]
DATA_PATH = "../pydemic/data"

# %% [markdown]
# <a id="loading"></a>
# ## Loading data


# %%
brazil_population = float(210147125)  # gathered from IBGE 2019
rio_population = float(6718903)       # gathered from IBGE 2019
sp_state_population = float(45919049) # gathered from IBGE 2019
rj_state_population = float(17264943) # gathered from IBGE 2019
ce_state_population = float(9132078)  # gathered from IBGE 2019

target_population = brazil_population

# %%
df_brazil_states_cases = pd.read_csv(
    ProjectConsts.casesBrazilStatesURL,
    usecols=["date", "state", "totalCases", "deaths", "recovered"],
    parse_dates=["date"],
)
df_brazil_states_cases.fillna(value={"recovered": 0}, inplace=True)
df_brazil_states_cases = df_brazil_states_cases[df_brazil_states_cases.state != "TOTAL"]

print(df_brazil_states_cases)


# %%
def get_brazil_state_dataframe(
    df_brazil: pd.DataFrame, state_name: str, confirmed_lower_threshold: int = 5
) -> pd.DataFrame:
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


df_sp_state_cases = get_brazil_state_dataframe(df_brazil_states_cases, state_name="SP")
df_rj_state_cases = get_brazil_state_dataframe(df_brazil_states_cases, state_name="RJ")
df_ce_state_cases = get_brazil_state_dataframe(df_brazil_states_cases, state_name="CE")

# %% [markdown]
# Initial Conditions:

# %%
# df_brazil_cases_by_day = pd.read_csv(f"{DATA_PATH}/brazil_by_day.csv", parse_dates=["date"])

url_data_brazil_ministry = run_url_catcher()
df_brazil_cases_by_day = pd.read_excel(url_data_brazil_ministry,
                                        usecols=["regiao", "data", "casosAcumulado", "obitosAcumulado", "Recuperadosnovos", "emAcompanhamentoNovos"],
                                        parse_dates=["data"],)
df_brazil_cases_by_day = df_brazil_cases_by_day[df_brazil_cases_by_day["regiao"]=="Brasil"]
df_brazil_cases_by_day = df_brazil_cases_by_day.drop(columns=["regiao"])
df_brazil_cases_by_day = df_brazil_cases_by_day.rename(columns={"data": "date", "casosAcumulado": "confirmed", "obitosAcumulado": "deaths", "Recuperadosnovos": "recovered", "emAcompanhamentoNovos": "active"})
df_brazil_cases_by_day = df_brazil_cases_by_day.fillna(value={"recovered": 0, "active": 0})
df_brazil_cases_by_day = df_brazil_cases_by_day[df_brazil_cases_by_day.confirmed > 5]
df_brazil_cases_by_day = df_brazil_cases_by_day.reset_index(drop=True)
df_brazil_cases_by_day["day"] = df_brazil_cases_by_day.date.apply(
    lambda x: (x - df_brazil_cases_by_day.date.min()).days + 1
)
df_brazil_cases_by_day = df_brazil_cases_by_day[["date", "day", "confirmed", "deaths", "recovered", "active"]]
df_brazil_cases_by_day.to_csv("../pydemic/data/brazil_by_day.csv", index=False)
print(df_brazil_cases_by_day)

# %%
# df_rio_cases_by_day = pd.read_csv(f"{DATA_PATH}/rio_covid19.csv")

df_rio_cases_by_day = pd.read_csv(
    ProjectConsts.casesBrazilStatesURL,
    usecols=["date", "state", "city", "totalCases", "deaths", "recovered"],
    parse_dates=["date"],
)
df_rio_cases_by_day = df_rio_cases_by_day[df_rio_cases_by_day["state"]=="RJ"]
df_rio_cases_by_day = df_rio_cases_by_day[df_rio_cases_by_day["city"]=="TOTAL"]
df_rio_cases_by_day = df_rio_cases_by_day.fillna(value={"recovered": 0})
df_rio_cases_by_day = df_rio_cases_by_day.reset_index(drop=True)
df_rio_cases_by_day["day"] = df_rio_cases_by_day.date.apply(
    lambda x: (x - df_rio_cases_by_day.date.min()).days + 1
)
df_rio_cases_by_day = df_rio_cases_by_day.drop(columns=["date", "state", "city"])
df_rio_cases_by_day = df_rio_cases_by_day.rename(columns={"totalCases": "cases", "recovered": "recoveries"})
df_rio_cases_by_day = df_rio_cases_by_day[["day", "cases", "deaths", "recoveries"]]
df_rio_cases_by_day.to_csv("../pydemic/data/rio_covid19.csv", index=False)
print(df_rio_cases_by_day)

# %%
df_target_country = df_brazil_cases_by_day

E0, A0, I0, P0, R0, D0, C0, H0 = (
    int(10 * float(df_target_country.confirmed.values[0])),
    int(1 * float(df_target_country.confirmed.values[0])),
    int(5 * float(df_target_country.confirmed.values[0])),
    int(float(df_target_country.confirmed.values[0])),
    int(float(df_target_country.recovered.values[0])),
    int(float(df_target_country.deaths.values[0])),
    int(float(df_target_country.confirmed.values[0])),
    int(float(df_target_country.recovered.values[0])),
)

S0 = target_population - (E0 + A0 + I0 + R0 + P0 + D0)
y0_seirpdq = S0, E0, A0, I0, P0, R0, D0, C0, H0  # SEIRPDQ IC array (not fully used)
# print(y0_seirpdq)

# %% [markdown]
# <a id="implementations"></a>
# ## Programming SEIRPD-Q model in Python

# %%
@jit(nopython=True)
def seirpdq_model(
    t,
    X,
    beta0=1e-7,
    beta1=1e-7,
    mu0=1e-7,
    mu1=1e-7,
    gamma_I=0.1,
    gamma_A=0.15,
    gamma_P=0.14,
    d_I=0.0105,
    d_P=0.003,
    omega=1 / 10,
    epsilon_I=1 / 3,
    rho=0.1,
    eta=2e-2,
    sigma=1 / 7,
    N=1,
):
    """
    SEIRPD-Q python implementation.
    """
    S, E, A, I, P, R, D, C, H = X
    beta = beta0  # * np.exp(-beta1 * t)
    mu = mu0  # * np.exp(-mu1 * t)
    S_prime = -beta / N * S * I - mu / N * S * A - omega * S + eta * R
    E_prime = beta / N * S * I + mu / N * S * A - sigma * E - omega * E
    A_prime = sigma * (1 - rho) * E - gamma_A * A - omega * A
    I_prime = sigma * rho * E - gamma_I * I - d_I * I - omega * I - epsilon_I * I
    P_prime = epsilon_I * I - gamma_P * P - d_P * P
    R_prime = gamma_A * A + gamma_I * I + gamma_P * P + omega * (S + E + A + I) - eta * R
    D_prime = d_I * I + d_P * P
    C_prime = epsilon_I * I
    H_prime = gamma_P * P
    return S_prime, E_prime, A_prime, I_prime, P_prime, R_prime, D_prime, C_prime, H_prime


# %% [markdown]
# ODE solvers wrapper using `scipy.integrate.solve_ivp`:

# %%
def seirpdq_ode_solver(
    y0,
    t_span,
    t_eval,
    beta0=1e-7,
    omega=1 / 10,
    # gamma_P=1 / 14,
    d_P=9e-3,
    d_I=2e-4,
    gamma_P=1 / 14,
    mu0=1e-7,
    gamma_I=1 / 14,
    gamma_A=1 / 14,
    epsilon_I=1 / 3,
    rho=0.85,
    sigma=1 / 5,
    eta=0,
    beta1=0,
    mu1=0,
    N=1,
):
    mu0 = beta0
    solution_ODE = solve_ivp(
        fun=lambda t, y: seirpdq_model(
            t,
            y,
            beta0=beta0,
            beta1=beta1,
            mu0=mu0,
            mu1=mu1,
            gamma_I=gamma_I,
            gamma_A=gamma_A,
            gamma_P=gamma_P,
            d_I=d_I,
            d_P=d_P,
            omega=omega,
            epsilon_I=epsilon_I,
            rho=rho,
            eta=eta,
            sigma=sigma,
            N=N,
        ),
        t_span=t_span,
        y0=y0,
        t_eval=t_eval,
        method="LSODA",
    )

    return solution_ODE


# %% [markdown]
# <a id="least-squares"></a>
# ## Least-Squares fitting
#
# Now, we can know how to solve the forward problem, so we can try to fit it with a non-linear Least-Squares method for parameter estimation. Let's begin with a generic Least-Square formulation:

# %%
def seirpdq_least_squares_error_ode_y0(
    par, time_exp, f_exp, fitting_model, known_initial_conditions, total_population
):
    num_of_initial_conditions_to_fit = 3
    num_of_parameters = len(par) - num_of_initial_conditions_to_fit
    args, trial_initial_conditions = [
        par[:num_of_parameters],
        par[num_of_parameters:],
    ]
    E0, A0, I0 = trial_initial_conditions
    _, P0, R0, D0, C0, H0 = known_initial_conditions
    S0 = total_population - (E0 + A0 + I0 + R0 + P0 + D0)
    initial_conditions = [S0, E0, A0, I0, P0, R0, D0, C0, H0]

    f_exp1, f_exp2, f_exp3, f_exp4 = f_exp
    time_span = (time_exp.min(), time_exp.max())

    # weighting_denominator = f_exp1.max() + f_exp2.max() + f_exp3.max() + f_exp4.max()
    # weighting_for_exp1_constraints = 1 / (f_exp1.max() / weighting_denominator)
    # weighting_for_exp2_constraints = 1 / (f_exp2.max() / weighting_denominator)
    # weighting_for_exp3_constraints = 1 / (f_exp3.max() / weighting_denominator)
    # weighting_for_exp4_constraints = 1 / (f_exp4.max() / weighting_denominator)
    weighting_for_exp1_constraints = 0e0
    weighting_for_exp2_constraints = 1e0
    weighting_for_exp3_constraints = 1e0
    weighting_for_exp4_constraints = 0e0
    num_of_qoi = len(f_exp1)

    try:
        y_model = fitting_model(initial_conditions, time_span, time_exp, *args)
        simulated_time = y_model.t
        simulated_ode_solution = y_model.y
        (
            _,
            _,
            _,
            _,
            simulated_qoi1,
            _,
            simulated_qoi2,
            simulated_qoi3,
            simulated_qoi4,
        ) = simulated_ode_solution

        residual1 = f_exp1 - simulated_qoi1
        residual2 = f_exp2 - simulated_qoi2  # Deaths
        residual3 = f_exp3 - simulated_qoi3  # Cases
        residual4 = f_exp4 - simulated_qoi4

        first_term = weighting_for_exp1_constraints * np.sum(residual1 ** 2.0)
        second_term = weighting_for_exp2_constraints * np.sum(residual2 ** 2.0)
        third_term = weighting_for_exp3_constraints * np.sum(residual3 ** 2.0)
        fourth_term = weighting_for_exp4_constraints * np.sum(residual4 ** 2.0)
        # first_term = weighting_for_exp1_constraints * np.abs(residual1).sum()
        # second_term = weighting_for_exp2_constraints * np.abs(residual2).sum()
        # third_term = weighting_for_exp3_constraints * np.abs(residual3).sum()
        # fourth_term = weighting_for_exp4_constraints * np.abs(residual4).sum()
        objective_function = 1 / num_of_qoi * (first_term + second_term + third_term + fourth_term)
    except ValueError:
        objective_function = 1e15

    return objective_function


def seirpdq_least_squares_error_ode(
    par, time_exp, f_exp, fitting_model, initial_conditions, total_population
):
    args = par
    f_exp1, f_exp2, f_exp3, f_exp4 = f_exp
    time_span = (time_exp.min(), time_exp.max())

    # weighting_denominator = f_exp1.max() + f_exp2.max() + f_exp3.max() + f_exp4.max()
    # weighting_for_exp1_constraints = 1 / (f_exp1.max() / weighting_denominator)
    # weighting_for_exp2_constraints = 1 / (f_exp2.max() / weighting_denominator)
    # weighting_for_exp3_constraints = 1 / (f_exp3.max() / weighting_denominator)
    # weighting_for_exp4_constraints = 1 / (f_exp4.max() / weighting_denominator)
    weighting_for_exp1_constraints = 0e0
    weighting_for_exp2_constraints = 1e0
    weighting_for_exp3_constraints = 1e0
    weighting_for_exp4_constraints = 0e0
    num_of_qoi = len(f_exp1)

    try:
        y_model = fitting_model(initial_conditions, time_span, time_exp, *args)
        simulated_time = y_model.t
        simulated_ode_solution = y_model.y
        (
            _,
            _,
            _,
            _,
            simulated_qoi1,  # P
            _,
            simulated_qoi2,  # D
            simulated_qoi3,  # C
            simulated_qoi4,  # H
        ) = simulated_ode_solution

        residual1 = f_exp1 - simulated_qoi1
        residual2 = f_exp2 - simulated_qoi2  # Deaths
        residual3 = f_exp3 - simulated_qoi3  # Cases
        residual4 = f_exp4 - simulated_qoi4

        first_term = weighting_for_exp1_constraints * np.sum(residual1 ** 2.0)
        second_term = weighting_for_exp2_constraints * np.sum(residual2 ** 2.0)
        third_term = weighting_for_exp3_constraints * np.sum(residual3 ** 2.0)
        fourth_term = weighting_for_exp4_constraints * np.sum(residual4 ** 2.0)
        # first_term = weighting_for_exp1_constraints * np.abs(residual1).sum()
        # second_term = weighting_for_exp2_constraints * np.abs(residual2).sum()
        # third_term = weighting_for_exp3_constraints * np.abs(residual3).sum()
        # fourth_term = weighting_for_exp4_constraints * np.abs(residual4).sum()
        objective_function = 1 / num_of_qoi * (first_term + second_term + third_term + fourth_term)
    except ValueError:
        objective_function = 1e15

    return objective_function


def callback_de(xk, convergence):
    print(f"parameters = {xk}\n")


# %% [markdown]
# Setting fitting domain (given time for each observation) and the observations (observed population at given time):

# %%
data_time = df_target_country.day.values.astype(np.float64)
infected_individuals = df_target_country.active.values
dead_individuals = df_target_country.deaths.values
confirmed_cases = df_target_country.confirmed.values
recovered_cases = df_target_country.recovered.values

# %% [markdown]
# To calibrate the model, we define an objective function, which is a Least-Squares function in the present case, and minimize it. To (*try to*) avoid local minima, we use Differential Evolution (DE) method (see this [nice presentation](https://www.maths.uq.edu.au/MASCOS/Multi-Agent04/Fleetwood.pdf) to get yourself introduced to this great subject). In summary, DE is a family of Evolutionary Algorithms that aims to solve Global Optimization problems. Moreover, DE is derivative-free and population-based method.
#
# Below, calibration is performed for selected models:

# %%
# num_of_parameters_to_fit_seirpdq = 10
# bounds_seirpdq = num_of_parameters_to_fit_seirpdq * [(0, 1)]

bounds_seirpdq = [
    (0, 1e-5),  # beta
    (0, 1),  # omega
    # (1 / 21, 1 / 10),  # gamma_P
    (0.1, 1e-5),  # d_P
    (0.1, 1e-5),  # d_I
    # (1 / 21, 1 / 14),  # gamma_P
]
# bounds_seirdaq = [(0, 1e-2), (0, 1), (0, 1), (0, 0.2), (0, 0.2), (0, 0.2)]

result_seirpdq = optimize.differential_evolution(
    seirpdq_least_squares_error_ode,
    bounds=bounds_seirpdq,
    args=(
        data_time,
        [infected_individuals, dead_individuals, confirmed_cases, recovered_cases],
        seirpdq_ode_solver,
        y0_seirpdq,
        target_population,
    ),
    popsize=20,
    strategy="best1bin",
    tol=1e-5,
    recombination=0.95,
    mutation=0.6,
    maxiter=10000,
    polish=True,
    disp=True,
    seed=seed,
    callback=callback_de,
    workers=-1,
)

print(result_seirpdq)

# %%
print(f"-- Initial conditions: {y0_seirpdq}")

# %%
(
    beta_deterministic,
    omega_deterministic,
    # gamma_P_deterministic,
    d_P_deterministic,
    d_I_deterministic,
    # gamma_P_deterministic,
) = result_seirpdq.x

gamma_I_deterministic = 1 / 14
gamma_A_deterministic = 1 / 14
gamma_P_deterministic = 1 / 14
# d_I_deterministic = 2e-4
# d_P_deterministic = 9e-3
epsilon_I_deterministic = 1 / 3
rho_deterministic = 0.85
sigma_deterministic = 1 / 5
eta_deterministic = 0

# %%
def calculate_reproduction_number(
    S0, beta, mu, gamma_A, gamma_I, d_I, epsilon_I, rho, omega, sigma=1 / 7
):
    left_term = sigma * (1 - rho) * mu / ((sigma + omega) * (gamma_A + omega))
    right_term = beta * sigma * rho / ((sigma + omega) * (gamma_I + d_I + omega + epsilon_I))
    return (left_term + right_term) * S0


reproduction_number = calculate_reproduction_number(
    S0,
    beta_deterministic,
    beta_deterministic,
    gamma_I_deterministic,
    gamma_A_deterministic,
    d_I_deterministic,
    epsilon_I_deterministic,
    rho_deterministic,
    omega_deterministic,
    sigma_deterministic,
)

# %%
t0 = data_time.min()
tf = data_time.max()

solution_ODE_seirpdq = seirpdq_ode_solver(y0_seirpdq, (t0, tf), data_time, *result_seirpdq.x)
t_computed_seirpdq, y_computed_seirpdq = solution_ODE_seirpdq.t, solution_ODE_seirpdq.y
(
    S_seirpdq,
    E_seirpdq,
    A_seirpdq,
    I_seirpdq,
    P_seirpdq,
    R_seirpdq,
    D_seirpdq,
    C_seirpdq,
    H_seirpdq,
) = y_computed_seirpdq


# %%
parameters_dict = {
    "Model": "SEAIRPD-Q",
    u"$beta$": beta_deterministic,
    u"$mu$": beta_deterministic,
    u"$gamma_I$": gamma_I_deterministic,
    u"$gamma_A$": gamma_A_deterministic,
    u"$gamma_P$": gamma_P_deterministic,
    u"$d_I$": d_I_deterministic,
    u"$d_P$": d_P_deterministic,
    u"$epsilon_I$": epsilon_I_deterministic,
    u"$rho$": rho_deterministic,
    u"$omega$": omega_deterministic,
    u"$sigma$": sigma_deterministic,
}

df_parameters_calibrated = pd.DataFrame.from_records([parameters_dict])

# df_parameters_calibrated


# %%
print(df_parameters_calibrated.to_latex(index=False))

# %% [markdown]
# Show calibration result based on available data:

# %%
plt.figure(figsize=(9, 7))

plt.plot(
    t_computed_seirpdq,
    I_seirpdq,
    label="Infected (SEAIRPD-Q)",
    marker="X",
    linestyle="-",
    markersize=10,
)
plt.plot(
    t_computed_seirpdq,
    A_seirpdq,
    label="Asymptomatic (SEAIRPD-Q)",
    marker="o",
    linestyle="-",
    markersize=10,
)
# plt.plot(t_computed_seirdq, R_seirdq * target_population, label='Recovered (SEIRDAQ)', marker='o', linestyle="-", markersize=10)
plt.plot(
    t_computed_seirpdq,
    P_seirpdq,
    label="Diagnosed (SEAIRPD-Q)",
    marker="s",
    linestyle="-",
    markersize=10,
)
plt.plot(
    t_computed_seirpdq,
    D_seirpdq,
    label="Deaths (SEAIRPD-Q)",
    marker="s",
    linestyle="-",
    markersize=10,
)

plt.plot(
    data_time, infected_individuals, label="Diagnosed data", marker="s", linestyle="", markersize=10
)
plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)
plt.legend()
plt.grid()
plt.xlabel("Time (days)")
plt.ylabel("Population")

plt.tight_layout()
plt.savefig("seirpdq_deterministic_calibration.png")
# plt.show()

# %%
plt.figure(figsize=(9, 7))

plt.plot(
    t_computed_seirpdq,
    C_seirpdq,
    label="Cases (SEAIRPD-Q)",
    marker="X",
    linestyle="-",
    markersize=10,
)

plt.plot(
    t_computed_seirpdq,
    H_seirpdq,
    label="Recovered (SEAIRPD-Q)",
    marker="D",
    linestyle="-",
    markersize=10,
)

plt.plot(
    t_computed_seirpdq,
    D_seirpdq,
    label="Deaths (SEAIRPD-Q)",
    marker="v",
    linestyle="-",
    markersize=10,
)

plt.plot(
    data_time, confirmed_cases, label="Confirmed data", marker="s", linestyle="", markersize=10
)

plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)

""" plt.plot(
    data_time, recovered_cases, label="Recorded recoveries", marker="v", linestyle="", markersize=10
) """

plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()
plt.grid()

plt.tight_layout()
plt.savefig("seirpdq_deterministic_cumulative_calibration.png")
# plt.show()

# %%
methods_list = list()
deaths_list = list()

methods_list.append("SEIRPD-Q")
deaths_list.append(int(D_seirpdq.max()))
print(f"-- Confirmed cases estimate for today (SEIRPD-Q):\t{int(P_seirpdq.max())}")
print(
    f"-- Confirmed cases estimate population percentage for today (SEIRPD-Q):\t{100 * P_seirpdq.max() / target_population:.3f}%"
)
print(f"-- Death estimate for today (SEIRPD-Q):\t{int(D_seirpdq.max())}")
print(
    f"-- Death estimate population percentage for today (SEIRPD-Q):\t{100 * D_seirpdq.max() / target_population:.3f}%"
)

methods_list.append("Recorded")
deaths_list.append(int(dead_individuals[-1]))

death_estimates_dict = {"Method": methods_list, "Deaths estimate": deaths_list}
df_deaths_estimates = pd.DataFrame(death_estimates_dict)
print(f"-- Recorded deaths until today:\t{int(dead_individuals[-1])}")


# %%
# df_deaths_estimates.set_index("Model", inplace=True)
print(df_deaths_estimates.to_latex(index=False))

# %% [markdown]
# <a id="deterministic-predictions"></a>
# ## Extrapolation/Predictions
#
# Now, let's extrapolate to next days.

# %%
t0 = float(data_time.min())
number_of_days_after_last_record = 120
tf = data_time.max() + number_of_days_after_last_record
time_range = np.linspace(t0, tf, int(tf - t0) + 1)

solution_ODE_predict_seirpdq = seirpdq_ode_solver(
    y0_seirpdq, (t0, tf), time_range, *result_seirpdq.x
)  # SEIRDAQ
#     solution_ODE_predict_seirdaq = seirdaq_ode_solver(y0_seirdaq, (t0, tf), time_range)  # SEIRDAQ
t_computed_predict_seirpdq, y_computed_predict_seirpdq = (
    solution_ODE_predict_seirpdq.t,
    solution_ODE_predict_seirpdq.y,
)
(
    S_predict_seirpdq,
    E_predict_seirpdq,
    A_predict_seirpdq,
    I_predict_seirpdq,
    P_predict_seirpdq,
    R_predict_seirpdq,
    D_predict_seirpdq,
    C_predict_seirpdq,
    H_predict_seirpdq,
) = y_computed_predict_seirpdq

# %% [markdown]
# Calculating the day when the number of infected individuals is max:

# %%
has_to_plot_infection_peak = True

crisis_day_seirpdq = np.argmax(P_predict_seirpdq) + 1


# %%
plt.figure(figsize=(9, 7))

#     plt.plot(t_computed_predict_seirdaq, 100 * S_predict_seirdq, label='Susceptible (SEIRD-Q)', marker='s', linestyle="-", markersize=10)
# plt.plot(t_computed_predict_seirpdq, E_predict_seirpdq, label='Exposed (SEIRPD-Q)', marker='*', linestyle="-", markersize=10)
plt.plot(
    t_computed_predict_seirpdq,
    I_predict_seirpdq,
    label="Infected (SEAIRPD-Q)",
    marker="X",
    linestyle="-",
    markersize=10,
)
plt.plot(
    t_computed_predict_seirpdq,
    A_predict_seirpdq,
    label="Asymptomatic (SEAIRPD-Q)",
    marker="o",
    linestyle="-",
    markersize=10,
)
#     plt.plot(t_computed_predict_seirdaq, 100 * R_predict_seirdaq, label='Recovered (SEIRDAQ)', marker='o', linestyle="-", markersize=10)
plt.plot(
    t_computed_predict_seirpdq,
    D_predict_seirpdq,
    label="Deaths (SEAIRPD-Q)",
    marker="v",
    linestyle="-",
    markersize=10,
)
plt.plot(
    t_computed_predict_seirpdq,
    P_predict_seirpdq,
    label="Diagnosed (SEAIRPD-Q)",
    marker="D",
    linestyle="-",
    markersize=10,
)
if has_to_plot_infection_peak:
    plt.axvline(
        x=crisis_day_seirpdq, color="red", linestyle="-", label="Diagnosed peak (SEAIRPD-Q)"
    )

""" plt.plot(
    data_time, infected_individuals, label="Diagnosed data", marker="s", linestyle="", markersize=10
) """
plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)

plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()
plt.grid()

plt.tight_layout()
plt.savefig("seirpdq_deterministic_predictions.png")
# plt.show()

# %%
plt.figure(figsize=(9, 7))

plt.plot(
    t_computed_predict_seirpdq,
    C_predict_seirpdq,
    label="Cases (SEAIRPD-Q)",
    marker="X",
    linestyle="-",
    markersize=10,
)

plt.plot(
    t_computed_predict_seirpdq,
    H_predict_seirpdq,
    label="Recovered (SEAIRPD-Q)",
    marker="D",
    linestyle="-",
    markersize=10,
)

plt.plot(
    t_computed_predict_seirpdq,
    D_predict_seirpdq,
    label="Deaths (SEAIRPD-Q)",
    marker="v",
    linestyle="-",
    markersize=10,
)

plt.plot(
    data_time, confirmed_cases, label="Confirmed data", marker="s", linestyle="", markersize=10
)

plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)

""" plt.plot(
    data_time, recovered_cases, label="Recorded recoveries", marker="v", linestyle="", markersize=10
) """

plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()
plt.grid()

plt.tight_layout()
plt.savefig("seirpdq_deterministic_cumulative_predictions.png")
# plt.show()

# %%
print(
    f"-- Max number of diagnosed individuals (SEIRPD-Q model):\t {int(np.max(P_predict_seirpdq))}"
)
print(
    f"-- Population percentage of max number of diagnosed individuals (SEIRPD-Q model):\t {100 * np.max(P_predict_seirpdq) / target_population:.2f}%"
)
print(
    f"-- Day estimate for max number of diagnosed individuals (SEIRPD-Q model):\t {crisis_day_seirpdq}"
)
print(
    f"-- Percentage of number of death estimate (SEIRPD-Q model):\t {100 * D_predict_seirpdq[-1] / target_population:.3f}%"
)
print(f"-- Number of death estimate (SEIRPD-Q model):\t {int(D_predict_seirpdq[-1])}")
print(f"-- Reproduction number (R0):\t {reproduction_number:.3f}")


# %% [markdown]
# <a id="bayes-calibration"></a>
# ## Bayesian Calibration

# %%
observations_to_fit = np.vstack([dead_individuals, confirmed_cases]).T


# %%
@theano.compile.ops.as_op(
    itypes=[t.dvector, t.dvector, t.dscalar, t.dscalar, t.dscalar, t.dscalar], otypes=[t.dmatrix]
)
def seirpdq_ode_wrapper(time_exp, initial_conditions, beta, gamma, delta, theta):
    time_span = (time_exp.min(), time_exp.max())

    args = [beta, gamma, delta, theta]
    y_model = seirpdq_ode_solver(initial_conditions, time_span, time_exp, *args)
    simulated_time = y_model.t
    simulated_ode_solution = y_model.y
    (_, _, _, _, _, _, simulated_qoi1, simulated_qoi2, _,) = simulated_ode_solution

    concatenate_simulated_qoi = np.vstack([simulated_qoi1, simulated_qoi2])

    return concatenate_simulated_qoi


@theano.compile.ops.as_op(
    itypes=[
        t.dvector,
        t.dvector,
        t.dscalar,
        t.dscalar,  # beta
        t.dscalar,  # omega
        # t.dscalar,  # gamma_P
        t.dscalar,  # d_P
        t.dscalar,  # d_I
        # t.dscalar,  # gamma_P
    ],
    otypes=[t.dmatrix],
)
def seirpdq_ode_wrapper_with_y0(
    time_exp, initial_conditions, total_population, beta, omega, d_P, d_I
):
    time_span = (time_exp.min(), time_exp.max())

    # args = [beta, omega, gamma_P, d_P, d_I]
    args = [beta, omega, d_P, d_I]
    # args = [beta, omega, gamma_P, d_P]
    # args = [beta, omega, gamma_P]
    y_model = seirpdq_ode_solver(initial_conditions, time_span, time_exp, *args)
    simulated_time = y_model.t
    simulated_ode_solution = y_model.y
    (_, _, _, _, _, _, simulated_qoi1, simulated_qoi2, _,) = simulated_ode_solution

    concatenate_simulated_qoi = np.vstack([simulated_qoi1, simulated_qoi2]).T

    return concatenate_simulated_qoi


# %%
print("\n*** Performing Bayesian calibration ***")

print("-- Running Monte Carlo simulations:")
draws = 3000
start_time = time.time()
percent_calibration = 0.95
with pm.Model() as model_mcmc:
    # Prior distributions for the model's parameters
    beta = pm.Uniform(
        "beta", 
        lower=0, 
        upper=1e-5,
    )
    omega = pm.Uniform(
        "omega", 
        lower=0, 
        upper=1,
    )
    # gamma_P = pm.Uniform(
    #     "gamma_P", 
    #     lower=1 / 21, 
    #     upper=1 / 10,
    # )
    # d_I = pm.Uniform("d_I", lower=(1 - percent_calibration) * d_I_deterministic, upper=(1 + percent_calibration) * d_I_deterministic,)
    # d_P = pm.Uniform("d_P", lower=(1 - percent_calibration) * d_P_deterministic, upper=(1 + percent_calibration) * d_P_deterministic,)
    d_I = pm.Uniform("d_I", lower=1e-5, upper=1e-1)
    d_P = pm.Uniform("d_P", lower=1e-5, upper=1e-1)

    standard_deviation = pm.Uniform("std_deviation", lower=1e0, upper=1e4, shape=2)

    # Defining the deterministic formulation of the problem
    fitting_model = pm.Deterministic(
        "seirpdq_model",
        seirpdq_ode_wrapper_with_y0(
            theano.shared(data_time),
            theano.shared(np.array(y0_seirpdq)),
            theano.shared(target_population),
            beta,
            omega,
            # gamma_P,
            d_P,
            d_I
        ),
    )

    R0_realizations = pm.Deterministic(
        "R0",
        calculate_reproduction_number(
            S0,
            beta,
            beta,
            gamma_I_deterministic,
            gamma_A_deterministic,
            # d_I_deterministic,
            d_I,
            epsilon_I_deterministic,
            rho_deterministic,
            omega,
            sigma_deterministic,
        ),
    )

    likelihood_model = pm.Normal(
        "likelihood_model", mu=fitting_model, sigma=standard_deviation, observed=observations_to_fit
    )

    seirdpq_trace_calibration = pm.sample_smc(
        draws=draws, n_steps=25, parallel=True, cores=int(os.cpu_count()), progressbar=True, random_seed=seed
    )

duration = time.time() - start_time

print(f"-- Monte Carlo simulations done in {duration / 60:.3f} minutes")

# %%
print("-- Arviz post-processing:")
import warnings

warnings.filterwarnings("ignore")

start_time = time.time()
plot_step = 1


def calculate_rv_posterior_mpv(pm_trace, variable_names: list) -> dict:
    rv_mpv_values_dict = dict()
    progress_bar = tqdm(variable_names)
    for variable in progress_bar:
        progress_bar.set_description(f"Calulating MPV from KDE for {variable}")
        rv_realization_values = pm_trace[f"{variable}"]

        try:
            num_of_dimensions = rv_realization_values.shape[1]
        except IndexError:
            num_of_dimensions = 0

        if num_of_dimensions == 0:
            rv_mpv_value = _scalar_rv_mvp_estimation(rv_realization_values)
            rv_mpv_values_dict[f"{variable}"] = rv_mpv_value
        else:
            for dimension in range(num_of_dimensions):
                variable_name_decomposed = f"{variable}[{dimension}]"
                rv_realization_values_decomposed = np.array(rv_realization_values[:, dimension])
                rv_mpv_value = _scalar_rv_mvp_estimation(rv_realization_values_decomposed)
                rv_mpv_values_dict[f"{variable_name_decomposed}"] = rv_mpv_value

    return rv_mpv_values_dict


def _scalar_rv_mvp_estimation(rv_realization_values: np.ndarray) -> np.ndarray:
    num_of_realizations = len(rv_realization_values)
    kernel = gaussian_kde(rv_realization_values)
    equally_spaced_samples = np.linspace(
        rv_realization_values.min(),
        rv_realization_values.max(),
        num_of_realizations
    )
    kde = kernel(equally_spaced_samples)
    kde_max_index = np.argmax(kde)
    rv_mpv_value = equally_spaced_samples[kde_max_index]
    return rv_mpv_value


def add_mpv_to_summary(arviz_summary: pd.DataFrame, rv_modes_dict: dict) -> pd.DataFrame:
    new_arviz_summary = arviz_summary.copy()
    variable_names = list(rv_modes_dict.keys())
    rv_mode_values = list(rv_modes_dict.values())
    new_arviz_summary["mpv"] = pd.Series(data=rv_mode_values, index=variable_names)
    return new_arviz_summary


# %%
calibration_variable_names = [
    "std_deviation",
    "beta",
    # "gamma_P",
    "omega",
    "d_I",
    "d_P",
    "R0",
]

progress_bar = tqdm(calibration_variable_names)
for variable in progress_bar:
    progress_bar.set_description("Arviz post-processing")
    pm.traceplot(seirdpq_trace_calibration[::plot_step], var_names=(f"{variable}"))
    plt.savefig(f"seirpdq_{variable}_traceplot_cal.png")

    pm.plot_posterior(
        seirdpq_trace_calibration[::plot_step], 
        var_names=(f"{variable}"), 
        kind="hist", 
        round_to=5,
        point_estimate="mode"
    )
    plt.savefig(f"seirpdq_{variable}_posterior_cal.png")

print("-- Post-processing stats")

df_stats_summary = az.summary(
    data=seirdpq_trace_calibration,
    var_names=calibration_variable_names,
    kind='stats',
    round_to=15,
)
calibration_variable_modes = calculate_rv_posterior_mpv(
    pm_trace=seirdpq_trace_calibration, variable_names=calibration_variable_names
)
df_stats_summary = add_mpv_to_summary(df_stats_summary, calibration_variable_modes)
df_stats_summary.to_csv("stats_summary_calibration.csv")
print(df_stats_summary)

az.plot_pair(
    seirdpq_trace_calibration,
    var_names=calibration_variable_names[1:],
    kind="hexbin",
    fill_last=False,
    figsize=(10, 8),
)
plt.savefig("seirpdq_marginals_cal.png")

# %%
percentile_cut = 2.5

y_min = np.percentile(seirdpq_trace_calibration["seirpdq_model"], percentile_cut, axis=0)
y_max = np.percentile(seirdpq_trace_calibration["seirpdq_model"], 100 - percentile_cut, axis=0)
y_fit = np.percentile(seirdpq_trace_calibration["seirpdq_model"], 50, axis=0)


# %%
std_deviation = seirdpq_trace_calibration.get_values("std_deviation")
sd_pop = np.sqrt(std_deviation.mean())
print(f"-- Estimated standard deviation mean: {sd_pop}")


# %%
plt.figure(figsize=(9, 7))

plt.plot(
    data_time,
    y_fit[:, 0],
    "r",
    label="Deaths (SEAIRPD-Q)",
    marker="D",
    linestyle="-",
    markersize=10,
)
plt.fill_between(data_time, y_min[:, 0], y_max[:, 0], color="r", alpha=0.2)

plt.plot(
    data_time, y_fit[:, 1], "b", label="Cases (SEAIRPD-Q)", marker="v", linestyle="-", markersize=10
)
plt.fill_between(data_time, y_min[:, 1], y_max[:, 1], color="b", alpha=0.2)

# plt.errorbar(data_time, infected_individuals, yerr=sd_pop, label='Recorded diagnosed', linestyle='None', marker='s', markersize=10)
# plt.errorbar(data_time, dead_individuals, yerr=sd_pop, label='Recorded deaths', marker='v', linestyle="None", markersize=10)
plt.plot(
    data_time, confirmed_cases, label="Confirmed data", marker="s", linestyle="", markersize=10
)
plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)

plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()
plt.grid()

plt.tight_layout()

plt.savefig("seirpdq_calibration_bayes.png")
# # plt.show()

# %%
duration = time.time() - start_time

print(f"-- Arviz post-processing done in {duration / 60:.3f} minutes")
# %% [markdown]
# Now we evaluate prediction. We have to retrieve parameter realizations.

# %%
print("\n*** Performing Bayesian prediction ***")
print("-- Exporting calibrated parameter to CSV")

start_time = time.time()

dict_realizations = dict()
progress_bar = tqdm(calibration_variable_names[1:])
for variable in progress_bar:
    progress_bar.set_description(f"Gathering {variable} realizations")
    parameter_realization = seirdpq_trace_calibration.get_values(f"{variable}")
    dict_realizations[f"{variable}"] = parameter_realization

df_realizations = pd.DataFrame(dict_realizations)
df_realizations.to_csv("calibration_realizations.csv")

duration = time.time() - start_time

print(f"-- Exported done in {duration:.3f} seconds")

print("-- Processing Bayesian predictions")

S_predicted = list()
E_predicted = list()
A_predicted = list()
I_predicted = list()
P_predicted = list()
R_predicted = list()
D_predicted = list()
C_predicted = list()
H_predicted = list()
Rt_predicted = list()
number_of_total_realizations = len(dict_realizations["beta"])
for realization in trange(number_of_total_realizations):
    parameters_realization = [
        dict_realizations["beta"][realization],
        dict_realizations["omega"][realization],
        # dict_realizations["gamma_P"][realization],
        dict_realizations["d_P"][realization],
        dict_realizations["d_I"][realization],
    ]
    solution_ODE_predict = seirpdq_ode_solver(
        y0_seirpdq, (t0, tf), time_range, *parameters_realization
    )
    t_computed_predict, y_computed_predict = solution_ODE_predict.t, solution_ODE_predict.y
    S, E, A, I, P, R, D, C, H = y_computed_predict

    reproduction_number_t = calculate_reproduction_number(
        S,
        dict_realizations["beta"][realization],
        dict_realizations["beta"][realization],
        gamma_I_deterministic,
        gamma_A_deterministic,
        # d_I_deterministic,
        dict_realizations["d_I"][realization],
        epsilon_I_deterministic,
        rho_deterministic,
        dict_realizations["omega"][realization],
        sigma_deterministic,
    )

    S_predicted.append(S)
    E_predicted.append(E)
    A_predicted.append(A)
    I_predicted.append(I)
    P_predicted.append(P)
    R_predicted.append(R)
    D_predicted.append(D)
    C_predicted.append(C)
    H_predicted.append(H)
    Rt_predicted.append(reproduction_number_t)

S_predicted = np.array(S_predicted)
E_predicted = np.array(E_predicted)
A_predicted = np.array(A_predicted)
I_predicted = np.array(I_predicted)
P_predicted = np.array(P_predicted)
R_predicted = np.array(R_predicted)
D_predicted = np.array(D_predicted)
C_predicted = np.array(C_predicted)
H_predicted = np.array(H_predicted)
Rt_predicted = np.array(Rt_predicted)

percentile_cut = 2.5
C_min = np.percentile(C_predicted, percentile_cut, axis=0)
C_max = np.percentile(C_predicted, 100 - percentile_cut, axis=0)
C_mean = np.percentile(C_predicted, 50, axis=0)

P_min = np.percentile(P_predicted, percentile_cut, axis=0)
P_max = np.percentile(P_predicted, 100 - percentile_cut, axis=0)
P_mean = np.percentile(P_predicted, 50, axis=0)

I_min = np.percentile(I_predicted, percentile_cut, axis=0)
I_max = np.percentile(I_predicted, 100 - percentile_cut, axis=0)
I_mean = np.percentile(I_predicted, 50, axis=0)

A_min = np.percentile(A_predicted, percentile_cut, axis=0)
A_max = np.percentile(A_predicted, 100 - percentile_cut, axis=0)
A_mean = np.percentile(A_predicted, 50, axis=0)

D_min = np.percentile(D_predicted, percentile_cut, axis=0)
D_max = np.percentile(D_predicted, 100 - percentile_cut, axis=0)
D_mean = np.percentile(D_predicted, 50, axis=0)

Rt_min = np.percentile(Rt_predicted, percentile_cut, axis=0)
Rt_max = np.percentile(Rt_predicted, 100 - percentile_cut, axis=0)
Rt_mean = np.percentile(Rt_predicted, 50, axis=0)

peak_day_min = np.argmax(P_min)
peak_day_max = np.argmax(P_max)
peak_day_mean = np.argmax(P_mean)

min_diagnosed_peak = int(P_min[peak_day_min])
mean_diagnosed_peak = int(P_mean[peak_day_mean])
max_diagnosed_peak = int(P_max[peak_day_max])

print(f"\n-- Min diagnosed peak day: {peak_day_min}")
print(f"-- Mean diagnosed peak day: {peak_day_mean}")
print(f"-- Max diagnosed peak day: {peak_day_max}")
print(f"-- Min number of diagnosed at peak day: {min_diagnosed_peak}")
print(f"-- Mean number of diagnosed at peak day:: {mean_diagnosed_peak}")
print(f"-- Max number of diagnosed at peak day:: {max_diagnosed_peak}\n")

print(f"-- Min number of cases: {int(C_min[-1])}")
print(f"-- Mean number of cases: {int(C_mean[-1])}")
print(f"-- Max number of cases: {int(C_max[-1])}\n")

print(f"-- Min number of deaths: {int(D_min[-1])}")
print(f"-- Mean number of deaths: {int(D_mean[-1])}")
print(f"-- Max number of deaths: {int(D_max[-1])}")

# %%
plt.figure(figsize=(9, 7))

plt.plot(
    t_computed_predict,
    C_mean,
    "b",
    label="Cases (SEAIRPD-Q)",
    marker="D",
    linestyle="-",
    markersize=10,
)
plt.fill_between(t_computed_predict, C_min, C_max, color="b", alpha=0.2)

plt.plot(
    t_computed_predict,
    D_mean,
    "r",
    label="Deaths (SEAIRPD-Q)",
    marker="v",
    linestyle="-",
    markersize=10,
)
plt.fill_between(t_computed_predict, D_min, D_max, color="r", alpha=0.2)

# plt.errorbar(data_time, infected_individuals, yerr=sd_pop, label='Recorded diagnosed', linestyle='None', marker='s', markersize=10)
# plt.errorbar(data_time, dead_individuals, yerr=sd_pop, label='Recorded deaths', marker='v', linestyle="None", markersize=10)
plt.plot(
    data_time, confirmed_cases, label="Confirmed data", marker="s", linestyle="", markersize=10
)
plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)

plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()
plt.grid()

plt.tight_layout()

plt.savefig("seirpdq_prediction_cumulative_bayes.png")
# plt.show()

# %%
plt.figure(figsize=(9, 7))

plt.plot(
    t_computed_predict,
    P_mean,
    "b",
    label="Diagnosed (SEAIRPD-Q)",
    marker="D",
    linestyle="-",
    markersize=10,
)
plt.fill_between(t_computed_predict, P_min, P_max, color="b", alpha=0.2)

plt.plot(
    t_computed_predict,
    I_mean,
    "g",
    label="Infected (SEAIRPD-Q)",
    marker="X",
    linestyle="-",
    markersize=10,
)
plt.fill_between(t_computed_predict, I_min, I_max, color="g", alpha=0.2)

plt.plot(
    t_computed_predict,
    A_mean,
    "m",
    label="Asymptomatic (SEAIRPD-Q)",
    marker="o",
    linestyle="-",
    markersize=10,
)
plt.fill_between(t_computed_predict, A_min, A_max, color="m", alpha=0.2)

plt.plot(
    t_computed_predict,
    D_mean,
    "r",
    label="Deaths (SEAIRPD-Q)",
    marker="v",
    linestyle="-",
    markersize=10,
)
plt.fill_between(t_computed_predict, D_min, D_max, color="r", alpha=0.2)

plt.axvline(
    x=peak_day_mean, color="blue", linestyle="-", label="Diagnosed peak (SEAIRPD-Q)"
)
plt.axvline(
    x=peak_day_min, color="blue", linestyle="--"
)
plt.axvline(
    x=peak_day_max, color="blue", linestyle="--"
)

# plt.errorbar(data_time, infected_individuals, yerr=sd_pop, label='Recorded diagnosed', linestyle='None', marker='s', markersize=10)
# plt.errorbar(data_time, dead_individuals, yerr=sd_pop, label='Recorded deaths', marker='v', linestyle="None", markersize=10)
""" plt.plot(
    data_time, infected_individuals, label="Active cases", marker="s", linestyle="", markersize=10
) """
plt.plot(
    data_time, dead_individuals, label="Recorded deaths", marker="v", linestyle="", markersize=10
)

plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()
plt.grid()

plt.tight_layout()

plt.savefig("seirpdq_prediction_bayes.png")
# plt.show()

# %%
plt.figure(figsize=(9, 7))

plt.plot(
    t_computed_predict,
    Rt_mean,
    "r",
    marker="X",
    linestyle="-",
    markersize=3,
)
plt.fill_between(t_computed_predict, Rt_min, Rt_max, color="r", alpha=0.2)

plt.xlabel("Time (days)")
plt.ylabel(r"$R(t)$")
plt.grid()

plt.tight_layout()

plt.savefig("Rt_prediction_bayes.png")
