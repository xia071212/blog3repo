from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR'] = str(ROOT / '.cache' / 'mplconfig')
(ROOT / '.cache' / 'mplconfig').mkdir(parents=True, exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,MultipleLocator
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import numpy as np
p=ROOT/'results';groups=['Tech','Finance','Healthcare','Other']
colors=['#2358a5','#bc6828','#228477','#7b8390']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'axes.labelcolor':'#374151','text.color':'#18283e','xtick.color':'#374151','ytick.color':'#374151','svg.fonttype':'none','pdf.fonttype':42})
def base(title,subtitle,ylabel):
 fig,ax=plt.subplots(figsize=(11.5,6.4));fig.subplots_adjust(left=.09,right=.95,top=.78,bottom=.2)
 fig.text(.09,.94,title,fontsize=20,weight='bold');fig.text(.09,.886,subtitle,fontsize=11)
 ax.set_ylabel(ylabel,labelpad=14);ax.set_axisbelow(True);ax.grid(axis='y',color='#e4e8ed');ax.tick_params(length=0,pad=8)
 fig.text(.09,.07,'Source: IPUMS CPS ASEC, extract 1. Ages 25–64, full-time/full-year wage and salary workers.',fontsize=9,color='#586575')
 fig.text(.09,.043,'Positive annual wages. Person weights: ASECWT. Occupation refers to the longest-held job in the previous year.',fontsize=9,color='#586575')
 return fig,ax
def save(fig,name,pdf):
 for ext in ['png','svg']:fig.savefig(p/(name+'.'+ext),dpi=180,facecolor='white')
 pdf.savefig(fig);plt.close(fig)
with PdfPages(p/'three_figures.pdf') as pdf:
 d=pd.read_csv(p/'recent_earnings_2022_2024.csv');fig,ax=base('Tech leads recent median annual earnings','Income years 2022–2024. All amounts expressed in 2024 dollars.','Weighted median annual earnings')
 x=np.arange(4);w=.23
 for j,(yr,c) in enumerate(zip([2022,2023,2024],['#b9cde8','#648cbd','#244e83'])):
  s=d[d.income_year.eq(yr)].set_index('group').loc[groups];v=s.weighted_median_2024_dollars
  bars=ax.bar(x+(j-1)*w,v,w-.025,label=str(yr),color=c)
  ax.bar_label(bars,labels=[f'{a/1000:.1f}k' for a in v],padding=4,fontsize=9)
 ax.set_xticks(x,groups);ax.set_ylim(0,135000);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'${v/1000:,.0f}k'));ax.legend(ncol=3,frameon=False,loc='upper right')
 save(fig,'figure1_recent_earnings',pdf)
 d=pd.read_csv(p/'pooled_age_2022_2024.csv');fig,ax=base('The earnings gap is already present at ages 25–29','Income years 2022–2024 pooled. Age groups compare different people, not individual career paths.','Weighted median annual earnings (2024 dollars)')
 ages=[f'{a}-{a+4}' for a in range(25,65,5)]
 for g,c in zip(groups,colors):
  s=d[d.group.eq(g)].set_index('age_group').loc[ages];ax.plot(range(8),s.weighted_median.where(~s.suppress_plot),label=g,color=c,lw=2.4,marker='o',ms=5)
 ax.set_xticks(range(8),[a.replace('-','–') for a in ages]);ax.set_xlabel('Age at survey');ax.set_ylim(0,140000);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'${v/1000:,.0f}k'));ax.legend(ncol=4,frameon=False,loc='lower center',bbox_to_anchor=(.5,1.01))
 save(fig,'figure2_age_profiles',pdf)
 d=pd.read_csv(p/'median_premiums.csv');fig,ax=base('Tech and Finance premiums are higher than in the 1970s','Unadjusted group comparisons. Premium = group median / Other median − 1.','Median earnings premium (%)')
 for g,c in zip(groups[:2],colors[:2]):
  ax.plot(d.income_year,100*d[g],label=g,color=c,lw=2.3)
  ax.annotate(f'{100*d[g].iloc[-1]:.1f}%',(2024,100*d[g].iloc[-1]),xytext=(6,0),textcoords='offset points',color=c,va='center',fontsize=10)
 ax.axvline(2013,color='#a9afb8',ls=':',lw=1);ax.text(2013.5,5,'2013 income:\noriginal 5/8 sample',fontsize=9,color='#687383')
 ax.set_xlim(1975,2028);ax.set_ylim(0,115);ax.set_xticks([1975,1980,1990,2000,2010,2020,2024]);ax.set_xlabel('Income year');ax.legend(ncol=2,frameon=False,loc='upper left')
 fig.text(.09,.105,'Harmonized occupations retain classification breaks. Income disclosure rules and population weights also change over time.',fontsize=9,color='#586575')
 save(fig,'figure3_long_run_premiums',pdf)
print('Saved three PNG/SVG charts and a three-page PDF.')
