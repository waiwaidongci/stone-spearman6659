import {store} from '../../stores/research.js';
import {table} from './table.js';
import {status} from './status.js';
import {esc} from '../../utils/format.js';
export function matchList(){return table(['编号 / 配对运行','试验批 → 对照批','容差','快照','状态','配对'],store.matchRuns.map(r=>[{html:`<a href="#match/${r.id}">#${r.id} ${esc(r.name)}</a>`},r.test_study+' → '+r.control_study,r.tolerance,r.snapshot.test.length+'+'+r.snapshot.control.length+'条',{html:status(r.status)},r.status==='completed'?r.pair_count+' 对':(r.expected_pairs?`${r.pair_count}/${r.expected_pairs}`:'—')]));}
