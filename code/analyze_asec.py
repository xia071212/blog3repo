"""IPUMS numeric CSV/CSV.GZ analysis. No microdata bundled. See 获取与核查报告.md.
Requires pandas and numpy. Outputs estimates only from supplied observations.
"""
from pathlib import Path
import argparse, hashlib, html, json
import numpy as np
import pandas as pd

GROUPS = ['Tech', 'Finance', 'Healthcare', 'Other']
AGES = [f'{a}-{a+4}' for a in range(25,65,5)]
COLORS = ['#2563eb','#d97706','#0f766e','#64748b']
REQUIRED = ['YEAR','SERIAL','PERNUM','ASECFLAG','AGE','ASECWT',
            'INCWAGE','OCC10LY','OCCLY','CLASSWLY','UHRSWORKLY','WKSWORK1','HFLAG','CPI99']

def weighted_median(values, weights):
    x, w = np.asarray(values, float), np.asarray(weights, float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x,w=x[ok],w[ok]
    if not len(x): return np.nan
    order=np.argsort(x,kind='stable'); x,w=x[order],w[order]
    return float(x[np.searchsorted(np.cumsum(w),w.sum()/2,side='left')])

def weighted_percentiles(values, weights, percentiles=(.10,.25,.50,.75,.90)):
    x, w = np.asarray(values,float), np.asarray(weights,float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x,w = x[ok],w[ok]
    if not len(x): return [np.nan]*len(percentiles)
    order=np.argsort(x,kind='stable'); x,w=x[order],w[order]
    cumulative=np.cumsum(w)
    return [float(x[np.searchsorted(cumulative,w.sum()*q,side='left')]) for q in percentiles]

def prepare(d, codebook, hflag=0, positive=True):
    d=d.copy()
    checks=[('ASEC_1976_2025',d.YEAR.between(1976,2025)&d.ASECFLAG.eq(1)),
            ('2014_one_questionnaire',d.YEAR.ne(2014)|d.HFLAG.eq(hflag)),
            ('age_25_64',d.AGE.between(25,64)),
            ('full_year_50_52',d.WKSWORK1.between(50,52)),
            ('full_time_35_99',d.UHRSWORKLY.between(35,99)),
            ('longest_job_wage_salary',d.CLASSWLY.isin([20,22,24,25,27,28])),
            ('known_civilian_occupation',d.OCC10LY.isin(codebook)&d.OCC10LY.lt(9800)),
            ('valid_positive_weight',np.isfinite(d.ASECWT)&d.ASECWT.gt(0)),
            ('valid_wage',np.isfinite(d.INCWAGE)&d.INCWAGE.ge(0)&d.INCWAGE.lt(99999998))]
    if positive: checks.append(('positive_wage',d.INCWAGE.gt(0)))
    mask=pd.Series(True,index=d.index); flow=[]
    for name,condition in checks:
        mask &= condition
        counts=d.loc[mask].groupby('YEAR').size()
        for y in range(1976,2026): flow.append({'survey_year':y,'stage':name,'n':int(counts.get(y,0))})
    d=d.loc[mask].copy()
    d['group']=d.OCC10LY.map(codebook)
    d['income_year']=d.YEAR-1
    d['age_group']=pd.cut(d.AGE,[25,30,35,40,45,50,55,60,65],right=False,labels=AGES)
    return d,pd.DataFrame(flow)

def summarize(d, keys, weight='ASECWT', value='INCWAGE'):
    rows=[]
    for labels,g in d.groupby(keys,observed=True,sort=True):
        if not isinstance(labels,tuple): labels=(labels,)
        w=g[weight].to_numpy(); n=len(g); neff=float(w.sum()**2/(w*w).sum())
        rows.append(dict(zip(keys,labels))|{'n_unweighted':n,'weighted_population':float(w.sum()),
          'weight_effective_n':neff,'weighted_median':weighted_median(g[value],w),
          'small_cell':n<100,'suppress_plot':n<30})
    return pd.DataFrame(rows)

def svg_chart(path, title, labels, series, ylabel, bars=False):
    # Standalone vector figure; missing/suppressed cells break lines.
    W,H=1050,560; L,R,T,B=95,25,95,90; pw,ph=W-L-R,H-T-B
    vals=[v for _,ys,_ in series for v in ys if np.isfinite(v)]
    if not vals: return
    low=min(0,min(vals)); high=max(vals)*1.13 if max(vals)>0 else 1
    def yy(v):return T+ph-(v-low)/(high-low)*ph
    def xx(i):return L+(i+.5)*pw/len(labels)
    e=lambda s:html.escape(str(s))
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<g font-family="Arial,sans-serif" fill="#172033">',
         f'<text x="{L}" y="32" font-size="22" font-weight="bold">{e(title)}</text>',
         f'<text x="{L}" y="55" font-size="13">{e(ylabel)}</text>']
    for k in range(6):
        v=low+(high-low)*k/5; y=yy(v)
        out += [f'<line x1="{L}" x2="{W-R}" y1="{y}" y2="{y}" stroke="#e2e8f0"/>',
                f'<text x="{L-10}" y="{y+4}" text-anchor="end" font-size="12">{v:,.0f}</text>']
    for i,label in enumerate(labels):
        if len(labels)<=10 or i%5==0 or i==len(labels)-1:
            out.append(f'<text x="{xx(i)}" y="{H-B+24}" text-anchor="middle" font-size="12">{e(label)}</text>')
    for j,(name,ys,color) in enumerate(series):
        out += [f'<rect x="{L+j*205}" y="70" width="12" height="12" fill="{color}"/>',
                f'<text x="{L+j*205+18}" y="81" font-size="12">{e(name)}</text>']
        segment=[]
        for i,v in enumerate(ys):
            if not np.isfinite(v):
                if segment: out.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
                segment=[]; continue
            if bars:
                bw=pw/len(labels)*.75/len(series); x=xx(i)-pw/len(labels)*.375+j*bw
                out.append(f'<rect x="{x}" y="{min(yy(v),yy(0))}" width="{bw-2}" height="{abs(yy(0)-yy(v))}" fill="{color}"/>')
            else:
                segment.append(f'{xx(i)},{yy(v)}')
        if segment: out.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
    out += [f'<text x="{L}" y="{H-30}" font-size="11">Source: IPUMS CPS ASEC. Ages 25-64; full-time, full-year wage/salary workers; positive wages.</text>',
            f'<text x="{L}" y="{H-13}" font-size="11">Weighted by ASECWT. Cells with n &lt; 30 omitted. Descriptive estimates; no causal interpretation.</text>','</g></svg>']
    path.write_text('\n'.join(out))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    meta=json.loads(Path(__file__).with_name('occupation_codes.json').read_text())
    codebook={r['code']:r['group'] for r in meta['occupations'] if r['group']!='Excluded'}
    cols=pd.read_csv(a.input,nrows=0).columns.tolist()
    missing=sorted(set(REQUIRED)-set(cols))
    if missing: raise ValueError(f'Missing required numeric columns: {missing}')
    use=REQUIRED+[x for x in ['MONTH','QINCWAGE','INCLONGJ','OINCWAGE','SRCEARN','CPSIDP','QINCLONG','QOINCWAGE','TINCLONGJ','TOINCWAGE','ASECWTCVD'] if x in cols]
    chunks=[]
    for c in pd.read_csv(a.input,usecols=use,chunksize=250000):
        for col in use:c[col]=pd.to_numeric(c[col],errors='raise')
        chunks.append(c.loc[c.YEAR.between(1976,2025)&c.ASECFLAG.eq(1)])
    raw=pd.concat(chunks,ignore_index=True)
    missing_years=sorted(set(range(1976,2026))-set(raw.YEAR.unique()))
    if missing_years:raise ValueError(f'Incomplete requested ASEC series: {missing_years}')
    if raw.duplicated(['YEAR','SERIAL','PERNUM']).any():raise ValueError('Duplicate ASEC person records: check overlapping extracts/sample versions.')
    if not raw.loc[raw.YEAR.eq(2014),'HFLAG'].isin([0,1]).all():raise ValueError('Invalid HFLAG in 2014.')
    deflator=raw.groupby('YEAR').CPI99.agg(['min','max'])
    if not ((deflator['min']>0)&np.isfinite(deflator['min'])&deflator['min'].eq(deflator['max'])).all():raise ValueError('CPI99 must be positive and constant within year.')
    d,flow=prepare(raw,codebook);flow.to_csv(a.out/'sample_flow.csv',index=False)
    annual=summarize(d,['income_year','group'])
    annual=annual.set_index(['income_year','group']).reindex(pd.MultiIndex.from_product([range(1975,2025),GROUPS],names=['income_year','group'])).reset_index()
    annual['n_unweighted']=annual.n_unweighted.fillna(0).astype(int)
    annual['suppress_plot']=annual.n_unweighted.lt(30);annual['small_cell']=annual.n_unweighted.lt(100)
    annual.to_csv(a.out/'annual_earnings.csv',index=False)
    narrow=d.copy()
    narrow.loc[narrow.group.eq('Finance') & ~narrow.OCC10LY.isin(meta['finance_narrow_codes']),'group']='Other'
    narrow_summary=summarize(narrow,['income_year','group'])
    narrow_summary.to_csv(a.out/'sensitivity_narrow_finance_annual.csv',index=False)
    narrow_med=narrow_summary.pivot(index='income_year',columns='group',values='weighted_median').reindex(columns=GROUPS)
    narrow_med[['Tech','Finance']].div(narrow_med.Other.where(narrow_med.Other.gt(0)),axis=0).sub(1).to_csv(a.out/'sensitivity_narrow_finance_premiums.csv')
    age=summarize(d,['income_year','group','age_group'])
    age=age.set_index(['income_year','group','age_group']).reindex(pd.MultiIndex.from_product([range(1975,2025),GROUPS,AGES],names=['income_year','group','age_group'])).reset_index()
    age['n_unweighted']=age.n_unweighted.fillna(0).astype(int)
    age['small_cell']=age.n_unweighted.lt(100);age['suppress_plot']=age.n_unweighted.lt(30)
    age.to_csv(a.out/'annual_age_earnings.csv',index=False)
    recent=d.loc[d.income_year.between(2022,2024)].copy()
    recent['earnings_2024']=recent.INCWAGE*recent.CPI99/deflator.loc[2025,'min']
    recent['pool_weight']=recent.ASECWT/3
    distribution=[]
    for (year,group), cell in recent.groupby(['income_year','group'],observed=True):
        q=weighted_percentiles(cell.earnings_2024,cell.ASECWT)
        distribution.append({'income_year':year,'group':group,'n_unweighted':len(cell),
                             'weighted_population':cell.ASECWT.sum(),
                             **dict(zip(['p10','p25','p50','p75','p90'],q))})
    pd.DataFrame(distribution).to_csv(a.out/'recent_earnings_distribution_2022_2024.csv',index=False)
    pooled=summarize(recent,['group','age_group'],'pool_weight','earnings_2024')
    pooled=pooled.set_index(['group','age_group']).reindex(pd.MultiIndex.from_product([GROUPS,AGES],names=['group','age_group'])).reset_index()
    pooled['n_unweighted']=pooled.n_unweighted.fillna(0).astype(int)
    pooled['suppress_plot']=pooled.n_unweighted.lt(30);pooled['small_cell']=pooled.n_unweighted.lt(100)
    pooled.to_csv(a.out/'pooled_age_2022_2024.csv',index=False)
    rec=annual.loc[annual.income_year.between(2022,2024)].copy()
    rec['weighted_median_2024_dollars']=rec.weighted_median*(rec.income_year+1).map(deflator['min'])/deflator.loc[2025,'min']
    rec.to_csv(a.out/'recent_earnings_2022_2024.csv',index=False)
    med=annual.pivot(index='income_year',columns='group',values='weighted_median')
    premium=med[['Tech','Finance']].div(med.Other.where(med.Other.gt(0)),axis=0).sub(1)
    premium.to_csv(a.out/'median_premiums.csv')
    count=d.groupby(['income_year','group','OCC10LY'],observed=True).agg(n=('ASECWT','size'),weighted_n=('ASECWT','sum')).reset_index()
    count['within_group_weight_share']=count.weighted_n/count.groupby(['income_year','group']).weighted_n.transform('sum')
    count.to_csv(a.out/'occupation_composition.csv',index=False)
    cross=d.groupby(['YEAR','OCCLY','OCC10LY'],observed=True).size().rename('n').reset_index()
    cross.to_csv(a.out/'observed_occupation_mapping.csv',index=False)
    for name,sub in [('2014_redesign',prepare(raw,codebook,hflag=1)[0].query('YEAR == 2014')),
                     ('include_zero_wages',prepare(raw,codebook,positive=False)[0])]:
        summarize(sub,['income_year','group']).to_csv(a.out/f'sensitivity_{name}.csv',index=False)
    if 'QINCWAGE' in d:
        d.groupby(['income_year','group','QINCWAGE'],observed=True,dropna=False).agg(n=('ASECWT','size'),weighted_n=('ASECWT','sum')).to_csv(a.out/'income_flag_distribution.csv')
    if {'INCLONGJ','SRCEARN'} <= set(d):
        alt=d.loc[d.YEAR.ge(1988)&d.SRCEARN.eq(1)&d.INCLONGJ.between(1,99999997)].copy()
        summarize(alt,['income_year','group'],value='INCLONGJ').to_csv(a.out/'sensitivity_longest_job_income.csv',index=False)
        summarize(alt,['income_year','group']).to_csv(a.out/'sensitivity_longest_job_matched_incwage.csv',index=False)
    for_table=rec.assign(plot_value=rec.weighted_median_2024_dollars.where(~rec.suppress_plot))
    p=for_table.pivot(index='group',columns='income_year',values='plot_value').reindex(GROUPS)
    svg_chart(a.out/'figure1_recent_earnings.svg','Median annual earnings by occupation',GROUPS,[(str(y),p[y].tolist(),c) for y,c in zip([2022,2023,2024],COLORS)],'2024 dollars; income years 2022-2024',True)
    p=pooled.assign(plot_value=pooled.weighted_median.where(~pooled.suppress_plot)).pivot(index='age_group',columns='group',values='plot_value').reindex(AGES)
    svg_chart(a.out/'figure2_age_profiles.svg','Earnings across age groups, 2022-2024 pooled',AGES,[(g,p[g].tolist(),c) for g,c in zip(GROUPS,COLORS)],'Median annual earnings, 2024 dollars; survey-time age')
    n=annual.pivot(index='income_year',columns='group',values='n_unweighted')
    svg_chart(a.out/'figure3_long_run_premiums.svg','Tech and Finance earnings relative to Other',list(premium.index),[(g,(100*premium[g]).where(n[g].ge(30)&n.Other.ge(30)).tolist(),c) for g,c in zip(['Tech','Finance'],COLORS)],'Median ratio minus one (%); income years; 2013 uses original 5/8 questionnaire')
    digest=hashlib.file_digest(a.input.open('rb'),'sha256').hexdigest()
    manifest={'input':a.input.name,'sha256':digest,'raw_asec_rows':len(raw),'analysis_rows':len(d),
      'survey_years':[1976,2025],'income_years':[1975,2024],'2014_main_hflag':0,
      'finance_definition':'12 codes; original 7-code definition exported as sensitivity, including redefined Other denominator',
      'pooled_weight':'ASECWT/3; population-weighted person-year mixture, not equal-year normalized',
      'limitations':['No survey-design confidence intervals','No person deduplication across years: repeated cross-sections',
      'Weight-effective n is not design-adjusted n','Topcode threshold exposure needs separate year-specific audit',
      'CPI99 must accompany unadjusted INCWAGE; do not double-adjust extract']}
    (a.out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
