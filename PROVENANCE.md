# Data provenance and decisions

## Source chain

The local extract was requested from the authenticated IPUMS CPS site as ASEC Extract 1, request 3087417, on September 28, 2026. The official download supplied `cps_00001.csv.gz` and matching DDI XML. The source file's SHA-256 is recorded in the README and `results/run_manifest.json`. Its 30 columns match the DDI variables. The file contains 8,580,140 ASEC records from 50 survey years, with no duplicate `YEAR/SERIAL/PERNUM` keys. Source identity rests on the download page and matching metadata; the local checksum confirms file continuity, not an external signature.

Main variable definitions: [INCWAGE](https://cps.ipums.org/cps-action/variables/INCWAGE) is total prior-calendar-year wage and salary income; [OCC10LY](https://cps.ipums.org/cps-action/variables/OCC10LY) is the longest-held prior-year occupation harmonized to 2010 codes; [ASECWT](https://cps.ipums.org/cps-action/variables/ASECWT) is the ASEC person weight. [AGE](https://cps.ipums.org/cps-action/variables/AGE) is measured at survey. [CPI99](https://cps.ipums.org/cps-action/variables/CPI99) is used to express dollar levels in 2024 dollars. [UHRSWORKLY](https://cps.ipums.org/cps-action/variables/UHRSWORKLY), [WKSWORK1](https://cps.ipums.org/cps-action/variables/WKSWORK1), and [CLASSWLY](https://cps.ipums.org/cps-action/variables/CLASSWLY) define the employment sample.

## Population and weighting

Keep ages 25–64, 50–52 weeks, 35–99 usual weekly hours, wage/salary class codes 20/22/24/25/27/28, valid civilian occupation, positive INCWAGE, and positive ASECWT. `UHRSWORKLY=999` is a special code and is excluded. The 2014 ASEC main series uses `HFLAG=0` to avoid combining the two nationally representative questionnaire samples; `HFLAG=1` is a sensitivity check. The final main sample contains **2,191,970** person-year records.

Compute each group's weighted median at the first income whose cumulative ASECWT reaches half the group's weight. These are population descriptions for the defined employed subset. Pooled 2022–2024 age profiles adjust each person's nominal income to 2024 dollars and use ASECWT/3. Dividing all three years' weights by three changes the population scale, not the median. The long-run premium is `median(Tech or Finance) / median(Other) - 1` within each income year.

## Occupation coding

`code/occupation_codes.json` identifies all civilian occupation codes and the four mutually exclusive groups. Tech covers computing, software, information systems, and computer hardware. Finance is a moderate 12-code expansion; a narrower seven-code definition is retained as a sensitivity. Healthcare covers medical management and practitioner/technical jobs, including veterinarians. Other contains remaining identified civilian occupations. Military and NIU codes are excluded.

The original OCC10LY DDI category list omits `0400`, although 139 observations appear in ASEC 1992–1995, all with original `OCCLY=016`. The official [1992–2002 OCC2010 crosswalk](https://cps.ipums.org/cps/resources/occupation_and_industry/occ2010/cps_1992-2002-occ2010-xwalk.xlsx) names it **Postmasters and Mail Superintendents**. It is included in Other; 105 records satisfy all other main filters. This correction added 27, 26, 27, and 25 records to income years 1991–1994 and did not change any annual group median or long-run premium. The prior machine-readable category file also labeled military as Other while the analysis filter excluded military; both now agree on exclusion.

## Limitations

OCC10LY harmonization does not remove all cross-version occupation changes. INCWAGE includes wages from all employee jobs held that year, while occupation identifies the longest-held job. The age profile compares different people rather than following careers. Public high-income amounts underwent different topcoding, replacement, or swapping treatments over time. ASEC weights and the 2014 survey questionnaire also changed. The analysis does not estimate causal career returns or AI-specific pay and does not provide complex-survey confidence intervals. These are descriptive comparisons, consistent with the Blog 3 prompt's stated emphasis.
