'use strict';

// Seeded placement on the currently generated road graph. Road speeds remain
// authoritative in SUMO; this creates trial demand, not measured traffic flow.
(() => {
  const editor=window.simulatorEditor,S=editor.state;
  const length=road=>road.shape.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-road.shape[i][0],p[1]-road.shape[i][1]),0);
  const classWeight=road=>({motorway:5,motorway_link:2.5,trunk:4,trunk_link:2.1,primary:3,primary_link:1.7,secondary:2,secondary_link:1.3,tertiary:1.5,rural:1.8,urban:1,residential:1,service:.35,living_street:.45}[road.road_class]||1);
  let priorities=new Map();
  function roadPriorities(rows){
    const atNode=new Map(),info=new Map();
    for(const {road,length:distance} of rows){
      info.set(road.id,{road,length:distance});
      for(const [node,points] of [[road.from,road.shape],[road.to,[...road.shape].reverse()]]){
        const a=points[0],b=points[1],dx=b[0]-a[0],dy=b[1]-a[1],norm=Math.hypot(dx,dy)||1;
        const list=atNode.get(node)||[];list.push({road,node,dx:dx/norm,dy:dy/norm});atNode.set(node,list);
      }
    }
    function extend(first,node,visited){
      let distance=0,current=first,at=node;
      for(let hop=0;hop<20;hop++){
        const away=(atNode.get(at)||[]).find(x=>x.road.id===current.id);if(!away)break;
        const options=(atNode.get(at)||[]).filter(x=>!visited.has(x.road.id));
        const ranked=options.map(x=>({x,cos:-(away.dx*x.dx+away.dy*x.dy)})).filter(x=>x.cos>.7).sort((a,b)=>b.cos-a.cos);
        if(!ranked.length)break;
        current=ranked[0].x.road;visited.add(current.id);distance+=info.get(current.id)?.length||0;at=current.from===at?current.to:current.from;
      }
      return distance;
    }
    const corridors=new Map();let max=1;
    for(const {road,length:distance} of rows){const corridor=distance+extend(road,road.from,new Set([road.id]))+extend(road,road.to,new Set([road.id]));corridors.set(road.id,corridor);max=Math.max(max,corridor);}
    priorities=new Map(rows.map(({road})=>[road.id,classWeight(road)*(.35+2.65*(corridors.get(road.id)/max)**3)]));
  }
  function spawn(count){
    if(!Number.isSafeInteger(count)||count<1||count>500)throw Error('V jednom kroku vyber 1 až 500 áut. Pre ďalšie autá generovanie zopakuj.');
    const percent=Number(document.getElementById('trafficTripPercent').value);
    if(!Number.isInteger(percent)||percent<20||percent>100)throw Error('Cieľová dĺžka jazdy musí byť 20–100 % dostupného času.');
    if(!S.world?.roads?.segments?.length)throw Error('Najprv načítaj alebo nakresli jazdné cesty.');
    const originalCount=S.demand.vehicles.length,originalSource=S.scenario.source_id,originalPolicy=S.scenario.node_policy?structuredClone(S.scenario.node_policy):null;
    const roads=S.world.roads.segments.map(road=>({road,length:length(road)})).filter(x=>x.length>=35&&x.road.speed_limit_mps>0);
    if(!roads.length)throw Error('Na mape nie je cesta dlhá aspoň 35 m.');
    roadPriorities(roads);
    let seed=((Number(S.scenario.seed)||1)^(originalCount*2654435761))>>>0;
    const next=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
    const laneWeight=road=>{const forward=road.lanes_forward??road.lanes_each_direction??1;if(road.oneway)return forward;return (forward+(road.lanes_reverse??road.lanes_each_direction??1))/2;};
    const weighted=roads.map(x=>({...x,w:x.length*Math.max(1,laneWeight(x.road))*(priorities.get(x.road.id)||1)}));
    const totalWeight=weighted.reduce((sum,x)=>sum+x.w,0),occupied=new Map();
    for(const car of S.demand.vehicles){const hop=car.route?.[0];if(!hop)continue;const key=`${hop.segment}:${hop.direction}`,positions=occupied.get(key)||[];positions.push(car.depart_pos_m||0);occupied.set(key,positions);}
    const usedIds=new Set(S.demand.vehicles.map(car=>car.id));
    for(const car of S.world.map_objects?.cars||[])usedIds.add(car.id);
    let nextId=0;while(usedIds.has(`car${nextId}`))nextId++;
    const made=[],plans=[];let attempts=0;
    try{
      while(made.length<count&&attempts<count*120){
        attempts++;
        let draw=next()*totalWeight,choice=weighted.at(-1);
        for(const row of weighted){draw-=row.w;if(draw<=0){choice=row;break;}}
        const road=choice.road,direction=road.oneway?'forward':next()<.5?'forward':'reverse';
        const position=10+next()*Math.max(0,choice.length-30),key=`${road.id}:${direction}`;
        if((occupied.get(key)||[]).some(at=>Math.abs(at-position)<15))continue;
        const id=`car${nextId}`;
        const car={id,depart_s:0,depart_speed_mps:10,max_speed_mps:36.1,depart_speed_mode:'max',depart_pos_m:Math.floor(position*10)/10,route:[{segment:road.id,direction}],technologies:['its_g5']};
        S.demand.vehicles.push(car);
        let plan;try{plan=window.simulatorRoutes.randomWalk(id,'batch');}catch(_){S.demand.vehicles.pop();continue;}
        if(S.scenario.node_policy)S.scenario.node_policy.cars[id]={ground:'all'};
        if(!S.scenario.source_id){S.scenario.source_id=id;if(S.world.flows?.[0])S.world.flows[0].source=id;}
        const positions=occupied.get(key)||[];positions.push(position);occupied.set(key,positions);
        made.push(id);plans.push(plan);usedIds.add(id);while(usedIds.has(`car${nextId}`))nextId++;
      }
      if(made.length!==count)throw Error(`Na tejto cestnej sieti sa podarilo pripraviť ${made.length} z ${count} áut. Vyber menší počet alebo dlhší výrez ciest.`);
    }catch(error){
      S.demand.vehicles.length=originalCount;S.scenario.source_id=originalSource;
      if(S.world.flows?.[0])S.world.flows[0].source=originalSource;
      if(originalPolicy)S.scenario.node_policy=originalPolicy;
      throw error;
    }
    S.selected=null;S.inspectorKey=null;S.groupCars=[];S.groupPlanned=[];S.routeTargetCar=null;S.routeTargetGroup=false;
    editor.rebuildObjectPicker();editor.markDirty();
    const short=plans.filter(plan=>plan.expected_s<plan.target_s*.75).length;
    const windowEnd=S.world.simulation.duration_s;
    const early=plans.filter((plan,i)=>S.demand.vehicles.find(c=>c.id===made[i]).depart_s+plan.expected_s<windowEnd).length;
    editor.status(`Vygenerovaných ${made.length} áut na ${new Set(made.map(id=>S.demand.vehicles.find(c=>c.id===id).route[0].segment)).size} cestách. Cieľ jazdy ${percent} % času pohybu${short?`; ${short} trás je kratších pre obmedzenú sieť`:''}${early?`; ${early} áut zostane po príchode do cieľa stáť do konca komunikačného okna`:''}.`);
    return made;
  }
  document.getElementById('spawnTraffic').onclick=()=>{try{spawn(Number(document.getElementById('spawnCount').value));}catch(error){editor.status(error.message);}};
  window.simulatorTraffic={spawn,roadPriority:id=>priorities.get(id)||1};
})();
