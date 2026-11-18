# Phase 3 demo — "why these datasets" + "why Plotly" (live example)

This folder is the small, self-contained piece to run *live* in front of the
teacher. It does not touch the real dashboard or its data — it's a tiny,
offline, 2-minute demo built specifically to make the "why Plotly" answer
something you can point at, not just say.

Full detail on both questions is in `../PROJECT_REPORT.md` (§4 for datasets,
§6 for tools). This README is the short version + the thing to actually run.

---

## 1. "Why did you choose these datasets?" — the 60-second answer

- The real app uses **4 sources**, each filling a gap the others don't cover:
  **OWID CO2** (emissions + GDP + population, one file, 218 countries,
  1750–2024), **NASA GISTEMP** (*observed* global temperature — kept separate
  from OWID's *modelled* CO2-attribution column so the two are never
  confused), **OWID Energy** (renewable electricity share, same key/format as
  the CO2 file, so it joins for free), and **NASA POWER** (solar/wind
  potential, cached to a file, never called live).
- No single free dataset has all five things this project needs (emissions,
  GDP, population, observed temperature, renewable potential) — so each
  dataset was added only where a real gap existed, not for variety's sake.
- Both OWID files were checked, not assumed: `profile_dataset.py` measured
  actual missingness before any cleaning rule was written (e.g. GDP is 27%
  missing and stops in 2022; one renewable-share column was *silently
  frozen* between 2015–2023 for 141 countries while the other one moved
  sensibly — so that one was rejected).

**The one-line version**: *"We picked datasets the way you'd pick tools for a
job — one for emissions and economics, one for real observed temperature so
we never mislabel modelled data as measured, one for renewables, one for
physical solar/wind potential — and we checked each one's actual data quality
before trusting it, we didn't just assume it was clean."*

---

## 2. "Why Plotly?" — the thing to actually demo

Don't just say it — run it. This folder builds **the same two charts twice**:
once in Matplotlib (what a static-image library produces) and once in Plotly
(what the real dashboard uses), from the same 8-row / 10-row toy dataset.

### Run it

```bash
cd docs/demo
python matplotlib_example.py
python plotly_example.py
```

This produces:

| File | What it is |
|---|---|
| `output/matplotlib_line.png` | Static line chart — open in any image viewer |
| `output/matplotlib_bubble.png` | Static bubble chart, with manually-placed text labels |
| `output/matplotlib_line.html` | Same static chart, embedded in an HTML page — opens in a **browser**, but still just a picture (no hover/zoom/legend) |
| `output/matplotlib_bubble.html` | Same static bubble chart, embedded in an HTML page — same non-interactivity |
| `output/plotly_line.html` | The same line chart — open in a **browser**, fully interactive |
| `output/plotly_bubble.html` | The same bubble chart — open in a **browser**, fully interactive |

Matplotlib now also produces `.html` files so every comparison is
**file-format vs. file-format** — both sides hand you a `.html` file to open
in a browser, and the only difference left is whether anything in it
responds when you touch it. That's a cleaner demo than "PNG vs HTML," which
could look like the format itself is the reason, rather than the library.

### What to actually show the teacher, in order

1. Open `matplotlib_bubble.html` in a browser. It opens like any web page —
   but it's still just an `<img>` tag around a picture. Point out the country
   labels — they had to be manually placed one by one in the code
   (`matplotlib_example.py`, the `ax.annotate` loop). Nothing on it responds
   to a click, a hover, or a drag, despite being a `.html` file exactly like
   the one you're about to open next.
2. Open `plotly_bubble.html` in a browser, side by side. Same data, same
   chart type. Now:
   - **Hover** over any bubble — the country name, GDP, and CO2/capita
     appear in a tooltip, with no manual label-placing code anywhere.
   - **Click-drag** a rectangle over a cluster of bubbles to zoom in;
     **double-click** to reset.
   - **Click a continent name in the legend** (top right) to hide/show
     that continent's countries.
   - Point at the camera icon in the top toolbar — one click exports the
     current view as a PNG, for free.
3. Open `plotly_example.py` and `matplotlib_example.py` side by side in an
   editor. Show that `bubble_chart()` in the Plotly version is *shorter*
   than the Matplotlib version, despite producing something with far more
   functionality — the size scaling, the color-by-continent, the hover
   labels, and the log axis are each **one keyword argument**
   (`size=`, `color=`, `hover_name=`, `log_x=True`), where Matplotlib needed
   a manual scaling formula and a manual label loop just to get partway there.

### The line to say afterward

*"This is the exact same Plotly API the real dashboard uses — `px.scatter`
with `size`, `color`, `hover_name`, `log_x` — just on 8 rows here instead of
the ~190 countries in the actual Q3 page. We didn't need extra code to make
the real dashboard interactive; interactivity is what you get by default
when you pick Plotly, which is the whole reason it was chosen over
Matplotlib for a project that specifically had to be an interactive,
deployed dashboard."*

---

## Files in this folder

- `demo_data.py` — the tiny hardcoded dataset (8 countries, 10 years),
  shaped exactly like the real, much larger OWID data the app uses.
  Hardcoded on purpose: the demo must work **offline**, with no network
  dependency, in front of the teacher.
- `matplotlib_example.py` — same two charts, static (outputs both `.png` and
  a `.html` wrapper around the same image, for format parity with Plotly's
  output — the wrapper does not add interactivity).
- `plotly_example.py` — same two charts, interactive (`.html` only —
  Plotly's native output format).
- `output/` — generated files (git-ignorable; regenerate any time by
  re-running the two scripts above).
