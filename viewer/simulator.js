'use strict';
const $=id=>document.getElementById(id), NS='http://www.w3.org/2000/svg';
const S={scenario:null,world:null,demand:null,tool:'select',selected:null,inspectorKey:null,draft:[],roadRedo:[],view:{x:0,y:0,w:4000,h:4000},dirty:false,saved:false,replay:null,runId:null,time:0,playing:false,timer:null,packet:null,linkFilter:null,eventFeed:null,drag:null,space:false,orbitPreview:null,orbitDirty:false,orbitRequest:0,orbitLoading:false,orbitError:'',mapMode:'empty',mapDrafts:{},routeTargetCar:null,routeTargetGroup:false,groupCars:[],groupPlanned:[],roadNetworkLoading:false,roadGraphVersion:0};
const extent=()=>S.world?.width_m||S.world?.extent_m||2000;
const height=()=>S.world?.height_m||S.world?.extent_m||2000;
function svg(tag,attrs={}){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;}
function fmt(n){return Number(n).toLocaleString('sk-SK',{maximumFractionDigits:1});}
function error(e){$('status').textContent=e.message||String(e);$('status').classList.add('error');}
function status(t){$('status').textContent=t;$('status').classList.remove('error');}
async function api(path,options={}){const r=await fetch(path,options);const x=await r.json();if(!r.ok)throw Error(x.reason||x.error||`HTTP ${r.status}`);return x;}
function post(path,body){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});}
function svgPoint(e){const map=$('groundMap'),m=map.getScreenCTM();if(!m)throw Error('Mapa ešte nemá rozmery.');const p=map.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(m.inverse());}
function worldPoint(e){const p=svgPoint(e);return {x:Math.max(0,Math.min(extent(),p.x)),y:Math.max(0,Math.min(height(),height()-p.y))};}
function unitsPerPixel(){const m=$('groundMap').getScreenCTM();return m?1/Math.hypot(m.a,m.b):S.view.w/Math.max(1,$('groundMap').clientWidth);}
function sy(y){return height()-y;}
function viewRatio(){const el=$('groundMap');return Math.max(0.1,el.clientWidth/Math.max(1,el.clientHeight));}
function fullView(){const ratio=viewRatio(),w=Math.max(extent(),height()*ratio),h=w/ratio;return {x:(extent()-w)/2,y:(height()-h)/2,w,h};}
function clampView(v){const full=fullView();v.w=Math.max(60,Math.min(full.w,v.w));v.h=v.w/viewRatio();v.x=v.w>=extent()?(extent()-v.w)/2:Math.max(0,Math.min(extent()-v.w,v.x));v.y=v.h>=height()?(height()-v.h)/2:Math.max(0,Math.min(height()-v.h,v.y));return v;}
function setView(){const v=S.view;$('groundMap').setAttribute('viewBox',`${v.x} ${v.y} ${v.w} ${v.h}`);let mpp=unitsPerPixel();let ideal=mpp*90;let pow=10**Math.floor(Math.log10(ideal));let n=[1,2,5,10].map(x=>x*pow).find(x=>x>=ideal)||10*pow;$('scale').querySelector('i').style.width=(n/mpp)+'px';$('scale').querySelector('b').textContent=`${fmt(n)} m`;$('zoomLabel').textContent=`${fmt(fullView().w/v.w)}×`;renderGrid();window.simulatorEarthSyncGround?.();}
function zoom(factor,anchor){const v=S.view,p=anchor?svgPoint(anchor):{x:v.x+v.w/2,y:v.y+v.h/2},px=(p.x-v.x)/v.w,py=(p.y-v.y)/v.h;let w=v.w*factor,h=w/viewRatio();v.x=p.x-px*w;v.y=p.y-py*h;v.w=w;v.h=h;clampView(v);setView();render();}
function fit(){const coords=[];if(!S.world)return;for(const n of S.world.roads.nodes)coords.push([n.x_m,sy(n.y_m)]);for(const r of S.world.rsus)coords.push([r.x_m,sy(r.y_m)]);if(!coords.length){S.view=fullView();setView();return;}let xs=coords.map(x=>x[0]),ys=coords.map(x=>x[1]);let a=Math.max(120,Math.max(...xs)-Math.min(...xs)+240),b=Math.max(120,Math.max(...ys)-Math.min(...ys)+240),ratio=viewRatio();let w=Math.max(a,b*ratio),h=w/ratio;let cx=(Math.max(...xs)+Math.min(...xs))/2,cy=(Math.max(...ys)+Math.min(...ys))/2;S.view=clampView({x:cx-w/2,y:cy-h/2,w,h});setView();render();}
function renderGrid(){const g=$('mapGrid');g.replaceChildren();if(!$('layerGrid').checked)return;let v=S.view,step=v.w<350?50:v.w<800?100:250;let x0=Math.floor(v.x/step)*step,y0=Math.floor(v.y/step)*step;for(let x=x0;x<=v.x+v.w;x+=step)g.append(svg('line',{x1:x,y1:v.y,x2:x,y2:v.y+v.h,stroke:x%500===0?'#29484e':'#1b343a','stroke-width':1,'vector-effect':'non-scaling-stroke'}));for(let y=y0;y<=v.y+v.h;y+=step)g.append(svg('line',{x1:v.x,y1:y,x2:v.x+v.w,y2:y,stroke:y%500===0?'#29484e':'#1b343a','stroke-width':1,'vector-effect':'non-scaling-stroke'}));}
function segment(id){return S.world.roads.segments.find(x=>x.id===id);}
function shapeLength(shape){let n=0;for(let i=1;i<shape.length;i++)n+=Math.hypot(shape[i][0]-shape[i-1][0],shape[i][1]-shape[i-1][1]);return n;}
function pointAt(shape,dist){for(let i=1;i<shape.length;i++){let a=shape[i-1],b=shape[i],d=Math.hypot(b[0]-a[0],b[1]-a[1]);if(dist<=d)return {x:a[0]+(b[0]-a[0])*dist/d,y:a[1]+(b[1]-a[1])*dist/d};dist-=d;}let x=shape.at(-1);return {x:x[0],y:x[1]};}
function carPosition(car){const first=car.route[0],road=segment(first.segment);if(!road)return null;const shape=first.direction==='reverse'?[...road.shape].reverse():road.shape;return pointAt(shape,car.depart_pos_m||0);}
function nearestRoad(p,onlyId=null){let best=null;for(const r of S.world.roads.segments){if(onlyId&&r.id!==onlyId)continue;let passed=0;for(let i=1;i<r.shape.length;i++){let a=r.shape[i-1],b=r.shape[i],dx=b[0]-a[0],dy=b[1]-a[1],len2=dx*dx+dy*dy,t=Math.max(0,Math.min(1,((p.x-a[0])*dx+(p.y-a[1])*dy)/len2));let x=a[0]+t*dx,y=a[1]+t*dy,d=Math.hypot(p.x-x,p.y-y);if(!best||d<best.d)best={road:r,d,at:passed+Math.sqrt(len2)*t};passed+=Math.sqrt(len2);}}return best;}
function entityAt(p){let radius=18*unitsPerPixel(),best=null;for(const r of S.world.rsus){let d=Math.hypot(p.x-r.x_m,p.y-r.y_m);if(d<radius&&(!best||d<best.d))best={type:'rsu',id:r.id,d};}for(const c of S.demand.vehicles){let q=replayCar(c.id)||carPosition(c);if(!q)continue;let d=Math.hypot(p.x-q.x,p.y-q.y);if(d<radius&&(!best||d<best.d))best={type:'car',id:c.id,d};}if(best)return best;const building=window.simulatorBuildings?.at(p);if(building)return {type:'building',id:building.id};let near=nearestRoad(p);return near&&near.d<Math.max(8,6*unitsPerPixel())?{type:'road',id:near.road.id}:null;}
function replayCar(id){if(!S.replay)return null;const points=S.replay.byCar?.get(id);if(!points?.length)return null;let lo=0,hi=points.length-1;while(lo<hi){let mid=(lo+hi+1)>>1;if(points[mid].time_us<=S.time)lo=mid;else hi=mid-1;}const a=points[lo],b=points[Math.min(lo+1,points.length-1)];if(a===b)return {x:a.x,y:a.y};const f=Math.max(0,Math.min(1,(S.time-a.time_us)/(b.time_us-a.time_us)));return {x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f};}
const LINK_COLORS={v2v:'#1769ff',v2r:'#00a65a',r2v:'#e02985',satellite:'#ff8500',isl:'#8651e5'};
function linkVisualKind(link){if(link.kind==='isl-model')return 'isl';const cars=S.replay?.byCar;if(link.kind==='its-g5')return cars?.has(link.from)?cars.has(link.to)?'v2v':'v2r':'r2v';return 'satellite';}
function linkKey(link){return `${link.from}\u0000${link.to}\u0000${link.kind}`;}
function activePacketLinks(){if(!S.replay||!$('layerPackets').checked)return [];const links=S.replay.packet_links||[];let lo=0,hi=links.length,start=S.time-250000,end=S.time+250000;while(lo<hi){let mid=(lo+hi)>>1;if(links[mid].time_us<start)lo=mid+1;else hi=mid;}const active=[];for(let i=lo;i<links.length&&links[i].time_us<=end;i++)active.push(links[i]);return active;}
function selectPacketLink(from,to,kind){S.linkFilter={from,to,kind};$('linkFilter').hidden=false;$('linkFilter').textContent=`${from} → ${to} · ${kind==='its-g5'?'ITS-G5':kind==='isl-model'?'ISL':'satelit'} · zrušiť filter`;render();resetPacketFeed();}
function groundPosition(id){const car=replayCar(id);if(car)return car;const rsu=S.world.rsus.find(r=>r.id===id);return rsu?{x:rsu.x_m,y:rsu.y_m}:null;}
function renderGroundPacketLinks(layer){const seen=new Set;let drawn=0;for(const link of activePacketLinks()){if(link.kind!=='its-g5')continue;const key=linkKey(link);if(seen.has(key))continue;seen.add(key);if(++drawn>100)break;const a=groundPosition(link.from),b=groundPosition(link.to);if(!a||!b)continue;const chosen=S.linkFilter&&key===linkKey(S.linkFilter),opacity=S.linkFilter&&!chosen?0.25:0.95;layer.append(svg('line',{x1:a.x,y1:sy(a.y),x2:b.x,y2:sy(b.y),stroke:'#13232b','stroke-width':chosen?8:7,'stroke-opacity':opacity,'vector-effect':'non-scaling-stroke','pointer-events':'none'}),svg('line',{x1:a.x,y1:sy(a.y),x2:b.x,y2:sy(b.y),stroke:chosen?'#fff0ab':LINK_COLORS[linkVisualKind(link)],'stroke-width':chosen?5:3.5,'stroke-opacity':opacity,'vector-effect':'non-scaling-stroke','pointer-events':'none'}),svg('line',{x1:a.x,y1:sy(a.y),x2:b.x,y2:sy(b.y),stroke:'transparent','stroke-width':16,'vector-effect':'non-scaling-stroke','pointer-events':'stroke','data-link-from':link.from,'data-link-to':link.to,'data-link-kind':link.kind}));}}
function markDirty(skipGlobalSync=false){clearPacketFeed();S.roadGraphVersion++;if(S.mapMode==='real'&&!skipGlobalSync)window.simulatorRealMapSyncActive?.();if(S.world&&S.scenario&&satelliteRequested()&&S.world.simulation.duration_s<6){S.world.simulation.duration_s=6;S.scenario.sample_count=60;S.orbitDirty=true;window.resetGlobeMotion?.();}S.replay=null;window.simulatorPhysicalAudit?.clear();S.packet=null;S.linkFilter=null;$('linkFilter').hidden=true;S.playing=false;$('play').textContent='▶';$('runStatus').textContent='Scenár zmenený. Spusti nový beh.';window.resetGlobeMotion?.(true);S.dirty=true;S.saved=false;renderDurationControls();status('Neuložené zmeny scenára.');render();}
function nextId(prefix,arr){let i=0,ids=new Set(arr.map(x=>x.id));if(S.mapMode==='real'){const kind={road:'roads',car:'cars',rsu:'rsus'}[prefix];for(const item of S.world?.map_objects?.[kind]||[])ids.add(item.id);}while(ids.has(prefix+i))i++;return prefix+i;}
function rebuildObjectPicker(){const picker=$('objectPicker'),current=S.selected?`${S.selected.type}:${S.selected.id}`:'';picker.replaceChildren(new Option('— vyber objekt —',''));for(const [title,type,items] of [['Autá','car',S.demand?.vehicles||[]],['RSU','rsu',S.world?.rsus||[]],['Cesty','road',S.world?.roads?.segments||[]],['Budovy','building',S.mapMode==='real'?(S.selected?.type==='building'?[window.simulatorBuildings?.find(S.selected.id)].filter(Boolean):[]):(window.simulatorBuildings?.list()||[])]]){const group=document.createElement('optgroup');group.label=`${title} (${items.length})`;for(const item of items){const label=type==='road'&&S.mapMode==='real'?`${item.name||item.road_class||'Cesta'} · ${item.id}`:item.id;group.append(new Option(label,`${type}:${item.id}`));}picker.append(group);}picker.value=current;}
function focusSelected(){if(!S.selected)return;let q=S.selected.type==='car'?replayCar(S.selected.id)||carPosition(S.demand.vehicles.find(x=>x.id===S.selected.id)):S.selected.type==='rsu'?S.world.rsus.find(x=>x.id===S.selected.id):S.selected.type==='building'?(()=>{const b=window.simulatorBuildings?.find(S.selected.id);return b?[(b.polygon_xy_m[0][0]+b.polygon_xy_m[2][0])/2,(b.polygon_xy_m[0][1]+b.polygon_xy_m[2][1])/2]:null;})():segment(S.selected.id)?.shape[0];if(!q)return;let x=Array.isArray(q)?q[0]:q.x??q.x_m,y=Array.isArray(q)?q[1]:q.y??q.y_m,v=S.view;v.x=clampView({...v,x:x-v.w/2,y:sy(y)-v.h/2}).x;v.y=clampView({...v,x:x-v.w/2,y:sy(y)-v.h/2}).y;setView();render();}
function removeRoadFromDraft(id){
 if(S.demand.vehicles.some(car=>car.route.some(step=>step.segment===id))){status('Cestu používajú autá; najprv zmeň ich trasu alebo ich odstráň.');return false;}
 const roads=S.world.roads;
 roads.segments=roads.segments.filter(road=>road.id!==id);
 if(roads.turn_rules)roads.turn_rules=roads.turn_rules.filter(rule=>!rule.from.startsWith(`${id}_`)&&!rule.to.startsWith(`${id}_`));
 const referenced=new Set(roads.segments.flatMap(road=>[road.from,road.to]));
 roads.nodes=roads.nodes.filter(node=>referenced.has(node.id));
 return true;
}
function addRoadPoint(p){if(S.draft.length&&Math.hypot(p.x-S.draft.at(-1).x,p.y-S.draft.at(-1).y)<1)return;S.roadRedo=[];S.draft.push(p);render();}
function undoRoadPoint(){if(!S.draft.length)return;S.roadRedo.push(S.draft.pop());render();}
function redoRoadPoint(){if(!S.roadRedo.length)return;S.draft.push(S.roadRedo.pop());render();}
function clearRoadDraft(){S.draft=[];S.roadRedo=[];render();}
function finishRoad(){if(S.draft.length<2)return status('Cesta potrebuje aspoň dva body.');let pts=S.draft.map(p=>[Math.round(p.x*10)/10,Math.round(p.y*10)/10]);let length=shapeLength(pts);if(length<30)return status('Cesta musí mať dĺžku aspoň 30 m.');if(pts.length>30)return status('Jeden úsek môže mať najviac 30 bodov.');let nodes=S.world.roads.nodes;function end(p){let old=nodes.find(n=>Math.hypot(n.x_m-p[0],n.y_m-p[1])<15);if(old){p[0]=old.x_m;p[1]=old.y_m;return old.id;}let id=nextId('node',nodes);nodes.push({id,x_m:p[0],y_m:p[1]});return id;}let from=end(pts[0]),to=end(pts.at(-1));if(from===to){status('Začiatok a koniec úseku musia byť rôzne uzly.');return;}if(shapeLength(pts)<30){status('Po prichytení uzlov musí mať cesta aspoň 30 m.');return;}S.world.roads.segments.push({id:nextId('road',S.world.roads.segments),from,to,shape:pts,speed_limit_mps:13.89,lanes_each_direction:1,lanes_forward:1,lanes_reverse:1,road_class:'urban'});S.draft=[];S.roadRedo=[];rebuildObjectPicker();markDirty();}
function addCar(p){let q=nearestRoad(p);if(!q||q.d>Math.max(35,S.view.w/20)){status('Auto umiestni na cestu.');return;}let id=nextId('car',S.demand.vehicles),at=Math.max(0,Math.min(shapeLength(q.road.shape)-20,q.at));S.demand.vehicles.push({id,depart_s:0,depart_speed_mps:10,max_speed_mps:S.mapMode==='real'?36.1:13.89,depart_speed_mode:S.mapMode==='real'?'max':'fixed',depart_pos_m:Math.floor(at*10)/10,route:[{segment:q.road.id,direction:'forward'}],technologies:['its_g5']});ensureNodePolicy().cars[id]={ground:'all'};if(!S.scenario.source_id){S.scenario.source_id=id;S.world.flows[0].source=id;}let routeError=null;try{if(S.mapMode==='real')window.simulatorRoutes?.randomWalk(id,true);}catch(e){routeError=e.message;}S.selected={type:'car',id};rebuildObjectPicker();markDirty();if(S.scenario.satellite&&satelliteRequested()&&!S.orbitPreview)refreshOrbits(true).catch(error);if(routeError)status(`Auto ${id} je vložené, ale ${routeError}`);}
function addRsu(p){let id=nextId('rsu',S.world.rsus);S.world.rsus.push({id,x_m:Math.round(p.x*10)/10,y_m:Math.round(p.y*10)/10,technologies:['its_g5','ip_backhaul']});ensureNodePolicy().rsus[id]={ground:true,satellite_backhaul:false};if(!S.scenario.rsu_id)S.scenario.rsu_id=id;if(!S.scenario.alert_target_rsu&&S.world.rsus.length>1)S.scenario.alert_target_rsu=id;S.selected={type:'rsu',id};rebuildObjectPicker();markDirty();if(S.scenario.satellite&&satelliteRequested())refreshOrbits(true).catch(error);}
function updateTool(tool){if(S.mapMode==='real'&&['road','building'].includes(tool))return status('V reálnom režime sú cesty v pracovnom výreze načítané automaticky.');S.tool=tool;for(const b of document.querySelectorAll('[data-tool]'))b.classList.toggle('active',b.dataset.tool===tool);$('roadActions').hidden=tool!=='road';const msg={select:S.mapMode==='real'?'Klikni na cestu, budovu, auto alebo RSU a zobraz parametre objektu. Mimo výrezu vyberieš nové miesto.':'Klikni na objekt a uprav jeho nastavenia. Koliesko približuje mapu.',road:'Klikaj na body cesty. Dokonči tlačidlom alebo dvojklikom. Konce sa pripnú k blízkym uzlom.',car:S.mapMode==='real'?'Klikni na zvýraznenú jazdnú cestu. Auto dostane náhodnú trasu; v jeho parametroch môžeš kliknutím určiť cieľ.':'Klikni na nakreslenú cestu a vlož auto.',rsu:'Klikni na miesto pre RSU. Každá RSU má vlastný terminál v satelitnom režime.',building:'Klikni na stred budovy. Šírku, dĺžku a výšku nastavíš v parametroch objektu.'};$('toolHelp').textContent=msg[tool];if(S.world)renderSumoInputs();}
function satelliteCount(){if(S.replay?.satellites?.length)return new Set(S.replay.satellites.map(row=>row.catalog_id)).size;return S.scenario?.satellite?.catalog_ids?.length||0;}
let roadRender={segments:null,count:-1,selected:'',mode:'',visible:false,version:-1};
function renderRoads(visible){
 const segments=S.world.roads.segments,selected=S.selected?.type==='road'?S.selected.id:'';
 if(roadRender.segments===segments&&roadRender.count===segments.length&&roadRender.selected===selected&&roadRender.mode===S.mapMode&&roadRender.visible===visible&&roadRender.version===S.roadGraphVersion)return;
 roadRender={segments,count:segments.length,selected,mode:S.mapMode,visible,version:S.roadGraphVersion};const layer=$('mapRoads');layer.replaceChildren();if(!visible)return;
 if(S.mapMode==='real'){
  const path=segments.map(r=>'M'+r.shape.map(([x,y])=>`${x},${sy(y)}`).join('L')).join('');
  for(const [stroke,width,opacity] of [['#103a42',6,.85],['#78d2c3',3,.95]])layer.append(svg('path',{d:path,fill:'none',stroke,'stroke-width':width,'stroke-opacity':opacity,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke','pointer-events':'none'}));
  const road=segments.find(r=>r.id===selected);
  if(road){const points=road.shape.map(([x,y])=>`${x},${sy(y)}`).join(' ');layer.append(svg('polyline',{points,fill:'none',stroke:'#17262a','stroke-width':12,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke','pointer-events':'none'}),svg('polyline',{points,fill:'none',stroke:'#ffe29a','stroke-width':7,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke','pointer-events':'none'}));}
 }else for(const r of segments){let points=r.shape.map(p=>`${p[0]},${sy(p[1])}`).join(' '),active=selected===r.id;layer.append(svg('polyline',{points,fill:'none',stroke:'#081619','stroke-width':active?15:13,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke'}),svg('polyline',{points,fill:'none',stroke:active?'#e1b969':'#597e79','stroke-width':active?9:7,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke'}));}
}
let sumoInputsKey='';
function renderSumoInputs(){
  const panel=document.querySelector('.sumo-inputs');
  panel.hidden=S.selected?.type!=='road'&&!(S.tool==='road'&&(!S.selected||S.draft.length>0));
  if(panel.hidden)return;
  const road=S.selected?.type==='road'?segment(S.selected.id):null,w=S.world;
  const key=`${S.roadGraphVersion}:${S.selected?.type||''}:${S.selected?.id||''}:${w.roads.segments.length}`;
  if(key===sumoInputsKey)return;sumoInputsKey=key;
  const list=$('sumoInputList');if(!list)return;list.replaceChildren();
  const row=(label,value)=>{const p=document.createElement('p'),strong=document.createElement('strong');strong.textContent=`${label}: `;p.append(strong,document.createTextNode(String(value)));list.append(p);};
  const nodes=new Map(w.roads.nodes.map(node=>[node.id,node])),edges=[],outgoing=new Map();
  for(const segment of w.roads.segments)for(const direction of (segment.oneway?['forward']:['forward','reverse'])){
    const forward=direction==='forward',edge={id:`${segment.id}_${direction}`,from:forward?segment.from:segment.to,to:forward?segment.to:segment.from,road:segment,direction};
    edges.push(edge);const list=outgoing.get(edge.from)||[];list.push(edge);outgoing.set(edge.from,list);
  }
  const denied=new Map();for(const rule of w.roads.turn_rules||[]){const set=denied.get(rule.from)||new Set();set.add(rule.to);denied.set(rule.from,set);}
  const explicit=[];for(const edge of edges){const blocked=denied.get(edge.id)||new Set();const allowed=(outgoing.get(edge.to)||[]).filter(next=>!blocked.has(next.id)&&!(next.road.id===edge.road.id&&next.direction!==edge.direction));if(allowed.length)for(const next of allowed)explicit.push({from:edge.id,to:next.id});else explicit.push({from:edge.id,to:''});}
  row('road.nod.xml',`${nodes.size} uzlov · X/Y v metroch`);
  row('road.edg.xml',`${edges.length} smerových hrán`);
  row('road.con.xml',`${explicit.length} záznamov spojení vrátane koncových hrán`);
  if(!road){row('Vybraný úsek','vyber cestu na zobrazenie jej presných vstupov');return;}
  for(const id of [road.from,road.to]){const node=nodes.get(id);if(node)row(`Uzol ${id}`,`x=${node.x_m} m, y=${node.y_m} m`);}
  const speed=mps=>`${String(mps)} m/s (≈ ${(Number(mps)*3.6).toFixed(3)} km/h)`;
  for(const edge of edges.filter(item=>item.road===road)){
    const shape=edge.direction==='forward'?road.shape:[...road.shape].reverse();
    row(`Hrana ${edge.id}`,`${edge.from} → ${edge.to}`);
    row(`Pruhy ${edge.id}`,road[`lanes_${edge.direction}`]??road.lanes_each_direction);
    row(`Limit ${edge.id}`,speed(road[`speed_${edge.direction}_mps`]??road.speed_limit_mps));
    row(`Tvar ${edge.id}`,shape.map(([x,y])=>`${x},${y}`).join(' '));
    const connections=explicit.filter(connection=>connection.from===edge.id);
    if(connections.length)row(`Spojenia z ${edge.id}`,connections.map(connection=>connection.to||'žiadny výjazd').join(' · '));
  }
}
function render(){if(!S.world)return;$('undoRoad').disabled=S.draft.length===0;$('redoRoad').disabled=S.roadRedo.length===0;if(!S.replay)$('physicalReplayStatus').hidden=true;let routeLayer=$('mapRoute'),entities=$('mapEntities'),coverage=$('mapCoverage'),draft=$('mapDraft'),packet=$('mapPackets');routeLayer.replaceChildren();entities.replaceChildren();coverage.replaceChildren();draft.replaceChildren();packet.replaceChildren();let layers={road:$('layerRoad').checked,car:$('layerCar').checked,rsu:$('layerRsu').checked,coverage:$('layerCoverage').checked,packet:$('layerPackets').checked};window.simulatorBuildings?.render();renderRoads(layers.road);
if(layers.road&&S.selected?.type==='car'){const car=S.demand.vehicles.find(x=>x.id===S.selected.id),shape=window.simulatorRoutes?.geometry(car)||[];if(shape.length>1){const points=shape.map(p=>`${p[0]},${sy(p[1])}`).join(' ');routeLayer.append(svg('polyline',{points,fill:'none',stroke:'#17262a','stroke-width':11,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke','pointer-events':'none'}),svg('polyline',{points,fill:'none',stroke:'#ffe29a','stroke-width':6,'stroke-linecap':'round','stroke-linejoin':'round','vector-effect':'non-scaling-stroke','pointer-events':'none'}));}}
if(layers.road)for(const id of S.groupPlanned){const car=S.demand.vehicles.find(x=>x.id===id),end=window.simulatorRoutes?.geometry(car).at(-1);if(end){const scale=unitsPerPixel();routeLayer.append(svg('circle',{cx:end[0],cy:sy(end[1]),r:7*scale,fill:'#f4d180',stroke:'#14282c','stroke-width':2,'vector-effect':'non-scaling-stroke','pointer-events':'none'}));}}
if(layers.coverage)for(const r of S.world.rsus){if(S.scenario.node_policy?.rsus[r.id]?.ground===false)continue;coverage.append(svg('circle',{cx:r.x_m,cy:sy(r.y_m),r:300,fill:'#56bdb218',stroke:'#60bcb9','stroke-dasharray':'7 8','stroke-width':1.4,'vector-effect':'non-scaling-stroke'}));}
if(layers.rsu)for(const r of S.world.rsus){let selected=S.selected?.type==='rsu'&&S.selected.id===r.id,scale=unitsPerPixel(),radioOff=S.scenario.node_policy?.rsus[r.id]?.ground===false;entities.append(svg('circle',{cx:r.x_m,cy:sy(r.y_m),r:(selected?10:8)*scale,fill:radioOff?'#334146':'#193c42',stroke:selected?'#f2cd84':radioOff?'#75888a':'#7cc8ba','stroke-width':selected?4:3,'vector-effect':'non-scaling-stroke'}),svg('circle',{cx:r.x_m,cy:sy(r.y_m),r:18*scale,class:'entity-hit','data-type':'rsu','data-id':r.id}));if(selected){let label=svg('text',{x:r.x_m+14*scale,y:sy(r.y_m)-11*scale,fill:'#b6ded5','font-size':14*scale,'font-weight':'700','pointer-events':'none'});label.textContent=r.id;entities.append(label);}}
if(layers.car)for(const c of S.demand.vehicles){let p=replayCar(c.id)||carPosition(c);if(!p)continue;let selected=S.selected?.type==='car'&&S.selected.id===c.id,grouped=S.groupCars.includes(c.id),scale=unitsPerPixel(),radioOff=S.scenario.node_policy?.cars[c.id]?.ground==='off';entities.append(svg('circle',{cx:p.x,cy:sy(p.y),r:(selected?10:7)*scale,fill:selected?'#f3c977':radioOff?'#857d72':'#e7b362',stroke:grouped?'#fff0b5':'#12252b','stroke-width':grouped?5:3,'vector-effect':'non-scaling-stroke'}),svg('circle',{cx:p.x,cy:sy(p.y),r:18*scale,class:'entity-hit','data-type':'car','data-id':c.id}));if(selected||grouped){const t=svg('text',{x:p.x+16*scale,y:sy(p.y)-10*scale,fill:'#f6db9a','font-size':14*scale,'font-weight':'700','pointer-events':'none'});t.textContent=c.id;entities.append(t);}}
if(S.draft.length){draft.append(svg('polyline',{points:S.draft.map(p=>`${p.x},${sy(p.y)}`).join(' '),fill:'none',stroke:'#e9bf77','stroke-width':3,'stroke-dasharray':'7 5','vector-effect':'non-scaling-stroke'}));for(const p of S.draft)draft.append(svg('circle',{cx:p.x,cy:sy(p.y),r:7,fill:'#e9bf77'}));}
if(layers.packet&&S.replay){renderGroundPacketLinks(packet);let pulses=0;for(const e of S.replay.events){if(Math.abs(e.time_us-S.time)>250000||(!S.packet&&e.stage==='CAM_UPER_RX')||(S.packet&&e.id!==S.packet))continue;if(++pulses>120)break;let p=replayCar(e.node)||S.world.rsus.find(r=>r.id===e.node);if(!p)continue;let x=p.x??p.x_m,y=p.y??p.y_m;packet.append(svg('circle',{cx:x,cy:sy(y),r:Math.max(15,S.view.w/70),fill:'none',stroke:e.id===S.packet?'#f9d58e':'#7bcac0','stroke-width':2,'vector-effect':'non-scaling-stroke'}));}}
$('counts').replaceChildren(...[[S.demand.vehicles.length,'áut'],[S.world.rsus.length,'RSU'],[satelliteCount(),'satelity']].map(([n,k])=>{let s=document.createElement('span');s.textContent=`${n} ${k}`;return s;}));renderInspector();renderSumoInputs();window.simulatorRoutes?.renderGroupControls();renderOrbit();window.simulatorPhysicalAudit?.draw(entities);window.simulatorPhysicalAudit?.render();}
function ensureNodePolicy(){if(!S.scenario.node_policy){S.scenario.node_policy={cars:Object.fromEntries(S.demand.vehicles.map(c=>[c.id,{ground:'all'}])),rsus:Object.fromEntries(S.world.rsus.map(r=>[r.id,{ground:true,satellite_backhaul:true}]))};S.scenario.schema_version=7;S.scenario.time_policy='ready_at_t0_full_duration';}return S.scenario.node_policy;}
function renderPerNodeControls(type,id,choose,box){let policy=S.scenario.node_policy;if(type==='car'){let value=policy?.cars[id]?.ground||'all';choose('Pozemné ITS-G5',value,[['all','Autá aj RSU'],['cars','Iba medzi autami'],['off','Vypnuté']],v=>{ensureNodePolicy().cars[id].ground=v;});}if(type==='rsu'){let setting=policy?.rsus[id],value=!setting||setting.ground&&setting.satellite_backhaul?'both':setting.ground?'ground':'off';choose('Komunikácia RSU',value,[['both','ITS-G5 + satelit'],['ground','Iba ITS-G5'],['off','Vypnutá']],v=>{let row=ensureNodePolicy().rsus[id];row.ground=v!=='off';row.satellite_backhaul=v==='both';if(!row.satellite_backhaul&&S.scenario.satellite?.terminal_mounts)delete S.scenario.satellite.terminal_mounts[id];S.inspectorKey=null;if(row.satellite_backhaul){S.orbitDirty=true;refreshOrbits(true).catch(error);}renderDurationControls();});let note=document.createElement('p');note.textContent='Každá RSU má vlastný satelitný terminál. Zdrojová a cieľová RSU DENM musia mať pozemnú aj satelitnú vrstvu zapnutú.';box.append(note);}}
function renderAntennaControls(type,id,field,choose,checkbox,box){
 const sat=S.scenario?.satellite;
 if(!sat||sat.orbit_group!=='starlink'||type!=='rsu')return;
 const enabled=!!S.scenario.node_policy?.rsus[id]?.satellite_backhaul;
 if(!enabled)return;
 const mounts=sat.terminal_mounts||{},mount=mounts[id];
 checkbox('Vlastný náklon a azimut antény Starlink FHP',!!mount,v=>{
  if(v){sat.terminal_mounts=mounts;mounts[id]={tilt_deg:8,azimuth_deg:0,frame:'north'};}
  else delete mounts[id];
  S.inspectorKey=null;
 });
 const note=document.createElement('p');note.textContent='Bez vlastnej montáže je anténa zvislá. Zorné pole terminálu sa modeluje v oboch prípadoch; náklon a azimut sú predpoklad scenára, aktívny lúč satelitu nepoznáme.';box.append(note);
 if(!mount)return;
 field('Náklon normály od zvislice · °',mount.tilt_deg,'number',v=>mount.tilt_deg=Math.max(0,Math.min(180,Number(v))));
 field('Azimut náklonu · °',mount.azimuth_deg,'number',v=>mount.azimuth_deg=((Number(v)%360)+360)%360);

}
function validateRoadPointEdit(road,shape){
  for(let i=1;i<shape.length;i++)if(Math.hypot(shape[i][0]-shape[i-1][0],shape[i][1]-shape[i-1][1])<1)throw Error(`${road.id}: susedné body musia byť vzdialené aspoň 1 m.`);
  const length=shapeLength(shape);
  if(length<2)throw Error(`${road.id}: cesta musí mať aspoň 2 m.`);
  for(const car of S.demand.vehicles){
    if(car.route[0]?.segment===road.id&&(car.depart_pos_m||0)>Math.max(0,length-20))throw Error(`${road.id}: ${car.id} má nástup za novým koncom cesty.`);
    if(car.route.at(-1)?.segment===road.id&&car.arrival_pos_m!==undefined&&car.arrival_pos_m>length)throw Error(`${road.id}: ${car.id} má cieľ za novým koncom cesty.`);
  }
}
function updateRoadPoint(road,index,axis,raw){
  if(S.mapMode==='real')throw Error('Súradnice ciest z reálnej mapy sa v pracovnom výreze neupravujú.');
  if(raw.trim()===''||!Number.isFinite(Number(raw)))throw Error('Zadaj číselnú súradnicu v metroch.');
  const value=Math.round(Number(raw)*10)/10,limit=axis===0?extent():height();
  if(value<0||value>limit)throw Error(`Súradnica musí byť od 0 do ${limit} m.`);
  const endpoint=index===0?road.from:index===road.shape.length-1?road.to:null;
  const affected=new Map();
  if(endpoint){
    for(const item of S.world.roads.segments){
      if(item.from!==endpoint&&item.to!==endpoint)continue;
      const shape=item.shape.map(point=>[...point]);
      if(item.from===endpoint)shape[0][axis]=value;
      if(item.to===endpoint)shape.at(-1)[axis]=value;
      affected.set(item,shape);
    }
  }else{
    const shape=road.shape.map(point=>[...point]);shape[index][axis]=value;affected.set(road,shape);
  }
  for(const [item,shape] of affected)validateRoadPointEdit(item,shape);
  if(endpoint){const node=S.world.roads.nodes.find(item=>item.id===endpoint);if(!node)throw Error(`Chýba uzol ${endpoint}.`);node[axis===0?'x_m':'y_m']=value;}
  for(const [item,shape] of affected)item.shape=shape;
  markDirty();
}
function renderRoadControls(road,box,choose){
  const meta=document.createElement('p');meta.className='road-meta';
  const updateMeta=()=>{meta.textContent=`${road.osm_way_id?`${road.name||'Nepomenovaná cesta'} · OSM way ${road.osm_way_id}`:'Ručne kreslená cesta'} · ${Math.round(shapeLength(road.shape))} m${road.road_class?` · trieda pre náhodnú dopravu: ${road.road_class}`:''}`;};
  updateMeta();box.append(meta);
  const sumoInfo=document.createElement('p');sumoInfo.className='road-sumo-info';
  const updateSumoInfo=()=>{sumoInfo.textContent=`Hrany SUMO: ${road.id}_forward${road.oneway?'':` a ${road.id}_reverse`}`;};
  updateSumoInfo();box.append(sumoInfo);
  if(S.mapMode!=='real'){
    choose('Klasifikácia cesty',road.road_class||'custom',[
      ['custom','Vlastná / bez klasifikácie'],['urban','Mestská cesta'],
      ['rural','Cesta mimo obce'],['motorway','Diaľnica'],['living_street','Obytná ulica']
    ],value=>{if(value==='custom')delete road.road_class;else road.road_class=value;updateMeta();});
    const classNote=document.createElement('p');classNote.className='road-class-note';
    classNote.textContent='Trieda ovplyvňuje výber cesty pri náhodnom generovaní áut. Limit nastav samostatne.';
    box.append(classNote);
  }
  const direction=document.createElement('label');direction.textContent='Povolený smer jazdy';
  const directionSelect=document.createElement('select');
  for(const [value,label] of [['both','Obojsmerná'],['forward','Jednosmerná · začiatok → koniec']])directionSelect.append(new Option(label,value));
  directionSelect.value=road.oneway?'forward':'both';
  directionSelect.onchange=()=>{
    if(directionSelect.value==='forward'){
      const reverse=S.demand.vehicles.find(car=>car.route.some(hop=>hop.segment===road.id&&hop.direction==='reverse'));
      if(reverse){directionSelect.value='both';return status(`Cesta ${road.id}: trasa auta ${reverse.id} používa opačný smer. Najprv uprav jeho trasu.`);}
    }
    road.oneway=directionSelect.value==='forward';
    if(road.oneway&&S.world.roads.turn_rules)S.world.roads.turn_rules=S.world.roads.turn_rules.filter(rule=>rule.from!==`${road.id}_reverse`&&rule.to!==`${road.id}_reverse`);
    updateLaneRows();
    updateSumoInfo();markDirty();
  };
  direction.append(directionSelect);box.append(direction);
  const speed=Math.round(road.speed_limit_mps*3.6*10)/10;
  const speeds=[3.6,...Array.from({length:28},(_,i)=>(i+1)*5),144];
  if(!speeds.includes(speed))speeds.push(speed);
  speeds.sort((a,b)=>a-b);
  choose('Rýchlostný limit · km/h',String(speed),speeds.map(value=>[String(value),`${value} km/h`]),value=>{road.speed_limit_mps=Number(value)/3.6;road.speed_forward_mps=road.speed_limit_mps;road.speed_reverse_mps=road.speed_limit_mps;road.speed_forward_source='manual';road.speed_reverse_source='manual';});
  const laneOptions=Array.from({length:6},(_,index)=>[index+1,String(index+1)]);
  choose('Pruhy · začiatok → koniec',road.lanes_forward??road.lanes_each_direction,laneOptions,value=>{
    road.lanes_forward=Number(value);
    road.lanes_each_direction=Math.min(3,road.lanes_forward);
    road.lanes_forward_source='manual';
  });
  const forwardLaneRow=box.lastElementChild;
  choose('Pruhy · koniec → začiatok',road.lanes_reverse??road.lanes_each_direction,laneOptions,value=>{
    road.lanes_reverse=Number(value);
    road.lanes_reverse_source='manual';
  });
  const reverseLaneRow=box.lastElementChild;
  function updateLaneRows(){
    forwardLaneRow.firstChild.textContent=road.oneway?'Pruhy v povolenom smere':'Pruhy · začiatok → koniec';
    reverseLaneRow.hidden=!!road.oneway;
  }
  updateLaneRows();
  const section=document.createElement('section');section.className='road-geometry';
  const heading=document.createElement('h4');heading.textContent='Body cesty · ID a súradnice';section.append(heading);
  const idNote=document.createElement('p');idNote.className='smallnote';idNote.textContent='Koncové body majú ID uzla; medzibody majú index v tvare cesty.';section.append(idNote);
  if(S.mapMode==='real'){const note=document.createElement('p');note.className='smallnote';note.textContent='Body načítanej OSM cesty sú v tomto výreze iba na zobrazenie.';section.append(note);}
  const list=document.createElement('div');list.className='road-point-list';list.setAttribute('aria-label',`Body cesty ${road.id}`);
  road.shape.forEach((point,index)=>{
    const row=document.createElement('div');row.className='road-point';
    const id=index===0?road.from:index===road.shape.length-1?road.to:`${road.id}[${index}]`;
    const title=document.createElement('strong');title.textContent=`${index===0?'Začiatok':index===road.shape.length-1?'Koniec':`Medzibod ${index}`} · ${id}`;row.append(title);
    const coords=document.createElement('div');coords.className='road-point-coords';
    for(const [axis,label] of [[0,'X · m'],[1,'Y · m']]){
      const field=document.createElement('label');field.textContent=label;
      const input=document.createElement('input');input.type='number';input.step='0.1';input.min='0';input.max=String(axis===0?extent():height());input.value=String(point[axis]);input.disabled=S.mapMode==='real';
      input.setAttribute('aria-label',`${id}, ${label}`);
      input.onchange=()=>{try{updateRoadPoint(road,index,axis,input.value);input.value=String(road.shape[index][axis]);updateMeta();}catch(e){input.value=String(road.shape[index][axis]);error(e);}};
      field.append(input);coords.append(field);
    }
    row.append(coords);list.append(row);
  });
  section.append(list);box.append(section);
}
function renderInspector(){let key=S.selected?`${S.selected.type}:${S.selected.id}`:'';if(S.inspectorKey===key)return;S.inspectorKey=key;$('objectPicker').value=key;let box=$('inspector');box.replaceChildren();if(!S.selected){let p=document.createElement('p');p.textContent='Vyber auto, RSU alebo cestu kliknutím na mape alebo podľa ID vyššie.';box.append(p);return;}let {type,id}=S.selected,entity=type==='car'?S.demand.vehicles.find(x=>x.id===id):type==='rsu'?S.world.rsus.find(x=>x.id===id):type==='building'?window.simulatorBuildings?.find(id):segment(id);if(!entity){S.selected=null;S.inspectorKey=null;renderInspector();return;}box.innerHTML=`<h3>${type==='car'?'Auto':type==='rsu'?'RSU':type==='building'?'Budova':'Cesta'} · ${id}</h3>`;if(type==='building'){window.simulatorBuildings.renderInspector(box,entity);return;}if(type==='rsu'&&window.simulatorRsuInputs){window.simulatorRsuInputs.render(box,entity);return;}if(type==='road'&&S.mapMode==='real')box.firstElementChild.textContent=`Cesta · ${entity.name||'bez názvu'}`;const rootBox=box;let carOther=null;if(type==='car'&&window.simulatorCarInputs){const panels=window.simulatorCarInputs.createTabs(rootBox);box=panels.sumo;carOther=panels.other;}function field(label,value,kind,change){let l=document.createElement('label');l.textContent=label;let input=document.createElement('input');input.type=kind;input.value=value;input.addEventListener('change',()=>{change(input.value);if(type==='rsu'&&S.scenario.satellite){S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;}markDirty();});l.append(input);box.append(l);}function choose(label,value,options,change){let l=document.createElement('label');l.textContent=label;let s=document.createElement('select');for(const [v,t] of options){let o=document.createElement('option');o.value=v;o.textContent=t;s.append(o);}s.value=value;s.onchange=()=>{change(s.value);markDirty();};l.append(s);box.append(l);}function checkbox(label,value,change){let l=document.createElement('label');l.className='check';let input=document.createElement('input');input.type='checkbox';input.checked=value;input.onchange=()=>{change(input.checked);if(type==='rsu'&&S.scenario.satellite){S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;}markDirty();};l.append(input,document.createTextNode(label));box.append(l);}if(type==='car'){if(window.simulatorCarInputs)window.simulatorCarInputs.renderSumo(entity,box);else{let p=document.createElement('p');p.textContent='Načítavam vstupy auta…';box.append(p);}box=carOther||rootBox;checkbox('Referenčné auto pre CAM',S.scenario.source_id===id,v=>{if(v){S.scenario.source_id=id;S.world.flows[0].source=id;}});let p=document.createElement('p');p.textContent=`Technológia: ${(entity.technologies||[]).join(', ')||'žiadna'}`;box.append(p);}if(type==='rsu'){field('X · m',entity.x_m,'number',v=>entity.x_m=Math.max(0,Math.min(extent(),Number(v))));field('Y · m',entity.y_m,'number',v=>entity.y_m=Math.max(0,Math.min(height(),Number(v))));let p=document.createElement('p');p.textContent='Pozemné rádio a satelitný backhaul nastav nižšie.';box.append(p);}renderPerNodeControls(type,id,choose,box);if(type==='car')window.simulatorCarInputs?.renderRadio(entity,box);renderAntennaControls(type,id,field,choose,checkbox,box);if(type==='car')renderCarDenmControls(id,box);if(type==='road')renderRoadControls(entity,box,choose);let del=document.createElement('button');del.className='subtle';del.textContent='Odstrániť';del.onclick=()=>{if(type==='car'){S.demand.vehicles=S.demand.vehicles.filter(x=>x.id!==id);S.scenario.denm_events=S.scenario.denm_events.filter(event=>event.source_id!==id);if(S.routeTargetCar===id)S.routeTargetCar=null;S.groupCars=S.groupCars.filter(x=>x!==id);S.groupPlanned=S.groupPlanned.filter(x=>x!==id);if(S.scenario.node_policy)delete S.scenario.node_policy.cars[id];if(S.scenario.source_id===id){S.scenario.source_id=S.demand.vehicles[0]?.id||'';if(S.world.flows?.[0])S.world.flows[0].source=S.scenario.source_id;}}else if(type==='rsu'){S.world.rsus=S.world.rsus.filter(x=>x.id!==id);if(S.scenario.node_policy)delete S.scenario.node_policy.rsus[id];if(S.scenario.rsu_id===id)S.scenario.rsu_id=S.world.rsus[0]?.id||'';if(S.scenario.alert_target_rsu===id)S.scenario.alert_target_rsu=S.world.rsus.find(x=>x.id!==S.scenario.rsu_id)?.id||'';}else{if(!removeRoadFromDraft(id))return;}if(['car','rsu'].includes(type)&&S.scenario.satellite?.terminal_mounts)delete S.scenario.satellite.terminal_mounts[id];if(type==='rsu'&&S.scenario.satellite){S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;}S.selected=null;S.inspectorKey=null;rebuildObjectPicker();markDirty();};(type==='car'?rootBox:box).append(del);}
function renderCatalog(){window.renderGlobe?.();}
function orbitControls(){$('constellation').disabled=false;}
let orbitSnapshots=[];
async function loadOrbitSnapshots(){orbitSnapshots=(await api('/api/simulator/orbit-snapshots')).snapshots;syncOrbitSnapshotPicker();}
function syncOrbitSnapshotPicker(){const picker=$('orbitSnapshot');if(!picker)return;picker.replaceChildren();const pin=S.scenario?.satellite?.orbit_snapshot;const old=document.createElement('option');old.value='legacy';old.textContent='Pôvodný archív scenára';picker.append(old);for(const entry of orbitSnapshots){const option=document.createElement('option');option.value=entry.path;option.textContent=`${entry.fetched_utc.slice(0,19).replace('T',' ')} UTC · ${entry.provider} · ${entry.manifest_sha256.slice(0,10)}`;picker.append(option);}if(pin&&!orbitSnapshots.some(x=>x.path===pin.path)){const option=document.createElement('option');option.value=pin.path;option.textContent=`Chýbajúci archív · ${pin.path}`;picker.append(option);}picker.value=pin?.path||'legacy';}
$('orbitSnapshot').onchange=()=>{try{if(!S.scenario?.satellite)throw Error('Najprv načítaj scenár.');const entry=orbitSnapshots.find(x=>x.path===$('orbitSnapshot').value);if(!entry)throw Error('Vyber overený orbitálny archív.');S.scenario.satellite.orbit_snapshot={path:entry.path,manifest_sha256:entry.manifest_sha256};const start=Date.parse(entry.fetched_utc);S.scenario.utc_origin=new Date(start-(S.scenario.schema_version<7?10000:0)).toISOString().replace(/\.\d{3}Z$/,'Z');S.orbitPreview=null;S.orbitDirty=true;S.orbitRequest++;markDirty();window.syncGlobeStart?.();$('orbitSelectionInfo').textContent='Nový archív a UTC sú pripnuté k scenáru; prepočítavam družice.';if(S.world.rsus.length||S.demand.vehicles.length)refreshOrbits(true).catch(error);else window.previewGlobeConstellation?.().catch(error);}catch(e){error(e);syncOrbitSnapshotPicker();}};

async function refreshOrbits(apply){
 if(!S.scenario?.satellite)return;
 if(!S.world.rsus.length&&!S.demand.vehicles.length){window.previewGlobeConstellation?.().catch(error);return;}
 syncSatelliteEndpoints();
 const group=$('constellation').value;
 const request=++S.orbitRequest;
 S.orbitLoading=true;S.orbitError='';
 $('orbitSelectionInfo').textContent='Načítavam konšteláciu a vyhodnocujem celý archivovaný katalóg…';
 renderOrbit();
 try{
  const p=await post('/api/simulator/editor/orbits',{group,scenario:S.scenario,world:S.world});
  if(request!==S.orbitRequest)return;
  S.orbitPreview=p;S.orbitLoading=false;renderCatalog();
  if(apply){S.scenario.satellite.catalog_ids=[];S.scenario.satellite.isls=[];S.scenario.satellite.initial_serving_sat=0;S.scenario.satellite.handover_target_sat=0;S.scenario.satellite.feeder_sat=0;if(S.scenario.link_policy&&!S.scenario.link_policy_override){S.scenario.link_policy.rf_hz=p.physical_profile.user_uplink_hz;S.scenario.link_policy.zenith_cone_deg=Math.min(90-p.physical_profile.minimum_elevation_deg,p.physical_profile.terminal_zenith_limit_deg);S.scenario.link_policy.beam_half_angle_deg=group==='starlink'?5:90;}S.orbitDirty=false;markDirty();}
  renderOrbit();
  $('orbitSelectionInfo').textContent=`${p.site_physical_count_at_start} fyzikálnych kandidátov · ${p.site_visible_count} nad maskou · ${p.eligible_count} družíc v archíve.`;
 }catch(e){
  if(request===S.orbitRequest){S.orbitLoading=false;S.orbitError=`Konštelácia sa nenačítala: ${e.message||e}`;$('orbitSelectionInfo').textContent=S.orbitError;renderOrbit();}
  throw e;
 }
}
function renderOrbit(){window.renderGlobe?.();}
function loadMapConstellation(){
 if(!S.scenario?.satellite)return;
 if(S.world.rsus.length||S.demand.vehicles.length)refreshOrbits(false).catch(error);
 else window.previewGlobeConstellation?.().catch(error);
}
function durationLimits(){return [satelliteRequested()?6:2,120];}
function renderDenmControls(){
 if(!S.scenario)return;const box=$('denmRows');box.replaceChildren();
 const active=(S.world?.rsus||[]).filter(r=>S.scenario.node_policy?.rsus[r.id]?.satellite_backhaul).map(r=>r.id);
 if(active.length){
  for(const [key,label,choices] of [
   ['rsu_id','Zdrojová RSU pre satelitný prenos',active],
   ['alert_target_rsu','Cieľová RSU po satelitnom prenose',active.filter(id=>id!==S.scenario.rsu_id)]]){
   const wrap=document.createElement('label');wrap.textContent=label;
   const input=document.createElement('select');
   if(key==='alert_target_rsu'&&!choices.length)input.append(new Option('Žiadna ďalšia RSU',''));
   for(const id of choices)input.append(new Option(id,id));
   input.value=S.scenario[key]||'';
   input.onchange=()=>{S.scenario[key]=input.value;if(key==='rsu_id')syncSatelliteEndpoints();markDirty();};
   wrap.append(input);box.append(wrap);
  }
 }
 const count=S.scenario.denm_events?.length||0;
 const note=document.createElement('p');note.className='smallnote';note.textContent=`Naplánované udalosti: ${count}. Vyber auto na mape a uprav jeho DENM.`;box.append(note);
}
function renderCarDenmControls(id,box){
 const events=S.scenario.denm_events||(S.scenario.denm_events=[]);
 const title=document.createElement('h4');title.textContent='DENM tohto auta';box.append(title);
 for(const event of events.filter(row=>row.source_id===id)){
  const group=document.createElement('fieldset');const legend=document.createElement('legend');legend.textContent=`Výstraha ${event.sequence}`;group.append(legend);
  function field(label,key,min,max,step){const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.type='number';input.min=min;input.max=max;input.step=step;input.value=event[key];input.onchange=()=>{event[key]=Number(input.value);S.inspectorKey=null;markDirty();};wrap.append(input);group.append(wrap);}
  const operation=document.createElement('label');operation.textContent='Operácia';const choice=document.createElement('select');for(const [key,label] of [['new','Nová výstraha'],['update','Aktualizácia'],['cancel','Zrušenie']])choice.append(new Option(label,key));choice.value=event.operation;choice.onchange=()=>{event.operation=choice.value;if(choice.value==='cancel')event.repetition_ms=0;S.inspectorKey=null;markDirty();};operation.append(choice);group.append(operation);
  field('Čas od začiatku simulácie · s','at_s',0,S.world.simulation.duration_s-0.001,0.001);
  field('Číslo výstrahy','sequence',0,65535,1);
  field('Platnosť · s','validity_s',1,86400,1);
  field('Polomer oblasti · m','radius_m',1,1780,1);
  field('Opakovanie · ms (0 = vypnuté)','repetition_ms',0,60000,100);
  const remove=document.createElement('button');remove.type='button';remove.className='subtle';remove.textContent='Odstrániť DENM';remove.onclick=()=>{S.scenario.denm_events=events.filter(row=>row!==event);S.inspectorKey=null;markDirty();};group.append(remove);box.append(group);
 }
 const add=document.createElement('button');add.type='button';add.className='subtle';add.textContent='Pridať DENM';add.disabled=events.length>=64||S.scenario.node_policy?.cars[id]?.ground==='off';add.onclick=()=>{
  const mine=events.filter(row=>row.source_id===id),at=Math.min(S.world.simulation.duration_s-0.001,mine.length?Math.max(...mine.map(row=>row.at_s))+1:1);
  let sequence=1;while(mine.some(row=>row.sequence===sequence))sequence++;
  events.push({source_id:id,at_s:Math.round(at*1000)/1000,sequence,operation:'new',validity_s:15,radius_m:1500,repetition_ms:0});S.inspectorKey=null;markDirty();
 };box.append(add);
}
function renderDurationControls(){if(!S.scenario||!S.world)return;let [min,max]=durationLimits(),input=$('mobilitySeconds');input.min=min;input.max=max;if(document.activeElement!==input)input.value=S.world.simulation.duration_s;$('durationHelp').textContent=`Dĺžka behu: ${S.world.simulation.duration_s} s.`;renderDenmControls();}
function commitDurationInput(){const input=$('mobilitySeconds'),v=Number(input.value),[minimum,maximum]=durationLimits();if(!Number.isInteger(v)||v<minimum||v>maximum)throw Error(`Dĺžka simulácie musí byť ${minimum}–${maximum} s.`);if(v===S.world.simulation.duration_s)return false;S.world.simulation.duration_s=v;S.scenario.sample_count=v*10;S.orbitPreview=null;S.orbitDirty=satelliteRequested();S.orbitRequest++;window.resetGlobeMotion?.();markDirty();return true;}
function mapDraftSnapshot(){
 return {scenario:structuredClone(S.scenario),world:structuredClone(S.world),demand:structuredClone(S.demand),selected:structuredClone(S.selected),draft:structuredClone(S.draft),roadRedo:structuredClone(S.roadRedo),view:{...S.view},dirty:S.dirty,saved:S.saved,orbitPreview:S.orbitPreview,orbitDirty:S.orbitDirty,replay:S.replay,time:S.time,scenarioId:$('scenarioId').value,groupCars:[...S.groupCars],groupPlanned:[...S.groupPlanned]};
}
function restoreMapDraft(d){
 S.scenario=structuredClone(d.scenario);S.world=structuredClone(d.world);S.demand=structuredClone(d.demand);S.selected=structuredClone(d.selected);S.draft=structuredClone(d.draft);S.roadRedo=structuredClone(d.roadRedo||[]);S.groupCars=[...(d.groupCars||[])];S.groupPlanned=[...(d.groupPlanned||[])];S.routeTargetGroup=false;S.routeTargetCar=null;S.view={...d.view};S.dirty=d.dirty;S.saved=d.saved;S.orbitPreview=d.orbitPreview;S.orbitDirty=d.orbitDirty;S.replay=d.replay;S.time=d.time;$('scenarioId').value=d.scenarioId;S.inspectorKey=null;S.orbitRequest++;S.orbitLoading=false;S.orbitError='';
}
function applyMapModeUI(){
 $('earthMode').value=S.mapMode;
 $('areaWidth').value=extent();$('areaHeight').value=height();
 document.querySelector('[data-tool="road"]').hidden=S.mapMode==='real';document.querySelector('[data-tool="building"]').hidden=S.mapMode==='real';
 document.querySelector('.tools').style.gridTemplateColumns=S.mapMode==='real'?'repeat(3,1fr)':'repeat(5,minmax(60px,1fr))';
 document.querySelector('.layer-groups>div:nth-child(2)').hidden=S.mapMode!=='real';
 document.querySelector('.layer-groups').style.gridTemplateColumns=S.mapMode==='real'?'':'1fr';
 if(S.mapMode==='real'&&['road','building'].includes(S.tool))S.tool='car';
 updateTool(S.tool);
 window.simulatorEarthApplyMode?.();window.simulatorRealMapInitialize?.();if(S.mapMode==='real')window.simulatorEarthLoadRoadNetwork?.();
 syncHeightCase();
}
function syncHeightCase(){const e=S.scenario?.satellite?.environment,control=$('heightCaseControl'),picker=$('heightCase');control.hidden=S.mapMode!=='real'||!e?.height_case;picker.value=e?.height_case||'central';}
window.simulatorSyncHeightCase=syncHeightCase;
function clearMapFor(mode){
 const w=extent(),h=height();S.world.width_m=w;S.world.height_m=h;delete S.world.extent_m;S.world.georeference.anchor_x_m=w/2;S.world.georeference.anchor_y_m=h/2;S.world.roads={nodes:[],segments:[]};S.world.rsus=[];S.world.vehicles=[];S.demand.vehicles=[];
 S.world.map_source=mode==='real'?'osm_live':'manual';
 if(mode==='real')S.world.map_objects={schema_version:1,roads:[],cars:[],rsus:[]};else delete S.world.map_objects;
 S.scenario.source_id='';S.scenario.rsu_id='';S.scenario.denm_events=[];if('alert_target_rsu' in S.scenario)S.scenario.alert_target_rsu='';if(S.scenario.satellite?.terminal_mounts)S.scenario.satellite.terminal_mounts={};
 if(S.scenario.satellite)delete S.scenario.satellite.environment;
 if(S.scenario.node_policy)S.scenario.node_policy={cars:{},rsus:{}};
 if(S.world.flows?.[0])S.world.flows[0].source='';
 S.selected=null;S.inspectorKey=null;S.routeTargetCar=null;S.routeTargetGroup=false;S.groupCars=[];S.groupPlanned=[];S.draft=[];S.roadRedo=[];S.replay=null;S.packet=null;
 S.orbitPreview=null;S.orbitDirty=!!S.scenario.satellite;S.orbitRequest++;S.orbitLoading=false;S.orbitError='';
 S.view=fullView();S.time=0;S.tool=mode==='real'?'car':'road';
}
function clearRealSite(){
 if(S.mapMode!=='real')return;
 S.world.roads={nodes:[],segments:[]};S.world.rsus=[];S.world.vehicles=[];S.demand.vehicles=[];
 S.world.map_objects={schema_version:1,roads:[],cars:[],rsus:[],sources:[]};
 S.scenario.source_id='';S.scenario.rsu_id='';S.scenario.denm_events=[];
 if(S.scenario.satellite)delete S.scenario.satellite.environment;
 if('alert_target_rsu' in S.scenario)S.scenario.alert_target_rsu='';
 if(S.scenario.node_policy)S.scenario.node_policy={cars:{},rsus:{}};
 if(S.world.flows?.[0])S.world.flows[0].source='';
 S.selected=null;S.inspectorKey=null;S.routeTargetCar=null;S.routeTargetGroup=false;S.groupCars=[];S.groupPlanned=[];S.replay=null;S.packet=null;
 S.view=fullView();S.time=0;
 window.simulatorRealMapInitialize?.();setView();rebuildObjectPicker();render();
}
function commitAreaSize(){
 if(!S.world)return;
 const w=Number($('areaWidth').value),h=Number($('areaHeight').value);
 if(!Number.isInteger(w)||!Number.isInteger(h)||w<500||w>4000||h<500||h>4000)throw Error('Šírka aj výška musia byť celé metre v rozsahu 500–4000.');
 if(w===extent()&&h===height())return;
 const dx=(w-extent())/2,dy=(h-height())/2;
 if(S.mapMode==='empty'){
  const existingEnvironment=S.scenario.satellite?.environment;
  if(existingEnvironment&&existingEnvironment.sources?.osm?.provider!=='manual-editor-v1')throw Error('Tento prázdny scenár má importované prostredie. Pred zmenou výrezu ho založ nanovo.');
  const points=[...S.world.roads.nodes.map(n=>[n.x_m,n.y_m]),...S.world.roads.segments.flatMap(r=>r.shape),...S.world.rsus.map(r=>[r.x_m,r.y_m]),...(window.simulatorBuildings?.list()||[]).flatMap(b=>b.polygon_xy_m)];
  if(points.some(([x,y])=>x+dx<0||x+dx>w||y+dy<0||y+dy>h))throw Error('Niektorý objekt by po zmenšení zostal mimo výrezu. Najprv ho premiestni alebo odstráň.');
  for(const n of S.world.roads.nodes){n.x_m+=dx;n.y_m+=dy;}
  for(const r of S.world.roads.segments)for(const p of r.shape){p[0]+=dx;p[1]+=dy;}
  for(const r of S.world.rsus){r.x_m+=dx;r.y_m+=dy;}
  for(const b of window.simulatorBuildings?.list()||[])for(const p of b.polygon_xy_m){p[0]+=dx;p[1]+=dy;}
  const env=S.scenario.satellite?.environment;
  if(env?.sources?.osm?.provider==='manual-editor-v1'){
   const cols=75+Math.ceil((w-2000)/30),rows=75+Math.ceil((h-2000)/30);
   env.width_m=w;env.height_m=h;delete env.extent_m;
   env.terrain.width=cols;env.terrain.height=rows;env.terrain.elevation_m=Array(cols*rows).fill(0);
  }
 }else clearRealSite();
 S.world.georeference.anchor_x_m=w/2;S.world.georeference.anchor_y_m=h/2;
 S.world.width_m=w;S.world.height_m=h;delete S.world.extent_m;
 if(S.mapMode==='empty'&&S.scenario.satellite?.environment?.sources?.osm?.provider==='manual-editor-v1')S.scenario.satellite.environment.georeference=structuredClone(S.world.georeference);
 S.view=fullView();S.orbitPreview=null;S.orbitDirty=!!S.scenario.satellite;S.orbitRequest++;
 window.simulatorEarthInvalidateRoads?.();setView();markDirty();if(S.mapMode==='real')window.simulatorEarthLoadRoadNetwork?.();
 status(`Pracovný výrez ${w} × ${h} m. ${S.mapMode==='real'?'Načítavam cesty a budovy pre nový výrez.':'Objekty zostali na svojich polohách voči miestu pokusu.'}`);
}
function newMap(mode){
 if(!S.world)return;
 if(S.mapMode==='real')window.simulatorRealMapSyncActive?.();
 S.mapDrafts[S.mapMode]=mapDraftSnapshot();delete S.mapDrafts[mode];
 clearMapFor(mode);S.mapMode=mode;
 window.resetGlobeMotion?.(true);applyMapModeUI();setView();rebuildObjectPicker();markDirty();
 status(mode==='real'?'Reálna mapa sa zobrazuje. Načítavam jazdné cesty a budovy výrezu…':'Prázdny svet: nakresli cestu, vlož autá a RSU. Potom nastav komunikáciu zariadení a over scenár.');
 loadMapConstellation();
}
function switchMapMode(mode){
 if(!['real','empty'].includes(mode)||!S.world)return;
 if(mode===S.mapMode){applyMapModeUI();return;}
 if(S.mapMode==='real')window.simulatorRealMapSyncActive?.();
 S.mapDrafts[S.mapMode]=mapDraftSnapshot();
 if(S.mapDrafts[mode])restoreMapDraft(S.mapDrafts[mode]);else clearMapFor(mode);
 S.mapMode=mode;S.routeTargetCar=null;S.routeTargetGroup=false;S.groupCars=[];S.groupPlanned=[];S.world.map_source=mode==='real'?'osm_live':'manual';
 $('constellation').value=S.scenario.satellite?.orbit_group||'iridium-NEXT';syncOrbitSnapshotPicker();
 window.resetGlobeMotion?.();applyMapModeUI();setView();rebuildObjectPicker();renderDurationControls();render();
 status(`Režim ${mode==='real'?'reálna mapa':'prázdny svet'}: ${S.demand.vehicles.length} áut a ${S.world.rsus.length} RSU v pracovnom výreze.`);
 loadMapConstellation();
}
function unifiedDraft(s){
 if(s.mode!=='unified'||![6,7].includes(s.schema_version))throw Error('Scenár má nepodporovanú verziu.');
 const draft=structuredClone(s);if(draft.schema_version===6){draft.utc_origin=new Date(Date.parse(draft.utc_origin)+10000).toISOString().replace('.000Z','Z');draft.schema_version=7;draft.time_policy='ready_at_t0_full_duration';}draft.denm_events??=[];for(const event of draft.denm_events)event.source_id??=draft.source_id;return draft;
}
function useSource(d,fresh=false,initialReal=false){clearPacketFeed();S.scenario=unifiedDraft(d.scenario);S.world=structuredClone(d.world);S.demand=structuredClone(d.demand);S.scenario.schema_version=7;S.scenario.time_policy='ready_at_t0_full_duration';S.scenario.sample_count=S.world.simulation.duration_s*10;S.mapMode=initialReal||S.world.map_source==='osm_live'?'real':'empty';S.mapDrafts={};S.world.map_source=S.mapMode==='real'?'osm_live':'manual';S.routeTargetCar=null;S.routeTargetGroup=false;S.groupCars=[];S.groupPlanned=[];S.selected=null;S.inspectorKey=null;rebuildObjectPicker();S.draft=[];S.roadRedo=[];S.replay=null;window.simulatorPhysicalAudit?.clear();S.packet=null;S.linkFilter=null;S.playing=false;$('play').textContent='▶';$('linkFilter').hidden=true;S.orbitPreview=null;S.orbitDirty=false;S.orbitRequest++;S.orbitLoading=false;S.orbitError='';window.resetGlobeMotion?.();$('constellation').value=S.scenario.satellite?.orbit_group||'iridium-NEXT';renderCatalog();S.dirty=fresh;S.saved=!fresh;S.time=0;syncOrbitSnapshotPicker();orbitControls();renderDurationControls();$('scenarioId').value=fresh?'novy-scenar':S.scenario.scenario_id+'-novy';$('runStatus').textContent='Otvor overený beh alebo spusti nový.';$('events').textContent='';$('packetDetail').textContent='Vyber udalosť, aby sa zobrazila jej cesta.';applyMapModeUI();fit();window.simulatorEarthFollowSite?.();status(fresh?(initialReal?'Reálna mapa sa zobrazuje. Načítavam jazdné cesty a budovy výrezu…':'Prázdny návrh: nakresli cestu, potom pridaj autá a RSU.'):`Načítaný scenár ${S.scenario.scenario_id}. Môžeš upravovať mapu.`);if(S.scenario.satellite&&(S.world.rsus.length||S.demand.vehicles.length))refreshOrbits(false).catch(error);else window.previewGlobeConstellation?.().catch(error);}
async function loadSource(id){try{useSource(await api('/api/simulator/editor/source?scenario='+encodeURIComponent(id)));}catch(e){error(e);}}
function satelliteRequested(){return Object.values(S.scenario?.node_policy?.rsus||{}).some(row=>row.satellite_backhaul);}
function syncSatelliteEndpoints(){const active=S.world.rsus.filter(r=>S.scenario.node_policy?.rsus[r.id]?.satellite_backhaul).map(r=>r.id);if(active.length){if(!active.includes(S.scenario.rsu_id))S.scenario.rsu_id=active[0];const targets=active.filter(id=>id!==S.scenario.rsu_id);if(!targets.includes(S.scenario.alert_target_rsu))S.scenario.alert_target_rsu=targets[0]||'';}else{S.scenario.rsu_id=S.world.rsus[0]?.id||'';S.scenario.alert_target_rsu='';}}
function currentPayload(){if(S.mapMode==='real')window.simulatorRealMapSyncActive?.();if(S.mapMode==='empty'&&S.scenario?.satellite?.environment?.sources?.osm?.provider==='manual-editor-v1'){S.scenario.satellite.environment.georeference=structuredClone(S.world.georeference);S.scenario.satellite.environment.width_m=extent();S.scenario.satellite.environment.height_m=height();delete S.scenario.satellite.environment.extent_m;}let scenario=structuredClone(S.scenario),world=structuredClone(S.world),demand=structuredClone(S.demand);scenario.scenario_id=$('scenarioId').value.trim();scenario.mode='unified';scenario.schema_version=7;scenario.time_policy='ready_at_t0_full_duration';scenario.sample_count=world.simulation.duration_s*10;scenario.satellite_enabled=satelliteRequested();for(const car of demand.vehicles)car.depart_s=0;const activeRsus=world.rsus.filter(r=>scenario.node_policy.rsus[r.id]?.satellite_backhaul).map(r=>r.id);if(activeRsus.length){if(!activeRsus.includes(scenario.rsu_id))scenario.rsu_id=activeRsus[0];const targets=activeRsus.filter(id=>id!==scenario.rsu_id);if(!targets.includes(scenario.alert_target_rsu))scenario.alert_target_rsu=targets[0]||'';}else{scenario.rsu_id=world.rsus[0]?.id||'';scenario.alert_target_rsu='';}world.vehicles=structuredClone(demand.vehicles);world.flows[0].source=scenario.source_id;return {scenario,world,demand};}
async function ensureAutomaticOrbit(){
 if(!satelliteRequested())return;
 if(S.orbitRefreshPromise)await S.orbitRefreshPromise.catch(()=>{});
 S.scenario.satellite.orbit_group=$('constellation').value;
 S.scenario.satellite.dynamic_physical=true;
 S.scenario.satellite.antenna_model='public-v1';
 S.scenario.satellite.catalog_ids=[];S.scenario.satellite.isls=[];S.scenario.satellite.initial_serving_sat=0;S.scenario.satellite.handover_target_sat=0;S.scenario.satellite.feeder_sat=0;
 if(S.scenario.satellite.orbit_group!=='starlink')S.scenario.satellite.terminal_mounts={};
}
async function save(){
 commitDurationInput();
 await ensureAutomaticOrbit();
 let payload=currentPayload(),r=await post('/api/simulator/editor/save',payload);
 S.scenario=r.scenario;S.world=payload.world;S.demand=payload.demand;S.dirty=false;S.saved=true;
 $('plan').textContent=JSON.stringify(r.plan,null,2);await loadSaved();
 status(`Uložené ${r.path}. Scenár je pripravený na beh.`);return r;
}
async function loadSaved(){let r=await api('/api/simulator/scenarios'),s=$('saved');s.replaceChildren();let blank=document.createElement('option');blank.value='';blank.textContent='— vybrať —';s.append(blank);for(const id of r.scenarios){let o=document.createElement('option');o.value=id;o.textContent=id;s.append(o);}}
async function run(){try{$('run').disabled=true;commitDurationInput();await ensureAutomaticOrbit();if(S.dirty||!S.saved||$('scenarioId').value.trim()!==S.scenario.scenario_id)await save();let r=await post('/api/simulator/runs',{scenario:S.scenario});S.runId=r.run_id;$('runId').value=r.run_id;$('runStatus').textContent=`Beží ${r.run_id} · ${S.world.simulation.duration_s} s…`;await poll(r.run_id);}catch(e){error(e);$('run').disabled=false;}}
function summary(d){
 const plan=d.plan,result=d.result,native=result.native_packet_backend;
 const rows=[['Autá',plan.cars],['RSU',plan.rsus]];
 if(native){
   rows.push(['Satelity',native.satellites]);
   if(native.application_messages?.includes('DENM')){
     rows.push(['CAM vyslané',native.cam_transmitted],['DENM udalosti',native.denm_events],
       ['DENM v bráne',native.denm_gateway_received],['DENM v cieľových autách',native.denm_remote_car_receipts]);
   }
 }else if(result.scenario){
   const ground=result.scenario;
   rows.push(['CAM vyslané / prijaté',`${ground.cam_tx} / ${ground.cam_rx}`],
     ['DENM udalosti / prijatia',`${ground.denm_events??0} / ${ground.denm_receipts??0}`]);
 }
 const table=document.createElement('table');
 for(const [label,value] of rows){const tr=document.createElement('tr');
   for(const item of [label,value]){const td=document.createElement('td');td.textContent=String(item);tr.append(td);}
   table.append(tr);}
 $('summary').replaceChildren(table);
}
async function poll(id){try{let d=await api('/api/simulator/runs/'+encodeURIComponent(id));if(d.status==='running'){S.timer=setTimeout(()=>poll(id),2000);return;}S.runId=id;$('run').disabled=false;$('runStatus').textContent=`Overený beh ${id} · ${d.plan.cars} áut · ${d.plan.rsus} RSU`;summary(d);let rep=await api(`/api/simulator/runs/${encodeURIComponent(id)}/replay`);S.playing=false;$('play').textContent='▶';S.linkFilter=null;S.packet=null;$('packetDetail').textContent='Vyber udalosť, aby sa zobrazila jej cesta.';$('linkFilter').hidden=true;S.replay=rep;window.simulatorPhysicalAudit?.clear();S.replay.byCar=new Map;S.replay.satelliteByCatalog=new Map;S.replay.satelliteNodeCatalog=new Map;for(const q of rep.points){if(q.kind!=='car')continue;let arr=S.replay.byCar.get(q.id)||[];arr.push(q);S.replay.byCar.set(q.id,arr);}for(const arr of S.replay.byCar.values())arr.sort((a,b)=>a.time_us-b.time_us);for(const q of rep.satellites||[]){S.replay.satelliteNodeCatalog.set(q.id,q.catalog_id);let arr=S.replay.satelliteByCatalog.get(q.catalog_id)||[];arr.push(q);S.replay.satelliteByCatalog.set(q.catalog_id,arr);}for(const arr of S.replay.satelliteByCatalog.values())arr.sort((a,b)=>a.time_us-b.time_us);S.world=rep.world;S.demand={...S.demand,vehicles:rep.world.vehicles};S.scenario=unifiedDraft(rep.scenario);S.mapMode=S.world.map_source==='osm_live'?'real':'empty';applyMapModeUI();rebuildObjectPicker();$('constellation').value=S.scenario.satellite?.orbit_group||'iridium-NEXT';syncOrbitSnapshotPicker();orbitControls();renderDurationControls();S.orbitPreview=null;S.orbitDirty=false;S.orbitRequest++;S.orbitLoading=false;S.orbitError='';window.resetGlobeMotion?.();renderCatalog();const firstCarTime=Math.min(...rep.points.filter(x=>x.kind==='car').map(x=>x.time_us));S.replay.min=rep.scenario.schema_version>=5?0:Number.isFinite(firstCarTime)?firstCarTime:0;S.time=S.replay.min;S.replay.max=rep.scenario.schema_version>=5?rep.world.simulation.duration_s*1e6:Math.max(...rep.points.map(x=>x.time_us),...rep.events.map(x=>x.time_us));$('runStatus').textContent=`Overený beh ${id} · ${rep.world.simulation.duration_s} s · ${d.plan.cars} áut · ${d.plan.rsus} RSU`;$('time').value=0;resetPacketFeed();showTime();window.simulatorPhysicalAudit?.load(id);if(S.scenario.satellite)window.simulatorLoadReplayOrbit?.().catch(error);status('Replay pripravený.');}catch(e){$('run').disabled=false;$('runStatus').textContent='Beh alebo replay sa nepodarilo overiť: '+e.message;}}
function showTime(){
 if(!S.replay)return;
 let t=S.time;$('timeLabel').textContent=`${(t/1e6).toFixed(2)} / ${(S.replay.max/1e6).toFixed(2)} s`;
 let physical=S.replay.physical_timeline,box=$('physicalReplayStatus');box.hidden=!physical;
 if(physical){
  const node=S.selected?.type==='car'||S.selected?.type==='rsu'?S.selected.id:S.scenario.rsu_id;
  const rows=physical.nodes[node]||[];
  const index=Math.max(0,Math.min(rows.length-1,Math.round(t/(physical.sample_step_s*1e6))));
  const row=rows[index];
  box.textContent=row?`${node} · ${(row.time_us/1e6).toFixed(1)} s · ${row.candidate_count} fyzikálnych kandidátov${row.best_catalog_id?` · najvyššie ${row.best_catalog_id} (${row.best_elevation_deg.toFixed(1)}°)`:''}`:'Bez satelitného výhľadu.';
 }
 window.simulatorSyncReplayOrbit?.();window.simulatorEnsureReplayOrbit?.();syncPacketFeed();render();
}
function setTimeFromSlider(){if(!S.replay)return;let v=Number($('time').value)/1000;S.time=S.replay.min+v*(S.replay.max-S.replay.min);showTime();}
const PACKET_PAGE=256,PACKET_ROW=52,PACKET_TRACK_MAX=12000000;
function decodePacketTimeline(data){
 if(data.timeline_encoding!=='uvarint-delta-us-v1')throw Error('Neznámy formát časového indexu paketov.');
 const raw=atob(data.time_deltas_us_b64),times=new Float64Array(data.total);
 let count=0,when=0,gap=0,shift=0;
 for(let i=0;i<raw.length;i++){
  const byte=raw.charCodeAt(i);gap+=(byte&127)*2**shift;
  if(byte&128){shift+=7;if(shift>49)throw Error('Neplatný časový index paketov.');continue;}
  when+=gap;if(count>=times.length)throw Error('Neplatný počet paketov.');times[count++]=when;gap=0;shift=0;
 }
 if(count!==times.length||shift)throw Error('Neúplný časový index paketov.');
 return times;
}
function syncPacketFeed(){
 const feed=S.eventFeed;if(!feed?.times||!S.replay)return;
 let lo=0,hi=feed.times.length;
 while(lo<hi){const mid=(lo+hi)>>1;if(feed.times[mid]<=S.time)lo=mid+1;else hi=mid;}
 if(feed.revealed!==lo){feed.revealed=lo;renderEvents();}
}
function clearPacketFeed(){
 S.eventFeed=null;$('packetCount').textContent='';
 const empty=document.createElement('p');empty.className='smallnote';empty.textContent='Zatiaľ žiadne udalosti.';
 $('events').replaceChildren(empty);
}
function resetPacketFeed(){
 if(!S.replay||!S.runId){clearPacketFeed();return;}
 const feed={runId:S.runId,filter:S.linkFilter?{...S.linkFilter}:null,
   pages:new Map(),pending:new Set(),total:null,times:null,revealed:0,follow:true,error:null};
 S.eventFeed=feed;$('events').scrollTop=0;
 $('events').textContent='Načítavam paketové udalosti…';$('packetCount').textContent='';
 requestPacketPage(feed,0);
}
async function requestPacketPage(feed,page){
 if(feed.pages.has(page)||feed.pending.has(page)||feed.error)return;
 feed.pending.add(page);
 const query=new URLSearchParams({offset:String(page*PACKET_PAGE),limit:String(PACKET_PAGE)});
 if(page===0&&!feed.times)query.set('timeline','1');
 if(feed.filter){query.set('from',feed.filter.from);query.set('to',feed.filter.to);query.set('kind',feed.filter.kind);}
 try{
  const data=await api(`/api/simulator/runs/${encodeURIComponent(feed.runId)}/events?${query}`);
  if(S.eventFeed!==feed)return;
  feed.total=data.total;feed.pages.set(page,data.events);
  if(page===0&&!feed.times){feed.times=decodePacketTimeline(data);syncPacketFeed();}
  if(feed.pages.size>20){const oldest=feed.pages.keys().next().value;if(oldest!==page)feed.pages.delete(oldest);}
 }catch(error){if(S.eventFeed===feed)feed.error=error.message;}
 finally{feed.pending.delete(page);if(S.eventFeed===feed)renderEvents();}
}
function renderEvents(){
 const feed=S.eventFeed,box=$('events');if(!feed)return;
 if(feed.error){box.textContent='Paketové udalosti sa nenačítali: '+feed.error;return;}
 if(feed.total===null)return;
 const count=feed.revealed;
 $('packetCount').textContent=`· ${count.toLocaleString('sk-SK')}${feed.filter?' príjmov':' udalostí'}`;
 if(!feed.total){box.textContent=feed.filter?'Na tomto spojení nie je zaznamenaný príjem paketu.':'Beh nemá paketové udalosti.';return;}
 if(!count){box.textContent='Do tohto času zatiaľ neprišiel žiadny paket.';return;}
 const visible=Math.ceil((box.clientHeight||300)/PACKET_ROW)+10;
 const maxStart=Math.max(0,count-visible),track=Math.min(count*PACKET_ROW,PACKET_TRACK_MAX);
 const compressed=count*PACKET_ROW>PACKET_TRACK_MAX;
 const scroll=feed.follow?Math.max(0,track-box.clientHeight):box.scrollTop;
 const anchor=compressed?Math.floor(scroll/Math.max(1,track-box.clientHeight)*maxStart):Math.floor(scroll/PACKET_ROW);
 const start=Math.max(0,Math.min(maxStart,anchor-3)),end=Math.min(count,start+visible);
 const top=compressed?(maxStart?Math.floor(start/maxStart*Math.max(0,track-visible*PACKET_ROW)):0):start*PACKET_ROW;
 const bottom=Math.max(0,track-top-(end-start)*PACKET_ROW);
 const fragment=document.createDocumentFragment(),spacer=height=>{const node=document.createElement('div');node.style.height=height+'px';return node;};
 fragment.append(spacer(top));
 for(let index=start;index<end;index++){
  const page=Math.floor(index/PACKET_PAGE),event=feed.pages.get(page)?.[index%PACKET_PAGE];
  if(!event){const pending=document.createElement('div');pending.className='event event-loading';pending.textContent='Načítavam…';fragment.append(pending);requestPacketPage(feed,page);continue;}
  const button=document.createElement('button');button.className='event'+(event.native_level?' event-native':'')+(S.packet===event.id?' active':'');
  const strong=document.createElement('strong');strong.textContent=event.stage;
  const small=document.createElement('span');small.textContent=`${(event.time_us/1e6).toFixed(3)} s · ${event.node} · ${event.bytes} B${event.native_level?' IP':''} · ${event.id}`;
  button.append(strong,small);button.onclick=()=>{
   S.playing=false;$('play').textContent='▶';
   S.time=Math.max(S.replay.min,Math.min(S.replay.max,event.time_us));
   $('time').value=Math.round(1000*(S.time-S.replay.min)/(S.replay.max-S.replay.min));
   showTime();openPacket(event.id);
  };
  fragment.append(button);
 }
 fragment.append(spacer(bottom));box.replaceChildren(fragment);
 if(feed.follow)box.scrollTop=box.scrollHeight-box.clientHeight;
}
async function openPacket(id){
 S.packet=id;renderEvents();render();const box=$("packetDetail");box.textContent="Načítavam surové bajty…";
 try{
   const p=await api(`/api/simulator/runs/${encodeURIComponent(S.runId)}/packet/${encodeURIComponent(id)}`);
   if(S.replay){S.replay.events=S.replay.events.filter(e=>!e.detailOnly);
     for(const stage of p.stages)if(stage.stage==='CAM_UPER_RX')S.replay.events.push({stage:stage.stage,node:stage.node,id,time_us:stage.time_us,bytes:stage.bytes,detailOnly:true});
     render();renderEvents();
   }
   window.simulatorPacketInspector.render(box,p,id);
 }catch(error){box.textContent=error.message;}
}
$('events').addEventListener('scroll',()=>{const feed=S.eventFeed;if(feed)feed.follow=$('events').scrollHeight-$('events').clientHeight-$('events').scrollTop<8;renderEvents();});
$('groundMap').addEventListener('pointerdown',e=>{if(!S.world)return;let pan=e.button===2;if(pan){S.drag={x:e.clientX,y:e.clientY,v:{...S.view},scale:unitsPerPixel()};$('groundMap').setPointerCapture(e.pointerId);e.preventDefault();return;}if(e.button!==0)return;const edge=e.target.closest?.('[data-link-from]');if(edge&&S.replay){selectPacketLink(edge.dataset.linkFrom,edge.dataset.linkTo,edge.dataset.linkKind);return;}let p=worldPoint(e);if(window.simulatorRoutes?.clickDestination(p))return;if(S.tool==='road'){if(S.mapMode==='real')return status('V reálnom režime cestu nekreslíš. Klikni na vozovku nástrojom Auto.');addRoadPoint(p);}else if(S.tool==='car'){if(S.mapMode==='real'&&!window.simulatorEarthEnsureRoad?.(p))return;addCar(p);}else if(S.tool==='rsu')addRsu(p);else if(S.tool==='building')window.simulatorBuildings?.add(p);else{let target=e.target.closest?.('[data-type][data-id]');const hit=target?{type:target.dataset.type,id:target.dataset.id}:entityAt(p);if(e.shiftKey&&hit?.type==='car'){window.simulatorRoutes?.toggleGroup(hit.id);return;}S.selected=hit;render();}});
$('groundMap').addEventListener('pointermove',e=>{if(S.drag){let v=S.view;v.x=S.drag.v.x-(e.clientX-S.drag.x)*S.drag.scale;v.y=S.drag.v.y-(e.clientY-S.drag.y)*S.drag.scale;clampView(v);setView();render();}let p=worldPoint(e);$('cursor').textContent=`x ${fmt(p.x)} m · y ${fmt(p.y)} m`;});
$('groundMap').addEventListener('pointerup',()=>{S.drag=null;});$('groundMap').addEventListener('pointercancel',()=>{S.drag=null;});$('groundMap').addEventListener('dblclick',e=>{if(S.tool==='road'){e.preventDefault();if(S.draft.length>2){S.draft.pop();finishRoad();}}});$('groundMap').addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY>0?1.2:1/1.2,e);},{passive:false});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&S.tool==='road')clearRoadDraft();});$('groundMap').addEventListener('contextmenu',e=>e.preventDefault());
$('objectPicker').onchange=()=>{let value=$('objectPicker').value;if(!value){S.selected=null;if(S.replay)showTime();else render();return;}let [type,id]=value.split(':');S.selected={type,id};focusSelected();if(S.replay)showTime();};
$('heightCase').onchange=()=>{const env=S.scenario?.satellite?.environment;if(!env)return;env.height_case=$('heightCase').value;markDirty();status(`Výšky budov: ${$('heightCase').selectedOptions[0].textContent}. Ulož a spusti nový beh na porovnanie.`);};
for(const id of ['areaWidth','areaHeight'])$(id).onchange=()=>{try{commitAreaSize();}catch(e){error(e);$('areaWidth').value=extent();$('areaHeight').value=height();}};
for(const b of document.querySelectorAll('[data-tool]'))b.onclick=()=>updateTool(b.dataset.tool);$('finishRoad').onclick=finishRoad;$('undoRoad').onclick=undoRoadPoint;$('redoRoad').onclick=redoRoadPoint;$('cancelRoad').onclick=clearRoadDraft;$('zoomIn').onclick=()=>zoom(.8);$('zoomOut').onclick=()=>zoom(1.25);$('fit').onclick=fit;$('constellation').onchange=()=>{S.scenario.satellite.orbit_group=$('constellation').value;S.scenario.link_policy_override=false;if(S.scenario.satellite.orbit_group!=='starlink')S.scenario.satellite.terminal_mounts={};S.inspectorKey=null;S.orbitPreview=null;S.orbitDirty=true;S.orbitRequest++;markDirty();window.resetGlobeMotion?.();renderCatalog();$('orbitSelectionInfo').textContent='Vyhodnocujem viditeľné satelity a spojenie k bráne…';if(S.world.rsus.length||S.demand.vehicles.length)refreshOrbits(true).catch(error);else window.previewGlobeConstellation?.().catch(error);};$('mobilitySeconds').onchange=()=>{try{if(commitDurationInput()&&satelliteRequested()){const pending=refreshOrbits(true);S.orbitRefreshPromise=pending;pending.catch(error).finally(()=>{if(S.orbitRefreshPromise===pending)S.orbitRefreshPromise=null;});}}catch(e){error(e);}};$('newBlank').onclick=()=>newMap('empty');$('newReal').onclick=()=>newMap('real');$('loadSaved').onclick=()=>{if($('saved').value)loadSource($('saved').value);};$('save').onclick=async()=>{try{await save();}catch(e){error(e);}};$('preflight').onclick=async()=>{try{commitDurationInput();await ensureAutomaticOrbit();if(S.dirty||$('scenarioId').value.trim()!==S.scenario.scenario_id){let r=await post('/api/simulator/editor/check',currentPayload());$('plan').textContent=JSON.stringify(r.plan,null,2);status(`Overené: ${r.plan.cars} áut, ${r.plan.rsus} RSU; natívna SNS-3 topológia sa overí pri spustení.`);}else{let r=await post('/api/simulator/preflight',{scenario:S.scenario});$('plan').textContent=JSON.stringify(r,null,2);status(`Overené: ${r.cars} áut, ${r.rsus} RSU; satelitná vetva podľa konfigurácie.`);}}catch(e){error(e);}};$('run').onclick=run;$('open').onclick=()=>{let id=$('runId').value.trim();if(!/^[A-Za-z0-9_-]{1,80}$/.test(id))return $('runStatus').textContent='Neplatné ID behu.';poll(id);};$('time').oninput=setTimeFromSlider;$('linkFilter').onclick=()=>{S.linkFilter=null;$('linkFilter').hidden=true;render();resetPacketFeed();};$('play').onclick=()=>{if(!S.replay)return;if(!S.playing&&S.time>=S.replay.max){S.time=S.replay.min;$('time').value=0;showTime();}S.playing=!S.playing;$('play').textContent=S.playing?'❚❚':'▶';if(S.playing&&S.eventFeed){S.eventFeed.follow=true;renderEvents();}window.simulatorSyncReplayOrbit?.();window.simulatorEnsureReplayOrbit?.();};for(const id of ['layerRoad','layerCar','layerRsu','layerCoverage','layerPackets','layerPhysicalState','layerSat','layerPhysicalFootprint','layerSite','layerGrid','layerBaseRoad','layerBuilding','layerStreetNames','layerPlaceNames','layerCountryNames','layerRivers','layerReferenceRsu'])$(id).onchange=()=>{renderGrid();render();window.simulatorEarthRefreshLayers?.();};
let previous=performance.now(),lastPaint=0,lastOrbitPaint=0;function frame(now){if(S.playing&&S.replay){const span=S.replay.max-S.replay.min;if(span>0)S.time=Math.min(S.replay.max,S.time+Math.max(0,now-previous)*1000);if(S.time>=S.replay.max){S.playing=false;$('play').textContent='▶';}if(now-lastOrbitPaint>=33){window.simulatorSyncReplayOrbit?.();lastOrbitPaint=now;}if(now-lastPaint>=100||!S.playing){$('time').value=Math.round(1000*(S.time-S.replay.min)/span);showTime();lastPaint=now;}}previous=now;requestAnimationFrame(frame);}requestAnimationFrame(frame);
(async()=>{try{window.simulatorDefaultDraft=await api('/api/simulator/editor/new');await loadOrbitSnapshots();await loadSaved();useSource(window.simulatorDefaultDraft,true,true);}catch(e){error(e);}})();
window.simulatorEditor={state:S,render,carPosition,replayCar,groundPosition,activePacketLinks,linkVisualKind,selectPacketLink,nearestRoad,addCar,addRsu,addRoadPoint,finishRoad,status,markDirty,rebuildObjectPicker,refreshOrbits,syncSatelliteEndpoints,renderDurationControls};window.simulatorEditorSwitchMapMode=switchMapMode;window.simulatorEditorClearRealSite=clearRealSite;

'use strict';

// Keep the car's SUMO route/type inputs separate from its radio and messages.
(() => {
  const editor=window.simulatorEditor,S=editor.state;
  let activeTab='sumo';
  const road=id=>S.world.roads.segments.find(item=>item.id===id);
  const length=item=>item.shape.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-item.shape[i][0],p[1]-item.shape[i][1]),0);
  function createTabs(root){
    const tabs=document.createElement('div');tabs.className='car-inspector-tabs';
    const sumo=document.createElement('section'),other=document.createElement('section');
    sumo.className='car-inspector-page';other.className='car-inspector-page';
    for(const title of ['Vstupy SUMO','Ostatné vstupy']){
      const button=document.createElement('button');button.type='button';button.textContent=title;tabs.append(button);
    }
    function show(tab){activeTab=tab;sumo.hidden=tab!=='sumo';other.hidden=tab!=='other';
      [...tabs.children].forEach((button,index)=>{const selected=(index===0?'sumo':'other')===tab;button.classList.toggle('active',selected);button.setAttribute('aria-pressed',String(selected));});}
    tabs.children[0].onclick=()=>show('sumo');tabs.children[1].onclick=()=>show('other');
    root.append(tabs,sumo,other);show(activeTab);return {sumo,other};
  }
  function renderSumo(car,box){
    const first=car.route[0],last=car.route.at(-1),firstRoad=road(first.segment),lastRoad=road(last.segment);
    const note=value=>{const p=document.createElement('p');p.className='smallnote';p.textContent=value;box.append(p);};
    const fixed=(label,value)=>{const p=document.createElement('p');p.className='car-fixed-input';const b=document.createElement('strong');b.textContent=`${label}: `;p.append(b,document.createTextNode(String(value)));box.append(p);};
    function numberField(label,value,min,max,step,change){
      const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');
      input.type='number';input.min=String(min);input.max=String(max);input.step=String(step);input.value=String(value);
      input.onchange=()=>{const next=Number(input.value);
        if(!input.value.trim()||!Number.isFinite(next)||next<min||next>max){input.value=String(value);return editor.status(`${label}: povolený rozsah je ${min} až ${max}.`);}
        try{const handled=change(next);if(handled!==false){S.inspectorKey=null;editor.markDirty();}}
        catch(error){input.value=String(value);editor.status(error.message||String(error));}
      };wrap.append(input);box.append(wrap);return input;
    }
    const heading=title=>{const h=document.createElement('h4');h.textContent=title;box.append(h);};
    heading('Auto v SUMO');
    fixed('ID',car.id);
    fixed('Typ',`passenger_${car.id}`);
    fixed('Odchod',`${car.depart_s} s · pruh best`);
    const maximum=car.max_speed_mps??(S.mapMode==='real'?Math.max(.1,car.depart_speed_mps):S.world.simulation.vehicle_model?.manual_max_speed_mps??40);
    numberField('Maximálna rýchlosť · km/h',Number((maximum*3.6).toFixed(6)),.36,144,'any',value=>{
      if((car.depart_speed_mode??(S.mapMode==='real'?'max':'fixed'))==='fixed'&&value/3.6<car.depart_speed_mps)throw Error('Maximum musí byť aspoň počiatočná rýchlosť.');
      car.max_speed_mps=value/3.6;
    });
    const mode=document.createElement('label');mode.textContent='Rýchlosť pri štarte';const modeSelect=document.createElement('select');
    modeSelect.append(new Option('Automatická · max','max'),new Option('Vlastná hodnota','fixed'));
    modeSelect.value=car.depart_speed_mode??(S.mapMode==='real'?'max':'fixed');
    modeSelect.onchange=()=>{if(modeSelect.value==='fixed'&&car.depart_speed_mps>maximum){modeSelect.value='max';return editor.status('Počiatočná rýchlosť presahuje maximum auta.');}car.depart_speed_mode=modeSelect.value;S.inspectorKey=null;editor.markDirty();};
    mode.append(modeSelect);box.append(mode);
    const initialSpeed=numberField('Počiatočná rýchlosť · km/h',Number((car.depart_speed_mps*3.6).toFixed(6)),0,144,'any',value=>{if(value/3.6>maximum)throw Error('Počiatočná rýchlosť presahuje maximum auta.');car.depart_speed_mps=value/3.6;});
    initialSpeed.disabled=modeSelect.value!=='fixed';
    heading('Trasa');
    numberField('Štart na prvom úseku · m',car.depart_pos_m??0,0,
      Math.max(0,length(firstRoad)-20),'any',value=>{
        if(car.route.length===1&&car.arrival_pos_m!==undefined&&value+1>=car.arrival_pos_m)throw Error('Odchod musí byť aspoň 1 m pred cieľom.');
        car.depart_pos_m=value;
      });
    const direction=document.createElement('label');direction.textContent='Smer prvého úseku';const select=document.createElement('select');
    for(const [value,label] of firstRoad.oneway?[['forward','→ jednosmerná']]:[['forward','→ po smere'],['reverse','← proti smeru']])select.append(new Option(label,value));
    select.value=first.direction;select.onchange=()=>{if(select.value===first.direction)return;
      car.depart_pos_m=Math.max(0,Math.min(length(firstRoad)-20,length(firstRoad)-(car.depart_pos_m??0)));
      car.route=[{segment:first.segment,direction:select.value}];delete car.arrival_pos_m;
      S.groupPlanned=S.groupPlanned.filter(id=>id!==car.id);S.inspectorKey=null;editor.markDirty();
    };direction.append(select);box.append(direction);
    const routeLabel=document.createElement('label');routeLabel.textContent='Trasa · smerové hrany v poradí';
    const routeText=document.createElement('textarea');routeText.rows=4;routeText.spellcheck=false;
    routeText.value=car.route.map(hop=>`${hop.segment}_${hop.direction}`).join('\n');routeLabel.append(routeText);box.append(routeLabel);
    const saveRoute=document.createElement('button');saveRoute.type='button';saveRoute.className='subtle';saveRoute.textContent='Uložiť upravenú trasu';
    saveRoute.onclick=()=>{try{
      const tokens=routeText.value.trim().split(/[\s,]+/).filter(Boolean);
      if(!tokens.length||tokens.length>200)throw Error('Trasa musí mať 1 až 200 smerových úsekov.');
      const roads=new Map(S.world.roads.segments.map(item=>[item.id,item]));
      const forbidden=new Set((S.world.roads.turn_rules||[]).map(rule=>`${rule.from}|${rule.to}`));
      let previousEnd=null,previousEdge='';const route=[];
      for(const token of tokens){const match=/^([A-Za-z][A-Za-z0-9_]*)_(forward|reverse)$/.exec(token),item=match&&roads.get(match[1]);
        if(!item||item.oneway&&match[2]==='reverse')throw Error(`Neplatná smerová hrana: ${token}.`);
        const start=match[2]==='forward'?item.from:item.to,end=match[2]==='forward'?item.to:item.from;
        if(previousEnd!==null&&previousEnd!==start)throw Error(`Nenapojená trasa pred ${token}.`);
        if(previousEdge&&previousEdge.slice(0,previousEdge.lastIndexOf('_'))===item.id&&previousEdge!==token)
          throw Error(`Priame otočenie na opačný smer tej istej cesty nie je povolené: ${token}.`);
        if(previousEdge&&forbidden.has(`${previousEdge}|${token}`))throw Error(`Zakázané odbočenie ${previousEdge} → ${token}.`);
        route.push({segment:item.id,direction:match[2]});previousEnd=end;previousEdge=token;
      }
      if((car.depart_pos_m??0)>Math.max(0,length(roads.get(route[0].segment))-20))throw Error('Počiatočná poloha je mimo prvého úseku.');
      if(car.arrival_pos_m!==undefined){const endLength=length(roads.get(route.at(-1).segment));
        if(car.arrival_pos_m>endLength||route.length===1&&car.arrival_pos_m<=(car.depart_pos_m??0)+1)throw Error('Cieľová poloha je mimo novej trasy.');}
      car.route=route;S.groupPlanned=S.groupPlanned.filter(id=>id!==car.id);S.inspectorKey=null;editor.markDirty();
      editor.status(`Trasa auta ${car.id} uložená: ${route.length} ${route.length===1?'úsek':route.length<5?'úseky':'úsekov'}.`);
    }catch(error){editor.status(error.message||String(error));}};box.append(saveRoute);
    const target=document.createElement('label');target.className='check';const toggle=document.createElement('input');toggle.type='checkbox';
    toggle.checked=car.arrival_pos_m!==undefined;toggle.onchange=()=>{if(toggle.checked)car.arrival_pos_m=length(lastRoad);else delete car.arrival_pos_m;
      S.inspectorKey=null;editor.markDirty();};target.append(toggle,document.createTextNode('Vlastná cieľová poloha'));box.append(target);
    if(car.arrival_pos_m!==undefined)numberField('Cieľová poloha na poslednom úseku · m',car.arrival_pos_m,0,length(lastRoad),'any',value=>{
      if(car.route.length===1&&value<=(car.depart_pos_m??0)+1)throw Error('Cieľ musí byť aspoň 1 m za odchodom.');car.arrival_pos_m=value;
    });else fixed('Cieľová poloha','koniec poslednej smerovej hrany');
    window.simulatorRoutes?.renderControls(car,box);
    const model=S.world.simulation.vehicle_model||{accel_mps2:2,decel_mps2:4.5,sigma:0,length_m:5,width_m:1.8,min_gap_m:2.5,speed_factor:1,manual_max_speed_mps:40};
    heading('Model auta');
    const reset=document.createElement('button');reset.type='button';reset.className='subtle';reset.textContent='Predvolené';
    reset.disabled=!car.vehicle_model;
    reset.onclick=()=>{delete car.vehicle_model;S.inspectorKey=null;editor.markDirty();};box.append(reset);
    for(const [label,key,min,max,step] of [['Zrýchlenie · m/s²','accel_mps2',.1,10,.1],['Brzdenie · m/s²','decel_mps2',.1,15,.1],['Náhodnosť vodiča σ','sigma',0,1,.01],['Dĺžka auta · m','length_m',1,20,.1],['Šírka auta · m','width_m',.5,3,.1],['Minimálny odstup · m','min_gap_m',0,10,.1],['Faktor rýchlosti','speed_factor',.1,2,.01]])
      numberField(`${label}${Object.hasOwn(car.vehicle_model||{},key)?' · vlastné':''}`,car.vehicle_model?.[key]??model[key],min,max,step,value=>{car.vehicle_model={...car.vehicle_model,[key]:value};});
  }
  function renderRadio(car,box){
    const heading=document.createElement('h4');heading.textContent='Pozemné rádio tohto auta';box.append(heading);
    const radio=car.radio_model||{},shared=S.scenario.radio;
    const number=(key,label,min,max,fallback)=>{
      const row=document.createElement('label'),input=document.createElement('input');
      row.textContent=`${label}${Object.hasOwn(radio,key)?' · vlastné':''}`;
      input.type='number';input.step='any';input.min=String(min);input.max=String(max);
      input.value=String(radio[key]??fallback);
      input.onchange=()=>{const value=Number(input.value);
        if(!input.value.trim()||!Number.isFinite(value)||value<min||value>max){input.value=String(radio[key]??fallback);return editor.status(`${label}: rozsah ${min} až ${max}.`);}
        car.radio_model||={};car.radio_model[key]=value;S.inspectorKey=null;editor.markDirty();
      };row.append(input);box.append(row);
    };
    for(const [key,label,min,max] of [
      ['tx_power_dbm','Výkon · dBm',0,33],['noise_figure_db','Šumové číslo · dB',0,20],
      ['tx_gain_dbi','Zisk TX · dBi',-20,20],['rx_gain_dbi','Zisk RX · dBi',-20,20]])
      number(key,label,min,max,shared[key]??0);
    number('antenna_height_m','Výška antény · m',.2,10,S.scenario.engine?.car_antenna_height_m??1.5);
    const reset=document.createElement('button');reset.type='button';reset.className='subtle';
    reset.textContent='Predvolené rádio';reset.disabled=!car.radio_model;
    reset.onclick=()=>{delete car.radio_model;S.inspectorKey=null;editor.markDirty();};box.append(reset);
  }
  window.simulatorCarInputs={createTabs,renderSumo,renderRadio};
  window.addEventListener('load',()=>{if(S.world){S.inspectorKey=null;editor.render();}});
})();
