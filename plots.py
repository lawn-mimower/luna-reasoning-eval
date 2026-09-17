#!/usr/bin/env python3
"""Blog-ready charts for the Luna reasoning-effort evaluation.

Deliberately plain matplotlib. Every label is spelled out in full words, every
chart carries a one-line explanation of what it shows, and nothing depends on
the reader knowing our internal suite names or shorthand.

    .venv/bin/python plots.py        # writes runs/plots/*.png
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent
RUNS = ROOT / "runs"
OUT = RUNS / "plots"
OUT.mkdir(parents=True, exist_ok=True)

MODES = ["none", "low", "medium", "high"]
# Full words everywhere the reader sees them.
LABEL = {"none": "No reasoning", "low": "Low", "medium": "Medium", "high": "High"}
# Effort is an ordered scale, so the colours are a single ramp rather than four
# unrelated hues -- a categorical palette would invite the wrong comparison.
COLOR = {"none": "#BBD3E8", "low": "#7FA9CF", "medium": "#427CB4", "high": "#17456F"}
SUITE = {
    "uc2_spot": "Finding a stated fact in a passage",
    "uc3_rules": "Applying a rule from the passage",
    "uc4_formula": "Writing a formula and substituting values",
}
GREEN, RED, GREY = "#177245", "#A81E1E", "#5B6672"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
    "savefig.facecolor": "white", "figure.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8A94A0", "axes.labelsize": 11,
    "axes.grid": True, "grid.color": "#E8ECF1", "grid.linewidth": 0.9,
    "axes.axisbelow": True, "legend.frameon": False,
    "xtick.color": "#3D4753", "ytick.color": "#3D4753", "font.size": 10,
})


def jl(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path) if l.strip()] if path.exists() else []


def headline(fig, title: str, explain: str):
    # Reserve real space above the axes instead of floating the text over them --
    # suptitle and the explanatory line were overlapping at the default spacing.
    # Title and standfirst live INSIDE the reserved band at the top of the figure.
    # Floating them above y=1.0 made bbox_inches="tight" expand the canvas and
    # leave a large empty strip.
    fig.subplots_adjust(top=0.78)
    fig.suptitle(title, x=0.012, ha="left", fontsize=15, fontweight="bold", y=1.005)
    fig.text(0.012, 0.905, explain, ha="left", fontsize=10.5, color="#3D4753")


def footnote(fig, text: str, y: float = -0.02):
    """`y` drops the note below a legend on the two charts that carry one."""
    fig.text(0.012, y, text, ha="left", fontsize=8.5, color=GREY)


def save(fig, name: str):
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)
    print(f"  wrote {name}.png")


def pct_axis(ax, top=105):
    ax.set_ylim(0, top)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])


# ============================================================= 1
def chart_1_the_headline():
    """The single comparison the whole project comes down to."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6))

    rows = jl(RUNS / "ladder10/results.jsonl") + jl(RUNS / "ladder_hi/results.jsonl")
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("method") == "truncated":
            continue
        agg[r["mode"]][1] += 1
        agg[r["mode"]][0] += bool(r["correct"])
    vals = [100 * agg[m][0] / agg[m][1] for m in MODES]
    left.bar([LABEL[m] for m in MODES], vals, color=[COLOR[m] for m in MODES], width=.62)
    for i, v in enumerate(vals):
        left.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
    pct_axis(left)
    left.set_title("Looking something up in a long document",
                   fontsize=12, loc="left", pad=10)
    left.set_ylabel("Answers correct")

    ho = jl(RUNS / "ho_live2/results_regraded.jsonl")
    agg2 = defaultdict(lambda: [0, 0])
    for r in ho:
        if "correct" not in r:
            continue
        agg2[r["mode"]][1] += 1
        agg2[r["mode"]][0] += bool(r["correct"])
    vals2 = [100 * agg2[m][0] / agg2[m][1] for m in MODES]
    right.bar([LABEL[m] for m in MODES], vals2, color=[COLOR[m] for m in MODES], width=.62)
    for i, v in enumerate(vals2):
        right.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
    pct_axis(right)
    right.set_title("Doing a multi-step calculation across several API calls",
                    fontsize=12, loc="left", pad=10)
    right.set_ylabel("Answers correct")

    headline(fig, "Turning up the reasoning setting only helps for one kind of work",
             "Same model, same four settings, same week. Left: 840 lookups. "
             "Right: 192 chained tax calculations.")
    footnote(fig, "Left panel never drops below 93%, so it shows no effect rather than "
                  "proving there is none. Right panel: the difference between no "
                  "reasoning and high is statistically overwhelming (p = 0.0000000019).")
    save(fig, "01_the_headline")


# ============================================================= 2
def chart_2_tool_calling():
    """BFCL, spelled out."""
    cats = {
        "simple_python": ("One function to choose from", 400,
                          [81.00, 82.00, 82.75, 84.50]),
        "multiple": ("Several functions, pick the right one", 200,
                     [85.50, 83.50, 84.50, 84.00]),
        "parallel": ("One function, called several times", 200,
                     [84.00, 85.00, 85.50, 83.00]),
        "parallel_multiple": ("Several functions, each called several times", 200,
                              [77.00, 70.50, 69.00, 70.00]),
    }
    fig, ax = plt.subplots(figsize=(11, 5))
    y = np.arange(len(cats))
    h = 0.19
    for i, m in enumerate(MODES):
        ax.barh(y + (1.5 - i) * h, [v[2][i] for v in cats.values()], h,
                color=COLOR[m], label=LABEL[m])
    ax.set_yticks(y)
    ax.set_yticklabels([f"{v[0]}\n({v[1]} tasks)" for v in cats.values()], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(60, 92)
    ax.set_xlabel("Tool calls that exactly matched the expected call")
    ax.set_xticks([60, 65, 70, 75, 80, 85, 90])
    ax.set_xticklabels([f"{t}%" for t in [60, 65, 70, 75, 80, 85, 90]])
    ax.legend(loc="lower right", ncol=4, fontsize=9.5, title="Reasoning setting",
              title_fontsize=9.5)
    ax.annotate("Reasoning makes this one worse",
                xy=(70, 3 - 0.1), xytext=(73.5, 3.55), fontsize=10, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
    headline(fig, "For calling tools, extra reasoning buys nothing — and sometimes costs you",
             "1,000 tasks at each of the four settings. Each task gives the model a set "
             "of functions and asks it to call the right ones.")
    footnote(fig, "Overall the four settings are statistically tied (p = 0.68), so pick "
                  "on cost: no reasoning is 34% cheaper. The one real effect is the "
                  "bottom row, where reasoning loses 7-8 points (p = 0.0009).")
    save(fig, "02_tool_calling")


# ============================================================= 3
def chart_3_benchmark_cannot_tell_models_apart():
    """The negative control that voided three of our four suites."""
    data = [
        ("Luna, no reasoning", 94.9, "#17456F"), ("Luna, low", 97.1, "#17456F"),
        ("Luna, medium", 95.7, "#17456F"), ("Luna, high", 95.7, "#17456F"),
        ("GPT-4.1-nano (cannot reason)", 92.8, "#6B7280"),
        ("GPT-5-nano, low", 92.8, "#C2410C"),
        ("GPT-5-nano, medium", 93.5, "#C2410C"),
        ("GPT-5-nano, high", 96.4, "#C2410C"),
    ]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ys = np.arange(len(data))
    ax.axvspan(92.8, 97.1, color="#427CB4", alpha=.10, lw=0)
    for i, (lab, v, c) in enumerate(data):
        ax.plot([88, v], [i, i], color="#DCE3EA", lw=1.2, zorder=1)
        ax.scatter(v, i, s=95, color=c, zorder=3)
        ax.text(v + 0.28, i, f"{v}%", va="center", fontsize=9.5, color="#3D4753")
    ax.set_yticks(ys)
    ax.set_yticklabels([d[0] for d in data])
    ax.invert_yaxis()
    ax.set_xlim(88, 99.5)
    ax.set_xlabel("Answers correct on the same 138 questions")
    ax.set_xticks([90, 92, 94, 96, 98])
    ax.set_xticklabels(["90%", "92%", "94%", "96%", "98%"])
    ax.text(94.9, -0.85, "every model and setting falls inside this 4.3-point band",
            ha="center", fontsize=9.5, color="#427CB4")
    headline(fig, "Three of our benchmarks could not tell a top model from a cheap one",
             "We re-ran the identical questions on two deliberately weaker models. "
             "Everything landed in the same narrow band.")
    footnote(fig, "Luna versus GPT-4.1-nano on matched questions: p = 0.549, no "
                  "detectable difference. GPT-5-nano at high actually scores above Luna "
                  "at high. We threw these three benchmarks out as measuring instruments.")
    save(fig, "03_benchmark_cannot_separate")


# ============================================================= 4
def chart_4_why_those_benchmarks_failed():
    """Prompt length is the whole explanation."""
    fig, ax = plt.subplots(figsize=(10, 4.2))
    names = ["Our three discarded\nbenchmarks", "The chained tax\nbenchmark"]
    vals = [646, 19538]
    bars = ax.barh(names, vals, color=["#BBD3E8", "#17456F"], height=.5)
    for b, v in zip(bars, vals):
        ax.text(v + 350, b.get_y() + b.get_height() / 2,
                f"{v:,} characters", va="center", fontsize=11, fontweight="bold")
    ax.set_xlim(0, 24000)
    ax.set_xlabel("Typical length of the text given to the model")
    ax.set_xticks([0, 5000, 10000, 15000, 20000])
    ax.set_xticklabels(["0", "5,000", "10,000", "15,000", "20,000"])
    headline(fig, "The reason: the questions were far too easy",
             "A 646-character passage is about 120 words. It is too short to contain a "
             "second plausible answer.")
    footnote(fig, "In 38% of the lookup questions the correct answer appears word for "
                  "word in the passage. There is nothing to search for, so no amount of "
                  "thinking can help.")
    save(fig, "04_why_they_failed")


# ============================================================= 5
def chart_5_context_length():
    """Does burying the answer in more text break it?"""
    rows = jl(RUNS / "ladder10/results.jsonl") + jl(RUNS / "ladder_hi/results.jsonl")
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("method") == "truncated":
            continue
        agg[(r["mode"], r["rung"])][1] += 1
        agg[(r["mode"], r["rung"])][0] += bool(r["correct"])
    rungs = sorted({k[1] for k in agg})

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.axvspan(15000, 30000, color="#427CB4", alpha=.08, lw=0)
    ax.text(22500, 27, "the amount of text this\nteam sends in production",
            ha="center", fontsize=9.5, color="#3D4753")
    for m in MODES:
        ys = [100 * agg[(m, g)][0] / agg[(m, g)][1] for g in rungs]
        ax.plot(rungs, ys, "o-", color=COLOR[m], lw=2.2, ms=6.5,
                label=LABEL[m], mec="white", mew=1.2)
    pct_axis(ax)
    ax.set_xlabel("Amount of surrounding text the answer was buried in (tokens)")
    ax.set_ylabel("Answers correct")
    ax.set_xticks(rungs)
    ax.set_xticklabels(["600\n(original)", "2,500", "5,000", "10,000", "15,000",
                        "20,000", "30,000"], fontsize=9)
    ax.legend(title="Reasoning setting", loc="lower left", ncol=4, fontsize=9.5,
              title_fontsize=9.5)
    headline(fig, "Burying the answer in 50 times more text changed nothing",
             "We padded each question with real regulatory documents, up to 290 "
             "competing passages, and asked exactly the same question.")
    footnote(fig, "No setting degrades, and no setting pulls ahead (p = 1.0). We never "
                  "found the breaking point, so this puts a floor under the model's "
                  "ability rather than measuring its limit.")
    save(fig, "05_context_length")


# ============================================================= 6
def chart_6_needle_position():
    """Does it matter WHERE in the document the answer sits?"""
    rows = jl(RUNS / "pos20k/results.jsonl")
    if not rows:
        return
    order = [0.0, 0.25, 0.5, 0.75, 1.0]
    names = ["Very beginning", "One quarter in", "Halfway through",
             "Three quarters in", "Very end"]
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("method") == "truncated":
            continue
        agg[r["target_pos"]][1] += 1
        agg[r["target_pos"]][0] += bool(r["correct"])
    fig, ax = plt.subplots(figsize=(11, 4.8))
    vals = [100 * agg[p][0] / agg[p][1] for p in order]
    ax.bar(names, vals, color="#427CB4", width=.56)
    for i, (p, v) in enumerate(zip(order, vals)):
        ax.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold")
        ax.text(i, 5, f"{agg[p][0]} of {agg[p][1]}", ha="center", fontsize=9,
                color="white")
    pct_axis(ax)
    ax.set_ylabel("Answers correct")
    ax.set_xlabel("Where the answer was placed inside a 20,000-token document")
    headline(fig, "It does not matter where in the document the answer is hidden",
             "Many models are known to lose track of information in the middle of a "
             "long document. This one did not.")
    footnote(fig, "259 correct out of 261. We ran this specifically because an earlier "
                  "version of our own code accidentally placed the answer near the end "
                  "almost every time, which would have flattered the result.")
    save(fig, "06_where_the_answer_sits")


# ============================================================= 7
def chart_7_handover():
    """Splitting one job across several calls."""
    rows = jl(RUNS / "ho_live2/results_regraded.jsonl")
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        if "correct" not in r:
            continue
        agg[(r["depth"], r["mode"])][1] += 1
        agg[(r["depth"], r["mode"])][0] += bool(r["correct"])
    depths = sorted({k[0] for k in agg})

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(depths))
    w = 0.2
    for i, m in enumerate(MODES):
        vals = [100 * agg[(d, m)][0] / agg[(d, m)][1] for d in depths]
        ax.bar(x + (i - 1.5) * w, vals, w, color=COLOR[m], label=LABEL[m])
        # an empty bar looks like missing data, so say "0%" out loud
        for xi, v in zip(x + (i - 1.5) * w, vals):
            if v < 1:
                ax.text(xi, 2, "0%", ha="center", fontsize=8.5, color=RED,
                        fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([
        "Done in a single call\n(nothing handed over)",
        "Split into 2 calls\n(1 handover)",
        "Split into 3 calls\n(2 handovers)",
        "Split into 4 calls\n(3 handovers)"], fontsize=9.5)
    pct_axis(ax)
    ax.set_ylabel("Tax calculations that came out exactly right")
    ax.legend(title="Reasoning setting", ncol=4, fontsize=9.5, title_fontsize=9.5,
              loc="upper center", bbox_to_anchor=(0.5, -0.16))
    headline(fig, "Here the reasoning setting decides whether the job gets done at all",
             "The same tax return, computed either in one go or broken into steps that "
             "hand results to each other. The work is identical in every column.")
    footnote(fig, "With no reasoning the model fails even when nothing is handed over, "
                  "so this is a limit of ability rather than information getting lost "
                  "between calls. Accuracy does not fall as more handovers are added.",
             y=-0.30)
    save(fig, "07_splitting_the_job")


# ============================================================= 8
def chart_8_thinking_is_demand_driven():
    """You pay for thinking the model chose to do, not for the setting."""
    src = [("The easy lookup questions", RUNS / "flat40/ledger.jsonl"),
           ("The same questions, buried in\n20,000 tokens of documents", RUNS / "ladder_hi/ledger.jsonl"),
           ("The chained tax calculation", RUNS / "ho_live2/ledger.jsonl")]
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(src))
    w = 0.2
    for i, m in enumerate(MODES):
        means = []
        for _, path in src:
            v = [r["reasoning_tokens"] for r in jl(path)
                 if r.get("role") == "target" and r.get("ok") and r["mode"] == m]
            means.append(np.mean(v) if v else 0)
        bars = ax.bar(x + (i - 1.5) * w, means, w, color=COLOR[m], label=LABEL[m])
        for b, v in zip(bars, means):
            if v > 0:
                ax.text(b.get_x() + b.get_width() / 2, v * 1.35, f"{v:,.0f}",
                        ha="center", fontsize=8, color="#3D4753")
    ax.set_yscale("log")
    ax.set_ylim(1, 20000)
    ax.set_xticks(x)
    ax.set_xticklabels([s[0] for s in src], fontsize=10)
    ax.set_ylabel("Average words of internal thinking per call\n(log scale)")
    ax.legend(title="Reasoning setting", ncol=4, fontsize=9.5, title_fontsize=9.5,
              loc="upper center", bbox_to_anchor=(0.5, -0.14))
    headline(fig, "The setting is a speed limit, not a target — the task decides the bill",
             "On easy questions the highest setting barely thinks. On hard ones it "
             "thinks 40 times harder. You are only billed for what it actually does.")
    footnote(fig, "This is why running everything on the highest setting is not as "
                  "expensive as it sounds, and why the highest setting is not as "
                  "wasteful on easy work as people assume.", y=-0.28)
    save(fig, "08_thinking_follows_the_task")


# ============================================================= 9
def chart_9_cost_and_time():
    """The practical trade for the one task where reasoning matters."""
    rows = jl(RUNS / "ho_live2/results_regraded.jsonl")
    led = jl(RUNS / "ho_live2/ledger.jsonl")
    acc, sec = {}, {}
    for m in MODES:
        r = [x for x in rows if x["mode"] == m and "correct" in x]
        acc[m] = 100 * sum(bool(x["correct"]) for x in r) / len(r)
        sec[m] = np.mean([sum(h["latency"] for h in x["hops"]) for x in r])
    cost = {}
    for m in MODES:
        c = [r for r in led if r["mode"] == m and r.get("ok")]
        n = len([x for x in rows if x["mode"] == m])
        cost[m] = (sum(r["prompt_tokens"] for r in c) * 0.20 / 1e6 +
                   sum(r["completion_tokens"] for r in c) * 1.20 / 1e6) / n

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
    for m in MODES:
        a1.scatter(sec[m], acc[m], s=190, color=COLOR[m], zorder=3,
                   edgecolor="white", lw=1.5)
        a1.annotate(LABEL[m], (sec[m], acc[m]), fontsize=10,
                    xytext=(0, -22), textcoords="offset points", ha="center")
    a1.plot([sec[m] for m in MODES], [acc[m] for m in MODES], color="#C6D3E0",
            lw=1.4, zorder=1)
    pct_axis(a1)
    a1.set_xlabel("Seconds to produce one finished answer")
    a1.set_ylabel("Answers correct")
    a1.set_title("Time", fontsize=12, loc="left", pad=10)
    a1.set_xlim(0, 55)

    for m in MODES:
        a2.scatter(cost[m] * 100, acc[m], s=190, color=COLOR[m], zorder=3,
                   edgecolor="white", lw=1.5)
        a2.annotate(LABEL[m], (cost[m] * 100, acc[m]), fontsize=10,
                    xytext=(0, -22), textcoords="offset points", ha="center")
    a2.plot([cost[m] * 100 for m in MODES], [acc[m] for m in MODES],
            color="#C6D3E0", lw=1.4, zorder=1)
    pct_axis(a2)
    a2.set_xlabel("Cost of one finished answer (US cents)")
    a2.set_ylabel("Answers correct")
    a2.set_title("Money", fontsize=12, loc="left", pad=10)
    a2.set_xlim(0, 1.6)

    headline(fig, "Medium is the sweet spot: nearly all the accuracy, half the wait",
             "For the chained tax calculation, where the reasoning setting genuinely "
             "matters.")
    footnote(fig, "Going from no reasoning to medium adds 62 points of accuracy for "
                  "about 1.5 times the cost. Going from medium to high adds 2 points "
                  "for another 1.5 times the cost and nearly double the wait.")
    save(fig, "09_cost_and_time")


# ============================================================= 10
def chart_10_thinking_on_failures():
    """Does it think harder on the ones it gets wrong?"""
    rows = jl(RUNS / "ho_live2/results_regraded.jsonl")
    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(3)
    w = 0.34
    shown = ["low", "medium", "high"]
    right = [np.median([sum(h["think"] for h in r["hops"])
                        for r in rows if r["mode"] == m and r.get("correct")])
             for m in shown]
    wrong = [np.median([sum(h["think"] for h in r["hops"])
                        for r in rows if r["mode"] == m and "correct" in r
                        and not r["correct"]]) for m in shown]
    b1 = ax.bar(x - w / 2, right, w, color=GREEN, label="Questions it got right")
    b2 = ax.bar(x + w / 2, wrong, w, color=RED, label="Questions it got wrong")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 130,
                    f"{b.get_height():,.0f}", ha="center", fontsize=9.5)
    ax.set_xticks(x)
    ax.set_xticklabels([LABEL[m] for m in shown])
    ax.set_xlabel("Reasoning setting")
    ax.set_ylabel("Typical words of internal thinking\nspent on one calculation")
    ax.legend(fontsize=10)
    ax.annotate("50% more thinking,\nstill wrong", xy=(2.17, 7659),
                xytext=(1.55, 9600), fontsize=10, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
    headline(fig, "It knows which problems are hard — it just cannot solve them",
             "Comparing how much the model thinks on problems it gets right versus "
             "problems it gets wrong.")
    footnote(fig, "At the highest setting it spends half as much again on the questions "
                  "it fails. Difficulty is being detected correctly and the extra "
                  "thinking is not converting into extra correct answers.")
    save(fig, "10_thinking_on_failures")


if __name__ == "__main__":
    print(f"writing charts to {OUT}/")
    chart_1_the_headline()
    chart_2_tool_calling()
    chart_3_benchmark_cannot_tell_models_apart()
    chart_4_why_those_benchmarks_failed()
    chart_5_context_length()
    chart_6_needle_position()
    chart_7_handover()
    chart_8_thinking_is_demand_driven()
    chart_9_cost_and_time()
    chart_10_thinking_on_failures()
    print("done")
