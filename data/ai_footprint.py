"""Curated AI-model footprint reference table.

data/ai_footprint.csv holds hand-derived, per-model per-use-case estimates
of energy (Wh), carbon (gCO2e), and water (mL) cost per AI query. These are
NOT measured or vendor-disclosed figures -- there is no standardized,
comprehensive measurement of per-query AI cost (MIT News, "Explained:
Generative AI's environmental impact", Jan 2025,
https://news.mit.edu/2025/explained-generative-ai-environmental-impact-0117).
Every row's magnitude is anchored to two numbers from that article: a
ChatGPT query uses ~5x the electricity of a basic web search, and data
centers need ~2L of water per kWh consumed for cooling (so water_ml =
energy_wh * 2 throughout the table). The co2_g figures assume a constant
grid carbon intensity of ~267 gCO2e/kWh across all rows -- a single
global-average grid-intensity assumption, not a per-region or
per-provider measurement. The ChatGPT / email_summary row is
additionally cross-checked for plausible order of magnitude -- not copied
-- against the ClimateAligned AI Footprint Calculator's displayed GPT-4o
"median use" figures
(https://www.climatealigned.co/tools/ai-footprint-calculator), which cites
Google's 2024 production measurements.

Model-to-model multipliers relative to the ChatGPT baseline (Claude 0.9x,
Gemini 0.75x, Grok 1.15x) are this project's own rough, qualitative
estimate based on public reporting about relative model/infrastructure
scale -- an explicitly unverified assumption, not a measurement. The same
caveat is shown to users in the AI Footprint page's on-page disclosure
banner (pages/ai_footprint.py).

word_count_max buckets the free-text prompt input by word count (see
ai_footprint_analysis.bucket_prompt); 100000 represents "no cap" for the
largest (coding_agent) use case.
"""

from pathlib import Path

import pandas as pd

AI_FOOTPRINT_PATH = str(Path(__file__).resolve().parent / "ai_footprint.csv")


def load_ai_footprint_data(path: str = AI_FOOTPRINT_PATH) -> pd.DataFrame:
    return pd.read_csv(path)
