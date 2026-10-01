"""Tester oracle: direct workbook calculations, no retail_analysis imports.
Usage: python docs/evidence/tester_independent_check.py INPUT_XLSX OUTPUT_DIR
"""
import sys, math, json, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
src, out = Path(sys.argv[1]), Path(sys.argv[2])
def read(name): return pd.read_csv(out / name, keep_default_na=False, dtype=str)
def check(actual, expected, label):
    if pd.isna(expected): assert actual == '', (label,actual)
    else: assert abs(float(actual)-float(expected)) <= .005001, (label,actual,expected)
def pct(a,b): return 100*a/b if b else float('nan')
raw=pd.read_excel(src,dtype=object,keep_default_na=False,na_values=[''])
cols=['InvoiceNo','StockCode','Description','Quantity','InvoiceDate','UnitPrice','CustomerID','Country']
assert list(raw.columns)==cols
codes=set('POST DOT C2 23444 AMAZONFEE CRUK D B 22016 M m S'.split()) | {'BANK CHARGES'} | {f'gift_0001_{n}' for n in (10,20,30,40,50)}
def ident(x):
    if pd.isna(x): return ''
    if isinstance(x,(float,int)) and math.isfinite(x) and int(x)==x: return str(int(x))
    return str(x).strip()
f=raw.copy(); f['row']=f.index+2
f['code']=f.StockCode.map(ident); f['inv']=f.InvoiceNo.map(ident)
f['q']=pd.to_numeric(f.Quantity,errors='coerce'); f['p']=pd.to_numeric(f.UnitPrice,errors='coerce')
f['date']=pd.to_datetime(f.InvoiceDate,errors='coerce',format='mixed')
f['value']=f.q*f.p; f['cancel']=f.inv.str.upper().str.startswith('C')
f['customer']=f.CustomerID.map(ident);f['country']=f.Country.fillna('').astype(str).str.strip().replace('','Unknown')
f['month']=f.date.dt.strftime('%Y-%m');f['desc']=f.Description.fillna('').astype(str).str.strip()
finite=np.isfinite(f.q)&np.isfinite(f.p)
invalid=f.inv.eq('')|f.code.eq('')|f.date.isna()|~finite|f.q.mod(1).ne(0)
steps=[('exact_duplicates',raw.duplicated(cols)),('excluded_codes',f.code.isin(codes)),('invalid_required_fields',invalid),('negative_prices',f.p.lt(0)),('zero_prices',f.p.eq(0)),('zero_quantities',f.q.eq(0)),('inconsistent_c_positive_quantity',f.cancel&f.q.gt(0))]
audit=read('cleaning_summary.csv').set_index('step')
def audit_values(g):
    good=np.isfinite(g.q)&np.isfinite(g.p)
    return {'signed_value_positive_price_gbp':math.fsum(g.loc[good&g.p.gt(0),'value']), 'signed_value_nonpositive_price_gbp':math.fsum(g.loc[good&g.p.le(0),'value']), 'uncomputable_value_count':int((~good).sum())}
remaining=f
excluded=None
for name,mask in steps:
    removed=remaining.loc[mask.reindex(remaining.index)]
    after=remaining.drop(removed.index)
    for part,g in [('input',remaining),('removed',removed),('remaining',after)]:
        check(audit.loc[name,part+'_rows'],len(g),name+' rows')
        for k,v in audit_values(g).items(): check(audit.loc[name,part+'_'+k],v,name+' '+part+' '+k)
    if name=='excluded_codes': excluded=removed
    remaining=after
el=remaining
print('PASS ordered cleaning counts and all stage value audits:',len(raw),'raw;',len(el),'eligible')
x=read('excluded_entries.csv').set_index('StockCode')
assert set(x.index)==set(excluded.code)
for code,g in excluded.groupby('code'):
    row=x.loc[code]; assert row.basis=='post_deduplication'
    good=np.isfinite(g.q)&np.isfinite(g.p)
    vals={'row_count':len(g),'positive_price_row_count':sum(good&g.p.gt(0)),'zero_price_row_count':sum(good&g.p.eq(0)),'negative_price_row_count':sum(good&g.p.lt(0)),'invalid_numeric_row_count':sum(~good),**audit_values(g)}
    for k,v in vals.items():check(row[k],v,code+' '+k)
print('PASS excluded-code counts, price partitions and diagnostic values')
def totals(g):
    s=math.fsum(g.loc[g.q.gt(0),'value']);c=-math.fsum(g.loc[g.q.lt(0)&g.cancel,'value']);a=-math.fsum(g.loc[g.q.lt(0)&~g.cancel,'value'])
    return dict(positive_sales_gbp=s,cancellation_value_gbp=c,other_negative_value_gbp=a,net_value_gbp=s-c-a,cancellation_value_rate_pct=pct(c,s))
total=totals(el);overall=read('overall_summary.csv').iloc[0]
for k,v in total.items(): check(overall[k],v,k)
check(overall.eligible_row_count,len(el),'eligible')
for k,func in [('coverage_start','min'),('coverage_end','max')]: assert pd.Timestamp(overall[k])==getattr(el.date,func)()
for key,file,index in [('code','product_summary.csv','StockCode'),('country','country_summary.csv','Country'),('month','monthly_summary.csv','Month')]:
    expected=pd.DataFrame([dict(key=k,**totals(g)) for k,g in el.groupby(key)]).set_index('key')
    actual=read(file).set_index(index);assert set(actual.index)==set(expected.index)
    for k,g in el.groupby(key):
        for metric,v in totals(g).items():check(actual.loc[k,metric],v,file+' '+k+' '+metric)
        if key!='month':check(actual.loc[k,'sales_share_pct'],pct(expected.loc[k,'positive_sales_gbp'],total['positive_sales_gbp']),'share')
        if key=='month':
            assert actual.loc[k,'is_partial_month']==str(k=='2011-12')
            assert pd.Timestamp(actual.loc[k,'coverage_start'])==g.date.min()
            assert pd.Timestamp(actual.loc[k,'coverage_end'])==g.date.max()
        if key=='code':
            counts=g.loc[g.desc.ne(''),'desc'].value_counts()
            desc=sorted(counts[counts==counts.max()].index)[0] if len(counts) else k
            assert actual.loc[k,'Description']==desc
    if key=='code':
        for metric,rank in [('positive_sales_gbp','positive_sales_rank'),('net_value_gbp','net_value_rank')]:
            ranks=expected[metric].rank(method='min',ascending=False)
            for k,v in ranks.items():assert int(actual.loc[k,rank])==int(v),(k,rank)
        ordered=expected.reset_index().sort_values(['positive_sales_gbp','key'],ascending=[False,True])['key'].tolist()
        assert list(actual.index)==ordered
    print('PASS every row:',file,'including ranks/labels or monthly coverage where applicable')
pos=el.loc[el.q.gt(0)];known=pos.loc[pos.customer.ne('')]
cs=known.groupby('customer').value.agg(lambda s:math.fsum(s)).reset_index().sort_values(['value','customer'],ascending=[False,True])
actual=read('customer_summary.csv');assert actual.CustomerID.tolist()==cs.customer.tolist()
identified=math.fsum(cs.value);top=math.fsum(cs.value.head(10))
for i,(_,r) in enumerate(cs.iterrows()):
    check(actual.iloc[i].positive_sales_gbp,r.value,'customer sales')
    check(actual.iloc[i].share_of_identified_sales_pct,pct(r.value,identified),'customer share')
    assert actual.iloc[i].is_top_10==str(i<10)
    assert int(actual.iloc[i].display_order)==i+1
for k,v in dict(identified_positive_sales_gbp=identified,unidentified_positive_sales_gbp=math.fsum(pos.loc[pos.customer.eq(''),'value']),identified_sales_coverage_pct=pct(identified,total['positive_sales_gbp']),top_10_customer_sales_gbp=top,top_10_customer_concentration_pct=pct(top,identified),identified_positive_customer_count=len(cs)).items():check(overall[k],v,k)
print('PASS all customer rows, exact top ten and overall concentration/coverage')
before=f
for _,mask in steps[1:]:before=before.loc[~mask.reindex(before.index)]
bt=totals(before);dup=read('duplicate_comparison.csv').set_index('metric')
for k in dup.index:
    for col,v in dict(before_gbp=bt[k],after_gbp=total[k],change_gbp=total[k]-bt[k],percentage_change=pct(total[k]-bt[k],bt[k])).items():check(dup.loc[k,col],v,k+' '+col)
print('PASS same-population duplicate sensitivity')
large=el.assign(absvalue=el.value.abs()).sort_values(['absvalue','row'],ascending=[False,True]).head(10)
l=read('large_value_lines.csv');assert l.source_row.astype(int).tolist()==large.row.tolist()
for i,(_,r) in enumerate(large.iterrows()):
    for k,v in [('Quantity',r.q),('UnitPrice',r.p),('signed_value_gbp',r.value),('absolute_line_value_gbp',r.absvalue)]:check(l.iloc[i][k],v,k)
print('PASS largest-value line selection and values')
meta=json.loads((out/'run_metadata.json').read_text());assert meta['input_sha256']==hashlib.sha256(src.read_bytes()).hexdigest()
assert meta['input_filename']==src.name
assert set(meta['output_paths'])=={p.name for p in out.iterdir()}
assert len(list(out.glob('*.csv')))==9 and len(list(out.glob('*.png')))==4
assert all(Path(p).name==n and Path(p).parent.name==out.name for n,p in meta['output_paths'].items())
assert meta['python_version']=='3.13.14'
for k,v in {'pandas':'3.0.6','openpyxl':'3.1.5','matplotlib':'3.11.2','pytest':'9.1.1'}.items():assert meta['dependency_versions'][k]==v
assert meta['raw_profile']['rows']==len(raw)
assert meta['raw_profile']['exact_duplicates_beyond_first']==int(raw.duplicated(cols).sum())
for k in cols: assert meta['raw_profile']['missing_by_column'][k]==int(raw[k].isna().sum())
print('PASS file inventory, metadata hash, paths, versions and raw missing/duplicate counts')
print('Metadata timestamp:',meta['run_timestamp_utc'])
print('Overall:',total)
print('Identified sales:',identified,'Top ten:',top,'Concentration:',pct(top,identified))
print('ALL INDEPENDENT CHECKS PASSED')
