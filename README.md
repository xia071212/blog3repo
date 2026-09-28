# Blog 3 replication package

This project reproduces **“Tech Dominates the Forbes Rich List. Do Tech and Finance Careers Really Pay More?”** It follows the Blog 2 project's `data/`, `code/`, `results/`, README, and provenance structure. The companion Quarto article lives at `myrepo1/blog/posts/post3/index.qmd` in the local website project. A generated copy is also `blog_post.qmd` here.

## Structure

- `code/`: weighted CPS analysis, independent verification, figure generation, and article generation.
- `data/raw/`: place the authenticated IPUMS extract here. The microdata and download tokens are ignored by Git.
- `data/metadata/`: local DDI for verification, official historical occupation crosswalk, and the data audit. The DDI contains extract metadata and is ignored by Git.
- `results/`: tables, three PNG/SVG figures, PDF, quality checks, and SHA-256 output manifest.
- `PROVENANCE.md`: exact source, sample, variable, and correction decisions.
- `blog_post.qmd`: article generated from the current result tables; the website post is copied from this file.

## Data access

The data are **IPUMS CPS ASEC Extract 1**, request 3087417, made September 28, 2026. IPUMS requires an account to download microdata. Sign in at [IPUMS CPS](https://cps.ipums.org/cps/) and select ASEC survey years **1976–2025** (income years 1975–2024), CSV format, unadjusted nominal income, and no online person filtering. Include the following 30 fields:

`YEAR SERIAL MONTH CPSID ASECFLAG HFLAG ASECWTH CPI99 PERNUM CPSIDP CPSIDV ASECWT ASECWTCVD AGE OCCLY OCC10LY CLASSWLY WKSWORK1 UHRSWORKLY INCWAGE INCLONGJ OINCWAGE SRCEARN QINCLONG QINCLONGD QOINCWAGE QOINCWAGED QINCWAGE TINCLONGJ TOINCWAGE`

IPUMS may add required technical fields automatically. Put the downloaded CSV.GZ at `data/raw/cps_00001.csv.gz` and its matching DDI XML at `data/metadata/cps_00001.xml`. The verified local file has SHA-256 `1bda5f77809804052f18417b3eba80b55217d6b279362466f14ebfff1e43c291`. A fresh IPUMS extract may have a different hash or extract number but should reproduce the estimates after confirming sample and variable settings. The 2025 ASEC contains **2024 earnings**; monthly 2025 CPS files measure something different.

The original microdata are kept locally and excluded from Git. Results and code can be shared. Follow the applicable [IPUMS usage and citation guidance](https://cps.ipums.org/cps/cite.shtml) for any public repository.

## Reproduce

From the `blog3repo` folder, use Python 3.12 or later:

```sh
python3 -m pip install -r requirements.txt
python3 code/run_all.py --website-root ../myrepo1
```

Without a sibling website project, run `python3 code/run_all.py`. It will still generate `blog_post.qmd` in this project. The sequence regenerates all weighted tables, figures, independent audit, article, and file hashes. The audit fails if any of 1,844 checked cells disagree on population weights, counts, or medians, if a year is missing, or if an undocumented occupation code appears. Check `results/audit/independent_audit_summary.json` and `results/output_manifest.json` after a run.

The historical exception `OCC10LY=0400` is documented in the official crosswalk kept under `data/metadata/`; it belongs to Other. The 2014 ASEC main series uses the original 5/8 questionnaire, with the redesigned 3/8 questionnaire reported separately. See `PROVENANCE.md` for details.

To preview the website article locally, run the Quarto executable from the website project:

```sh
cd ../myrepo1
quarto render blog/posts/post3/index.qmd
```

Rendering the post locally does not publish it. The public Blog URL and GitHub repository URL should be added only after they actually exist and are verified.

## Core results

- `results/recent_earnings_2022_2024.csv`: nominal medians, 2024-dollar medians, counts, and weighted population.
- `results/pooled_age_2022_2024.csv`: eight age bands by four occupation groups.
- `results/median_premiums.csv`: annual Tech and Finance premiums over Other, 1975–2024.
- `results/figure1_recent_earnings.png`, `figure2_age_profiles.png`, `figure3_long_run_premiums.png`: the three article figures.
- `results/three_figures.pdf`: a standalone figure deck.
- `results/sample_flow.csv`, `results/quality_flags_and_topcodes.csv`, and `results/audit/`: supporting data-quality checks.

**Citation:** Sarah Flood, Miriam King, Renae Rodgers, Steven Ruggles, J. Robert Warren, Daniel Backman, Etienne Breton, Grace Cooper, Julia A. Rivera Drew, Stephanie Richards, David Van Riper, and Kari C. Williams. *IPUMS CPS: Version 13.0* [dataset]. Minneapolis, MN: IPUMS, 2025. https://doi.org/10.18128/D030.V13.0
