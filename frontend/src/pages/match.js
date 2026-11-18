import {store} from '../stores/research.js';
import {matchRuns} from '../api/research.js';
import {esc,fmt} from '../utils/format.js';
import {table} from '../components/common/table.js';
import {status} from '../components/common/status.js';
import {matchList} from '../components/common/match-list.js';
export async function render(id){if(!id)return `<div class="eyebrow">RESULTS ARCHIVE / MATCH</div><h1>配对结果档案</h1><p>选择一次配对运行查看逐对试件与吸水率差。</p>${matchList()}`;const r=await matchRuns.get(id);store.matchId=r.id;let body='';
if(r.status==='failed')body=`<div class="error">配对失败：${esc(r.error)}。请调整容差或修复数据后创建新运行。</div>`;
else if(r.status==='completed'){const pairs=await matchRuns.pairs(id);body=`<section class="result-intro"><strong>${esc(r.result.interpretation)}</strong><p>${esc(r.result.caveat)}</p></section><h2>核心数值</h2>${table(['业务指标','计算值'],Object.entries(r.result.metrics).map(([k,v])=>[k,fmt(v)]))}<h2>逐对结果 <small>${pairs.length} 对 · 吸水率差 = 试验批 − 对照批</small></h2>${pairs.length?table(['序号','试验试件','对照试件','试验孔隙率(%)','对照孔隙率(%)','孔隙率差','试验吸水率(%)','对照吸水率(%)','吸水率差'],pairs.map(p=>[p.pair_index+1,p.test_key,p.control_key,p.test_porosity,p.control_porosity,p.porosity_diff,p.test_absorption,p.control_absorption,p.absorption_diff])):'<p class="method-note">容差内无可配对试件。</p>'}`;}
else body=`<p class="method-note">配对任务正在队列中。此页每2秒更新，配对清单写齐后才显示完成。${r.expected_pairs?` 清单写入 ${r.pair_count}/${r.expected_pairs}。`:''}</p>`;
return `<div class="eyebrow">MATCH RESULT · RUN ${r.id}</div><h1>${esc(r.name)} ${status(r.status)}</h1><div class="checksum">INPUT SHA256 ${r.checksum}</div><p>试验批 ${esc(r.test_study)} → 对照批 ${esc(r.control_study)} · 容差 ${r.tolerance} 百分点 · 快照 ${r.snapshot.test.length}+${r.snapshot.control.length} 条 · ${esc(r.created_at)}</p>${body}<details><summary>本次冻结的容差与源记录</summary><pre>${esc(JSON.stringify({tolerance:r.tolerance,snapshot:r.snapshot},null,2))}</pre></details>`;}
export function bind(){}
