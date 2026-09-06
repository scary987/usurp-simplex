import gurobipy as gp
from gurobipy import GRB
import pandas as pd


# ============================================================
# G(T, K)
# ============================================================

G = {
   # 0: {9: 0.000, 10: 0.000, 11: 0.000, 12: 0.000},

    1: {9: 0.600, 10: 0.667, 11: 0.733, 12: 0.800, 6:0.400},
    2: {9: 1.200, 10: 1.333, 11: 1.467, 12: 1.600, 6:0.800},
    3: {9: 1.800, 10: 2.000, 11: 2.200, 12: 2.400, 6:1.200},
    4: {9: 2.400, 10: 2.667, 11: 2.933, 12: 3.200, 6:1.600},
    5: {9: 3.000, 10: 3.333, 11: 3.667, 12: 4.000, 6:2.000},
    6: {9: 3.600, 10: 4.000, 11: 4.400, 12: 4.800, 6:2.400},
}


# ============================================================
# Settings
# ============================================================

T_VALUES = range(1,7)

BD_PURE_VALUES = range(20, 31)

K_VALUES = [0, 3, 4, 5, 6]


# ============================================================
# Solve one Gurobi model
#
# T and BD_pure are fixed.
# Gurobi chooses:
#   RC_pure
#   K_pure
#   X
# ============================================================

def solve_model(T, BD_pure):

    model = gp.Model(f"T{T}_BD{BD_pure}")

    # --------------------------------------------------------
    # Variables
    # --------------------------------------------------------

    RC_pure = model.addVar(
        vtype=GRB.INTEGER,
        lb=0,
        ub=19,
        name="RC_pure"
    )

    K_pure = model.addVar(
        vtype=GRB.INTEGER,
        lb=3,
        ub=6,
        name="K_pure"
    )

    X = model.addVar(
        vtype=GRB.INTEGER,
        lb=0,
        name="X"
    )

    # Binary selector variables
    z = {
        k: model.addVar(
            vtype=GRB.BINARY,
            name=f"z_{k}"
        )
        for k in K_VALUES
    }

    # --------------------------------------------------------
    # Select exactly one K_pure
    # --------------------------------------------------------

    model.addConstr(
        gp.quicksum(z[k] for k in K_VALUES) == 1,
        name="select_K"
    )

    # K_pure = 3,4,5,6
    model.addConstr(
        K_pure ==
        gp.quicksum(k * z[k] for k in K_VALUES),
        name="define_K"
    )

    # --------------------------------------------------------
    # 51 pure elements
    #
    # BD_pure + RC_pure + K_pure = 51
    # --------------------------------------------------------

    model.addConstr(
        BD_pure + RC_pure + K_pure == 51,
        name="pure_elements"
    )

    # --------------------------------------------------------
    # X <= 2 * G(T,K) * 3 + 3
    #
    # = 6 * G(T,K) + 3
    #
    # The binary variables select the appropriate G value.
    # ----------------------------------------    model.addConstr(
    model.addConstr(
        X >= 1,
        name="X_lower_bound_by_T=1"
    )

    model.addConstr(
        X <=
        6 * gp.quicksum(
            G[T][k + 6] * z[k]
            for k in K_VALUES
        ) + 3,
        name="G_constraint"
    )

    # --------------------------------------------------------
    # X <= (RC_pure + 6)/60 * (4T)
    # --------------------------------------------------------

    model.addConstr(
        X <=
        (4 * T / 60) * (RC_pure + 6),
        name="RC_constraint"
    )
    model.addConstr(
        X >= 1,
        name="X_lower_bound_by_T=1"
    )
    # --------------------------------------------------------
    # Objective
    #
    # BD = BD_pure + 6
    #
    # maximize BD * X / 60
    # --------------------------------------------------------


    # 5 > X iff G(T,K) < 1
    low_G = model.addVar(
        vtype=GRB.BINARY,
        name="low_G"
    )

    if T == 1:
        model.addConstr(low_G == 1, name="G_below_1")
    else:
        model.addConstr(low_G == 0, name="G_not_below_1")

    M = 10000

    model.addConstr(
        X <= 4 + M * (1 - low_G),
        name="X_less_than_5_if_G_below_1"
    )

    model.addConstr(
        X >= 5 - M * low_G,
        name="X_at_least_5_if_G_not_below_1"
    )
    BD = BD_pure + 6

    model.setObjective(
        BD * X / 60,
        GRB.MAXIMIZE
    )

    # --------------------------------------------------------
    # Optimize
    # --------------------------------------------------------

    model.optimize()

    # --------------------------------------------------------
    # Return optimal solution
    # --------------------------------------------------------

    if model.Status == GRB.OPTIMAL:

        K_pure_value = round(K_pure.X)
        RC_pure_value = round(RC_pure.X)
        X_value = round(X.X)

        K = K_pure_value + 6
        RC = RC_pure_value + 6

        g_value = G[T][K]

        return {
            "T": T,

            "BD_pure": BD_pure,
            "RC_pure": RC_pure_value,
            "K_pure": K_pure_value,

            "BD": BD,
            "RC": RC,
            "K": K,

            "G": g_value,

            "X": X_value,

            "objective": model.ObjVal,

            "status": "OPTIMAL"
        }

    else:

        return {
            "T": T,
            "BD_pure": BD_pure,
            "status": model.Status
        }


# ============================================================
# Run all models
# ============================================================

all_results = []

for T in T_VALUES:

    for BD_pure in BD_PURE_VALUES:

        result = solve_model(T, BD_pure)

        if result["status"] == "OPTIMAL":
            all_results.append(result)


# ============================================================
# All feasible solutions
# ============================================================

df_all = pd.DataFrame(all_results)


# ============================================================
# BEST RESULT FOR EACH T
# ============================================================

best_by_T = (
    df_all
    .loc[
        df_all.groupby("T")["objective"].idxmax()
    ]
    .sort_values("T")
    .reset_index(drop=True)
)


# ============================================================
# BEST RESULT FOR EACH T AND K_pure
# ============================================================

best_by_T_K = (
    df_all
    .loc[
        df_all.groupby(
            ["T", "K_pure"]
        )["objective"].idxmax()
    ]
    .sort_values(["T", "K_pure"])
    .reset_index(drop=True)
)


# ============================================================
# TABLE 1
# ============================================================

print("\n")
print("=" * 110)
print("BEST SOLUTION FOR EACH T")
print("=" * 110)

print(
    best_by_T[
        [
            "T",
            "BD_pure",
            "RC_pure",
            "K_pure",
            "BD",
            "RC",
            "K",
            "G",
            "X",
            "objective"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# TABLE 2
# ============================================================

print("\n")
print("=" * 110)
print("BEST SOLUTION FOR EACH T AND K_pure")
print("=" * 110)

print(
    best_by_T_K[
        [
            "T",
            "K_pure",
            "K",
            "BD_pure",
            "RC_pure",
            "BD",
            "RC",
            "G",
            "X",
            "objective"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# OVERALL BEST
# ============================================================

overall = df_all.loc[
    df_all["objective"].idxmax()
]

print("\n")
print("=" * 110)
print("OVERALL BEST")
print("=" * 110)

for column in [
    "T",
    "BD_pure",
    "RC_pure",
    "K_pure",
    "BD",
    "RC",
    "K",
    "G",
    "X",
    "objective"
]:
    print(f"{column:15s}: {overall[column]}")


# ============================================================
# SAVE
# ============================================================

df_all.to_csv(
    "all_gurobi_results.csv",
    index=False
)

best_by_T.to_csv(
    "best_by_T.csv",
    index=False
)

best_by_T_K.to_csv(
    "best_by_T_K_pure.csv",
    index=False
)