"""Validate generated CSVs against key database and simplified business rules."""
import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'data/generated'
TABLES=['customers','accounts','transactions','loans','loan_disbursements','loan_repayments']
KEYS=['customer_id','account_id','transaction_id','loan_id','disbursement_id','repayment_id']

def check():
    errors=[]; data={}
    for table,key in zip(TABLES,KEYS):
        with (PATH/f'{table}.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        data[table]=rows
        values=[r[key] for r in rows]
        if len(values)!=len(set(values)): errors.append(f'{table}: duplicate primary key')
        if not all(values): errors.append(f'{table}: empty primary key')
    c={r['customer_id']:r for r in data['customers']}
    a={r['account_id']:r for r in data['accounts']}
    l={r['loan_id']:r for r in data['loans']}
    for r in data['accounts']:
        if r['customer_id'] not in c: errors.append('accounts: dangling customer_id')
        elif r['open_date']<c[r['customer_id']]['open_date']: errors.append('account opens before customer')
    for r in data['transactions']:
        if r['account_id'] not in a: errors.append('transactions: dangling account_id'); continue
        if Decimal(r['amount'])<=0: errors.append('invalid transaction amount')
        if datetime.fromisoformat(r['transaction_time']).date()<date.fromisoformat(a[r['account_id']]['open_date']): errors.append('transaction before account opening')
    for r in data['loans']:
        if r['customer_id'] not in c: errors.append('loans: dangling customer_id')
        elif r['contract_date']<c[r['customer_id']]['open_date']: errors.append('loan before customer')
        if Decimal(r['contract_amount'])<=0: errors.append('invalid loan amount')
    sums_d=defaultdict(Decimal); sums_p=defaultdict(Decimal); first_dis={}
    for r in data['loan_disbursements']:
        lid=r['loan_id']
        if lid not in l: errors.append('disbursements: dangling loan_id'); continue
        value=Decimal(r['disbursement_amount'])
        if value<=0: errors.append('invalid disbursement amount')
        d=datetime.fromisoformat(r['disbursement_time'])
        if d.date()<date.fromisoformat(l[lid]['contract_date']): errors.append('disbursement before contract')
        if r['disbursement_status']=='SUCCESS':
            sums_d[lid]+=value
            first_dis[lid]=min(d, first_dis.get(lid,d))
    for r in data['loan_repayments']:
        lid=r['loan_id']
        if lid not in l: errors.append('repayments: dangling loan_id'); continue
        p=Decimal(r['principal_amount']); interest=Decimal(r['interest_amount'])
        if p<0 or interest<0 or p+interest<=0: errors.append('invalid repayment amount')
        if r['repayment_status']=='SUCCESS':
            sums_p[lid]+=p
            if lid not in first_dis or datetime.fromisoformat(r['repayment_time'])<=first_dis[lid]: errors.append('repayment before successful disbursement')
    for lid,loan in l.items():
        if sums_d[lid]>Decimal(loan['contract_amount']): errors.append('disbursement exceeds contract')
        if sums_p[lid]>sums_d[lid]: errors.append('repaid principal exceeds disbursement')
        if loan['loan_status']=='PAID_OFF' and sums_p[lid]!=sums_d[lid]: errors.append('PAID_OFF principal imbalance')
    # Database CHECK enumerations
    enums={
        'customers': {'customer_type':{'INDIVIDUAL','BUSINESS'},'customer_status':{'ACTIVE','INACTIVE','CLOSED'}},
        'accounts': {'account_type':{'SAVINGS','CURRENT','CREDIT'},'account_status':{'ACTIVE','FROZEN','CLOSED'}},
        'transactions': {'transaction_type':{'DEPOSIT','WITHDRAWAL','TRANSFER'},'transaction_status':{'PENDING','SUCCESS','FAILED','CANCELLED','REVERSED'}},
        'loans': {'loan_status':{'PENDING','ACTIVE','PAID_OFF','CANCELLED'}},
        'loan_disbursements': {'disbursement_status':{'PENDING','SUCCESS','FAILED','CANCELLED'}},
        'loan_repayments': {'repayment_status':{'PENDING','SUCCESS','FAILED','CANCELLED'}}}
    for table,cols in enums.items():
        for row in data[table]:
            for field,allowed in cols.items():
                if row[field] not in allowed: errors.append(f'{table}: invalid {field}')
    report=['Bank source data validation', '===========================']
    report += [f'{table}: {len(data[table])} rows' for table in TABLES]
    report += [f'Status: {"FAIL" if errors else "PASS"}',f'Errors: {len(errors)}']
    report += errors[:100]
    (PATH/'validation_report.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('\n'.join(report))
    return not errors

if __name__=='__main__':
    raise SystemExit(0 if check() else 1)
