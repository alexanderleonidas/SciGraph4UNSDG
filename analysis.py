# """
# Analyses the output of linkedsdg_classifier.py:
#   1. Classified vs skipped work counts per bucket
#   2. Agreement between OpenAlex SDG tags and LinkedSDG classifications
# """
#
# import os
# from collections import defaultdict
# from helper_funcs import load_json
#
# # ---------------------------------------------------------------------------
# # Constants
# # ---------------------------------------------------------------------------
#
# BUCKETS = [
#     {
#         "name":        "SDG-labelled",
#         "works_path":  "data/OpenAlex/works_sdg",
#         "class_path":  "data/LinkedSDG/classifications_sdg",
#         "skip_path":   "data/LinkedSDG/classifications_sdg_skipped",
#     },
#     {
#         "name":        "citation-expanded",
#         "works_path":  "data/OpenAlex/extracted_works_expanded",
#         "class_path":  "data/LinkedSDG/classifications_expanded",
#         "skip_path":   "data/LinkedSDG/classifications_expanded_skipped",
#     },
# ]
#
# # OpenAlex concept prefix used to identify SDG tags in the source works.
# SDG_CONCEPT_PREFIX = "sustainable_development_goals"
#
#
# for bucket in BUCKETS:
#     works         = load_json(bucket["works_path"])
#     classifications = load_json(bucket["class_path"])
#     skipped       = load_json(bucket["skip_path"])
#
#     print("=" * 60)
#     print(f"BUCKET: {bucket['name']}")
#     print("=" * 60)
#
#     # ------------------------------------------------------------------
#     # 1. Classified vs Skipped counts
#     # ------------------------------------------------------------------
#     classified_count = len(classifications)
#     skipped_count    = len(skipped)
#     total_count      = classified_count + skipped_count
#
#     print(f"\n--- Classification Coverage ---")
#     print(f"  Total works processed : {total_count}")
#     print(f"  Classified            : {classified_count}  ({classified_count / total_count * 100:.1f}%)" if total_count else "  Classified : 0")
#     print(f"  Skipped               : {skipped_count}  ({skipped_count / total_count * 100:.1f}%)"    if total_count else "  Skipped    : 0")
#
#     if bucket["name"] == "SDG-labelled":
#         # ------------------------------------------------------------------
#         # 2. SDG Agreement between OpenAlex and LinkedSDG
#         # ------------------------------------------------------------------
#
#         # Index works and classifications by OpenAlex ID for O(1) lookup
#         works_by_id = {w["id"]: w for w in works if w.get("id")}
#         cls_by_id   = {c["openalex_id"]: c for c in classifications if c.get("openalex_id")}
#
#         agreement_count   = 0
#         disagreement_count = 0
#         missing_oa_sdg    = 0   # works where OpenAlex provided no SDG label
#         missing_ls_sdg    = 0   # classifications with no flat_series scores
#
#         # Track per-goal agreement/disagreement for detailed breakdown
#         goal_stats = defaultdict(lambda: {"agree": 0, "disagree": 0})
#
#         for oa_id, cls in cls_by_id.items():
#             work = works_by_id.get(oa_id)
#             if not work:
#                 continue
#
#             # --- OpenAlex SDG goal ---
#             oa_sdg_entry = (work.get("sustainable_development_goals") or [None])[0]
#             if not oa_sdg_entry:
#                 missing_oa_sdg += 1
#                 continue
#             oa_goal = oa_sdg_entry.get("id")
#
#             # --- LinkedSDG top goal (highest cumulative score) ---
#             goal_totals = {}
#             for series in cls.get("flat_series", []):
#                 goal_uri = series["goal_id"]
#                 goal_totals[goal_uri] = goal_totals.get(goal_uri, 0) + series["score"]
#
#             if not goal_totals:
#                 missing_ls_sdg += 1
#                 continue
#
#             max_total = max(goal_totals.values())
#             ls_goal = next(
#                 (series["goal_id"] for series in cls["flat_series"]
#                  if goal_totals[series["goal_id"]] == max_total),
#                 None
#             )
#
#             # --- Compare ---
#             if oa_goal == ls_goal:
#                 agreement_count += 1
#                 goal_stats[oa_goal]["agree"] += 1
#             else:
#                 disagreement_count += 1
#                 goal_stats[oa_goal]["disagree"] += 1
#
#         comparable = agreement_count + disagreement_count
#
#         print(f"\n--- SDG Assignment Agreement ---")
#         print(f"  Comparable pairs      : {comparable}")
#         print(f"  Agreement             : {agreement_count}  ({agreement_count / comparable * 100:.1f}%)" if comparable else "  Agreement  : 0")
#         print(f"  Disagreement          : {disagreement_count}  ({disagreement_count / comparable * 100:.1f}%)" if comparable else "  Disagreement: 0")
#         print(f"  Missing OpenAlex SDG  : {missing_oa_sdg}")
#         print(f"  Missing LinkedSDG score: {missing_ls_sdg}")
#
#         print(f"\n--- Per-Goal Breakdown ---")
#         print(f"  {'Goal':<55} {'Agree':>6} {'Disagree':>9} {'Acc %':>7}")
#         print(f"  {'-'*55} {'-'*6} {'-'*9} {'-'*7}")
#         for goal, stats in sorted(goal_stats.items()):
#             total = stats["agree"] + stats["disagree"]
#             acc   = stats["agree"] / total * 100 if total else 0.0
#             print(f"  {goal:<55} {stats['agree']:>6} {stats['disagree']:>9} {acc:>6.1f}%")
#
# print("\nDone.")




"""
Analyses the output of linkedsdg_classifier.py:
  1. Classified vs skipped work counts per bucket
  2. Agreement between OpenAlex SDG tags and LinkedSDG classifications
  3. Visual comparison of goal distributions between OpenAlex and LinkedSDG
"""

import os
from collections import defaultdict
from helper_funcs import load_json
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUCKETS = [
    {
        "name":        "SDG-labelled",
        "works_path":  "data/OpenAlex/works_sdg",
        "class_path":  "data/LinkedSDG/classifications_sdg",
        "skip_path":   "data/LinkedSDG/classifications_sdg_skipped",
    },
    {
        "name":        "citation-expanded",
        "works_path":  "data/OpenAlex/extracted_works_expanded",
        "class_path":  "data/LinkedSDG/classifications_expanded",
        "skip_path":   "data/LinkedSDG/classifications_expanded_skipped",
    },
]

SDG_CONCEPT_PREFIX = "sustainable_development_goals"


def extract_goal_number(uri: str) -> int:
    """Extract the SDG goal number from a URI for sorting."""
    try:
        return int(uri.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return 999


for bucket in BUCKETS:
    works           = load_json(bucket["works_path"])
    classifications = load_json(bucket["class_path"])
    skipped         = load_json(bucket["skip_path"])

    print("=" * 60)
    print(f"BUCKET: {bucket['name']}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Classified vs Skipped counts
    # ------------------------------------------------------------------
    classified_count = len(classifications)
    skipped_count    = len(skipped)
    total_count      = classified_count + skipped_count

    print(f"\n--- Classification Coverage ---")
    print(f"  Total works processed : {total_count}")
    print(f"  Classified            : {classified_count}  ({classified_count / total_count * 100:.1f}%)" if total_count else "  Classified : 0")
    print(f"  Skipped               : {skipped_count}  ({skipped_count / total_count * 100:.1f}%)"    if total_count else "  Skipped    : 0")

    if bucket["name"] == "SDG-labelled":
        # ------------------------------------------------------------------
        # 2. SDG Agreement between OpenAlex and LinkedSDG
        # ------------------------------------------------------------------
        works_by_id = {w["id"]: w for w in works if w.get("id")}
        cls_by_id   = {c["openalex_id"]: c for c in classifications if c.get("openalex_id")}

        agreement_count    = 0
        disagreement_count = 0
        missing_oa_sdg     = 0
        missing_ls_sdg     = 0

        goal_stats = defaultdict(lambda: {"agree": 0, "disagree": 0})

        # --- Distribution counters: how many works each source assigns to each goal ---
        oa_goal_counts = defaultdict(int)   # OpenAlex top-goal distribution
        ls_goal_counts = defaultdict(int)   # LinkedSDG top-goal distribution

        for oa_id, cls in cls_by_id.items():
            work = works_by_id.get(oa_id)
            if not work:
                continue

            # --- OpenAlex SDG goal ---
            oa_sdg_entry = (work.get("sustainable_development_goals") or [None])[0]
            if not oa_sdg_entry:
                missing_oa_sdg += 1
                continue
            oa_goal = oa_sdg_entry.get("id")

            # --- LinkedSDG top goal (highest cumulative score) ---
            goal_totals = {}
            for series in cls.get("flat_series", []):
                goal_uri = series["goal_id"]
                goal_totals[goal_uri] = goal_totals.get(goal_uri, 0) + series["score"]

            if not goal_totals:
                missing_ls_sdg += 1
                continue

            max_total = max(goal_totals.values())
            ls_goal = next(
                (series["goal_id"] for series in cls["flat_series"]
                 if goal_totals[series["goal_id"]] == max_total),
                None
            )

            # Count goal distributions
            if oa_goal:
                oa_goal_counts[oa_goal] += 1
            if ls_goal:
                ls_goal_counts[ls_goal] += 1

            # --- Compare ---
            if oa_goal == ls_goal:
                agreement_count += 1
                goal_stats[oa_goal]["agree"] += 1
            else:
                disagreement_count += 1
                goal_stats[oa_goal]["disagree"] += 1
                # Track where LinkedSDG disagrees — add to oa goal disagree bucket
                # (already tracked above via goal_stats)

        comparable = agreement_count + disagreement_count

        print(f"\n--- SDG Assignment Agreement ---")
        print(f"  Comparable pairs      : {comparable}")
        print(f"  Agreement             : {agreement_count}  ({agreement_count / comparable * 100:.1f}%)" if comparable else "  Agreement  : 0")
        print(f"  Disagreement          : {disagreement_count}  ({disagreement_count / comparable * 100:.1f}%)" if comparable else "  Disagreement: 0")
        print(f"  Missing OpenAlex SDG  : {missing_oa_sdg}")
        print(f"  Missing LinkedSDG score: {missing_ls_sdg}")

        print(f"\n--- Per-Goal Breakdown ---")
        print(f"  {'Goal':<55} {'Agree':>6} {'Disagree':>9} {'Acc %':>7}")
        print(f"  {'-'*55} {'-'*6} {'-'*9} {'-'*7}")
        for goal, stats in sorted(goal_stats.items()):
            total = stats["agree"] + stats["disagree"]
            acc   = stats["agree"] / total * 100 if total else 0.0
            print(f"  {goal:<55} {stats['agree']:>6} {stats['disagree']:>9} {acc:>6.1f}%")

        # ------------------------------------------------------------------
        # 3. Side-by-side bar chart: OpenAlex vs LinkedSDG goal distributions
        # ------------------------------------------------------------------
        all_goals = sorted(
            set(oa_goal_counts.keys()) | set(ls_goal_counts.keys()),
            key=extract_goal_number
        )
        goal_labels = [f"SDG {extract_goal_number(g)}" for g in all_goals]

        oa_counts = [oa_goal_counts.get(g, 0) for g in all_goals]
        ls_counts = [ls_goal_counts.get(g, 0) for g in all_goals]
        diff      = [ls - oa for oa, ls in zip(oa_counts, ls_counts)]

        x     = np.arange(len(all_goals))
        width = 0.35

        # ── Panel 1: Side-by-side counts ──────────────────────────────────
        fig, axes = plt.subplots(2, 1, figsize=(16, 12))
        fig.patch.set_facecolor("white")

        ax1 = axes[0]
        ax1.set_facecolor("white")

        bars_oa = ax1.bar(x - width / 2, oa_counts, width,
                          label="OpenAlex",  color="#4C72B0", alpha=0.85, edgecolor="white")
        bars_ls = ax1.bar(x + width / 2, ls_counts, width,
                          label="LinkedSDG", color="#DD8452", alpha=0.85, edgecolor="white")

        # Value labels
        for bar in bars_oa:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                         str(int(h)), ha="center", va="bottom", fontsize=7)
        for bar in bars_ls:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                         str(int(h)), ha="center", va="bottom", fontsize=7)

        ax1.set_xticks(x)
        ax1.set_xticklabels(goal_labels, rotation=45, ha="right", fontsize=9)
        ax1.set_title("Works per SDG Goal: OpenAlex vs LinkedSDG assignments\n(SDG-labelled bucket)",
                      fontsize=13, fontweight="bold", pad=12)
        ax1.set_ylabel("Number of Works", fontsize=10)
        ax1.legend(fontsize=10)
        ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax1.grid(axis="y", linestyle="--", alpha=0.4)

        # ── Panel 2: Difference (LinkedSDG − OpenAlex) ────────────────────
        ax2 = axes[1]
        ax2.set_facecolor("white")

        colors_diff = ["#2ca02c" if d >= 0 else "#d62728" for d in diff]
        bars_diff   = ax2.bar(x, diff, color=colors_diff, alpha=0.85, edgecolor="white")

        for bar, d in zip(bars_diff, diff):
            if d != 0:
                va  = "bottom" if d >= 0 else "top"
                ypos = d + (0.2 if d >= 0 else -0.2)
                ax2.text(bar.get_x() + bar.get_width() / 2, ypos,
                         f"{d:+d}", ha="center", va=va, fontsize=7)

        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_xticks(x)
        ax2.set_xticklabels(goal_labels, rotation=45, ha="right", fontsize=9)
        ax2.set_title("Difference in Goal Assignments (LinkedSDG − OpenAlex)\n"
                      "Green = LinkedSDG assigns more  |  Red = OpenAlex assigns more",
                      fontsize=12, fontweight="bold", pad=12)
        ax2.set_ylabel("Δ Works", fontsize=10)
        ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax2.grid(axis="y", linestyle="--", alpha=0.4)

        plt.tight_layout(pad=3.0)
        out_path = "sdg_assignment_comparison.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.show()
        print(f"\n  [chart saved → {out_path}]")

print("\nDone.")
