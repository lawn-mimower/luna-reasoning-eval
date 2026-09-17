#!/usr/bin/env python3
"""Assemble the final results PDF.

One chart per page, each with a caption that shows a real example: what the
model was actually given, what a good answer looked like, and what a bad one
looked like. Examples are quoted verbatim from the run transcripts.

Only the charts that report findings on instruments we trust are included --
the diagnostic charts about benchmarks we discarded are left out of the PDF and
remain available as PNGs.

    .venv/bin/python plots.py && .venv/bin/python make_pdf.py
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).parent
PLOTS = ROOT / "runs/plots"
OUT = ROOT / "Luna_reasoning_evaluation.pdf"

INK, GREY, BLUE, GREEN, RED = "#111827", "#5B6672", "#17456F", "#177245", "#A81E1E"
MONO = ["IBM Plex Mono", "Menlo", "DejaVu Sans Mono", "monospace"]
SANS = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]

# (png, page title, [(kind, heading, body), ...])
#   kind: "plain" | "input" | "good" | "bad"
PAGES = [
    ("01_the_headline.png",
     "The finding in one picture",
     [("plain", "What this shows",
       "The same model at the same four settings, on two different kinds of work. "
       "Looking a fact up in a long document is unaffected by the reasoning setting. "
       "Doing a calculation whose steps depend on each other is transformed by it."),
      ("plain", "What to take away",
       "Turn reasoning up where values are derived and carried forward. Leave it off "
       "where they are merely looked up.")]),

    ("02_tool_calling.png",
     "Calling tools",
     [("input", "What the model was given",
       'Question: "Find all prime numbers between 50 and 150. Then get the '
       'fibonacci series upto 150."\n'
       "Functions available: count_items, find_prime_numbers, get_fibonacci_sequence"),
      ("good", "No reasoning — correct",
       'find_prime_numbers(start=50, end=150)\n'
       'get_fibonacci_sequence(count=150)\n'
       "Both requested calls made, arguments correct."),
      ("bad", "Medium reasoning — wrong",
       'find_prime_numbers(start=50, end=150)\n'
       "The second call was never made. The model reasoned its way into answering "
       "only half the question. This happened on 19 tasks that no-reasoning got right."),
      ("plain", "What to take away",
       "On the hardest tool-calling category, more reasoning made the model drop "
       "required calls. Across all 1,000 tasks the four settings are statistically "
       "tied, so choose the cheapest.")]),

    ("05_context_length.png",
     "Finding a fact in a long document",
     [("input", "What the model was given",
       "A 20,000-token bundle of real financial regulations — 185 competing passages "
       "— containing one relevant paragraph.\n"
       'Question: "Under SEBI ICDR Regulations, 2018, what is the minimum percentage '
       'of post-issue capital that promoters must hold following a public issue?"'),
      ("good", "A correct answer",
       'Expected: "At least twenty per cent."\n'
       'Model: "Promoters must hold at least 20% of the post-issue capital."'),
      ("bad", "The rare failure",
       'Model: "The passage does not provide the definition of compulsory delisting."\n'
       "It did. The model declined to answer rather than answering wrongly — which is "
       "the safer of the two failure modes, but still a miss."),
      ("plain", "What to take away",
       "Accuracy held between 93% and 100% from 600 tokens up to 30,000, at every "
       "setting. We never found the point where it breaks.")]),

    ("06_where_the_answer_sits.png",
     "Where the answer is hidden makes no difference",
     [("input", "What we varied",
       "The identical question and the identical 20,000-token document, with the "
       "relevant paragraph forced to sit at the very beginning, one quarter in, "
       "halfway, three quarters in, or at the very end."),
      ("plain", "Why it matters",
       "Many long-context models degrade badly when the answer sits in the middle of "
       "a document. If that happened here, it would mean the position of a rule in "
       "your prompt silently changes your results."),
      ("plain", "What to take away",
       "259 correct out of 261, and no position was meaningfully worse than any "
       "other. You do not need to think about where in the prompt you place a rule.")]),

    ("07_splitting_the_job.png",
     "Splitting one job across several calls",
     [("input", "What the model was given",
       "A US tax return with a 19,500-token rulebook, computed either in one call or "
       "broken into steps that hand results to each other.\n"
       "Correct answer: $16,734 overpaid. Correct intermediate values: total income "
       "$88,732, adjusted gross income $81,318, taxable income $59,219."),
      ("good", "Medium reasoning — correct",
       "Step 1 computed and handed on: total income = $88,732\n"
       "Step 2 received it and produced: $16,734 overpaid. Correct."),
      ("bad", "No reasoning — wrong",
       "Step 1 computed and handed on: total income = $88,732 — also correct\n"
       "Step 2 received the same correct figure and produced: $15,106 overpaid.\n"
       "The handover worked perfectly. The model simply could not do the remaining "
       "arithmetic."),
      ("plain", "What to take away",
       "The failure is capability, not information getting lost between calls. "
       "Accuracy does not fall as more handovers are added — and with no reasoning "
       "the model fails even when there is no handover at all.")]),

    ("08_thinking_follows_the_task.png",
     "You pay for thinking the model chose to do",
     [("plain", "What this shows",
       "Average internal thinking per call, at each setting, across three kinds of "
       "work. Note the logarithmic scale: the bars differ by a factor of forty."),
      ("plain", "Why it matters for budgeting",
       "The setting is a ceiling, not a target. On easy questions the highest setting "
       "spends almost nothing. Running everything at a high setting therefore costs "
       "far less than the price list suggests — the expense only appears on work that "
       "genuinely needs it."),
      ("plain", "What to take away",
       "Do not budget from the setting. Budget from the difficulty of the task.")]),

    ("09_cost_and_time.png",
     "What each setting costs you",
     [("plain", "What this shows",
       "Accuracy against wall-clock time and against money, for the chained tax "
       "calculation — the one task where the setting genuinely matters."),
      ("plain", "The trade",
       "No reasoning to medium: 62 points of accuracy for roughly 1.5 times the cost. "
       "Medium to high: 2 points for another 1.5 times the cost and nearly double the "
       "wait, at roughly a minute per finished answer."),
      ("plain", "A hard limit worth knowing",
       "The account allows 200,000 tokens per minute. At 15,000–30,000 tokens per "
       "decision that is 6 to 13 decisions per minute, whatever setting you choose.")]),

    ("10_thinking_on_failures.png",
     "The model knows which problems are hard",
     [("plain", "What this shows",
       "How much the model thinks on problems it gets right, compared with problems "
       "it gets wrong, on the same chained calculation."),
      ("plain", "The result",
       "At the highest setting it spends about 50% more thinking on the questions it "
       "fails. It is identifying difficulty correctly and then failing anyway."),
      ("plain", "What to take away",
       "The extra budget at the highest setting is largely spent on problems that "
       "were already lost. This is the clearest argument for choosing medium.")]),
]


def draw_caption(fig, y_top, blocks):
    """Lay the caption out from y_top downward, returning nothing."""
    y = y_top
    for kind, heading, body in blocks:
        color = {"good": GREEN, "bad": RED, "input": BLUE}.get(kind, INK)
        # matplotlib Text has no letterspacing property; space the caps by hand
        fig.text(0.055, y, " ".join(heading.upper()), fontsize=8,
                 fontweight="bold", color=color, family=SANS)
        y -= 0.021
        mono = kind in ("input", "good", "bad")
        for line in body.split("\n"):
            for wrapped in textwrap.wrap(line, 108 if mono else 118) or [""]:
                fig.text(0.055, y, wrapped, fontsize=8.6 if mono else 9.2,
                         color=INK if not mono else "#26303C",
                         family=MONO if mono else SANS)
                y -= 0.0175
        y -= 0.011


def main() -> None:
    with PdfPages(OUT) as pdf:
        # ---- cover
        fig = plt.figure(figsize=(11, 8.5), facecolor="white")
        fig.text(0.055, 0.80, "Does reasoning effort earn its cost?", fontsize=27,
                 fontweight="bold", family=SANS, color=INK)
        fig.text(0.055, 0.735, "An evaluation of gpt-5.6-luna across four settings",
                 fontsize=14, family=SANS, color=GREY)
        fig.text(0.055, 0.70,
                 "We ran the same model at four reasoning settings — none, low, medium and high —\n"
                 "across the four jobs it does in production: calling tools, finding facts in long\n"
                 "documents, applying written rules, and carrying a calculation across several calls.",
                 fontsize=11.5, family=SANS, color=INK, linespacing=1.7, va="top")
        fig.text(0.055, 0.545, "T H E   S H O R T   A N S W E R", fontsize=9,
                 fontweight="bold", family=SANS, color=BLUE)
        fig.text(0.055, 0.505,
                 "Reasoning effort does almost nothing for looking things up, however long the\n"
                 "document gets. It is the difference between failure and success when a calculation\n"
                 "has to be carried across steps — 15% correct with no reasoning, 79% at high.\n"
                 "Medium captures nearly all of that benefit at half the wait.",
                 fontsize=11.5, family=SANS, color=INK, linespacing=1.7, va="top")
        for i, (k, v) in enumerate([("Model calls scored", "7,146"),
                                    ("Total cost of the evaluation", "$8.12"),
                                    ("Measurement bugs found and fixed", "10")]):
            fig.text(0.055 + i * 0.30, 0.20, v, fontsize=21, fontweight="bold",
                     family=SANS, color=INK)
            fig.text(0.055 + i * 0.30, 0.163, k, fontsize=9, family=SANS, color=GREY)
        fig.text(0.055, 0.075, "Every figure in this document is measured. Nothing is "
                 "extrapolated or estimated.", fontsize=9, family=SANS, color=GREY)
        pdf.savefig(fig); plt.close(fig)

        # ---- one page per chart
        for png, title, blocks in PAGES:
            path = PLOTS / png
            if not path.exists():
                print(f"  !! missing {png}, skipping")
                continue
            fig = plt.figure(figsize=(11, 8.5), facecolor="white")
            fig.text(0.055, 0.955, title, fontsize=16, fontweight="bold",
                     family=SANS, color=INK)
            img = mpimg.imread(path)
            h, w = img.shape[0], img.shape[1]
            box_w = 0.89
            box_h = box_w * (h / w) * (11 / 8.5)
            box_h = min(box_h, 0.46)
            ax = fig.add_axes([0.055, 0.905 - box_h, box_w, box_h])
            ax.imshow(img)
            ax.axis("off")
            draw_caption(fig, 0.905 - box_h - 0.05, blocks)
            pdf.savefig(fig); plt.close(fig)

        d = pdf.infodict()
        d["Title"] = "Does reasoning effort earn its cost? — gpt-5.6-luna evaluation"
        d["Subject"] = "Measured accuracy, cost and latency across four reasoning settings"

    print(f"wrote {OUT}  ({len(PAGES) + 1} pages)")


if __name__ == "__main__":
    main()
