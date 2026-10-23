"""Generate six CSVs matching sql/001_schema.sql. No database credentials needed."""
import csv
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import yaml
from faker import Faker

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')
TABLES = ('customers','accounts','transactions','loans','loan_disbursements','loan_repayments')
COLUMNS = {
    'customers': ['customer_id','customer_name','customer_type','customer_status','open_date','created_at'],
    'accounts': ['account_id','customer_id','account_type','account_status','open_date','created_at'],
    'transactions': ['transaction_id','account_id','transaction_type','amount','transaction_status','transaction_time','created_at'],
    'loans': ['loan_id','customer_id','contract_amount','loan_status','contract_date','created_at'],
    'loan_disbursements': ['disbursement_id','loan_id','disbursement_amount','disbursement_status','disbursement_time','created_at'],
    'loan_repayments': ['repayment_id','loan_id','principal_amount','interest_amount','repayment_status','repayment_time','created_at'],
}

def money(v):
    return str(Decimal(str(v)).quantize(Decimal('0.01')))

def timestamp(d):
    return datetime.combine(d,time(12,0),tzinfo=TZ).isoformat()

def random_date(rng, start, end):
    return start + timedelta(days=int(rng.integers(0, (end-start).days+1)))

def generate():
    cfg = yaml.safe_load((ROOT/'config/generator.yaml').read_text(encoding='utf-8'))
    rng=np.random.default_rng(int(cfg['seed']))
    fake=Faker('zh_CN'); fake.seed_instance(int(cfg['seed']))
    start=date.fromisoformat(cfg['start_date']); end=date.fromisoformat(cfg['end_date'])
    if end <= start + timedelta(days=3):
        raise ValueError('日期范围至少需要 5 天')
    n=int(cfg['customers'])
    if n<1 or int(cfg['accounts_per_customer_min'])<1 or not (0<=float(cfg['loan_probability'])<=1):
        raise ValueError('客户数、每人账户数和贷款概率配置不合法')
    out={k:[] for k in TABLES}
    acc_id=tx_id=loan_id=dis_id=rep_id=0
    for customer_id in range(1,n+1):
        opened=random_date(rng,start,end-timedelta(days=3))
        customer_type=str(rng.choice(['INDIVIDUAL','BUSINESS'],p=[0.93,0.07]))
        customer_status=str(rng.choice(['ACTIVE','INACTIVE','CLOSED'],p=[0.88,0.09,0.03]))
        name=fake.name() if customer_type=='INDIVIDUAL' else fake.company()
        out['customers'].append([customer_id,name,customer_type,customer_status,opened.isoformat(),timestamp(opened)])
        n_acc=int(rng.integers(int(cfg['accounts_per_customer_min']),int(cfg['accounts_per_customer_max'])+1))
        for _ in range(n_acc):
            acc_id+=1
            acc_open=random_date(rng,opened,end-timedelta(days=1))
            acc_type=str(rng.choice(['SAVINGS','CURRENT','CREDIT'],p=[0.55,0.35,0.10]))
            acc_status=str(rng.choice(['ACTIVE','FROZEN','CLOSED'],p=[0.89,0.08,0.03]))
            out['accounts'].append([acc_id,customer_id,acc_type,acc_status,acc_open.isoformat(),timestamp(acc_open)])
            n_tx=int(rng.integers(int(cfg['transactions_per_account_min']),int(cfg['transactions_per_account_max'])+1))
            for _ in range(n_tx):
                tx_id+=1
                tx_date=random_date(rng,acc_open,end)
                typ=str(rng.choice(['DEPOSIT','WITHDRAWAL','TRANSFER'],p=[0.40,0.35,0.25]))
                status=str(rng.choice(['SUCCESS','PENDING','FAILED','CANCELLED','REVERSED'],p=[0.82,0.05,0.07,0.04,0.02]))
                amt=money(rng.integers(100,300001)/100)
                out['transactions'].append([tx_id,acc_id,typ,amt,status,timestamp(tx_date),timestamp(tx_date)])
        # Keep loan records internally consistent: every loan is disbursed and may be partially/fully repaid.
        if rng.random()<float(cfg['loan_probability']) and opened<=end-timedelta(days=3):
            loan_id+=1
            contract_date=random_date(rng,opened,end-timedelta(days=3))
            loan_total=Decimal(int(rng.integers(10,501))*1000)
            dis_date=contract_date+timedelta(days=1)
            dis_id+=1
            out['loan_disbursements'].append([dis_id,loan_id,money(loan_total),'SUCCESS',timestamp(dis_date),timestamp(dis_date)])
            rep_date=random_date(rng,dis_date+timedelta(days=1),end)
            fully_paid=bool(rng.random()<0.25)
            principal=loan_total if fully_paid else (loan_total*Decimal(str(round(float(rng.uniform(0.05,0.75)),2)))).quantize(Decimal('.01'))
            interest=(loan_total*Decimal('0.005')).quantize(Decimal('.01'))
            rep_id+=1
            out['loan_repayments'].append([rep_id,loan_id,money(principal),money(interest),'SUCCESS',timestamp(rep_date),timestamp(rep_date)])
            out['loans'].append([loan_id,customer_id,money(loan_total),'PAID_OFF' if fully_paid else 'ACTIVE',contract_date.isoformat(),timestamp(contract_date)])
    directory=ROOT/'data/generated'; directory.mkdir(parents=True,exist_ok=True)
    for table,rows in out.items():
        with (directory/f'{table}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.writer(f); writer.writerow(COLUMNS[table]); writer.writerows(rows)
        print(f'{table:20s} {len(rows):>7,d} rows')
    return out

if __name__=='__main__':
    generate()
