import gurobipy as gp
from gurobipy import GRB
import pandas as pd


# ============================================================
# PARAMETERS
# ============================================================

TOTAL = 60

# Usual ranges
T_VALUES = range(1, 7)       # T = 1,...,6  -> n = 4,...,24
BD_VALUES = range(10, 51)    # BD = 10,...,30
K_PURE_VALUES = range(3, 7)  # K_pure = 3,...,6

# Maximum number of special pure RC elements
MAX_RC_WEIGHT_3 = 6
MAX_RC_WEIGHT_2 = 4

# Weighted contribution from the 6 shared RC elements:
# 3 elements * weight 6 + 3 elements * weight 1
SHARED_RC_WEIGHT = 3 * 6 + 3 * 1   # = 21


# ============================================================
# G MATRIX
# ============================================================

G = {
    1: {9: 0, 10: 0, 11: 0, 12: 0},
    2: {9: 1, 10: 1, 11: 1, 12: 1},
    3: {9: 1, 10: 2, 11: 2, 12: 2},
    4: {9: 2, 10: 2, 11: 2, 12: 3},
    5: {9: 3, 10: 3, 11: 3, 12: 4},
    6: {9: 3, 10: 4, 11: 4, 12: 4},
}


# ============================================================
# RESULTS
# ============================================================

results = []


# ============================================================
# LOOP OVER T AND FIXED BD
# ============================================================

for T in T_VALUES:

    for BD_VALUE in BD_VALUES:

        model = gp.Model(
            f"Weighted_RC_T{T}_BD{BD_VALUE}"
        )

        # ----------------------------------------------------
        # VARIABLES
        # ----------------------------------------------------

        # Pure elements
        BD_pure = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            name="BD_pure"
        )

        RC_pure = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            name="RC_pure"
        )

        K_pure = model.addVar(
            vtype=GRB.INTEGER,
            lb=3,
            ub=6,
            name="K_pure"
        )

        # Actual group sizes
        BD = model.addVar(
            vtype=GRB.INTEGER,
            lb=10,
            ub=50,
            name="BD"
        )

        RC = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=60,
            name="RC"
        )

        K = model.addVar(
            vtype=GRB.INTEGER,
            lb=9,
            ub=12,
            name="K"
        )

        # X
        X = model.addVar(
            vtype=GRB.INTEGER,
            lb=1,
            name="X"
        )

        # ----------------------------------------------------
        # PURE RC WEIGHT VARIABLES
        # ----------------------------------------------------

        # Number of pure RC elements with weight 3
        RC_3 = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=MAX_RC_WEIGHT_3,
            name="RC_3"
        )

        # Number of pure RC elements with weight 2
        RC_2 = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=MAX_RC_WEIGHT_2,
            name="RC_2"
        )

        # Number of pure RC elements with weight 1
        RC_1 = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            name="RC_1"
        )

        # ----------------------------------------------------
        # K SELECTOR VARIABLES
        # ----------------------------------------------------

        z = {
            k_pure: model.addVar(
                vtype=GRB.BINARY,
                name=f"z_{k_pure}"
            )
            for k_pure in K_PURE_VALUES
        }

        # ----------------------------------------------------
        # CONSTRAINTS
        # ----------------------------------------------------

        # ----------------------------------------------------
        # FIX BD
        # ----------------------------------------------------

        model.addConstr(
            BD == BD_VALUE,
            name="fix_BD"
        )

        # ----------------------------------------------------
        # PURE / ACTUAL ELEMENT RELATIONSHIPS
        # ----------------------------------------------------

        model.addConstr(
            BD == BD_pure + 6,
            name="BD_definition"
        )

        model.addConstr(
            RC == RC_pure + 6,
            name="RC_definition"
        )

        model.addConstr(
            K == K_pure + 6,
            name="K_definition"
        )

        # ----------------------------------------------------
        # 51 PURE ELEMENTS
        # ----------------------------------------------------

        model.addConstr(
            BD_pure + RC_pure + K_pure == 48,
            name="pure_total"
        )

        # ----------------------------------------------------
        # K SELECTION
        # ----------------------------------------------------

        model.addConstr(
            gp.quicksum(
                z[k_pure]
                for k_pure in K_PURE_VALUES
            ) == 1,
            name="select_K"
        )

        model.addConstr(
            K_pure == gp.quicksum(
                k_pure * z[k_pure]
                for k_pure in K_PURE_VALUES
            ),
            name="K_pure_selector"
        )

        # ----------------------------------------------------
        # PURE RC COMPOSITION
        # ----------------------------------------------------

        model.addConstr(
            RC_1 + RC_2 + RC_3 == RC_pure,
            name="RC_composition"
        )

        # Maximum number of weight-3 pure RC elements
        model.addConstr(
            RC_3 <= MAX_RC_WEIGHT_3,
            name="RC_3_limit"
        )

        # Maximum number of weight-2 pure RC elements
        model.addConstr(
            RC_2 <= MAX_RC_WEIGHT_2,
            name="RC_2_limit"
        )

        # ----------------------------------------------------
        # WEIGHTED RC STRENGTH
        # ----------------------------------------------------

        RC_weight = (
            3 * RC_3
            + 2 * RC_2
            + RC_1
            + SHARED_RC_WEIGHT
        )

        # ----------------------------------------------------
        # G CONSTRAINT
        # ----------------------------------------------------

        G_expression = gp.quicksum(
            G[T][k_pure + 6] * z[k_pure]
            for k_pure in K_PURE_VALUES
        )

        model.addConstr(
            X <= 6 * G_expression + 3,
            name="G_constraint"
        )

        # ----------------------------------------------------
        # WEIGHTED RC CONSTRAINT
        # ----------------------------------------------------

        model.addConstr(
            X <= (4 * T / TOTAL) * RC_weight,
            name="weighted_RC_constraint"
        )

        # ----------------------------------------------------
        # X MINIMUM
        # ----------------------------------------------------

        model.addConstr(
            X >= 1,
            name="X_min"
        )
        # X must always be strictly smaller than 3T
        model.addConstr(
            X <= 3 * T,
            name="X_upper_3T"
        )
        # ----------------------------------------------------
        # OBJECTIVE
        # ----------------------------------------------------

        # BD is fixed, so this is a linear ILP objective.
        model.setObjective(
            BD_VALUE * X / TOTAL,
            GRB.MAXIMIZE
        )

        # ----------------------------------------------------
        # SOLVE
        # ----------------------------------------------------

        model.optimize()

        # ----------------------------------------------------
        # STORE RESULT
        # ----------------------------------------------------

        if model.Status == GRB.OPTIMAL:

            selected_K_pure = next(
                k_pure
                for k_pure in K_PURE_VALUES
                if z[k_pure].X > 0.5
            )

            selected_K = selected_K_pure + 6

            RC_3_weight = min(T, 3)
            RC_2_weight = min(T, 2)

            weighted_RC = (
                RC_3_weight * round(RC_3.X)
                + RC_2_weight * round(RC_2.X)
                + round(RC_1.X)
                + SHARED_RC_WEIGHT
            )

            results.append({
                "T": T,
                "n": 4 * T,
                "BD": BD_VALUE,
                "BD_pure": round(BD_pure.X),
                "RC": round(RC.X),
                "RC_pure": round(RC_pure.X),
                "RC_weight_3": round(RC_3.X),
                "RC_weight_2": round(RC_2.X),
                "RC_weight_1": round(RC_1.X),
                "RC_weighted": weighted_RC,
                "K": selected_K,
                "K_pure": selected_K_pure,
                "G": G[T][selected_K],
                "X": round(X.X),
                "Objective": model.ObjVal,
                "Status": "OPTIMAL",
            })

        else:

            results.append({
                "T": T,
                "n": 4 * T,
                "BD": BD_VALUE,
                "BD_pure": None,
                "RC": None,
                "RC_pure": None,
                "RC_weight_3": None,
                "RC_weight_2": None,
                "RC_weight_1": None,
                "RC_weighted": None,
                "K": None,
                "K_pure": None,
                "G": None,
                "X": None,
                "Objective": None,
                "Status": model.Status,
            })


# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(results)


# ============================================================
# PRINT ALL RESULTS
# ============================================================

print("\n============================================================")
print("ALL RESULTS")
print("============================================================")

print(
    df.to_string(index=False)
)


# ============================================================
# BEST RESULT FOR EACH T
# ============================================================

valid = df.dropna(subset=["Objective"])

best_per_T = (
    valid.loc[
        valid.groupby("T")["Objective"].idxmax()
    ]
    .sort_values("T")
    .reset_index(drop=True)
)


print("\n============================================================")
print("BEST RESULT FOR EACH T")
print("============================================================")

print(
    best_per_T.to_string(index=False)
)


# ============================================================
# OVERALL BEST
# ============================================================

if not valid.empty:

    best_overall = valid.loc[
        valid["Objective"].idxmax()
    ]

    print("\n============================================================")
    print("OVERALL BEST")
    print("============================================================")

    print(
        best_overall.to_string()
    )


# ============================================================
# SAVE RESULTS
# ============================================================

df.to_csv(
    "ILP_60_weighted_RC_results.csv",
    index=False
)

best_per_T.to_csv(
    "ILP_60_weighted_RC_best_per_T.csv",
    index=False
)


print("\n============================================================")
print("FILES SAVED")
print("============================================================")

print("ILP_60_weighted_RC_results.csv")
print("ILP_60_weighted_RC_best_per_T.csv")
