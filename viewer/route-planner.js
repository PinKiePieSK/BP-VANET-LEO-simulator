'use strict';

// Directed road graph shared by the real-map and hand-drawn-road editors.
(() => {
  const editor=window.simulatorEditor,S=editor.state;
  const carCount=n=>`${n} ${n===1?'auto':n<5?'autá':'áut'}`;
  let cachedSegments=null,cachedCount=-1,cachedVersion=-1,cachedGraph=null;
  const roadLength=road=>road.shape.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-road.shape[i][0],p[1]-road.shape[i][1]),0);
  function graph(){
    const segments=S.world?.roads?.segments||[];
    if(segments===cachedSegments&&segments.length===cachedCount&&S.roadGraphVersion===cachedVersion)return cachedGraph;
    const roads=new Map(),adj=new Map(),denied=new Set((S.world?.roads?.turn_rules||[]).map(rule=>`${rule.from}|${rule.to}`));
    const add=(node,edge)=>{if(!adj.has(node))adj.set(node,[]);adj.get(node).push(edge);};
    for(const road of segments){const length=roadLength(road);if(length<.5)continue;roads.set(road.id,{...road,length});add(road.from,{segment:road.id,direction:'forward',from:road.from,to:road.to,length});if(!road.oneway)add(road.to,{segment:road.id,direction:'reverse',from:road.to,to:road.from,length});}
    cachedSegments=segments;cachedCount=segments.length;cachedVersion=S.roadGraphVersion;cachedGraph={roads,adj,denied};return cachedGraph;
  }
  class Heap{
    constructor(){this.items=[];}
    push(row){let a=this.items,i=a.length;a.push(row);while(i){const p=(i-1)>>1;if(a[p][0]<=row[0])break;a[i]=a[p];i=p;}a[i]=row;}
    pop(){const a=this.items,result=a[0],last=a.pop();if(a.length){let i=0;while(i*2+1<a.length){let c=i*2+1;if(c+1<a.length&&a[c+1][0]<a[c][0])c++;if(a[c][0]>=last[0])break;a[i]=a[c];i=c;}a[i]=last;}return result;}
    get length(){return this.items.length;}
  }
  const edgeId=edge=>`${edge.segment}_${edge.direction}`;
  const allowed=(g,incoming,outgoing)=>!incoming||
    !(incoming.slice(0,incoming.lastIndexOf('_'))===outgoing.slice(0,outgoing.lastIndexOf('_'))&&incoming!==outgoing)&&
    !g.denied.has(`${incoming}|${outgoing}`);
  function tree(start,g,startEdge=''){
    const initial=`${start}|${startEdge}`,stateDist=new Map([[initial,0]]),dist=new Map([[start,0]]),prev=new Map(),states=new Map([[start,[initial]]]),heap=new Heap();heap.push([0,initial,start,startEdge]);
    while(heap.length){const [d,key,node,incoming]=heap.pop();if(d!==stateDist.get(key))continue;for(const edge of g.adj.get(node)||[]){const outgoing=edgeId(edge);if(!allowed(g,incoming,outgoing))continue;const next=d+edge.length,nextKey=`${edge.to}|${outgoing}`;if(next<(stateDist.get(nextKey)??Infinity)){stateDist.set(nextKey,next);prev.set(nextKey,{key,edge});if(!states.has(edge.to))states.set(edge.to,[]);states.get(edge.to).push(nextKey);dist.set(edge.to,Math.min(next,dist.get(edge.to)??Infinity));heap.push([next,nextKey,edge.to,outgoing]);}}}
    return {dist,prev,stateDist,states,initial,g};
  }
  function pathTo(t,start,end,finalEdge=''){const choices=(t.states.get(end)||[]).filter(key=>!finalEdge||allowed(t.g,key.split('|').at(-1),finalEdge));choices.sort((a,b)=>t.stateDist.get(a)-t.stateDist.get(b));let at=choices[0];if(!at)return null;const hops=[];while(at!==t.initial){const step=t.prev.get(at);if(!step)return null;hops.push({segment:step.edge.segment,direction:step.edge.direction});at=step.key;if(hops.length>200)return null;}return hops.reverse();}
  function legal(route){const g=graph();return route.every((hop,i)=>i===0||allowed(g,`${route[i-1].segment}_${route[i-1].direction}`,`${hop.segment}_${hop.direction}`));}
  function startOptions(car,g){
    const first=car.route[0],road=g.roads.get(first.segment);if(!road)return [];
    if(first.direction==='reverse'&&road.oneway)return [];
    const position=Math.max(0,Math.min(road.length-20,car.depart_pos_m??0));
    return [{road,direction:first.direction,position,end:first.direction==='forward'?road.to:road.from,remaining:road.length-position}];
  }
  function apply(car,route,position,silent,arrivalPos){
    if(!route.length||route.length>200)throw Error('Trasa musí obsahovať 1 až 200 navzájom napojených úsekov.');
    car.route=route;car.depart_pos_m=Math.floor(position*10)/10;
    if(arrivalPos===undefined)delete car.arrival_pos_m;
    else car.arrival_pos_m=Math.floor(arrivalPos*10)/10;
    const global=S.world.map_objects?.cars.find(x=>x.id===car.id);
    if(global){global.route=structuredClone(route);global.road_id=route[0].segment;global.direction=route[0].direction;if(arrivalPos===undefined)delete global.arrival_pos_m;else global.arrival_pos_m=car.arrival_pos_m;}
    S.inspectorKey=null;if(!silent)editor.markDirty();else if(silent!== 'batch')editor.render();
  }
  function randomSeed(id){let value=(Number(S.scenario?.seed)||1)>>>0;for(const c of id)value=(Math.imul(value,1664525)+c.charCodeAt(0)+1013904223)>>>0;return value;}
  function random(id,silent=false){
    const car=S.demand.vehicles.find(x=>x.id===id);if(!car)throw Error('Auto neexistuje v tomto výreze.');
    const g=graph(),options=startOptions(car,g);if(!options.length)throw Error('Auto nie je na použiteľnej ceste.');
    const candidates=[];
    for(const option of options){const result=tree(option.end,g,`${option.road.id}_${option.direction}`);for(const [node,d] of result.dist){if(d<100)continue;const hops=pathTo(result,option.end,node);if(!hops||hops.length>=200)continue;const route=[{segment:option.road.id,direction:option.direction},...hops];if(!legal(route))continue;const total=option.remaining+d;candidates.push({total,route,position:option.position});}}
    candidates.sort((a,b)=>a.total-b.total);
    const preferred=candidates.filter(x=>x.total>=500&&x.total<=2400);
    const pool=preferred.length?preferred:candidates.slice(Math.max(0,candidates.length-20));
    if(!pool.length)throw Error('Z tejto cesty nevedie dostatočne dlhá prepojená trasa. Skús iný úsek.');
    const current=pool.findIndex(candidate=>candidate.route.length===car.route.length&&candidate.route.every((hop,i)=>hop.segment===car.route[i].segment&&hop.direction===car.route[i].direction));
    let index=randomSeed(id)%pool.length;
    if(current>=0&&pool.length>1){
      let stride=1+randomSeed(id)%(pool.length-1);
      const gcd=(a,b)=>b?gcd(b,a%b):a;
      while(gcd(stride,pool.length)!==1)stride=stride%pool.length+1;
      index=(current+stride)%pool.length;
    }
    const picked=pool[index];apply(car,picked.route,picked.position,silent);
    if(!silent)editor.status(`Náhodná platná trasa auta ${id}: ${picked.route.length} úsekov, ${Math.round(picked.total)} m.`);
    return picked;
  }
  function travelSpeed(car,road,direction='forward'){
    const cap=Math.max(.1,car.max_speed_mps??(S.mapMode==='real'?car.depart_speed_mps:S.world.simulation.vehicle_model?.manual_max_speed_mps??40));
    return Math.max(1,Math.min(road[`speed_${direction}_mps`]??road.speed_limit_mps,cap)*.8);
  }
  function targetTravelSeconds(car){
    const input=Number(document.getElementById('trafficTripPercent').value);
    if(!Number.isInteger(input)||input<20||input>100)throw Error('Cieľová dĺžka jazdy musí byť 20–100 % dostupného času.');
    const available=Math.max(1,S.world.simulation.duration_s-car.depart_s);
    const communicationEnd=S.world.simulation.duration_s;
    return Math.max(available*input/100,communicationEnd-car.depart_s+1);
  }
  function estimatedSeconds(car){
    if(!car?.route?.length)return 0;
    const g=graph();let seconds=0;
    car.route.forEach((hop,i)=>{const road=g.roads.get(hop.segment);if(!road)return;const start=i===0?car.depart_pos_m||0:0,end=i===car.route.length-1?car.arrival_pos_m??road.length:road.length;seconds+=Math.max(0,end-start)/travelSpeed(car,road,hop.direction);});
    return seconds;
  }
  function durationNotice(cars){
    const late=cars.map(car=>({id:car.id,estimated:estimatedSeconds(car),available:Math.max(0,S.world.simulation.duration_s-car.depart_s)})).filter(row=>row.estimated>row.available);
    if(!late.length)return '';
    const longest=Math.round(Math.max(...late.map(row=>row.estimated)));
    return ` Pozor: ${late.length===cars.length?'cieľ žiadneho auta':'cieľ '+late.length+' áut'} sa pri aktuálnej dĺžke ${S.world.simulation.duration_s} s pravdepodobne nestihne; najdlhší odhad je ${longest} s. Predĺž beh, zvýš rýchlosť alebo vyber bližší cieľ.`;
  }
  function randomWalk(id,silent='batch'){
    const car=S.demand.vehicles.find(x=>x.id===id);if(!car)throw Error('Auto neexistuje v aktuálnom výreze.');
    const g=graph(),first=startOptions(car,g)[0];if(!first)throw Error('Auto nie je na použiteľnej ceste.');
    const wanted=targetTravelSeconds(car),base=randomSeed(id);
    let best=null;
    for(let attempt=0;attempt<6;attempt++){
      let seed=(base^Math.imul(attempt+1,2654435761))>>>0||0x9e3779b9;
      const next=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
      const sideTrip=next()<.12,route=[{segment:first.road.id,direction:first.direction}],used=new Set([`${first.road.id}:${first.direction}`]);
      let road=first.road,direction=first.direction,position=first.position,node=first.end,seconds=0,total=0,arrival,sideTaken=false;
      while(route.length<=200){
        const speed=travelSpeed(car,road,direction),remaining=road.length-position,needed=(wanted-seconds)*speed;
        if(needed>=2&&needed<remaining-1){arrival=position+needed;seconds=wanted;total+=needed;break;}
        seconds+=remaining/speed;total+=remaining;
        if(seconds>=wanted-.25||route.length>=200)break;
        const edges=(g.adj.get(node)||[]).filter(edge=>edge.segment!==road.id&&!used.has(`${edge.segment}:${edge.direction}`)&&allowed(g,`${road.id}_${direction}`,edgeId(edge)));
        if(!edges.length)break;
        const incoming=direction==='forward'?road.shape:[...road.shape].reverse(),a=incoming.at(-2),b=incoming.at(-1),ix=b[0]-a[0],iy=b[1]-a[1],ilen=Math.hypot(ix,iy);
        const weighted=edges.map(edge=>{const nextRoad=g.roads.get(edge.segment),shape=edge.direction==='forward'?nextRoad.shape:[...nextRoad.shape].reverse(),dx=shape[1][0]-shape[0][0],dy=shape[1][1]-shape[0][1],cos=(ix*dx+iy*dy)/(ilen*Math.hypot(dx,dy)||1),priority=window.simulatorTraffic?.roadPriority(nextRoad.id)||1;return {edge,road:nextRoad,weight:(.4+6*Math.max(0,cos)**3)*priority};});
        const strongest=Math.max(...weighted.map(x=>x.weight)),sideOptions=weighted.filter(x=>x.weight<strongest*.6);
        const pool=sideTrip&&!sideTaken&&sideOptions.length?sideOptions:weighted;
        let draw=next()*pool.reduce((sum,x)=>sum+x.weight,0),chosen=pool.at(-1);for(const item of pool){draw-=item.weight;if(draw<=0){chosen=item;break;}}
        if(pool===sideOptions)sideTaken=true;
        road=chosen.road;direction=chosen.edge.direction;node=chosen.edge.to;position=0;
        route.push({segment:road.id,direction});used.add(`${road.id}:${direction}`);
      }
      if(total<20||!legal(route))continue;
      const plan={route,total,position:first.position,arrival,expected_s:seconds,target_s:wanted};
      if(!best||Math.abs(seconds-wanted)<Math.abs(best.expected_s-wanted))best=plan;
      if(Math.abs(seconds-wanted)<.01)break;
    }
    if(!best)throw Error('Z tejto cesty sa nedá vytvoriť náhodná prejazdná trasa.');
    apply(car,best.route,best.position,silent,best.arrival);
    if(!silent)editor.status(`Trasa auta ${id}: odhad jazdy ${Math.round(best.expected_s)} s z cieľových ${Math.round(wanted)} s${best.expected_s<wanted*.75?' (sieť neumožňuje dlhšiu trasu)':''}.`);
    return best;
  }
  function destination(p,roadId=null){
    const near=editor.nearestRoad(p,roadId);if(!near||near.d>(S.mapMode==='real'?25:35))throw Error('Klikni presne na jazdnú cestu v pracovnom výreze.');
    const g=graph(),target=g.roads.get(near.road.id);if(!target)throw Error('Cieľová cesta nie je v dopravnom grafe.');
    return {near,g,target};
  }
  function candidate(car,target,direction,arrival,g,options){
    let best=null;
    for(const option of options){
      const result=option.result;
        if(option.road.id===target.id&&option.direction===direction&&arrival>option.position+1){
          const direct={route:[{segment:target.id,direction}],total:arrival-option.position,position:option.position,arrival};
          if(!best||direct.total<best.total)best=direct;
        }
        const start=direction==='forward'?target.from:target.to,d=result.dist.get(start);
        if(d===undefined)continue;
        const hops=pathTo(result,option.end,start,`${target.id}_${direction}`);if(!hops)continue;
        const route=[{segment:option.road.id,direction:option.direction},...hops,{segment:target.id,direction}];
        if(route.length>200||!legal(route))continue;
        const total=option.remaining+d+arrival;
        if(!best||total<best.total)best={route,total,position:option.position,arrival};
    }
    return best;
  }
  function planToPoint(id,p,roadId=null){
    const car=S.demand.vehicles.find(x=>x.id===id);if(!car)throw Error('Auto už nie je v aktuálnom výreze.');
    const {near,g,target}=destination(p,roadId),options=startOptions(car,g).map(option=>({...option,result:tree(option.end,g,`${option.road.id}_${option.direction}`)}));
    let best=null;
    for(const direction of (target.oneway?['forward']:['forward','reverse'])){
      const arrival=Math.max(1,Math.min(target.length-1,direction==='forward'?near.at:target.length-near.at));
      const plan=candidate(car,target,direction,arrival,g,options);
      if(plan&&(!best||plan.total<best.total))best=plan;
    }
    if(!best)throw Error('Medzi autom a cieľovou cestou nie je prejazdná cesta.');
    S.routeTargetCar=null;S.groupPlanned=[];apply(car,best.route,best.position,false,best.arrival);
    editor.status(`Naplánovaná trasa auta ${id}: ${best.route.length} úsekov, približne ${Math.round(best.total)} m, odhad jazdy ${Math.round(estimatedSeconds(car))} s.${durationNotice([car])}`);
    return best;
  }
  function planGroup(ids,p,roadId=null){
    const cars=[...new Set(ids)].map(id=>S.demand.vehicles.find(car=>car.id===id));
    if(!cars.length||cars.some(car=>!car))throw Error('Vyber aspoň jedno auto z aktuálneho výrezu.');
    const {near,g,target}=destination(p,roadId),gap=12,span=(cars.length-1)*gap;
    if(target.length<span+2)throw Error(`Cieľová cesta je príliš krátka pre ${cars.length} áut s odstupom ${gap} m. Vyber dlhší úsek.`);
    const starts=cars.map(car=>startOptions(car,g).map(option=>({...option,result:tree(option.end,g,`${option.road.id}_${option.direction}`)})));
    let best=null;
    for(const direction of (target.oneway?['forward']:['forward','reverse'])){
      const clicked=direction==='forward'?near.at:target.length-near.at;
      const lead=Math.max(span+1,Math.min(target.length-1,clicked+span/2));
      const arrivals=cars.map((_,i)=>lead-i*gap);
      // Arrival positions are measured from the beginning of the chosen driving direction.
      // The vehicles therefore form one physical queue on a single road direction.
      const choices=cars.map((car,i)=>arrivals.map(at=>candidate(car,target,direction,at,g,starts[i])));
      const occupied=new Array(cars.length).fill(-1);
      const oneLaneQueue=cars.every(car=>car.route[0].segment===target.id&&car.route[0].direction===direction);
      if(oneLaneQueue){
        // Vehicles already on the destination lane cannot overtake a stopped leader.
        // Assign the farthest destination to the front vehicle, then work backwards.
        const frontFirst=cars.map((_,i)=>i).sort((a,b)=>cars[b].depart_pos_m-cars[a].depart_pos_m);
        for(let j=0;j<frontFirst.length;j++)occupied[j]=frontFirst[j];
        if(occupied.some((i,j)=>!choices[i][j]))continue;
      }else{
        const order=cars.map((_,i)=>i).sort((a,b)=>choices[a].filter(Boolean).length-choices[b].filter(Boolean).length);
        function assign(i,seen){
          const slots=choices[i].map((plan,j)=>({plan,j})).filter(x=>x.plan).sort((a,b)=>a.plan.total-b.plan.total);
          for(const {j} of slots){if(seen.has(j))continue;seen.add(j);if(occupied[j]<0||assign(occupied[j],seen)){occupied[j]=i;return true;}}
          return false;
        }
        if(!order.every(i=>assign(i,new Set())))continue;
      }
      const plans=occupied.map((carIndex,j)=>({car:cars[carIndex],...choices[carIndex][j]}));
      const total=plans.reduce((sum,plan)=>sum+plan.total,0);
      if(!best||total<best.total)best={plans,total,direction};
    }
    if(!best)throw Error('Pre všetky vybrané autá neexistuje prejazdná trasa k spoločnému cieľu. Vyber iný úsek.');
    for(const plan of best.plans)apply(plan.car,plan.route,plan.position,'batch',plan.arrival);
    S.routeTargetGroup=false;S.groupPlanned=best.plans.map(plan=>plan.car.id);
    editor.markDirty();
    editor.status(`Spoločný cieľ pre ${carCount(cars.length)}: ${target.id}, odstup cieľov ${gap} m. Trasy sú pripravené na simuláciu.${durationNotice(cars)}`);
    return best;
  }
  function clickDestination(p,roadId=null){if(!S.routeTargetCar&&!S.routeTargetGroup)return false;try{if(S.routeTargetGroup)planGroup(S.groupCars,p,roadId);else planToPoint(S.routeTargetCar,p,roadId);}catch(e){editor.status(e.message);}return true;}
  function sliceShape(shape,start,end){
    const points=[];let passed=0;
    for(let i=1;i<shape.length;i++){
      const a=shape[i-1],b=shape[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]);
      const lo=Math.max(start,passed),hi=Math.min(end,passed+length);
      if(length>0&&hi>=lo){
        for(const at of [lo,hi]){const t=(at-passed)/length,p=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];if(!points.length||Math.hypot(p[0]-points.at(-1)[0],p[1]-points.at(-1)[1])>0.001)points.push(p);}
      }
      passed+=length;
    }
    return points;
  }
  function geometry(car){
    if(!car?.route?.length)return [];
    const g=graph(),points=[];
    for(let i=0;i<car.route.length;i++){
      const hop=car.route[i],road=g.roads.get(hop.segment);if(!road)return [];
      const shape=hop.direction==='reverse'?[...road.shape].reverse():road.shape;
      const start=i===0?car.depart_pos_m||0:0,end=i===car.route.length-1?car.arrival_pos_m??road.length:road.length;
      for(const p of sliceShape(shape,start,end))if(!points.length||Math.hypot(p[0]-points.at(-1)[0],p[1]-points.at(-1)[1])>0.001)points.push(p);
    }
    return points;
  }
  function renderControls(car,box){
    const route=car.route||[],points=geometry(car),length=points.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-points[i][0],p[1]-points[i][1]),0);
    const countLabel=route.length===1?'úsek':route.length<5?'úseky':'úsekov';
    const info=document.createElement('p');info.textContent=`${route.length} ${countLabel} · približne ${Math.max(0,Math.round(length))} m · odhad jazdy ${Math.round(estimatedSeconds(car))} s`;box.append(info);
    if(car.arrival_pos_m!==undefined&&estimatedSeconds(car)>Math.max(0,S.world.simulation.duration_s-car.depart_s)){const warning=document.createElement('p');warning.className='route-duration-warning';warning.textContent=`Cieľ je pravdepodobne mimo ${S.world.simulation.duration_s} s behu; odhad jazdy ${Math.round(estimatedSeconds(car))} s.`;box.append(warning);}
    const randomButton=document.createElement('button');randomButton.type='button';randomButton.className='subtle';randomButton.textContent='Nová trasa podľa času behu';randomButton.onclick=()=>{try{randomWalk(car.id,false);}catch(e){editor.status(e.message);}};box.append(randomButton);
    const planButton=document.createElement('button');planButton.type='button';planButton.className='subtle';planButton.textContent=S.routeTargetCar===car.id?'Zrušiť výber cieľa':'Určiť cieľ kliknutím';planButton.onclick=()=>{S.routeTargetCar=S.routeTargetCar===car.id?null:car.id;S.routeTargetGroup=false;S.inspectorKey=null;editor.render();editor.status(S.routeTargetCar?`Klikni na cieľový bod na ceste auta ${car.id} v pracovnom výreze.`:'Výber cieľa zrušený.');};box.append(planButton);
  }
  let listKey='';
  function toggleGroup(id){S.groupCars=S.groupCars.includes(id)?S.groupCars.filter(x=>x!==id):[...S.groupCars,id];S.routeTargetGroup=false;S.groupPlanned=[];editor.render();}
  function renderGroupControls(){
    const panel=document.getElementById('groupRoutePanel');if(!panel)return;
    const cars=S.demand?.vehicles||[],key=cars.map(car=>car.id).join('\u001f');
    S.groupCars=S.groupCars.filter(id=>cars.some(car=>car.id===id));
    if(key!==listKey){listKey=key;const list=document.getElementById('groupRouteCars');list.replaceChildren();for(const car of cars){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=car.id;input.onchange=()=>toggleGroup(car.id);label.append(input,document.createTextNode(car.id));list.append(label);}}
    for(const input of document.querySelectorAll('#groupRouteCars input'))input.checked=S.groupCars.includes(input.value);
    document.getElementById('groupRouteCount').textContent=`${S.groupCars.length} vybraných`;
    const button=document.getElementById('groupRouteStart');button.disabled=!S.groupCars.length;button.textContent=S.routeTargetGroup?'Zrušiť výber cieľa':'Spoločný cieľ kliknutím';
    document.getElementById('groupRouteFit').disabled=!S.groupCars.length;
  }
  document.getElementById('groupRouteAll').onclick=()=>{S.groupCars=(S.demand?.vehicles||[]).map(car=>car.id);S.groupPlanned=[];S.routeTargetGroup=false;editor.render();};
  document.getElementById('groupRouteClear').onclick=()=>{S.groupCars=[];S.groupPlanned=[];S.routeTargetGroup=false;editor.render();};
  document.getElementById('groupRouteStart').onclick=()=>{if(!S.groupCars.length)return;S.routeTargetGroup=!S.routeTargetGroup;S.routeTargetCar=null;S.inspectorKey=null;editor.render();editor.status(S.routeTargetGroup?`Klikni na spoločný cieľ na ceste pre ${carCount(S.groupCars.length)}. Cieľové polohy budú vzdialené 12 m.`:'Výber spoločného cieľa zrušený.');};
  document.getElementById('groupRouteFit').onclick=()=>{
    if(!S.groupCars.length)return;
    const oldVehicles=structuredClone(S.demand.vehicles),oldGlobal=S.world.map_objects?.cars?structuredClone(S.world.map_objects.cars):null;
    try{
      const plans=S.groupCars.map(id=>randomWalk(id,'batch'));
      S.routeTargetGroup=false;S.routeTargetCar=null;S.groupPlanned=[];editor.markDirty();
      const short=plans.filter(plan=>plan.expected_s<plan.target_s*.75).length;
      editor.status(`Nové trasy pre ${plans.length} áut podľa dĺžky behu${short?`; pri ${short} je cestná sieť kratšia než cieľ`:''}.`);
    }catch(error){S.demand.vehicles=oldVehicles;if(oldGlobal)S.world.map_objects.cars=oldGlobal;S.inspectorKey=null;editor.render();editor.status(error.message);}
  };
  window.simulatorRoutes={random,randomWalk,estimatedSeconds,targetTravelSeconds,planToPoint,planGroup,clickDestination,renderControls,renderGroupControls,toggleGroup,geometry};
})();
