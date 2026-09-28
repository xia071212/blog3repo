from pathlib import Path
import sys,json
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from analyze_asec import prepare,summarize
out=ROOT/'results'
meta=json.loads((ROOT/'code/occupation_codes.json').read_text())
codes={r['code']:r['group'] for r in meta['occupations'] if r['group']!='Excluded'}
parts=[]; coverage=[]
cols=['YEAR','ASECFLAG','HFLAG','AGE','WKSWORK1','UHRSWORKLY','CLASSWLY','OCC10LY','ASECWT','INCWAGE','CPI99','ASECWTCVD','QINCLONG','QOINCWAGE','TINCLONGJ','TOINCWAGE','INCLONGJ','OINCWAGE','SRCEARN']
for c in pd.read_csv(ROOT/'data/raw/cps_00001.csv.gz',usecols=cols,chunksize=250000):
 d,_=prepare(c,codes)
 parts.append(d)
d=pd.concat(parts,ignore_index=True)
rows=[]
for (year,group),g in d.groupby(['YEAR','group']):
 r={'income_year':year-1,'group':group,'n':len(g),'median':0}
 # Independent median check: aggregate weights by distinct income first.
 a=g.groupby('INCWAGE').ASECWT.sum().sort_index(); m=a.index[np.flatnonzero(a.cumsum().values>=a.sum()/2)[0]]
 r['median']=float(m)
 for col in ['QINCLONG','QOINCWAGE','TINCLONGJ','TOINCWAGE']:
  known=g[col].notna(); w=g.loc[known,'ASECWT']; r[col+'_known_n']=int(known.sum())
  r[col+'_nonzero_weight_share']=float(g.loc[known & g[col].gt(0),'ASECWT'].sum()/w.sum()) if w.sum()>0 else np.nan
 # Early directly topcoded INCWAGE; after 1987 use component flags separately.
 cap=50000 if year<=1981 else 75000 if year<=1984 else 99999 if year<=1987 else None
 if cap:
  r['direct_topcode']=cap;r['at_or_above_cap_weight_share']=g.loc[g.INCWAGE.ge(cap),'ASECWT'].sum()/g.ASECWT.sum();r['median_at_cap']=bool(m>=cap)
 rows.append(r)
qc=pd.DataFrame(rows);qc.to_csv(out/'quality_flags_and_topcodes.csv',index=False)
annual=pd.read_csv(out/'annual_earnings.csv')
test=annual.merge(qc,on=['income_year','group'],validate='one_to_one')
assert np.array_equal(test.weighted_median,test['median'])
assert np.array_equal(test.n_unweighted,test.n)
cv=d.loc[d.YEAR.between(2019,2021)&d.ASECWTCVD.gt(0)]
cvtab=summarize(cv,['income_year','group'],weight='ASECWTCVD');cvtab.to_csv(out/'sensitivity_covid_weights.csv',index=False)
recent=d.loc[d.YEAR.between(2023,2025)].copy()
recent['real']=recent.INCWAGE*recent.CPI99/d.loc[d.YEAR.eq(2025),'CPI99'].iloc[0]
recent['weight']=recent.ASECWT/3
pooled=summarize(recent,['group'],weight='weight',value='real');pooled.to_csv(out/'pooled_group_2022_2024.csv',index=False)
for flag in ['QINCLONG','QOINCWAGE','TINCLONGJ','TOINCWAGE']:
 d.groupby(['YEAR',flag],dropna=False).size().rename('n').to_csv(out/f'{flag}_coverage.csv')
checks={'independent_medians_verified':len(test),'independent_counts_verified':len(test),'raw_file_gzip_read_to_end':True,'early_topcode_medians_at_cap':int(qc.median_at_cap.fillna(False).sum()),'min_annual_group_n':int(annual.n_unweighted.min()),'pooled_age_min_n':int(pd.read_csv(out/'pooled_age_2022_2024.csv').n_unweighted.min()),'covid_weight_years':sorted(cv.YEAR.unique().tolist())}
(out/'quality_checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
