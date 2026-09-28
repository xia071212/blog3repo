"""Independent audit: no import of the original estimation program."""
from pathlib import Path
import xml.etree.ElementTree as ET
import hashlib,json
import numpy as np
import pandas as pd

base=Path(__file__).resolve().parents[1];out=base/'results'/'audit';out.mkdir(parents=True,exist_ok=True)
r=ET.parse(base/'data/metadata/cps_00001.xml').getroot();ns={'d':r.tag.split('}')[0][1:]}
vs={v.attrib['name']:v for v in r.findall('.//d:var',ns)}
ddi_valid={int(e.find('d:catValu',ns).text) for e in vs['OCC10LY'].findall('d:catgry',ns)}
# 0400 is explicitly documented in the official 1992-2002 OCC2010 crosswalk,
# although the OCC10LY DDI categories omit it. All observed records have OCCLY=016.
valid=ddi_valid|{400}
tech={110,1005,1006,1007,1010,1020,1030,1050,1060,1105,1106,1107,1400}
finance={120,800,820,830,840,850,860,900,910,950,4810,4820}
health={350}|{c for c in valid if 3000<=c<=3540}
assert not (tech&finance or tech&health or finance&health)
assert (tech|finance|health)<=valid
meta=json.loads((base/'code/occupation_codes.json').read_text())
expected={c:('Excluded' if c>=9800 else 'Tech' if c in tech else 'Finance' if c in finance else 'Healthcare' if c in health else 'Other') for c in valid}
assert all(expected[row['code']]==row['group'] for row in meta['occupations'])
header=pd.read_csv(base/'data/raw/cps_00001.csv.gz',nrows=0).columns.tolist()
assert set(header)==set(vs)
cols=['YEAR','SERIAL','PERNUM','ASECFLAG','HFLAG','AGE','WKSWORK1','UHRSWORKLY','CLASSWLY','OCC10LY','ASECWT','INCWAGE','CPI99']
parts=[]; rawstats=[]; ids=[]; cpi={};badflags=0;outside=0;unknown=set()
for c in pd.read_csv(base/'data/raw/cps_00001.csv.gz',usecols=cols,chunksize=200000):
 assert c.SERIAL.max()<1000000 and c.PERNUM.max()<100
 ids.append((c.YEAR.to_numpy(np.int64)*100000000+c.SERIAL.to_numpy(np.int64)*100+c.PERNUM.to_numpy(np.int64)))
 badflags+=int(c.ASECFLAG.ne(1).sum());outside+=int((~c.YEAR.between(1976,2025)).sum())
 unknown|=set(c.OCC10LY.dropna().astype(int))-ddi_valid
 for y,g in c.groupby('YEAR'):
  v=set(g.CPI99);cpi.setdefault(int(y),set()).update(v)
  rawstats.append({'survey_year':int(y),'raw_n':len(g),'raw_weight_sum':g.ASECWT.sum(),'negative_weights':int(g.ASECWT.lt(0).sum()),'missing_weights':int(g.ASECWT.isna().sum()),'zero_weights':int(g.ASECWT.eq(0).sum())})
 ok=(c.ASECFLAG.eq(1)&c.YEAR.between(1976,2025)&(c.YEAR.ne(2014)|c.HFLAG.eq(0))&c.AGE.between(25,64)&c.WKSWORK1.between(50,52)&c.UHRSWORKLY.between(35,99)&c.CLASSWLY.isin([20,22,24,25,27,28])&c.OCC10LY.isin(valid)&c.OCC10LY.lt(9800)&c.ASECWT.gt(0)&np.isfinite(c.ASECWT)&c.INCWAGE.gt(0)&c.INCWAGE.lt(99999998))
 g=c.loc[ok,['YEAR','AGE','OCC10LY','ASECWT','INCWAGE','CPI99']].copy()
 g['group']=np.select([g.OCC10LY.isin(tech),g.OCC10LY.isin(finance),g.OCC10LY.isin(health)],['Tech','Finance','Healthcare'],default='Other')
 g['income_year']=g.YEAR-1;g['age_group']=((g.AGE//5)*5).astype(str)+'-'+((g.AGE//5)*5+4).astype(str)
 parts.append(g)
keys=np.concatenate(ids);duplicate_n=len(keys)-len(np.unique(keys));del ids,keys
d=pd.concat(parts,ignore_index=True);del parts
stats=pd.DataFrame(rawstats).groupby('survey_year').sum().reset_index();stats.to_csv(out/'raw_year_coverage_and_weights.csv',index=False)
assert duplicate_n==0 and badflags==0 and outside==0
assert set(stats.survey_year)==set(range(1976,2026))
assert unknown<={400}, 'Unresolved occupation codes beyond the documented historical 0400 exception'
assert all(len(v)==1 and min(v)>0 for v in cpi.values())
cp={y:next(iter(v)) for y,v in cpi.items()}
def median(g,value,weight):
 # Weighted empirical CDF on distinct dollar values, independently coded.
 a=g.groupby(value,sort=True)[weight].sum();return float(a.index[a.cumsum().ge(a.sum()/2)][0])
def verify(file,keys,data,value='INCWAGE',weight='ASECWT'):
 target=pd.read_csv(base/'results'/file);rows=[]
 for key,g in data.groupby(keys,observed=True):
  if not isinstance(key,tuple):key=(key,)
  est=median(g,value,weight);w=g[weight].sum()
  rows.append(dict(zip(keys,key))|{'audit_n':len(g),'audit_population':w,'audit_median':est,'unweighted_median':float(g[value].median()),'fraction_below_median':g.loc[g[value].lt(est),weight].sum()/w,'fraction_at_or_below_median':g.loc[g[value].le(est),weight].sum()/w})
 z=target.merge(pd.DataFrame(rows),on=keys,how='outer',validate='one_to_one')
 z['median_match']=np.isclose(z.weighted_median,z.audit_median,atol=1e-7,rtol=0,equal_nan=True)
 z['count_match']=z.n_unweighted.eq(z.audit_n.fillna(0))
 z['population_match']=np.isclose(z.weighted_population,z.audit_population,rtol=1e-12,atol=1e-6,equal_nan=True)
 assert z[['median_match','count_match','population_match']].all().all(),file
 present=z.audit_n.notna();assert (z.loc[present,'fraction_below_median']<.5+1e-12).all();assert (z.loc[present,'fraction_at_or_below_median']>=.5-1e-12).all()
 z.to_csv(out/('verified_'+file),index=False)
 return len(z)
n1=verify('annual_earnings.csv',['income_year','group'],d)
n2=verify('annual_age_earnings.csv',['income_year','group','age_group'],d)
rec=d[d.income_year.ge(2022)].copy();rec['earnings_real']=rec.INCWAGE*rec.CPI99/cp[2025];rec['pooled_weight']=rec.ASECWT/3
# Verify each boxplot quantile against an independently aggregated weighted CDF.
distribution=pd.read_csv(base/'results/recent_earnings_distribution_2022_2024.csv').set_index(['income_year','group'])
quantile_checks=0
for key,g in rec.groupby(['income_year','group'],observed=True):
 a=g.groupby('earnings_real',sort=True).ASECWT.sum();cdf=a.cumsum()/a.sum()
 for name,q in [('p10',.10),('p25',.25),('p50',.50),('p75',.75),('p90',.90)]:
  assert np.isclose(distribution.loc[key,name],float(cdf.index[cdf.ge(q)][0]),atol=1e-7,rtol=0)
  quantile_checks+=1
finance=rec[rec.group.eq('Finance') & rec.age_group.isin(['35-39','40-44','45-49'])]
age_rows=[];composition=[]
labels={r['code']:r['label'] for r in meta['occupations']}
for (year,age),g in finance.groupby(['income_year','age_group'],observed=True):
 age_rows.append({'income_year':year,'age_group':age,'n_unweighted':len(g),'weighted_median_2024_dollars':median(g,'earnings_real','ASECWT')})
for age,g in finance.groupby('age_group',observed=True):
 for code,cell in g.groupby('OCC10LY'):
  composition.append({'age_group':age,'occupation_code':code,'occupation':labels[code],'n_unweighted':len(cell),'weighted_share':cell.ASECWT.sum()/g.ASECWT.sum(),'weighted_median_2024_dollars':median(cell,'earnings_real','ASECWT')})
pd.DataFrame(age_rows).to_csv(out/'finance_age_by_year.csv',index=False)
pd.DataFrame(composition).to_csv(out/'finance_age_occupation_composition.csv',index=False)
(out/'boxplot_quantile_checks.json').write_text(json.dumps({'weighted_quantiles_verified':quantile_checks,'method':'Independent weighted empirical CDF on distinct earnings values','all_matched':True},indent=2))
n3=verify('pooled_age_2022_2024.csv',['group','age_group'],rec,'earnings_real','pooled_weight')
n4=verify('recent_earnings_2022_2024.csv',['income_year','group'],rec)
latest=pd.read_csv(out/'verified_recent_earnings_2022_2024.csv')
latest['real_check']=latest.weighted_median*(latest.income_year+1).map(cp)/cp[2025]
assert np.allclose(latest.real_check,latest.weighted_median_2024_dollars)
ann=pd.read_csv(base/'results/annual_earnings.csv');m=ann.pivot(index='income_year',columns='group',values='weighted_median')
pr=pd.read_csv(base/'results/median_premiums.csv').set_index('income_year')
assert np.allclose(pr[['Tech','Finance']],m[['Tech','Finance']].div(m.Other,axis=0)-1)
sumgroups=ann.groupby('income_year').weighted_population.sum();dsum=d.groupby('income_year').ASECWT.sum()
assert np.allclose(sumgroups,dsum)
pool=pd.read_csv(base/'results/pooled_age_2022_2024.csv');assert np.isclose(pool.weighted_population.sum(),sumgroups.loc[2022:2024].mean())
result={'source_header_matches_ddi_30_fields':len(header)==30,'raw_records':int(stats.raw_n.sum()),'retained_records':len(d),'duplicate_person_year_records':duplicate_n,'non_asec_rows':badflags,'out_of_range_year_rows':outside,'observed_occupation_codes_not_in_ddi':sorted(unknown),'verified_estimate_cells':n1+n2+n3+n4,'median_and_population_and_count_checks':'all matched','premium_checks':100,'cpi99_recent':{y:cp[y] for y in [2023,2024,2025]},'mean_annual_pooled_population':float(pool.weighted_population.sum()),'sha256_matches_prior':hashlib.file_digest(Path(base/'data/raw/cps_00001.csv.gz').open('rb'),'sha256').hexdigest()==json.loads((base/'results/run_manifest.json').read_text())['sha256']}
(out/'independent_audit_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));print(latest[latest.income_year.eq(2024)][['group','audit_n','audit_population','audit_median','unweighted_median']].to_string(index=False))
