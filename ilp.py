import math
import pandas as pd


# ============================================================
# G(T, K_pure + 6)
#
# T = n / 4
# K_total = K_pure + 6
#
# K_pure = 3, 4, 5, 6
# K_total = 9, 10, 11, 12
# ============================================================


###
# G is the expected amount of Gates drawn
###
G = {
    0: {9: 0.000, 10: 0.000, 11: 0.000, 12: 0.000},

    1: {9: 0.600, 10: 0.667, 11: 0.733, 12: 0.800},
    2: {9: 1.200, 10: 1.333, 11: 1.467, 12: 1.600},
    3: {9: 1.800, 10: 2.000, 11: 2.200, 12: 2.400},
    4: {9: 2.400, 10: 2.667, 11: 2.933, 12: 3.200},
    5: {9: 3.000, 10: 3.333, 11: 3.667, 12: 4.000},
    6: {9: 3.600, 10: 4.000, 11: 4.400, 12: 4.800},
}


# ============================================================
# Constants
# ============================================================

TOTAL_PURE = 51
SHARED_PER_GROUP = 6

MIN_K_PURE = 3
MAX_K_PURE = 6

MAX_RC_PURE = 19

T_VALUES = range(7)


# ============================================================
# Calculate the best solution for one T
# ============================================================

def optimize_for_T(T):

    best = None

    # --------------------------------------------------------
    # Enumerate K_pure
    # --------------------------------------------------------

    for K_pure in range(MIN_K_PURE, MAX_K_PURE + 1):

        K = K_pure + SHARED_PER_GROUP

        # ----------------------------------------------------
        # Enumerate RC_pure
        # ----------------------------------------------------

        for RC_pure in range(MAX_RC_PURE + 1):

            # ------------------------------------------------
            # The 51 pure elements must satisfy:
            #
            # BD_pure + RC_pure + K_pure = 51
            # ------------------------------------------------

            BD_pure = TOTAL_PURE - RC_pure - K_pure

            # Must be non-negative
            if BD_pure < 0:
                continue

            # ------------------------------------------------
            # Actual group sizes include 6 shared elements
            # ------------------------------------------------

            BD = BD_pure + SHARED_PER_GROUP
            RC = RC_pure + SHARED_PER_GROUP

            # ------------------------------------------------
            # G(T, K)
            # ------------------------------------------------

            g = G[T][K]

            # ------------------------------------------------
            # X constraints:
            #
            # X <= 6 * G(T,K) + 3
            #
            # X <= (RC_pure + 6)/60 * (4T)
            # ------------------------------------------------

            x_g = 6 * g + 3

            x_rc = ((RC_pure + 6) / 60) * (4 * T)

            # X must be an integer
            X = math.floor(min(x_g, x_rc))

            # ------------------------------------------------
            # X must be non-negative
            # ------------------------------------------------

            if X < 0:
                continue

            # ------------------------------------------------
            # Objective:
            #
            # maximize BD * X / 60
            # ------------------------------------------------

            objective = BD * X / 60

            # ------------------------------------------------
            # Store if this is the best solution so far
            # ------------------------------------------------

            if best is None or objective > best["objective"]:

                best = {
                    "T": T,
                    "K_pure": K_pure,
                    "RC_pure": RC_pure,
                    "BD_pure": BD_pure,

                    "K": K,
                    "RC": RC,
                    "BD": BD,

                    "G": g,

                    "X_limit_G": x_g,
                    "X_limit_RC": x_rc,

                    "X": X,

                    "objective": objective
                }

    return best


# ============================================================
# Optimize for every T
# ============================================================

results = []

for T in T_VALUES:
    result = optimize_for_T(T)

    if result is not None:
        results.append(result)


# ============================================================
# Create results DataFrame
# ============================================================

df = pd.DataFrame(results)


# ============================================================
# Print T-by-T optimization results
# ============================================================

print("\n" + "=" * 110)
print("BEST SOLUTION FOR EACH T")
print("=" * 110)

print(
    df[
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
# Overall best solution
# ============================================================

best_overall = df.loc[df["objective"].idxmax()]

print("\n" + "=" * 110)
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
    print(f"{column:15s}: {best_overall[column]}")


# ============================================================
# Optional: save the T-by-T results to CSV
# ============================================================

df.to_csv("T_optimization_results.csv", index=False)

print("\nResults saved to: T_optimization_results.csv")