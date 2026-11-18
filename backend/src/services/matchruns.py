import os,json,math
from pathlib import Path
from redis import Redis
from sqlalchemy import select,func
from fastapi import HTTPException
from src.models.matchrun import MatchRun,MatchPair
from src.models.study import Study
from src.services import studies
from src.services.matching import points,count_candidates,plan_pairs,summarize,MAX_EDGES
from src.services.audits import log
from src.utils.serializers import record,now,checksum

def _tolerance(v):
    if isinstance(v,bool): raise HTTPException(422,'容差必须是数值')
    try: t=float(v)
    except (TypeError,ValueError): raise HTTPException(422,'容差必须是数值')
    if not math.isfinite(t) or not 0<=t<=100: raise HTTPException(422,'容差须在0到100百分点之间')
    return t

def create(db,data,user):
    if data.test_study_id==data.control_study_id: raise HTTPException(422,'试验批与对照批不能相同')
    tol=_tolerance(data.tolerance)
    test=studies.require(db,data.test_study_id);control=studies.require(db,data.control_study_id)
    # 同一事务内读取两批观测：可重复读快照保证两批取自同一时点，并发改样不会混入本次运行
    test_rows=studies.observations(db,test.id);control_rows=studies.observations(db,control.id)
    if not test_rows or not control_rows: raise HTTPException(422,'两批都需先录入业务观测')
    try:
        t=points(test_rows);c=points(control_rows)
        if count_candidates(t,c,tol)>MAX_EDGES: raise ValueError('容差下候选配对超过50万条，请缩小容差')
    except ValueError as e: raise HTTPException(422,str(e))
    snapshot={'test':[{'source_key':x['source_key'],'values':x['values']} for x in test_rows],'control':[{'source_key':x['source_key'],'values':x['values']} for x in control_rows]}
    run=MatchRun(name=data.name,test_study_id=test.id,control_study_id=control.id,tolerance=tol,snapshot=snapshot,checksum=checksum(snapshot),status='queued',created_at=now())
    db.add(run);db.flush();log(db,user,'match.queue',str(run.id));db.commit()
    Redis.from_url(os.environ['REDIS_URL']).rpush('match-queue',run.id)
    return record(run)

def _names(db): return {s.id:s.name for s in db.scalars(select(Study))}

def get(db,id):
    run=db.get(MatchRun,id)
    if not run: raise HTTPException(404,'配对运行不存在')
    r=record(run);names=_names(db)
    r['test_study']=names.get(run.test_study_id,'');r['control_study']=names.get(run.control_study_id,'')
    r['pair_count']=db.scalar(select(func.count()).select_from(MatchPair).where(MatchPair.run_id==id))
    return r

def list_runs(db): return [get(db,x) for x in db.scalars(select(MatchRun.id).order_by(MatchRun.id.desc()))]

def pairs(db,id):
    if not db.get(MatchRun,id): raise HTTPException(404,'配对运行不存在')
    return [record(x) for x in db.scalars(select(MatchPair).where(MatchPair.run_id==id).order_by(MatchPair.pair_index))]

def _insert_ignore(db,rows):
    """幂等写入：唯一键冲突整行忽略，中断重试不会新增重复配对。"""
    if not rows: return
    if db.get_bind().dialect.name=='mysql':
        from sqlalchemy.dialects.mysql import insert
        db.execute(insert(MatchPair).prefix_with('IGNORE'),rows)
    else:
        from sqlalchemy.dialects.sqlite import insert
        db.execute(insert(MatchPair).on_conflict_do_nothing(),rows)

def execute(db,run):
    """worker 执行：重算确定性的配对，分块幂等写清单，写齐才 completed。"""
    if checksum(run.snapshot)!=run.checksum: raise ValueError('输入快照校验失败')
    t=points(run.snapshot['test']);c=points(run.snapshot['control'])
    found=plan_pairs(t,c,run.tolerance)
    run.expected_pairs=len(found)
    result=summarize(found,run.tolerance,len(t),len(c));result['input_sha256']=run.checksum
    run.result=result
    db.commit()  # 先落应有配对数与摘要；状态保持 running，清单写齐才 completed
    for start in range(0,len(found),500):
        _insert_ignore(db,[{'run_id':run.id,'pair_index':k,**p} for k,p in enumerate(found[start:start+500],start)])
        db.commit()  # 每块提交：中断留下部分进度；恢复时重算同一份配对，唯一键去重
    written=db.scalar(select(func.count()).select_from(MatchPair).where(MatchPair.run_id==run.id))
    if written!=run.expected_pairs: raise ValueError(f'配对清单未写齐 {written}/{run.expected_pairs}')
    run.status='completed'
    Path(f'/app/artifacts/match-{run.id}.json').write_text(json.dumps({'result':result,'pairs':found},ensure_ascii=False,allow_nan=False))
