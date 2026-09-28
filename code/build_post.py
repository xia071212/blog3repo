"""Build the Blog 3 Quarto post from checked result tables."""
from pathlib import Path
import argparse
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def dollars(value):
    return f"${value:,.0f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-root", type=Path)
    args = parser.parse_args()
    recent = pd.read_csv(RESULTS / "recent_earnings_2022_2024.csv")
    ages = pd.read_csv(RESULTS / "pooled_age_2022_2024.csv")
    prem = pd.read_csv(RESULTS / "median_premiums.csv").set_index("income_year")
    distribution = pd.read_csv(RESULTS / "recent_earnings_distribution_2022_2024.csv")
    audit = pd.read_json(RESULTS / "audit" / "independent_audit_summary.json", typ="series")
    current = recent[recent.income_year.eq(2024)].set_index("group")
    young = ages[ages.age_group.eq("25-29")].set_index("group")
    middle = ages[ages.age_group.eq("40-44")].set_index("group")
    older = ages[ages.age_group.eq("60-64")].set_index("group")
    late_forties = ages[ages.age_group.eq("45-49")].set_index("group")
    dist_2024 = distribution[distribution.income_year.eq(2024)].set_index("group")
    first = prem.loc[1975]
    last = prem.loc[2024]
    tech_2022 = recent[(recent.income_year.eq(2022)) & (recent.group.eq("Tech"))].iloc[0]
    finance_2022 = recent[(recent.income_year.eq(2022)) & (recent.group.eq("Finance"))].iloc[0]
    finance_2024 = current.loc["Finance"]
    r = lambda x: f"{x:.1f}%"
    count = int(audit["retained_records"])
    gap_1975 = (first['Tech']-first['Finance'])*100
    gap_2024 = (last['Tech']-last['Finance'])*100

    article = f'''---
title: "Tech Dominates the Forbes Rich List. Do Tech and Finance Careers Really Pay More?"
description: "A look at the typical worker's earnings across occupations, ages, and fifty income years."
author: "Yuting Xia"
date: 2026-09-28
date-format: "MMMM D, YYYY"
categories: [Labor Markets, Data Visualization, CPS]
image: /images/blog3/rich_list_editorial.png
image-alt: "Pastel Finance and Tech scenes with a Billionaires List in the center."
body-classes: blog3-post
toc: true
---

The [Forbes billionaires list](https://www.forbes.com/billionaires/) highlights extraordinary wealth associated with technology companies. Finance also has a reputation for high pay. But billionaire wealth comes largely from ownership, while most career decisions concern wages. **Do typical tech and finance workers earn more than people in other occupations? Is the advantage visible early in adulthood, and has it changed over time?**

![](/images/blog3/rich_list_editorial.png){{fig-alt="Pastel pink Finance scene on the left, blue Tech scene on the right, and a conceptual Billionaires List in the center."}}

## From the survey to the comparison

I use [IPUMS CPS](https://cps.ipums.org/cps/), drawing on the Annual Social and Economic Supplement (ASEC) from survey years 1976–2025. Each survey asks about income in the preceding calendar year, so the earnings series runs from **1975 to 2024**. The sample contains {count:,} person-year records after restricting to wage and salary workers ages 25–64 who usually worked at least 35 hours a week and at least 50 weeks in the previous year. A person appearing in multiple surveys contributes multiple records.

Earnings are annual pretax wages and salaries (`INCWAGE`). Occupations are based on the longest-held job in that income year (`OCC10LY`), harmonized to a 2010 classification. I group computing, software, information systems, and computer hardware jobs as **Tech**; financial management, accounting, analysis, advice, insurance, and related sales as **Finance**; healthcare management and clinical or technical jobs as **Healthcare**; and other identified civilian occupations as **Other**. Thus these are *occupations*, not employer industries. The Tech group captures many AI-related jobs but cannot identify every AI worker.

Each median uses the CPS ASEC person weight (`ASECWT`) to describe the represented population, rather than treating every survey respondent as equally representative. To compare dollar levels across years, I use IPUMS's CPI factor to express them in 2024 dollars. The three-year age chart pools observations after this adjustment and divides each person's weight by three.

## Which occupations pay more now?

For income earned in 2024, Tech's weighted median was **{dollars(current.loc['Tech','weighted_median'])}**, followed by **{dollars(current.loc['Finance','weighted_median'])}** in Finance, **{dollars(current.loc['Healthcare','weighted_median'])}** in Healthcare, and **{dollars(current.loc['Other','weighted_median'])}** in Other. The 2024 estimates use {int(current.loc['Tech','n_unweighted']):,} Tech and {int(current.loc['Finance','n_unweighted']):,} Finance sample records. The boxplots put 2022–2024 incomes on a common 2024-dollar scale.

![Weighted earnings distributions for four occupation groups in 2022–2024. Boxes show the 25th to 75th percentiles, center lines the medians, and whiskers the 10th to 90th percentiles.](/images/blog3/figure1_recent_earnings.png){{fig-alt="Grouped weighted boxplots for Tech, Finance, Healthcare, and Other in income years 2022, 2023, and 2024. All amounts in 2024 dollars."}}

Across all three years, the medians rank **Tech, Finance, Healthcare, then Other**. Tech stays near {dollars(current.loc['Tech','weighted_median'])}, while Finance rises each year from {dollars(finance_2022['weighted_median_2024_dollars'])} to {dollars(finance_2024['weighted_median'])}. Healthcare edges down; Other is roughly stable. Tech and Finance also have wider earnings distributions in dollar terms than Healthcare and Other, as shown by their larger interquartile ranges: in 2024, Tech's middle half runs from {dollars(dist_2024.loc['Tech','p25'])} to {dollars(dist_2024.loc['Tech','p75'])}, versus {dollars(dist_2024.loc['Other','p25'])} to {dollars(dist_2024.loc['Other','p75'])} for Other. Finance's 90th percentile slightly exceeds Tech's, despite its lower median; the distributions overlap.

## Is the gap present early?

Yes. Among respondents ages 25–29 in the pooled 2022–2024 data, Tech's median was **{dollars(young.loc['Tech','weighted_median'])}**, Finance's **{dollars(young.loc['Finance','weighted_median'])}**, and Other's **{dollars(young.loc['Other','weighted_median'])}** in 2024 dollars. Tech leads at every plotted age. The Tech–Finance gap is {dollars(young.loc['Tech','weighted_median']-young.loc['Finance','weighted_median'])} at 25–29, {dollars(middle.loc['Tech','weighted_median']-middle.loc['Finance','weighted_median'])} at 40–44, and {dollars(older.loc['Tech','weighted_median']-older.loc['Finance','weighted_median'])} at 60–64. After ages 45–49, the gap widens across each successive age group, from {dollars(late_forties.loc['Tech','weighted_median']-late_forties.loc['Finance','weighted_median'])} at 45–49 to {dollars(older.loc['Tech','weighted_median']-older.loc['Finance','weighted_median'])} at 60–64. Different job mixes and cohorts can help explain the uneven pattern.

![Median earnings by five-year age group, pooled over income years 2022–2024.](/images/blog3/figure2_age_profiles.png){{fig-alt="Four weighted age-earnings lines from ages 25–29 through 60–64; Tech is above Finance, Healthcare, and Other throughout."}}

The lines compare *different people* at different ages. They cannot show how one person's wages will grow. Education, occupation mix, cohort differences, and who remains in full-time work can also shape the curves.

## Has the advantage changed since the 1970s?

I measure each group's annual premium as its weighted median divided by the Other median, minus one. This same-year ratio avoids comparing nominal dollars across decades. In 1975, Tech's premium was **{r(first['Tech']*100)}** and Finance's **{r(first['Finance']*100)}**. By 2024 they were **{r(last['Tech']*100)}** and **{r(last['Finance']*100)}**. The gap between their premiums grew from **{gap_1975:.1f}** to **{gap_2024:.1f} percentage points**. It fluctuated along the way; it did not widen every year.

![Tech and Finance median earnings premiums relative to Other, income years 1975–2024.](/images/blog3/figure3_long_run_premiums.png){{fig-alt="Two annual premium lines: Tech rises from about 49 to 93 percent and Finance from about 27 to 63 percent, with fluctuations."}}

The earlier Tech samples are smaller, and changes in occupational coding, income disclosure rules, and CPS weights limit exact comparisons over fifty years. The 2013 income observation uses the original 5/8 questionnaire in the 2014 ASEC redesign. These descriptive differences do not isolate the effect of choosing a career, let alone the effect of AI.

## What should a career chooser take away?

**Tech and Finance workers in this full-time, full-year sample earn more at the median than the broad Other group, and the gap is already visible at ages 25–29.** Tech leads Finance in the recent data and throughout the age profile. Their relative advantages are larger than in the 1970s, but the pattern is uneven. These group medians do not predict what any one person will earn.

::: {{.source-note}}
**Source and replication.** [Flood et al., *IPUMS CPS: Version 13.0*](https://doi.org/10.18128/D030.V13.0), ASEC extract 1. See the [full replication guide](https://xia071212.github.io/blog3repo/replication-guide.html), [README](https://github.com/xia071212/blog3repo#readme), and analysis [repository](https://github.com/xia071212/blog3repo) for definitions, sample counts, code, and results. The authenticated CPS microdata are kept outside the public repository.
:::
'''
    target = ROOT / "blog_post.qmd"
    target.write_text(article)
    if args.website_root:
        site = args.website_root.resolve()
        post = site / "blog/posts/post3/index.qmd"
        image_dir = site / "images/blog3"
        post.parent.mkdir(parents=True, exist_ok=True)
        image_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, post)
        for name in ("figure1_recent_earnings.png", "figure2_age_profiles.png", "figure3_long_run_premiums.png"):
            shutil.copy2(RESULTS / name, image_dir / name)
        shutil.copy2(ROOT / "images/rich_list_editorial.png", image_dir / "rich_list_editorial.png")
    print(f"Built {target}")


if __name__ == "__main__":
    main()
