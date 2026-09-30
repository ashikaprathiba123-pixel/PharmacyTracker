import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.patches as mpatches

def show_graph(self):
    """
    Improved analytics: single window with Bar, Pie and Line charts.
    - Bar: days left until expiry per medicine (colored by status).
    - Pie: distribution of Expired / Soon (<=30 days) / Safe (>30 days).
    - Line: days left trend (sorted).
    Drop this method into your MediExpiryApp class to replace the existing analytics.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT medicine_name, expiry_date FROM medicines")
        data = cursor.fetchall()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if not data:
        messagebox.showinfo("No Data", "No inventory data to display.")
        return

    names = []
    days_list = []
    colors = []
    today = datetime.today()

    for name, expiry in data:
        if not expiry or not name:
            continue
        try:
            exp_date = datetime.strptime(expiry, "%Y-%m-%d")
        except Exception:
            continue
        days_left = (exp_date - today).days
        names.append(str(name))
        days_list.append(int(days_left))
        if days_left < 0:
            colors.append("red")
        elif days_left <= 30:
            colors.append("orange")
        else:
            colors.append("green")

    if not names:
        messagebox.showinfo("No Valid Dates", "No valid expiry dates found to plot.")
        return

    # Sort by days_left for clearer line and bar ordering
    sorted_idx = sorted(range(len(days_list)), key=lambda i: days_list[i])
    names_sorted = [names[i] for i in sorted_idx]
    days_sorted = [days_list[i] for i in sorted_idx]
    colors_sorted = [colors[i] for i in sorted_idx]

    # Shorten long labels for readability (keeps full names in tooltip-less static plots)
    def shorten(s, n=28):
        return s if len(s) <= n else s[:n-3] + "..."

    labels_short = [shorten(nm) for nm in names_sorted]
    positions = list(range(len(labels_short)))

    # Prepare figure with 3 subplots
    plt.close("all")
    fig, axs = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)

    # -------- BAR GRAPH --------
    ax = axs[0]
    ax.bar(positions, days_sorted, color=colors_sorted)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Days Until Expiry (per medicine)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Days left", fontsize=10)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels_short, rotation=45, ha="right", fontsize=9)
    red_p = mpatches.Patch(color='red', label='Expired (<0 days)')
    ora_p = mpatches.Patch(color='orange', label='Expiring soon (≤30 days)')
    gre_p = mpatches.Patch(color='green', label='Safe (>30 days)')
    ax.legend(handles=[red_p, ora_p, gre_p], loc="upper right", fontsize=9)

    ymin = min(days_sorted + [0])
    ymax = max(days_sorted + [0])
    margin = max(1, int((ymax - ymin) * 0.08))
    ax.set_ylim(ymin - margin, ymax + margin)

    # -------- PIE CHART --------
    ax = axs[1]
    expired = sum(1 for d in days_sorted if d < 0)
    soon = sum(1 for d in days_sorted if 0 <= d <= 30)
    safe = sum(1 for d in days_sorted if d > 30)
    pie_sizes = [expired, soon, safe]
    pie_labels = ['Expired', 'Soon (≤30d)', 'Safe (>30d)']
    if sum(pie_sizes) == 0:
        ax.text(0.5, 0.5, "No valid date data", ha="center", va="center")
        ax.set_title("Expiry Distribution", fontsize=12, fontweight="bold")
    else:
        colors_pie = ['red', 'orange', 'green']
        wedges, texts, autotexts = ax.pie(
            pie_sizes,
            labels=pie_labels,
            autopct=lambda pct: f"{pct:.1f}%\n({int(round(pct/100*sum(pie_sizes)))})",
            colors=colors_pie,
            startangle=90,
            textprops={'fontsize': 9}
        )
        for t in autotexts:
            t.set_color('white')
            t.set_fontsize(8)
        ax.set_title("Expiry Distribution", fontsize=12, fontweight="bold")

    # -------- LINE GRAPH --------
    ax = axs[2]
    ax.plot(positions, days_sorted, marker='o', linestyle='-', color='#1f4e79')
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Expiry Trend (sorted)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Days left", fontsize=10)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels_short, rotation=45, ha="right", fontsize=9)
    ax.set_ylim(ymin - margin, ymax + margin)

    plt.show()
