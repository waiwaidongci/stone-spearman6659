"""孔隙率一维配对：稀疏候选边 + 不交叉最大权链。

业务规则：单件只配一次；|孔隙率差|≤容差；配对数最多；同配对数取孔隙率总差最小；同分不随读入顺序变。

为什么可以不建全量配对矩阵：在一维孔隙率轴上，若两对 (a,b)、(a',b') 交叉
（a<a' 而 b'<b），交换为 (a,b')、(a',b) 后由排序不等式总差不增，且由
a'≤b'+容差、a≥b-容差 可知两条新边仍在容差内——即必存在不交叉的最优配对。
不交叉配对一一对应候选边 (i,j) 在二维偏序（i 与 j 同时递增）下的链，
于是问题化为候选边集上的最大权链：扫描线 + 树状数组，O(E log n) 时间、O(E) 空间。
两批各三万件、每件最多八个候选时 E≤24万，无需 3万×3万 全量配对矩阵。

边权按 (配对数, -量化孔隙率总差, -边规范序号) 字典序：先最多配对，再最小总差，
最后按（孔隙率, 源记录编号）规范序定分——同一数据集无论读入顺序都得到同一份配对。
"""
import math
from bisect import bisect_left,bisect_right

SCALE=1_000_000  # 孔隙率差量化到 1e-6，整数目标保证结果可复现
MAX_EDGES=500_000  # 候选边上限；超出说明容差过大，创建运行时在事务外拒绝
_EPS=1e-9  # 二分窗口外扩量，远大于浮点误差，随后仍按精确差过滤

def points(rows):
    """从冻结快照提取 (源记录编号, 孔隙率, 吸水率) 并校验有限数值。"""
    out=[]
    for row in rows:
        values=row['values']
        if 'porosity' not in values or 'absorption' not in values: raise ValueError('观测字段不完整')
        try: p=float(values['porosity']);a=float(values['absorption'])
        except (TypeError,ValueError): raise ValueError('观测必须为数值')
        if not math.isfinite(p) or not math.isfinite(a): raise ValueError('观测必须为有限数值')
        out.append((str(row['source_key']),p,a))
    return out

def count_candidates(test,control,tol):
    """容差内候选边数的上界（二分计数，不实体化边）。"""
    cp=sorted(p for _,p,_ in control);total=0
    for _,p,_ in test:
        total+=bisect_right(cp,p+tol+_EPS)-bisect_left(cp,p-tol-_EPS)
    return total

def plan_pairs(test,control,tol):
    """返回规范序配对列表；test/control 为 points() 的输出。"""
    t=sorted(test,key=lambda x:(x[1],x[0]))  # 规范序：孔隙率升序，同值按源记录编号
    c=sorted(control,key=lambda x:(x[1],x[0]))
    cp=[x[1] for x in c]
    edges=[]  # (i, j, 量化差)，按 (i,j) 生成，边序号即规范秩
    for i in range(len(t)):
        p=t[i][1]
        for j in range(bisect_left(cp,p-tol-_EPS),bisect_right(cp,p+tol+_EPS)):
            d=abs(p-cp[j])
            if d<=tol: edges.append((i,j,int(round(d*SCALE))))
    if not edges: return []
    E=len(edges);INF=E+1;size=len(t)+1
    order=sorted(range(E),key=lambda e:(edges[e][1],edges[e][0]))  # 按对照列扫描，同列按试验序
    f1=[0]*size;f2=[0]*size;f3=[0]*size;f4=[-INF]*size  # 树状数组：前缀最优键 (w1,w2,w3,-边序)
    parent=[INF]*E
    gbest=(0,0,0,-INF);pending=[];last_j=-1
    def flush():  # 同列边先算完再统一更新，保证同一对照件不被同列复用
        for pos,key in pending:
            k=pos
            while k<size:
                if key>(f1[k],f2[k],f3[k],f4[k]): f1[k],f2[k],f3[k],f4[k]=key
                k+=k&-k
        pending.clear()
    for e in order:
        i,j,D=edges[e]
        if j!=last_j: flush();last_j=j
        best=(0,0,0,-INF);k=i  # 位置 i+1 对应试验序 i；前缀查询严格小于 i
        while k>0:
            node=(f1[k],f2[k],f3[k],f4[k])
            if node>best: best=node
            k-=k&-k
        key=(best[0]+1,best[1]-D,best[2]-e,-e)
        parent[e]=-best[3]
        pending.append((i+1,key))
        if key>gbest: gbest=key
    chain=[];e=-gbest[3]
    while e!=INF:
        chain.append(e);e=parent[e]
    chain.reverse()
    pairs=[]
    for e in chain:
        i,j,_=edges[e]
        tk,tp,ta=t[i];ck,cp_,ca=c[j]
        pairs.append({'test_key':tk,'control_key':ck,'test_porosity':tp,'control_porosity':cp_,'porosity_diff':round(abs(tp-cp_),6),'test_absorption':ta,'control_absorption':ca,'absorption_diff':round(ta-ca,6)})
    return pairs

def summarize(pairs,tol,test_n,control_n):
    """汇总配对结果为业务指标与解释；差异只支持后续假设，不解释为因果。"""
    k=len(pairs)
    tp=sum(p['porosity_diff'] for p in pairs)
    ta=sum(p['test_absorption'] for p in pairs);ca=sum(p['control_absorption'] for p in pairs)
    ad=sum(p['absorption_diff'] for p in pairs)
    metrics={'试验批试件数':test_n,'对照批试件数':control_n,'容差(百分点)':tol,'配对数':k,'孔隙率总差':round(tp,6)}
    if k: metrics|={'平均孔隙率差':round(tp/k,6),'试验批平均吸水率':round(ta/k,6),'对照批平均吸水率':round(ca/k,6),'平均吸水率差(试验-对照)':round(ad/k,6)}
    if k: interpretation=f"容差±{tol}内配成{k}对，已达最大配对数；孔隙率总差{tp:.6g}为同配对数下最小。试验批吸水率均值{ta/k:.4f}，对照批{ca/k:.4f}，平均差{ad/k:+.4f}个百分点。"
    else: interpretation='容差内无可配对试件，请放宽容差或核对两批孔隙率分布。'
    return {'metrics':metrics,'interpretation':interpretation,'caveat':'配对只按孔隙率对齐两批，未控制的混杂因素仍在；吸水率差只支持后续研究假设，不解释为因果。同分配对按(孔隙率,源记录编号)规范序确定，与读入顺序无关。'}
