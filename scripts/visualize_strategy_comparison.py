from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def visualize_results():
    # Setup paths
    csv_path = Path("data/backtest/strategy_comparison_results.csv")
    output_path = Path("data/backtest/strategy_comparison.png")

    if not csv_path.exists():
        print(f"Error: Results file not found at {csv_path}")
        return

    # Load data
    df = pd.read_csv(csv_path)

    # Prepare data for plotting
    plot_data = df.melt(
        id_vars=["meet_name"],
        value_vars=[
            "coach_illegal_score",
            "coach_legal_score",
            "coach_fatigue_score",
            "aqua_score",
            "gurobi_score",
            "actual_seton_score",
        ],
        var_name="Strategy",
        value_name="Score",
    )

    # Rename strategies for better legibility
    strategy_map = {
        "coach_illegal_score": "Coach (Illegal)",
        "coach_legal_score": "Coach (Legal)",
        "coach_fatigue_score": "Coach (Fatigue)",
        "aqua_score": "AquaOptimizer",
        "gurobi_score": "Gurobi",
        "actual_seton_score": "Actual (Official)",
    }
    plot_data["Strategy"] = plot_data["Strategy"].map(strategy_map)

    # Shorten meet names for X-axis
    plot_data["Meet"] = plot_data["meet_name"].apply(
        lambda x: x[:20] + "..." if len(x) > 20 else x
    )

    # Set theme
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(12, 6))

    # Create Bar Chart
    ax = sns.barplot(
        data=plot_data,
        x="Meet",
        y="Score",
        hue="Strategy",
        palette="viridis",
        edgecolor="black",
    )

    # Add labels
    plt.title(
        "Championship Strategy Comparison: Seton Swimming",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    plt.ylabel("Projected Score", fontsize=12)
    plt.xlabel("Meet", fontsize=12)
    plt.xticks(rotation=15)
    plt.legend(title="Strategy", bbox_to_anchor=(1.05, 1), loc="upper left")

    # Add numeric labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", padding=3)

    plt.tight_layout()

    # Save
    plt.savefig(output_path, dpi=300)
    print(f"Visualization saved to {output_path}")


if __name__ == "__main__":
    visualize_results()
