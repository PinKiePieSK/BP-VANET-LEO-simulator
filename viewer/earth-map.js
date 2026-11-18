const maplibregl=window.maplibregl;

const editor=window.simulatorEditor;
const extent=()=>editor.state.world?.width_m||editor.state.world?.extent_m||2000;
const height=()=>editor.state.world?.height_m||editor.state.world?.extent_m||2000;
const earth=document.getElementById('earthMap');
const shell=earth.closest('.orbit-shell');
const wholeEarthZoom=()=>0.45;
const mode=document.getElementById('earthMode');
const note=document.getElementById('earthNote');
const realStyle='https://tiles.openfreemap.org/styles/liberty';
const emptyStyle={version:8,sources:{land:{type:'geojson',data:'/globe-land.json'}},layers:[
  {id:'ocean',type:'background',paint:{'background-color':'#14313d'}},
  {id:'land',type:'fill',source:'land',paint:{'fill-color':'#245056','fill-outline-color':'#648688'}}
]};
const empty={type:'FeatureCollection',features:[]};
const point=(coordinates,properties={})=>({type:'Feature',geometry:{type:'Point',coordinates},properties});
const line=(coordinates,properties={})=>({type:'Feature',geometry:{type:'LineString',coordinates},properties});
const collection=features=>({type:'FeatureCollection',features});

function basis(){
  const g=editor.state.world.georeference,lat=g.latitude_deg*Math.PI/180,lon=g.longitude_deg*Math.PI/180;
  const sl=Math.sin(lat),cl=Math.cos(lat),so=Math.sin(lon),co=Math.cos(lon),a=6378137,e2=6.69437999014e-3;
  const n=a/Math.sqrt(1-e2*sl*sl);
  return {g,a,e2,origin:[(n+g.height_m)*cl*co,(n+g.height_m)*cl*so,(n*(1-e2)+g.height_m)*sl],east:[-so,co,0],north:[-sl*co,-sl*so,cl]};
}
function localToGeo(x,y,b=basis()){
  const dx=x-b.g.anchor_x_m,dy=y-b.g.anchor_y_m;
  const [X,Y,Z]=b.origin.map((v,i)=>v+dx*b.east[i]+dy*b.north[i]);
  const p=Math.hypot(X,Y),lon=Math.atan2(Y,X),e2=b.e2,a=b.a;
  let lat=Math.atan2(Z,p*(1-e2));
  for(let i=0;i<6;i++){const n=a/Math.sqrt(1-e2*Math.sin(lat)**2);lat=Math.atan2(Z+e2*n*Math.sin(lat),p);}
  return [lon*180/Math.PI,lat*180/Math.PI];
}
function geoToLocal(lonDeg,latDeg,b=basis()){
  const lat=latDeg*Math.PI/180,lon=lonDeg*Math.PI/180,sl=Math.sin(lat),cl=Math.cos(lat),so=Math.sin(lon),co=Math.cos(lon);
  const n=b.a/Math.sqrt(1-b.e2*sl*sl),h=b.g.height_m;
  const xyz=[(n+h)*cl*co,(n+h)*cl*so,(n*(1-b.e2)+h)*sl];
  const d=xyz.map((v,i)=>v-b.origin[i]);
  return {x:b.g.anchor_x_m+d.reduce((v,q,i)=>v+q*b.east[i],0),y:b.g.anchor_y_m+d.reduce((v,q,i)=>v+q*b.north[i],0)};
}
window.simulatorEarthCoordinates={localToGeo,geoToLocal};

let map,groundMap,ready=false,lastSatellite=0,lastEditor=0,lastEditorKey='',lastOrbitDraw=0,lastOrbitKey='',lastOrbitPreview=null,lastOrbitMotion=null,lastOrbitData=null,lastGroundKey='',renderedMode=mode.value;
const originalVisibility=new WeakMap();
const layerOn=id=>document.getElementById(id).checked;
function category(layer){
  const source=layer['source-layer'],id=layer.id;
  if(source==='poi'||source==='aerodrome_label'||source==='water_name'||id==='label_other'||id==='highway-name-path'||id.includes('shield'))return 'hidden';
  if(source==='transportation_name')return id.startsWith('highway-name-')?'layerStreetNames':'hidden';
  if(source==='place'){
    if(id.startsWith('label_country')||id==='label_state')return 'layerCountryNames';
    if(['label_city','label_city_capital','label_town','label_village'].includes(id))return 'layerPlaceNames';
    return 'hidden';
  }
  if(source==='waterway')return 'layerRivers';
  if(source==='building')return 'layerBuilding';
  if(source==='transportation'&&layer.type!=='symbol')return 'layerBaseRoad';
  return null;
}
function rememberStyle(displayMap){
  originalVisibility.set(displayMap,new Map(displayMap.getStyle().layers.map(layer=>[layer.id,layer.layout?.visibility||'visible'])));
}
function applyBaseLayers(displayMap){
  if(!displayMap||!originalVisibility.has(displayMap))return;
  const defaults=originalVisibility.get(displayMap);
  for(const layer of displayMap.getStyle().layers){
    const group=category(layer);
    if(!group)continue;
    const expected=group==='hidden'||!layerOn(group)?'none':defaults.get(layer.id)||'visible';
    if((layer.layout?.visibility||'visible')!==expected)displayMap.setLayoutProperty(layer.id,'visibility',expected);
  }
}
function syncGround(){
  if(!groundMap||!editor.state.world)return;
  const holder=document.getElementById('groundBasemap'),svg=document.getElementById('groundMap');
  const size=svg.clientWidth,v=editor.state.view,g=editor.state.world.georeference;
  const key=[size,v.x,v.y,v.w,v.h,g.latitude_deg,g.longitude_deg,g.height_m,mode.value].join(':');
  if(key===lastGroundKey)return;
  lastGroundKey=key;
  holder.style.width=svg.clientWidth+'px';
  holder.style.height=svg.clientHeight+'px';
  holder.style.left='0px';
  holder.style.top='0px';
  if(mode.value!=='real'){holder.closest('.map-shell').classList.remove('has-basemap');return;}
  holder.closest('.map-shell').classList.add('has-basemap');
  groundMap.resize();
  const center=localToGeo(v.x+v.w/2,height()-v.y-v.h/2);
  const metersPerPixel=v.w/size;
  const zoom=Math.log2(78271.51696402048*Math.cos(center[1]*Math.PI/180)/metersPerPixel);
  groundMap.jumpTo({center,zoom,pitch:0,bearing:0});
}
window.simulatorEarthSyncGround=syncGround;
function initializeGround(){
  if(groundMap)return;
  const holder=document.getElementById('groundBasemap');
  holder.closest('.map-shell').classList.add('has-basemap');
  groundMap=new maplibregl.Map({container:holder,style:realStyle,center:[17.1077,48.1486],zoom:14,interactive:false,attributionControl:false});
  groundMap.on('style.load',()=>{rememberStyle(groundMap);applyBaseLayers(groundMap);syncGround();});
  syncGround();
}
function addOverlay(){
  const lightMap=mode.value==='real';
  for(const id of ['experiment-site','editor-area','editor-buildings','editor-roads','editor-road-selected','editor-route','editor-objects','editor-draft','reference-rsus','orbit-satellites','orbit-footprints','packet-links'])map.addSource(id,{type:'geojson',data:empty});
  map.addLayer({id:'orbit-footprint-fill',type:'fill',source:'orbit-footprints',maxzoom:8,
    paint:{'fill-color':'#f4d278','fill-opacity':.09}});
  map.addLayer({id:'orbit-footprint-outline',type:'line',source:'orbit-footprints',maxzoom:8,
    paint:{'line-color':'#f4d278','line-width':1.4,'line-opacity':.65,'line-dasharray':[4,3]}});
  map.addLayer({id:'orbit-other',type:'circle',source:'orbit-satellites',filter:['==',['get','kind'],'other'],maxzoom:12,
    paint:{'circle-color':lightMap?'#215377':'#d1e4e5','circle-radius':lightMap?2.4:2,'circle-opacity':lightMap?.86:.72}});
  map.addLayer({id:'orbit-visible',type:'circle',source:'orbit-satellites',filter:['==',['get','kind'],'visible'],maxzoom:12,
    paint:{'circle-color':lightMap?'#56808b':'#5c8e9b','circle-radius':3,'circle-stroke-color':lightMap?'#f7faf6':'#17343d','circle-stroke-width':1}});
  map.addLayer({id:'orbit-physical',type:'circle',source:'orbit-satellites',filter:['==',['get','kind'],'physical'],maxzoom:12,
    paint:{'circle-color':lightMap?'#008f83':'#6ce0cc','circle-radius':4,'circle-stroke-color':lightMap?'#f7faf6':'#17343d','circle-stroke-width':1.2}});
  map.addLayer({id:'orbit-active-outside',type:'circle',source:'orbit-satellites',filter:['==',['get','kind'],'active_outside'],maxzoom:12,
    paint:{'circle-color':'#e86d7e','circle-radius':7,'circle-stroke-color':'#19262a','circle-stroke-width':2}});
  map.addLayer({id:'orbit-active-halo',type:'circle',source:'orbit-satellites',filter:['==',['get','kind'],'active'],maxzoom:12,
    paint:{'circle-color':'#ffb83f','circle-radius':12,'circle-opacity':.28}});
  map.addLayer({id:'orbit-active',type:'circle',source:'orbit-satellites',filter:['==',['get','kind'],'active'],maxzoom:12,
    paint:{'circle-color':lightMap?'#f3af32':'#f4d278','circle-radius':7,'circle-stroke-color':'#19262a','circle-stroke-width':2.5}});
  map.addLayer({id:'packet-link-casing',type:'line',source:'packet-links',paint:{'line-color':'#12232b','line-width':['case',['get','selected'],9,7],'line-opacity':['case',['get','dimmed'],.25,.95]}});
  map.addLayer({id:'packet-link-line',type:'line',source:'packet-links',paint:{'line-color':['case',['get','selected'],'#fff0ab',['match',['get','visualKind'],'v2v','#1769ff','v2r','#00a65a','r2v','#e02985','satellite','#ff8500','isl','#8651e5','#ffffff']],'line-width':['case',['get','selected'],5,3.5],'line-opacity':['case',['get','dimmed'],.25,.98]}});
  map.addLayer({id:'packet-link-hit',type:'line',source:'packet-links',paint:{'line-color':'#ffffff','line-width':16,'line-opacity':.01}});
  map.addLayer({id:'editor-area-fill',type:'fill',source:'editor-area',paint:{'fill-color':'#e9bb72','fill-opacity':0.035}});
  map.addLayer({id:'editor-area-line',type:'line',source:'editor-area',paint:{'line-color':'#f4b65c','line-width':2,'line-dasharray':[4,3]}});
  map.addLayer({id:'editor-buildings-fill',type:'fill',source:'editor-buildings',paint:{'fill-color':'#a78070','fill-opacity':.65,'fill-outline-color':'#f5c2a3'}});
  map.addLayer({id:'editor-roads-outline',type:'line',source:'editor-roads',paint:{'line-color':'#103a42','line-width':7,'line-opacity':0.85}});
  map.addLayer({id:'editor-roads-line',type:'line',source:'editor-roads',paint:{'line-color':'#78d2c3','line-width':3.5,'line-opacity':0.95}});
  map.addLayer({id:'editor-roads-hit',type:'line',source:'editor-roads',paint:{'line-color':'#78d2c3','line-width':14,'line-opacity':0}});
  map.addLayer({id:'editor-road-selected-outline',type:'line',source:'editor-road-selected',paint:{'line-color':'#17262a','line-width':13}});
  map.addLayer({id:'editor-road-selected-line',type:'line',source:'editor-road-selected',paint:{'line-color':'#ffe29a','line-width':7}});
  map.addLayer({id:'editor-route-outline',type:'line',source:'editor-route',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':'#17262a','line-width':10}});
  map.addLayer({id:'editor-route-line',type:'line',source:'editor-route',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':'#ffe29a','line-width':5}});
  map.addLayer({id:'editor-draft-line',type:'line',source:'editor-draft',paint:{'line-color':'#ffe297','line-width':3,'line-dasharray':[2,2]}});
  map.addLayer({id:'reference-rsus-circle',type:'circle',source:'reference-rsus',minzoom:7,
    paint:{'circle-color':'#c796f2','circle-radius':6,'circle-stroke-color':'#281739','circle-stroke-width':2}});
  map.addLayer({id:'editor-objects-circle',type:'circle',source:'editor-objects',minzoom:7,
    paint:{'circle-color':['match',['get','type'],'car','#e7b362','rsu','#7cc8ba','#d5d5d5'],
      'circle-radius':['match',['get','type'],'car',6,'rsu',8,5],'circle-opacity':['case',['get','active'],1,.5],'circle-stroke-color':'#102126','circle-stroke-width':2}});
  map.addLayer({id:'experiment-site-circle',type:'circle',source:'experiment-site',
    paint:{'circle-color':'#f4b65c','circle-radius':7,'circle-stroke-color':'#fff2d6','circle-stroke-width':2}});
  map.addLayer({id:'experiment-site-label',type:'symbol',source:'experiment-site',layout:{'text-field':'Miesto pokusu','text-font':['Noto Sans Regular'],'text-size':12,'text-offset':[0,1.5],'text-anchor':'top'},paint:{'text-color':'#fff2d6','text-halo-color':'#102126','text-halo-width':1.5}});
  for(const id of ['packet-link-casing','packet-link-line','packet-link-hit'])map.moveLayer(id,'editor-objects-circle');
}
function setSource(id,features){map.getSource(id)?.setData(collection(features));}
let referenceRsus=[],referenceKey='',referenceRequest=0;
function referenceEnabled(){return mode.value==='real'&&document.getElementById('layerReferenceRsu').checked;}
function drawReferenceRsus(){
  const group=document.getElementById('mapReferenceRsus');group.replaceChildren();
  if(!referenceEnabled())return;
  const radius=Math.max(3,Math.min(14,editor.state.view.w*5/Math.max(1,document.getElementById('groundMap').clientWidth)));
  for(const row of referenceRsus){const p=geoToLocal(row.longitude_deg,row.latitude_deg);
    if(p.x<0||p.x>extent()||p.y<0||p.y>height())continue;
    const node=document.createElementNS('http://www.w3.org/2000/svg','circle');
    for(const [key,value] of Object.entries({cx:p.x,cy:height()-p.y,r:radius,fill:'#c796f2',stroke:'#281739','stroke-width':2,'vector-effect':'non-scaling-stroke','pointer-events':'none'}))node.setAttribute(key,String(value));
    group.append(node);
  }
}
async function loadReferenceRsus(){
  const status=document.getElementById('referenceRsuStatus');
  if(!referenceEnabled()){referenceRequest++;referenceKey='';referenceRsus=[];status.hidden=true;render();return;}
  const geo=editor.state.world.georeference,key=JSON.stringify([geo,extent(),height()]);
  if(key===referenceKey)return;
  referenceKey=key;referenceRsus=[];const request=++referenceRequest;
  status.hidden=false;status.textContent='Načítavam evidované polohy RSU z verejného registra USA…';
  const params=new URLSearchParams({lat:String(geo.latitude_deg),lon:String(geo.longitude_deg),anchor_x:String(geo.anchor_x_m),anchor_y:String(geo.anchor_y_m),width_m:String(extent()),height_m:String(height())});
  try{
    const response=await fetch('/api/simulator/rsu-reference?'+params),data=await response.json();
    if(!response.ok)throw Error(data.error||`HTTP ${response.status}`);
    if(request!==referenceRequest||!referenceEnabled())return;
    referenceRsus=data.records;
    status.replaceChildren();
    status.append(document.createTextNode(`${referenceRsus.length} evidovaných polôh RSU vo výreze · USA, register 09/2025. Poloha nie je potvrdenie prevádzky ani typu rádia. `));
    const link=document.createElement('a');link.href=data.source;link.target='_blank';link.rel='noopener';link.textContent='Zdroj US DOT ↗';status.append(link);
    render();
  }catch(error){if(request===referenceRequest){referenceRsus=[];status.textContent=`Register RSU sa nenačítal: ${error.message}`;render();}}
}
window.simulatorEarthLoadReferenceRsus=loadReferenceRsus;
function editorFeatures(){
  const s=editor.state,b=basis(),w=s.world;
  const square=[[0,0],[extent(),0],[extent(),height()],[0,height()],[0,0]].map(([x,y])=>localToGeo(x,y,b));
  setSource('editor-area',layerOn('layerSite')?[{type:'Feature',geometry:{type:'Polygon',coordinates:[square]},properties:{}}]:[]);
  const allBuildings=window.simulatorBuildings?.list()||[];
  const shownBuildings=s.mapMode==='empty'?allBuildings:s.selected?.type==='building'?allBuildings.filter(row=>row.id===s.selected.id):[];
  setSource('editor-buildings',shownBuildings.map(row=>({type:'Feature',geometry:{type:'Polygon',coordinates:[row.polygon_xy_m.concat([row.polygon_xy_m[0]]).map(([x,y])=>localToGeo(x,y,b))]},properties:{id:row.id,type:'building'}})));
  setSource('editor-roads',layerOn('layerRoad')?w.roads.segments.map(r=>line(r.shape.map(([x,y])=>localToGeo(x,y,b)),{id:r.id,name:r.name||'',road_class:r.road_class||''})):[]);
  const selectedRoad=s.selected?.type==='road'?w.roads.segments.find(r=>r.id===s.selected.id):null;
  setSource('editor-road-selected',layerOn('layerRoad')&&selectedRoad?[line(selectedRoad.shape.map(([x,y])=>localToGeo(x,y,b)),{id:selectedRoad.id})]:[]);
  const selected=s.selected?.type==='car'?s.demand.vehicles.find(c=>c.id===s.selected.id):null;
  const byId=new Map(w.roads.segments.map(r=>[r.id,r]));
  const routeShape=layerOn('layerRoad')&&selected?window.simulatorRoutes?.geometry(selected)||[]:[];
  setSource('editor-route',routeShape.length>1?[line(routeShape.map(([x,y])=>localToGeo(x,y,b)),{id:selected.id})]:[]);
  const store=globalStore(),objects=[];
  if(store&&!s.replay){
    if(layerOn('layerRsu'))for(const r of store.rsus)objects.push(point([r.longitude_deg,r.latitude_deg],{id:r.id,type:'rsu',active:w.rsus.some(x=>x.id===r.id)}));
    if(layerOn('layerCar'))for(const c of store.cars)objects.push(point([c.longitude_deg,c.latitude_deg],{id:c.id,type:'car',active:s.demand.vehicles.some(x=>x.id===c.id)}));
  }else{
    if(layerOn('layerRsu'))for(const r of w.rsus)objects.push(point(localToGeo(r.x_m,r.y_m,b),{id:r.id,type:'rsu',active:true}));
    if(layerOn('layerCar'))for(const car of s.demand.vehicles){const pos=editor.replayCar(car.id)||editor.carPosition(car);if(pos)objects.push(point(localToGeo(pos.x,pos.y,b),{id:car.id,type:'car',active:true}));}
  }
  setSource('editor-objects',objects);
  setSource('reference-rsus',referenceEnabled()?referenceRsus.map(row=>point([row.longitude_deg,row.latitude_deg],{id:row.id,label:row.label})):[]);
  drawReferenceRsus();
  setSource('editor-draft',s.draft.length>1?[line(s.draft.map(p=>localToGeo(p.x,p.y,b)))]:[]);
  setSource('experiment-site',layerOn('layerSite')?[point([b.g.longitude_deg,b.g.latitude_deg])]:[]);
}
function renderSky(data){
  const panel=document.getElementById('satelliteSky'),plot=document.getElementById('satelliteSkyPlot');
  const visible=(data.sky||[]).filter(row=>row.el>=0);
  panel.hidden=!document.getElementById('layerSat').checked||!visible.length;
  if(panel.hidden)return;
  const ns='http://www.w3.org/2000/svg',add=(tag,attrs)=>{const node=document.createElementNS(ns,tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));plot.append(node);return node;};
  plot.replaceChildren();
  add('circle',{cx:90,cy:90,r:73,fill:'#102b36',stroke:'#80aeb1','stroke-width':2});
  for(const r of [36,72])add('circle',{cx:90,cy:90,r,fill:'none',stroke:'#456e75','stroke-width':1});
  for(const [label,x,y] of [['S',90,13],['J',90,174],['Z',13,94],['V',167,94]]){const t=add('text',{x,y,fill:'#adc8c8','font-size':10,'text-anchor':'middle'});t.textContent=label;}
  for(const row of visible.filter(row=>!row.active).slice(0,1000)){
    const r=72*(90-row.el)/90,a=row.az*Math.PI/180;add('circle',{cx:90+r*Math.sin(a),cy:90-r*Math.cos(a),r:2,fill:row.physical?'#69d7cb':'#5c8e9b',opacity:.8});
  }
  for(const row of visible.filter(row=>row.active)){
    const r=72*(90-row.el)/90,a=row.az*Math.PI/180,x=90+r*Math.sin(a),y=90-r*Math.cos(a);
    const dot=add('circle',{cx:x,cy:y,r:5,fill:row.physical?'#f4d278':'#e86d7e',stroke:'#172529','stroke-width':2});
    const title=document.createElementNS(ns,'title');title.textContent=`Satelit ${row.id}, azimut ${row.az.toFixed(0)}°, výška ${row.el.toFixed(0)}°`;dot.append(title);
  }
  document.getElementById('satelliteSkyNote').textContent=`${visible.filter(row=>row.active).length} v paketovom podgrafe · ${visible.filter(row=>row.physical).length} fyzikálnych kandidátov · ${visible.length} nad maskou`;
}
function renderPacketLinks(orbitData){
  const state=editor.state,seen=new Set,features=[];
  if(!state.replay||!layerOn('layerPackets')){setSource('packet-links',[]);return;}
  const sat=new Map((orbitData?.features||[]).map(f=>[f.properties.id,f.geometry.coordinates]));
  function location(node){
    if(node==='gateway'){
      const gateway=state.scenario?.satellite?.gateway;
      return gateway?[gateway[1],gateway[0]]:null;
    }
    const catalog=state.replay.satelliteNodeCatalog?.get(node)??
      (node.startsWith('sat-')?Number(node.slice(4)):undefined);
    if(catalog!==undefined)return sat.get(catalog)||null;
    const local=editor.groundPosition(node);
    return local?localToGeo(local.x,local.y):null;
  }
  for(const packet of editor.activePacketLinks()){
    const key=`${packet.from}:${packet.to}:${packet.kind}`;
    if(seen.has(key))continue;
    seen.add(key);if(features.length>=100)break;
    const a=location(packet.from),b=location(packet.to);
    if(!a||!b)continue;
    const selected=!!state.linkFilter&&state.linkFilter.from===packet.from&&state.linkFilter.to===packet.to&&state.linkFilter.kind===packet.kind;
    features.push(line([a,b],{from:packet.from,to:packet.to,kind:packet.kind,visualKind:editor.linkVisualKind(packet),id:packet.id,selected,dimmed:!!state.linkFilter&&!selected}));
  }
  setSource('packet-links',features);
}
function render(){
  if(!ready||!editor.state.world)return;
  if(referenceEnabled()&&referenceKey!==JSON.stringify([editor.state.world.georeference,extent(),height()]))loadReferenceRsus();
  else if(!referenceEnabled()&&(referenceKey||referenceRsus.length))loadReferenceRsus();
  syncGround();
  const now=performance.now(),g=window.simulatorGlobeState;
  const state=editor.state,geo=state.world.georeference,view=state.view;
  const playing=(!!g?.playing&&!!g?.motion)||!!state.playing;
  const editorKey=[state.world.roads.segments.length,state.world.rsus.length,state.demand.vehicles.length,state.draft.length,state.selected?.type,state.selected?.id,geo.latitude_deg,geo.longitude_deg,view.x,view.y,view.w,view.h,state.time,mode.value].join(':');
  if(!playing||lastEditor===0||editorKey!==lastEditorKey){editorFeatures();lastEditor=now;lastEditorKey=editorKey;}
  const dense=(g?.motion?.catalog_ids?.length||0)>1000;
  const drawInterval=playing?(dense?66:33):0;
  if(!playing||now-lastOrbitDraw>=drawInterval){
    const ids=state.orbitDirty?'':(state.scenario?.satellite?.catalog_ids||[]).join(',');
    const key=`${state.orbitRequest}:${g?.motion?.group||''}:${playing?(g.time||0).toFixed(3):(g?.time||0).toFixed(1)}:${layerOn('layerSat')}:${layerOn('layerPhysicalFootprint')}:${layerOn('layerPackets')}:${state.linkFilter?.from||''}:${state.linkFilter?.to||''}:${state.orbitDirty}:${ids}`;
    if(key!==lastOrbitKey||state.orbitPreview!==lastOrbitPreview||g?.motion!==lastOrbitMotion){
      const data=window.simulatorOrbitMapData();lastOrbitData=data;
      setSource('orbit-satellites',layerOn('layerSat')?data.features:[]);
      setSource('orbit-footprints',layerOn('layerPhysicalFootprint')?data.footprints:[]);
      renderPacketLinks(data);
      lastOrbitKey=key;lastOrbitPreview=state.orbitPreview;lastOrbitMotion=g?.motion||null;
    }
    lastOrbitDraw=now;
  }
  const skyInterval=dense?1000:400;
  if(!playing||now-lastSatellite>=skyInterval){
    const data=lastOrbitData;
    renderSky(data||{sky:[]});
    const label=document.getElementById('orbitInfo');
    label.textContent=data?.features.length?`${data.features.length.toLocaleString('sk-SK')} družíc · ${data.visible} nad maskou · ${data.possible} fyzikálnych kandidátov`:state.orbitLoading?'Načítavam konšteláciu…':state.orbitError||(!state.scenario?.satellite?'Vyber satelitný režim.':!state.world.rsus.length?'Pridaj RSU, aby sa určila viditeľnosť satelitov.':'Načítaj satelitný scenár alebo náhľad pohybu.');
    document.getElementById('orbitTimeLabel').textContent=(data?.time||0).toLocaleString('sk-SK',{maximumFractionDigits:1})+' s';
    document.getElementById('orbitTime').value=String(data?.time||0);
    lastSatellite=now;
  }
  if(playing){document.getElementById('orbitTimeLabel').textContent=g.time.toLocaleString('sk-SK',{maximumFractionDigits:1})+' s';document.getElementById('orbitTime').value=String(g.time);}
}
window.renderEarthMap=render;
window.simulatorEarthRefreshLayers=()=>{lastEditor=0;applyBaseLayers(map);applyBaseLayers(groundMap);render();};
window.simulatorEarthFollowSite=()=>{
  if(!map||!editor.state.world)return;
  const g=editor.state.world.georeference;
  map.easeTo({center:[g.longitude_deg,g.latitude_deg],duration:350});
  render();
};
function updateNote(){note.textContent=mode.value==='real'?'Reálna mapa: autá na cesty, RSU na mapu.':'Prázdna mapa: kreslenie ciest a budov.';}
function setMode(){
  if(!map)return;
  if(mode.value!=='real'){roadRequest++;roadLoadingKey='';if(roadTimer)clearTimeout(roadTimer);editor.state.roadNetworkLoading=false;}
  if(renderedMode!==mode.value){ready=false;window.simulatorEarthReady=false;shell.classList.remove('earth-ready');lastOrbitKey='';lastGroundKey='';renderedMode=mode.value;map.setStyle(mode.value==='real'?realStyle:emptyStyle);}
  updateNote();syncGround();window.renderGlobe?.();
}
window.simulatorEarthApplyMode=setMode;
function clipSegment(a,b){
  let lo=0,hi=1,dx=b.x-a.x,dy=b.y-a.y;
  for(const [p,q] of [[-dx,a.x],[dx,extent()-a.x],[-dy,a.y],[dy,height()-a.y]]){
    if(Math.abs(p)<1e-9){if(q<0)return null;continue;}
    const t=q/p;
    if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);
    if(lo>hi)return null;
  }
  return [{x:a.x+lo*dx,y:a.y+lo*dy},{x:a.x+hi*dx,y:a.y+hi*dy}];
}
function roadLines(feature){
  const g=feature.geometry;
  if(g?.type==='LineString')return [g.coordinates];
  if(g?.type==='MultiLineString')return g.coordinates;
  return [];
}
function featureRoadPath(feature){
  let best=[],bestLength=0;
  for(const coords of roadLines(feature)){
    let current=[];
    const consider=()=>{let len=0;for(let i=1;i<current.length;i++)len+=Math.hypot(current[i].x-current[i-1].x,current[i].y-current[i-1].y);if(len>bestLength){best=current;bestLength=len;}current=[];};
    for(let i=1;i<coords.length;i++){
      const clipped=clipSegment(geoToLocal(coords[i-1][0],coords[i-1][1]),geoToLocal(coords[i][0],coords[i][1]));
      if(!clipped){consider();continue;}
      if(current.length&&Math.hypot(current.at(-1).x-clipped[0].x,current.at(-1).y-clipped[0].y)>1)consider();
      if(!current.length)current.push(clipped[0]);
      if(Math.hypot(current.at(-1).x-clipped[1].x,current.at(-1).y-clipped[1].y)>0.5)current.push(clipped[1]);
    }
    consider();
  }
  if(bestLength<0.5)return [];
  const reduced=[best[0]];
  for(let i=1;i<best.length-1;i++)if(Math.hypot(best[i].x-reduced.at(-1).x,best[i].y-reduced.at(-1).y)>=0.5)reduced.push(best[i]);
  const last=best.at(-1),gap=Math.hypot(last.x-reduced.at(-1).x,last.y-reduced.at(-1).y);
  if(gap>=0.5||reduced.length===1)reduced.push(last);
  else if(reduced.length>1&&Math.hypot(last.x-reduced.at(-2).x,last.y-reduced.at(-2).y)>=0.5)reduced[reduced.length-1]=last;
  best=reduced;
  bestLength=0;for(let i=1;i<best.length;i++)bestLength+=Math.hypot(best[i].x-best[i-1].x,best[i].y-best[i-1].y);
  if(bestLength<0.5)return [];
  if(best.length<=30)return best;
  const cumulative=[0];for(let i=1;i<best.length;i++)cumulative.push(cumulative.at(-1)+Math.hypot(best[i].x-best[i-1].x,best[i].y-best[i-1].y));
  return Array.from({length:30},(_,i)=>{const d=i*bestLength/29;let j=1;while(j<cumulative.length-1&&cumulative[j]<d)j++;const t=(d-cumulative[j-1])/(cumulative[j]-cumulative[j-1]);return {x:best[j-1].x+t*(best[j].x-best[j-1].x),y:best[j-1].y+t*(best[j].y-best[j-1].y)};});
}
let activeGlobal={roads:new Set(),cars:new Set(),rsus:new Set()};
let roadCleanupStats={snapped:0,spurs:0,detached:0};
const shortDetachedLimitM=100;
const cleanedRoadGraphs=new WeakSet();
const sanitizedStores=new WeakSet();
function hideShortDetachedComponents(roads,nodes,protectedIds=new Set()){
  const byNode=new Map(),length=road=>road.shape.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-road.shape[i][0],p[1]-road.shape[i][1]),0);
  for(const road of roads)for(const id of [road.from,road.to]){const list=byNode.get(id)||[];list.push(road);byNode.set(id,list);}
  const seen=new Set(),components=[];
  for(const road of roads){
    if(seen.has(road.id))continue;
    const queue=[road];seen.add(road.id);let meters=0,protectedRoad=false;
    for(const item of queue){meters+=length(item);protectedRoad ||=protectedIds.has(item.id);
      for(const id of [item.from,item.to])for(const next of byNode.get(id)||[])if(!seen.has(next.id)){seen.add(next.id);queue.push(next);}
    }
    components.push({roads:queue,meters,protectedRoad});
  }
  const largest=components.reduce((best,item)=>!best||item.roads.length>best.roads.length?item:best,null),kept=new Set();
  for(const component of components)if(component===largest||component.protectedRoad||component.meters>=shortDetachedLimitM)
    for(const road of component.roads)kept.add(road.id);
  const segments=roads.filter(road=>kept.has(road.id)),usedNodes=new Set(segments.flatMap(road=>[road.from,road.to]));
  return {segments,nodes:nodes.filter(node=>usedNodes.has(node.id)),stats:{snapped:0,spurs:0,detached:roads.length-segments.length}};
}
function cleanRealRoadGraph(roads,nodes,protectedIds=new Set()){
  const length=road=>road.shape.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-road.shape[i][0],p[1]-road.shape[i][1]),0);
  const nodeById=new Map(nodes.map(node=>[node.id,node]));
  const incident=new Map();
  const add=(id,road)=>{const list=incident.get(id)||[];list.push(road);incident.set(id,list);};
  for(const road of roads){add(road.from,road);add(road.to,road);}
  const parent=new Map(nodes.map(node=>[node.id,node.id]));
  const root=id=>{let at=id;while(parent.get(at)!==at)at=parent.get(at);return at;};
  for(const road of roads)parent.set(root(road.from),root(road.to));
  const free=[];
  for(const [id,list] of incident){
    if(list.length!==1||protectedIds.has(list[0].id))continue;
    const road=list[0],first=road.from===id,point=road.shape[first?0:road.shape.length-1];
    const next=road.shape[first?1:road.shape.length-2];
    if(Math.min(point[0],point[1],extent()-point[0],height()-point[1])<5)continue;
    free.push({id,road,first,point,away:[point[0]-next[0],point[1]-next[1]]});
  }
  const grid=new Map(),cell=5,key=(x,y)=>`${x}:${y}`;
  free.forEach((end,index)=>{end.index=index;const x=Math.floor(end.point[0]/cell),y=Math.floor(end.point[1]/cell),k=key(x,y);const list=grid.get(k)||[];list.push(end);grid.set(k,list);});
  const candidates=[];
  for(const a of free){
    const x=Math.floor(a.point[0]/cell),y=Math.floor(a.point[1]/cell);
    for(let gx=x-1;gx<=x+1;gx++)for(let gy=y-1;gy<=y+1;gy++)for(const b of grid.get(key(gx,gy))||[]){
      if(b.index<=a.index||a.road===b.road||root(a.id)===root(b.id)||a.road.road_class!==b.road.road_class)continue;
      const dx=b.point[0]-a.point[0],dy=b.point[1]-a.point[1],distance=Math.hypot(dx,dy);
      if(distance<.1||distance>5)continue;
      const na=Math.hypot(...a.away),nb=Math.hypot(...b.away);
      if((a.away[0]*dx+a.away[1]*dy)/(na*distance)<.75||
         (-b.away[0]*dx-b.away[1]*dy)/(nb*distance)<.75)continue;
      candidates.push({a,b,distance});
    }
  }
  candidates.sort((a,b)=>a.distance-b.distance);
  const choices=new Map();for(const {a,b} of candidates)for(const end of [a,b])choices.set(end.id,(choices.get(end.id)||0)+1);
  const touched=new Set();let snapped=0;
  for(const {a,b} of candidates){
    if(choices.get(a.id)!==1||choices.get(b.id)!==1||touched.has(a.id)||touched.has(b.id)||root(a.id)===root(b.id))continue;
    const x=Math.round((a.point[0]+b.point[0])*5)/10,y=Math.round((a.point[1]+b.point[1])*5)/10;
    if(Math.hypot(x-(a.point[0]-a.away[0]),y-(a.point[1]-a.away[1]))<1||
       Math.hypot(x-(b.point[0]-b.away[0]),y-(b.point[1]-b.away[1]))<1)continue;
    const keep=a.id< b.id?a:b,replace=keep===a?b:a;
    const node=nodeById.get(keep.id);node.x_m=x;node.y_m=y;
    for(const end of [a,b]){
      end.road.shape[end.first?0:end.road.shape.length-1]=[x,y];
      if(end.id===replace.id)end.road[end.first?'from':'to']=keep.id;
    }
    parent.set(root(replace.id),root(keep.id));touched.add(a.id);touched.add(b.id);snapped++;
  }
  const degree=new Map();for(const road of roads){degree.set(road.from,(degree.get(road.from)||0)+1);degree.set(road.to,(degree.get(road.to)||0)+1);}
  const minor=new Set(['service','residential','living_street','unclassified','road']);
  const withoutSpurs=roads.filter(road=>protectedIds.has(road.id)||
    !(minor.has(road.road_class)&&length(road)<30&&
      (degree.get(road.from)===1||degree.get(road.to)===1)));
  const spurs=roads.length-withoutSpurs.length;
  const byNode=new Map();for(const road of withoutSpurs){
    for(const id of [road.from,road.to]){const list=byNode.get(id)||[];list.push(road);byNode.set(id,list);}
  }
  const seen=new Set(),components=[];
  for(const road of withoutSpurs){
    if(seen.has(road.id))continue;
    const queue=[road];seen.add(road.id);let meters=0,hasCar=false;
    for(const item of queue){meters+=length(item);hasCar ||=protectedIds.has(item.id);
      for(const id of [item.from,item.to])for(const next of byNode.get(id)||[]){
        if(!seen.has(next.id)){seen.add(next.id);queue.push(next);}
      }
    }
    components.push({roads:queue,meters,hasCar});
  }
  const largest=components.reduce((best,item)=>!best||item.roads.length>best.roads.length?item:best,null);
  const kept=new Set();
  for(const component of components)if(component===largest||component.hasCar||component.meters>=100)
    for(const road of component.roads)kept.add(road.id);
  const segments=withoutSpurs.filter(road=>kept.has(road.id));
  const usedNodes=new Set(segments.flatMap(road=>[road.from,road.to]));
  return {segments,nodes:nodes.filter(node=>usedNodes.has(node.id)),
    stats:{snapped,spurs,detached:withoutSpurs.length-segments.length}};
}
window.simulatorCleanRoadGraph=cleanRealRoadGraph;
function roadJoinCandidates(road,end){
  const store=globalStore(),from=end==='from',point=road.shape[from?0:road.shape.length-1];
  const probe={x:point[0],y:point[1]},global=new Map(store.roads.map(row=>[row.id,row])),found=[];
  for(const target of editor.state.world.roads.segments){
    if(target.id===road.id||!global.has(target.id)||nearestOnShape(target.shape,probe)?.d>50)continue;
    const coords=global.get(target.id).coordinates;let best=null;
    for(let i=0;i<coords.length-1;i++){
      const a=geoToLocal(...coords[i]),b=geoToLocal(...coords[i+1]),dx=b.x-a.x,dy=b.y-a.y,size=dx*dx+dy*dy;
      if(size<1)continue;
      const t=Math.max(0,Math.min(1,((probe.x-a.x)*dx+(probe.y-a.y)*dy)/size));
      const x=a.x+t*dx,y=a.y+t*dy,distance=Math.hypot(probe.x-x,probe.y-y);
      if(x<0||x>extent()||y<0||y>height()||best&&distance>=best.distance)continue;
      best={target,segment:i,t,geo:[coords[i][0]+t*(coords[i+1][0]-coords[i][0]),coords[i][1]+t*(coords[i+1][1]-coords[i][1])],x,y,distance};
    }
    if(best?.distance<=50)found.push(best);
  }
  return found.sort((a,b)=>a.distance-b.distance).slice(0,20);
}
function joinRoadEnd(road,end,targetId){
  const store=globalStore(),state=editor.state;
  if(!store||state.mapMode!=='real')throw Error('Napojenie opravuj v režime reálnej mapy.');
  if((store.manual_joins||[]).length>=1000)throw Error('Limit manuálnych opráv spojení je 1000.');
  const nodeId=road[end],degree=state.world.roads.segments.reduce((n,item)=>n+(item.from===nodeId)+(item.to===nodeId),0);
  if(degree!==1)throw Error('Tento koniec cesty je už napojený.');
  const candidate=roadJoinCandidates(road,end).find(item=>item.target.id===targetId);
  if(!candidate)throw Error('Vybraná cieľová cesta už nie je v dosahu 50 m.');
  const used=new Set(store.cars.flatMap(car=>(car.route||[{segment:car.road_id}]).map(hop=>hop.segment)));
  for(const car of state.demand.vehicles)for(const hop of car.route)used.add(hop.segment);
  if(used.has(road.id)||used.has(targetId))throw Error('Po jednej z týchto ciest už vedie trasa auta. Najprv uprav alebo odstráň jeho trasu.');
  syncActiveGlobal();
  const source=store.roads.find(item=>item.id===road.id),target=store.roads.find(item=>item.id===targetId);
  if(!source||!target)throw Error('Cesta chýba v uloženom mapovom katalógu.');
  const displayed=road.shape[end==='from'?0:road.shape.length-1],original=geoToLocal(...source.coordinates[end==='from'?0:source.coordinates.length-1]);
  if(Math.hypot(displayed[0]-original.x,displayed[1]-original.y)>2)
    throw Error('Tento koniec je orezaný hranou mapy; zvoľ koniec skutočnej cesty.');
  const sourceCoords=source.coordinates.map(point=>[...point]),targetCoords=target.coordinates.map(point=>[...point]);
  const {segment,t}=candidate;
  let cut,joinGeo;
  const a=geoToLocal(...targetCoords[segment]),b=geoToLocal(...targetCoords[segment+1]);
  if(t*Math.hypot(b.x-a.x,b.y-a.y)<1){cut=segment;joinGeo=targetCoords[cut];}
  else if((1-t)*Math.hypot(b.x-a.x,b.y-a.y)<1){cut=segment+1;joinGeo=targetCoords[cut];}
  else{cut=segment+1;joinGeo=candidate.geo;targetCoords.splice(cut,0,joinGeo);}
  const sourceIndex=end==='from'?0:sourceCoords.length-1;
  sourceCoords[sourceIndex]=[...joinGeo];
  const sourceLocal=sourceCoords.map(point=>geoToLocal(...point));
  if(sourceLocal.slice(1).some((p,i)=>Math.hypot(p.x-sourceLocal[i].x,p.y-sourceLocal[i].y)<1))
    throw Error('Spojenie by vytvorilo príliš krátky úsek vybranej cesty.');
  let newPartId=null,left=null,right=null;
  if(cut>0&&cut<targetCoords.length-1){
    left=targetCoords.slice(0,cut+1);right=targetCoords.slice(cut);
    const valid=coords=>{const points=coords.map(point=>geoToLocal(...point));return points.slice(1).every((p,i)=>Math.hypot(p.x-points[i].x,p.y-points[i].y)>=1)&&
      points.slice(1).reduce((n,p,i)=>n+Math.hypot(p.x-points[i].x,p.y-points[i].y),0)>=2;};
    if(!valid(left)||!valid(right))throw Error('Cieľová cesta sa v tomto bode nedá rozdeliť na platné úseky.');
    if(state.world.roads.segments.length>=30000)throw Error('Cestná sieť už dosiahla limit úsekov.');
    const ids=new Set(store.roads.map(item=>item.id));let n=1;
    do{newPartId=`${target.id.slice(0,26)}_j${n++}`;}while(ids.has(newPartId));
  }
  source.coordinates=sourceCoords;
  if(newPartId){target.coordinates=left;store.roads.push({...structuredClone(target),id:newPartId,coordinates:right});}
  store.manual_joins??=[];
  store.manual_joins.push({road_id:road.id,end,target_id:targetId,longitude_deg:joinGeo[0],latitude_deg:joinGeo[1],distance_m:Math.round(candidate.distance*10)/10,...(newPartId?{new_part_id:newPartId}:{})});
  projectGlobalToCurrentSite();state.selected={type:'road',id:road.id};state.inspectorKey=null;
  editor.markDirty(true);
  editor.status(`Cesta ${road.id} je napojená na ${targetId}${newPartId?' cez nový grafový uzol':''}.`);
}
function renderRoadJoinControls(road,box){
  if(editor.state.mapMode!=='real')return;
  const section=document.createElement('section');section.className='road-join-controls';
  const title=document.createElement('h4');title.textContent='Opraviť chýbajúce napojenie';section.append(title);
  const note=document.createElement('p');note.textContent='Spoj len skutočnú križovatku v rovnakej úrovni. Oprava zmení cestný graf a uloží sa so scenárom.';section.append(note);
  const endpoint=document.createElement('label');endpoint.textContent='Nenapojený koniec';
  const endpointSelect=document.createElement('select');endpointSelect.append(new Option('Začiatok','from'),new Option('Koniec','to'));endpoint.append(endpointSelect);section.append(endpoint);
  const target=document.createElement('label');target.textContent='Cieľová cesta · do 50 m';
  const targetSelect=document.createElement('select');target.append(targetSelect);section.append(target);
  const button=document.createElement('button');button.type='button';button.textContent='Spojiť cesty';section.append(button);
  const refresh=()=>{
    const id=road[endpointSelect.value],degree=editor.state.world.roads.segments.reduce((n,item)=>n+(item.from===id)+(item.to===id),0);
    targetSelect.replaceChildren();
    if(degree===1)for(const candidate of roadJoinCandidates(road,endpointSelect.value))
      targetSelect.append(new Option(`${candidate.target.name||candidate.target.id} · ${candidate.distance.toFixed(1)} m · ${candidate.target.id}`,candidate.target.id));
    if(!targetSelect.options.length)targetSelect.append(new Option(degree===1?'Žiadna cesta v dosahu':'Koniec je už napojený',''));
    button.disabled=!targetSelect.value;
  };
  const degrees=Object.fromEntries(['from','to'].map(end=>[end,editor.state.world.roads.segments.reduce((n,item)=>n+(item.from===road[end])+(item.to===road[end]),0)]));
  endpointSelect.value=degrees.from===1?'from':'to';
  if(degrees.from===1&&degrees.to===1&&!roadJoinCandidates(road,'from').length&&roadJoinCandidates(road,'to').length)endpointSelect.value='to';
  endpointSelect.onchange=refresh;refresh();
  button.onclick=()=>{try{joinRoadEnd(road,endpointSelect.value,targetSelect.value);}catch(e){editor.status(e.message);}};
  box.append(section);
}
window.simulatorRoadJoinControls=renderRoadJoinControls;
function globalStore(){const w=editor.state.world;if(w?.map_source!=='osm_live')return null;const store=w.map_objects ||= {schema_version:1,roads:[],cars:[],rsus:[],sources:[],turn_restrictions:[]};store.sources ||= [];store.turn_restrictions ||= [];
  if(!sanitizedStores.has(store)){for(const road of store.roads)delete road.conditional_rules;for(const road of w.roads.segments)delete road.conditional_rules;for(const source of store.sources)delete source.conditional_ways;store.turn_restrictions=store.turn_restrictions.filter(rule=>!rule.conditional).map(rule=>{delete rule.conditional;return rule;});sanitizedStores.add(store);}
  return store;}
function globalCounts(){
  const box=document.getElementById('globalCounts'),store=globalStore();
  box.hidden=!store;
  if(store)box.textContent=`Cesty: ${editor.state.world.roads.segments.length} · autá: ${editor.state.demand.vehicles.length} · RSU: ${editor.state.world.rsus.length}`;
}
function upsert(rows,item){const i=rows.findIndex(row=>row.id===item.id);if(i<0)rows.push(item);else rows[i]=item;}
function syncActiveGlobal(){
  const store=globalStore();if(!store)return;
  const s=editor.state,w=s.world;
  const current={roads:new Set(w.roads.segments.map(x=>x.id)),cars:new Set(s.demand.vehicles.map(x=>x.id)),rsus:new Set(w.rsus.map(x=>x.id))};
  for(const kind of ['roads','cars','rsus'])store[kind]=store[kind].filter(row=>!activeGlobal[kind].has(row.id)||current[kind].has(row.id));
  for(const road of w.roads.segments){const old=store.roads.find(r=>r.id===road.id);const extra={};for(const key of ['speed_forward_mps','speed_reverse_mps','lanes_forward','lanes_reverse','speed_forward_source','speed_reverse_source','lanes_forward_source','lanes_reverse_source','service','bridge','tunnel','layer','access_rules'])if(road[key]!==undefined)extra[key]=road[key];upsert(store.roads,{id:road.id,coordinates:old?.osm_way_id?old.coordinates:road.shape.map(([x,y])=>localToGeo(x,y)),speed_limit_mps:road.speed_limit_mps,lanes_each_direction:road.lanes_each_direction,...extra,...(road.oneway===undefined?{}:{oneway:road.oneway}),...(road.osm_way_id?{osm_way_id:road.osm_way_id}:old?.osm_way_id?{osm_way_id:old.osm_way_id}:{}),...(old?.osm_from_node_id?{osm_from_node_id:old.osm_from_node_id}:{}),...(old?.osm_to_node_id?{osm_to_node_id:old.osm_to_node_id}:{}),...(road.name!==undefined?{name:road.name}:{}),...(road.road_class?{road_class:road.road_class}:{})});}
  for(const car of s.demand.vehicles){
    const pos=editor.carPosition(car);if(!pos)continue;
    const [longitude_deg,latitude_deg]=localToGeo(pos.x,pos.y),policy=s.scenario.node_policy?.cars[car.id];
    upsert(store.cars,{id:car.id,longitude_deg,latitude_deg,road_id:car.route[0].segment,depart_s:car.depart_s,depart_speed_mps:car.depart_speed_mps,...(car.max_speed_mps===undefined?{}:{max_speed_mps:car.max_speed_mps}),...(car.depart_speed_mode===undefined?{}:{depart_speed_mode:car.depart_speed_mode}),...(car.vehicle_model?{vehicle_model:structuredClone(car.vehicle_model)}:{}),...(car.radio_model?{radio_model:structuredClone(car.radio_model)}:{}),direction:car.route[0].direction,route:structuredClone(car.route),...(car.arrival_pos_m===undefined?{}:{arrival_pos_m:car.arrival_pos_m}),technologies:[...car.technologies],ground_mode:policy?.ground||'all',source:s.scenario.source_id===car.id});
  }
  for(const rsu of w.rsus){
    const [longitude_deg,latitude_deg]=localToGeo(rsu.x_m,rsu.y_m),policy=s.scenario.node_policy?.rsus[rsu.id];
    upsert(store.rsus,{id:rsu.id,longitude_deg,latitude_deg,technologies:[...rsu.technologies],...(rsu.radio_model?{radio_model:structuredClone(rsu.radio_model)}:{}),ground:policy?.ground!==false,satellite_backhaul:policy?.satellite_backhaul!==false,primary:s.scenario.rsu_id===rsu.id,alert_target:s.scenario.alert_target_rsu===rsu.id});
  }
  activeGlobal=current;globalCounts();
}
function nearestOnShape(path,p){
  let best=null,passed=0;
  for(let i=1;i<path.length;i++){
    const a=path[i-1],b=path[i],dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy);
    if(len<.001)continue;
    const t=Math.max(0,Math.min(1,((p.x-a[0])*dx+(p.y-a[1])*dy)/(len*len)));
    const d=Math.hypot(p.x-a[0]-t*dx,p.y-a[1]-t*dy);
    if(!best||d<best.d)best={d,at:passed+len*t};passed+=len;
  }
  return best;
}
function projectGlobalToCurrentSite(){
  const store=globalStore();if(!store)return;
  const s=editor.state,w=s.world,roads=[],nodes=[],activeRoads=new Set(),nodeIndex=new Map();
  function endpoint(p,key){
    let found=nodeIndex.get(key);
    if(found){p[0]=found.x_m;p[1]=found.y_m;return found.id;}
  if(nodes.length>=30000)return null;
    const id=`node${nodes.length}`;found={id,x_m:p[0],y_m:p[1]};nodes.push(found);nodeIndex.set(key,found);return id;
  }
  for(const record of store.roads){
  if(roads.length>=30000||nodes.length>=29999)break;
    const path=featureRoadPath({geometry:{type:'LineString',coordinates:record.coordinates}});
    if(path.length<2)continue;
    const shape=path.map(p=>[Math.round(p.x*100)/100,Math.round(p.y*100)/100]);
    const length=shape.slice(1).reduce((n,p,i)=>n+Math.hypot(p[0]-shape[i][0],p[1]-shape[i][1]),0);
    if(length<0.5||shape.some((p,i)=>i&&Math.hypot(p[0]-shape[i-1][0],p[1]-shape[i-1][1])<0.5))continue;
    const endKey=(end,point)=>{
      const original=geoToLocal(...record.coordinates[end==='from'?0:record.coordinates.length-1]);
      if(Math.hypot(original.x-point[0],original.y-point[1])>0.15)return `clip:${record.id}:${end}`;
      const joins=store.manual_joins||[];
      for(let i=0;i<joins.length;i++){
        const join=joins[i];
        if(![join.road_id,join.target_id,join.new_part_id].includes(record.id))continue;
        const at=geoToLocal(join.longitude_deg,join.latitude_deg);
        if(Math.hypot(at.x-point[0],at.y-point[1])<=0.15)return `manual:${i}`;
      }
      const osm=record[`osm_${end}_node_id`];
      return osm?`osm:${osm}`:`coord:${point[0].toFixed(2)}:${point[1].toFixed(2)}`;
    };
    const from=endpoint(shape[0],endKey('from',shape[0])),to=endpoint(shape.at(-1),endKey('to',shape.at(-1)));
    if(!from||!to||from===to)continue;
    const extra={};for(const key of ['speed_forward_mps','speed_reverse_mps','lanes_forward','lanes_reverse','speed_forward_source','speed_reverse_source','lanes_forward_source','lanes_reverse_source','service','bridge','tunnel','layer','access_rules','osm_from_node_id','osm_to_node_id'])if(record[key]!==undefined)extra[key]=record[key];
    roads.push({id:record.id,from,to,shape,speed_limit_mps:record.speed_limit_mps,lanes_each_direction:record.lanes_each_direction,...extra,...(record.oneway===undefined?{}:{oneway:record.oneway}),...(record.osm_way_id?{osm_way_id:record.osm_way_id}:{}),...(record.name!==undefined?{name:record.name}:{}),...(record.road_class?{road_class:record.road_class}:{})});activeRoads.add(record.id);
  }
  const protectedIds=new Set(store.cars.flatMap(car=>(car.route||[{segment:car.road_id}]).map(hop=>hop.segment)));
  for(const join of store.manual_joins||[])for(const id of [join.road_id,join.target_id,join.new_part_id])if(id)protectedIds.add(id);
  const clean=hideShortDetachedComponents(roads,nodes,protectedIds);
  roadCleanupStats=clean.stats;
  const directed=[];for(const road of clean.segments){directed.push({id:`${road.id}_forward`,from:road.from,to:road.to,road,osmFrom:road.osm_from_node_id,osmTo:road.osm_to_node_id});if(!road.oneway)directed.push({id:`${road.id}_reverse`,from:road.to,to:road.from,road,osmFrom:road.osm_to_node_id,osmTo:road.osm_from_node_id});}
  const byNode=new Map();for(const edge of directed){const list=byNode.get(edge.from)||[];list.push(edge);byNode.set(edge.from,list);}
  const denied=new Set();let appliedRestrictions=0,unresolvedRestrictions=0;
  for(const rule of store.turn_restrictions){
    if(rule.via_way_id||rule.conditional||rule.except?.split(/[;,]/).some(x=>['motorcar','motor_vehicle','vehicle','passenger'].includes(x.trim()))){unresolvedRestrictions++;continue;}
    const incoming=directed.filter(edge=>edge.road.osm_way_id===rule.from_way_id&&edge.osmTo===rule.via_node_id);
    const outgoing=directed.filter(edge=>edge.road.osm_way_id===rule.to_way_id&&edge.osmFrom===rule.via_node_id);
    if(!incoming.length||!outgoing.length){unresolvedRestrictions++;continue;}
    let matched=false;
    for(const a of incoming)for(const b of outgoing){if(a.to!==b.from)continue;matched=true;const targets=rule.kind.startsWith('only_')?(byNode.get(a.to)||[]).filter(x=>!outgoing.some(allowed=>allowed.id===x.id)):[b];for(const target of targets)denied.add(`${a.id}|${target.id}`);}
    if(matched)appliedRestrictions++;else unresolvedRestrictions++;
  }
  w.roads={nodes:clean.nodes,segments:clean.segments,turn_rules:[...denied].map(pair=>{const [from,to]=pair.split('|');return {from,to};})};
  w.osm_import_status={applied_restrictions:appliedRestrictions,unresolved_restrictions:unresolvedRestrictions};cleanedRoadGraphs.add(w.roads);
  activeRoads.clear();for(const road of clean.segments)activeRoads.add(road.id);
  const cars=[],activeCars=new Set();
  for(const record of store.cars){
    if(!activeRoads.has(record.road_id))continue;
    const p=geoToLocal(record.longitude_deg,record.latitude_deg);
    if(p.x<0||p.x>extent()||p.y<0||p.y>height())continue;
    const road=clean.segments.find(r=>r.id===record.road_id),near=nearestOnShape(road.shape,p);
    if(!near||near.d>15)continue;
    const length=road.shape.slice(1).reduce((n,q,i)=>n+Math.hypot(q[0]-road.shape[i][0],q[1]-road.shape[i][1]),0);
    const at=record.direction==='reverse'?length-near.at:near.at;
    const desired=record.route||[{segment:record.road_id,direction:record.direction}],route=[];
    for(const hop of desired){const next=clean.segments.find(r=>r.id===hop.segment);if(!next||next.oneway&&hop.direction==='reverse')break;if(route.length){const prev=clean.segments.find(r=>r.id===route.at(-1).segment),end=route.at(-1).direction==='forward'?prev.to:prev.from,start=hop.direction==='forward'?next.from:next.to;if(end!==start)break;}route.push({...hop});}
    if(!route.length)continue;
    const departPos=Math.floor(Math.max(0,Math.min(length-20,at))*10)/10;
    const finalRoad=clean.segments.find(r=>r.id===route.at(-1).segment);
    const finalLength=finalRoad.shape.slice(1).reduce((n,q,i)=>n+Math.hypot(q[0]-finalRoad.shape[i][0],q[1]-finalRoad.shape[i][1]),0);
    const arrival=record.arrival_pos_m;
    const keepArrival=Number.isFinite(arrival)&&route.length===desired.length&&arrival<=finalLength&&(route.length>1||arrival>departPos+1);
    cars.push({id:record.id,depart_s:record.depart_s,depart_speed_mps:record.depart_speed_mps,...(record.max_speed_mps===undefined?{}:{max_speed_mps:record.max_speed_mps}),...(record.depart_speed_mode===undefined?{}:{depart_speed_mode:record.depart_speed_mode}),...(record.vehicle_model?{vehicle_model:structuredClone(record.vehicle_model)}:{}),...(record.radio_model?{radio_model:structuredClone(record.radio_model)}:{}),depart_pos_m:departPos,route,...(keepArrival?{arrival_pos_m:arrival}:{}),technologies:[...record.technologies]});activeCars.add(record.id);
  }
  const rsus=[],activeRsus=new Set();
  for(const record of store.rsus){
    const p=geoToLocal(record.longitude_deg,record.latitude_deg);
    if(p.x<0||p.x>extent()||p.y<0||p.y>height())continue;
    rsus.push({id:record.id,x_m:Math.round(p.x*10)/10,y_m:Math.round(p.y*10)/10,technologies:[...record.technologies],...(record.radio_model?{radio_model:structuredClone(record.radio_model)}:{})});activeRsus.add(record.id);
  }
  w.rsus=rsus;w.vehicles=structuredClone(cars);s.demand.vehicles=cars;
  s.scenario.source_id=store.cars.find(c=>activeCars.has(c.id)&&c.source)?.id||cars[0]?.id||'';
  s.scenario.rsu_id=store.rsus.find(r=>activeRsus.has(r.id)&&r.primary)?.id||rsus[0]?.id||'';
  if('alert_target_rsu' in s.scenario)s.scenario.alert_target_rsu=store.rsus.find(r=>activeRsus.has(r.id)&&r.alert_target&&r.id!==s.scenario.rsu_id)?.id||rsus.find(r=>r.id!==s.scenario.rsu_id)?.id||'';
  if(s.scenario.node_policy)s.scenario.node_policy={cars:Object.fromEntries(store.cars.filter(c=>activeCars.has(c.id)).map(c=>[c.id,{ground:c.ground_mode}])),rsus:Object.fromEntries(store.rsus.filter(r=>activeRsus.has(r.id)).map(r=>[r.id,{ground:r.ground,satellite_backhaul:r.satellite_backhaul}]))};
  if(w.flows?.[0])w.flows[0].source=s.scenario.source_id;
  activeGlobal={roads:activeRoads,cars:activeCars,rsus:activeRsus};
  s.selected=null;s.inspectorKey=null;editor.rebuildObjectPicker();editor.render();globalCounts();
}
function initializeGlobal(){
  if(!editor.state.world||!editor.state.demand)return;
  const store=globalStore();
  if(!editor.state.world.roads.segments.length)roadCleanupStats={snapped:0,spurs:0,detached:0};
  if(store&&editor.state.world.roads.segments.length&&!cleanedRoadGraphs.has(editor.state.world.roads)){
    const protectedIds=new Set(store.cars.flatMap(car=>(car.route||[{segment:car.road_id}]).map(hop=>hop.segment)));
    for(const car of editor.state.demand.vehicles)for(const hop of car.route)protectedIds.add(hop.segment);
    for(const join of store.manual_joins||[])for(const id of [join.road_id,join.target_id,join.new_part_id])if(id)protectedIds.add(id);
    const graph=editor.state.world.roads,clean=hideShortDetachedComponents(graph.segments,graph.nodes,protectedIds);
    roadCleanupStats=clean.stats;
    if(clean.stats.detached){
      const kept=new Set(clean.segments.map(road=>road.id));
      editor.state.world.roads={...graph,nodes:clean.nodes,segments:clean.segments,turn_rules:(graph.turn_rules||[]).filter(rule=>kept.has(rule.from.replace(/_(forward|reverse)$/,''))&&kept.has(rule.to.replace(/_(forward|reverse)$/,'')))};
      editor.state.roadGraphVersion++;editor.state.dirty=true;editor.state.saved=false;
    }
    cleanedRoadGraphs.add(editor.state.world.roads);
  }
  activeGlobal={roads:new Set(editor.state.world?.roads.segments.map(x=>x.id)||[]),cars:new Set(editor.state.demand?.vehicles.map(x=>x.id)||[]),rsus:new Set(editor.state.world?.rsus.map(x=>x.id)||[])};
  if(store&&!(store.roads.length+store.cars.length+store.rsus.length)&&activeGlobal.roads.size)syncActiveGlobal();
  globalCounts();
}
window.simulatorRealMapInitialize=initializeGlobal;
window.simulatorRealMapSyncActive=syncActiveGlobal;
window.simulatorRealMapProjectActive=projectGlobalToCurrentSite;
let roadRequest=0,roadTimer=null,roadLoadingKey='';
function siteCovered(source){
  const b=source.bbox;if(!Array.isArray(b)||b.length!==4)return false;
  return [[0,0],[0,height()],[extent(),0],[extent(),height()]].every(([x,y])=>{const [lon,lat]=localToGeo(x,y);return lon>=b[0]&&lon<=b[2]&&lat>=b[1]&&lat<=b[3];});
}
async function fetchRoadNetwork(requestId,key,attempt=0){
  const s=editor.state,geo=structuredClone(s.world.georeference);
  let retryScheduled=false;
  try{
    const response=await fetch('/api/simulator/editor/roads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({georeference:geo,width_m:extent(),height_m:height()})});
    const data=await response.json();
    if(response.status===429&&attempt<6&&requestId===roadRequest){
      const delay=Math.min(3600,Math.max(1,Number(data.retry_after_s)||30));
      retryScheduled=true;
      editor.status(`OSM dočasne obmedzil sťahovanie. Pokus ${attempt+1}/6; cesty automaticky načítam znova za ${delay} s. Miesto nemeň.`);
      roadTimer=setTimeout(()=>{if(requestId===roadRequest)fetchRoadNetwork(requestId,key,attempt+1);},(delay+1)*1000);
      return;
    }
    if(!response.ok)throw Error(data.reason||`HTTP ${response.status}`);
    if(requestId!==roadRequest||s.mapMode!=='real'||key!==JSON.stringify([s.world.georeference,extent(),height()]))return;
    syncActiveGlobal();const store=globalStore(),known=new Map(store.roads.map(x=>[x.id,x]));
    const fresh=data.roads.filter(x=>!known.has(x.id));
    if(store.roads.length+fresh.length>100000||store.sources.length>=100)throw Error('Globálny katalóg ciest je plný. Ulož a otvor nový mapový scenár.');
    for(const incoming of data.roads){
      const old=known.get(incoming.id);if(!old)continue;
      const manualSpeedDirection=['forward','reverse'].some(direction=>old[`speed_${direction}_source`]==='manual');
      const preserveSpeed=!manualSpeedDirection&&Math.abs(old.speed_limit_mps-(old.speed_forward_mps===undefined?incoming.legacy_speed_mps:incoming.speed_limit_mps))>0.001;
      const manualLaneDirection=['forward','reverse'].some(direction=>old[`lanes_${direction}_source`]==='manual');
      const preserveLanes=!manualLaneDirection&&old.lanes_each_direction!==(old.lanes_forward===undefined?incoming.legacy_lanes_each_direction:incoming.lanes_each_direction);
      for(const direction of ['forward','reverse']){const field=`speed_${direction}_mps`;old[field]=old[`speed_${direction}_source`]==='manual'?(old[field]??old.speed_limit_mps):preserveSpeed?old.speed_limit_mps:incoming[field];}
      for(const direction of ['forward','reverse']){const field=`lanes_${direction}`;old[field]=old[`${field}_source`]==='manual'?(old[field]??old.lanes_each_direction):preserveLanes?old.lanes_each_direction:incoming[field];}
      for(const field of ['service','bridge','tunnel','layer','access_rules'])old[field]=incoming[field];delete old.conditional_rules;for(const direction of ['forward','reverse']){old[`speed_${direction}_source`]=old[`speed_${direction}_source`]==='manual'||preserveSpeed?'manual':incoming[`speed_${direction}_source`];old[`lanes_${direction}_source`]=old[`lanes_${direction}_source`]==='manual'||preserveLanes?'manual':incoming[`lanes_${direction}_source`];}
      for(const [end,index] of [['from',0],['to',-1]]){
        const key=`osm_${end}_node_id`,a=old.coordinates.at(index),b=incoming.coordinates.at(index);
        if(a?.[0]===b?.[0]&&a?.[1]===b?.[1])old[key]=incoming[key];
        else delete old[key];
      }
    }
    // A newer parser may split an old OSM way at the work-area boundary.
    // Replace stale pieces only when saved vehicle routes can be mapped safely.
    const incomingIds=new Set(data.roads.map(row=>row.id)),stale=store.roads.filter(row=>row.osm_way_id&&activeGlobal.roads.has(row.id)&&!incomingIds.has(row.id));
    const retainedWays=new Set(),removed=new Set();
    const same=(a,b)=>a?.[0]===b?.[0]&&a?.[1]===b?.[1];
    for(const old of stale){
      const uses=store.cars.flatMap(car=>(car.route||[{segment:car.road_id,direction:car.direction}]).flatMap((hop,index,route)=>hop.segment===old.id?[{car,hop,index,last:route.length-1}]:[]));
      const joined=(store.manual_joins||[]).some(join=>[join.road_id,join.target_id,join.new_part_id].includes(old.id));
      let replacement=null;
      if(uses.length&&!joined){const choices=data.roads.filter(row=>row.osm_way_id===old.osm_way_id&&uses.every(use=>{
        const forward=use.hop.direction==='forward',start=forward?0:-1,end=forward?-1:0;
        return (use.index===0||same(row.coordinates.at(start),old.coordinates.at(start)))&&
               (use.index===use.last||same(row.coordinates.at(end),old.coordinates.at(end)));
      }));if(choices.length===1)replacement=choices[0];}
      if((uses.length&&!replacement)||joined){retainedWays.add(old.osm_way_id);continue;}
      if(replacement){
        const manualSpeedDirection=['forward','reverse'].some(direction=>old[`speed_${direction}_source`]==='manual');
        const preserveSpeed=!manualSpeedDirection&&Math.abs(old.speed_limit_mps-(old.speed_forward_mps===undefined?replacement.legacy_speed_mps:replacement.speed_limit_mps))>0.001;
        if(manualSpeedDirection||preserveSpeed)replacement.speed_limit_mps=old.speed_limit_mps;
        for(const direction of ['forward','reverse'])if(old[`speed_${direction}_source`]==='manual'||preserveSpeed){replacement[`speed_${direction}_mps`]=old[`speed_${direction}_source`]==='manual'?(old[`speed_${direction}_mps`]??old.speed_limit_mps):old.speed_limit_mps;replacement[`speed_${direction}_source`]='manual';}
        const manualLaneDirection=['forward','reverse'].some(direction=>old[`lanes_${direction}_source`]==='manual');
        const preserveLanes=!manualLaneDirection&&old.lanes_each_direction!==(old.lanes_forward===undefined?replacement.legacy_lanes_each_direction:replacement.lanes_each_direction);
        if(manualLaneDirection||preserveLanes)replacement.lanes_each_direction=old.lanes_each_direction;
        for(const direction of ['forward','reverse'])if(old[`lanes_${direction}_source`]==='manual'||preserveLanes){replacement[`lanes_${direction}`]=old[`lanes_${direction}_source`]==='manual'?(old[`lanes_${direction}`]??old.lanes_each_direction):old.lanes_each_direction;replacement[`lanes_${direction}_source`]='manual';}
        for(const use of uses){use.hop.segment=replacement.id;if(use.index===0)use.car.road_id=replacement.id;}
      }
      removed.add(old.id);
    }
    if(removed.size)store.roads=store.roads.filter(row=>!removed.has(row.id));
    store.roads.push(...fresh.filter(row=>!retainedWays.has(row.osm_way_id)).map(row=>{const {legacy_speed_mps,legacy_lanes_each_direction,...saved}=row;return saved;}));store.sources.push(data.source);
    const knownRules=new Set(store.turn_restrictions.map(x=>x.id));for(const rule of data.turn_restrictions||[])if(!knownRules.has(rule.id)){store.turn_restrictions.push(rule);knownRules.add(rule.id);}
    if(data.environment&&s.scenario.satellite){
      const previous=s.scenario.satellite.environment;
      if(previous&&JSON.stringify(previous.georeference)===JSON.stringify(data.environment.georeference)){
        const edited=new Map((previous.buildings||[]).filter(row=>row.manual_edited).map(row=>[row.id,row]));
        const removed=new Set(previous.manual_removed_buildings||[]);
        data.environment.buildings=data.environment.buildings.filter(row=>!removed.has(row.id)).map(row=>edited.get(row.id)||row);
        data.environment.manual_removed_buildings=[...removed];
        data.environment.height_case=previous.height_case||data.environment.height_case;
        data.environment.building_count=data.environment.buildings.length;
      }
      s.scenario.satellite.environment=data.environment;window.simulatorSyncHeightCase?.();
    }
    projectGlobalToCurrentSite();editor.markDirty(true);window.simulatorTechnicalRefresh?.();
    editor.status(`Cesty: ${s.world.roads.segments.length} · budovy: ${data.environment?.buildings?.length||0}`);
  }catch(e){if(requestId===roadRequest)editor.status(`Cestná sieť sa nenačítala: ${e.message}. Skús zvoliť miesto znova.`);}
  finally{if(requestId===roadRequest&&!retryScheduled){s.roadNetworkLoading=false;roadLoadingKey='';}}
}
function loadRoadNetwork(force=false){
  if(editor.state.mapMode!=='real'||!editor.state.world)return;
  const store=globalStore();if(!force&&store.sources.some(source=>siteCovered(source)&&source.import_revision===10))return;
  const key=JSON.stringify([editor.state.world.georeference,extent(),height()]);if(!force&&key===roadLoadingKey)return;
  roadLoadingKey=key;editor.state.roadNetworkLoading=true;const requestId=++roadRequest;
  if(roadTimer)clearTimeout(roadTimer);
  editor.status('Načítavam všetky jazdné cesty v pracovnom výreze…');
  roadTimer=setTimeout(()=>fetchRoadNetwork(requestId,key),350);
}
window.simulatorEarthLoadRoadNetwork=loadRoadNetwork;
window.simulatorEarthInvalidateRoads=()=>{roadRequest++;roadLoadingKey='';lastGroundKey='';if(roadTimer)clearTimeout(roadTimer);editor.state.roadNetworkLoading=false;};
function ensureRoad(p){
  if(editor.state.roadNetworkLoading){editor.status('Najprv počkaj na načítanie cestnej siete výrezu.');return false;}
  if(!globalStore()?.sources.some(siteCovered)){editor.status('Cestná sieť sa nenačítala. Vyber miesto pokusu znova a počkaj na celý výrez.');return false;}
  const near=editor.nearestRoad(p);
  if(near&&near.d<20)return true;
  editor.status('Na tomto mieste sa nenašla jazdná cesta z OpenStreetMap. Klikni bližšie k vozovke.');
  return false;
}
window.simulatorEarthEnsureRoad=ensureRoad;
function roadAtScreenPoint(point){
  const radius=16,base=basis();
  let best=null;
  for(const road of editor.state.world.roads.segments){
    let a=null;
    for(const [x,y] of road.shape){
      const b=map.project(localToGeo(x,y,base));
      if(a){
        const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((point.x-a.x)*dx+(point.y-a.y)*dy)/(dx*dx+dy*dy||1)));
        const d=Math.hypot(point.x-a.x-t*dx,point.y-a.y-t*dy);
        if(d<=radius&&(!best||d<best.distance))best={id:road.id,distance:d};
      }
      a=b;
    }
  }
  return best?.id||null;
}
function mapClick(e){
  if(!editor.state.world)return;
  const picked=geoToLocal(e.lngLat.lng,e.lngLat.lat);
  if(!editor.state.replay&&!editor.state.routeTargetCar&&!editor.state.routeTargetGroup&&
      (map.getZoom()<9||editor.state.tool==='select'&&
      (picked.x<0||picked.x>extent()||picked.y<0||picked.y>height()))){
    try{window.simulatorSitePlacement.place(e.lngLat.lat,e.lngLat.lng);}catch(error){editor.status(error.message);}
    return;
  }
  if(editor.state.replay&&editor.state.tool==='select'){
    const packet=map.queryRenderedFeatures(e.point,{layers:['packet-link-hit']})[0];
    if(packet&&editor.activePacketLinks().some(link=>link.from===packet.properties.from&&
        link.to===packet.properties.to&&link.kind===packet.properties.kind)){
      editor.selectPacketLink(packet.properties.from,packet.properties.to,packet.properties.kind);return;
    }
  }
  const [lon,lat]=[e.lngLat.lng,e.lngLat.lat],p=geoToLocal(lon,lat),tool=editor.state.tool;
  if(editor.state.routeTargetCar||editor.state.routeTargetGroup){
    if(p.x<0||p.x>extent()||p.y<0||p.y>height()){editor.status(`Cieľ trasy vyber v pracovnom ${extent()/1000} × ${height()/1000} km výreze.`);return;}
    window.simulatorRoutes?.clickDestination(p,roadAtScreenPoint(e.point));return;
  }
  const hit=map.queryRenderedFeatures(e.point,{layers:['editor-objects-circle']})[0];
  if(hit&&editor.state.tool==='select'){
    const type=hit.properties.type,id=hit.properties.id;
    const active=type==='car'?editor.state.demand.vehicles.some(x=>x.id===id):editor.state.world.rsus.some(x=>x.id===id);
    if(active){if(type==='car'&&e.originalEvent?.shiftKey){window.simulatorRoutes?.toggleGroup(id);return;}editor.state.selected={type,id};editor.state.inspectorKey=null;editor.render();return;}
  }
  if(tool==='select'){
    const building=map.queryRenderedFeatures(e.point,{layers:['editor-buildings-fill']})[0];
    if(building){
      editor.state.selected={type:'building',id:building.properties.id};editor.state.inspectorKey=null;editor.render();return;
    }
    if(referenceEnabled()){
      const reference=referenceRsus.find(row=>{const p=map.project([row.longitude_deg,row.latitude_deg]);return Math.hypot(p.x-e.point.x,p.y-e.point.y)<=10;});
      if(reference){editor.status(`Evidovaná RSU ${reference.label||reference.id} · ${reference.latitude_deg.toFixed(6)}°, ${reference.longitude_deg.toFixed(6)}°. Modelovú RSU sem pridáš nástrojom RSU.`);return;}
    }
    if(p.x>=0&&p.x<=extent()&&p.y>=0&&p.y<=height()){
      const localBuilding=window.simulatorBuildings?.at(p);
      if(localBuilding){editor.state.selected={type:'building',id:localBuilding.id};editor.state.inspectorKey=null;editor.render();return;}
      const roadId=roadAtScreenPoint(e.point);
      if(roadId){
        editor.state.selected={type:'road',id:roadId};editor.state.inspectorKey=null;editor.render();return;
      }
    }
    return;
  }
  if(p.x<0||p.x>extent()||p.y<0||p.y>height()){editor.status(`Objekt je mimo žltého ${extent()/1000} × ${height()/1000} km výrezu. Vyber nové miesto pokusu alebo priblíž na výrez.`);return;}
  if(tool==='road'){if(mode.value==='real')return editor.status('V reálnom režime cestu nekreslíš.');editor.addRoadPoint(p);}
  else if(tool==='car'){if(mode.value==='real'&&!ensureRoad(p))return;editor.addCar(p);}
  else if(tool==='rsu')editor.addRsu(p);
  else if(tool==='building')window.simulatorBuildings?.add(p);
}
try{
  const g=editor.state.world?.georeference||{longitude_deg:17.1077,latitude_deg:48.1486};
  map=new maplibregl.Map({container:earth,style:mode.value==='real'?realStyle:emptyStyle,center:[g.longitude_deg,g.latitude_deg],zoom:wholeEarthZoom(),minZoom:-1,maxZoom:20,attributionControl:true,antialias:true});
  map.addControl(new maplibregl.ScaleControl({maxWidth:120,unit:'metric'}),'bottom-left');
  map.dragRotate.enable();
  map.on('style.load',()=>{rememberStyle(map);map.setProjection({type:'globe'});addOverlay();lastOrbitKey='';lastOrbitDraw=0;lastEditor=0;applyBaseLayers(map);ready=true;window.simulatorEarthReady=true;shell.classList.add('earth-ready');map.resize();requestAnimationFrame(()=>{if(ready){map.resize();map.triggerRepaint();}});if(mode.value==='real')initializeGround();syncGround();render();});
  new ResizeObserver(()=>{if(ready)map.resize();}).observe(earth);
  map.on('error',e=>{if(!ready){note.textContent='Reálna mapa sa nenačítala; zostáva lokálny glóbus. '+(e.error?.message||'');}});
  map.on('click',mapClick);
  map.on('dblclick',e=>{if(editor.state.tool==='road'){e.preventDefault();if(editor.state.draft.length>2){editor.state.draft.pop();editor.finishRoad();}}});
  map.on('zoomend',render);
  document.getElementById('earthWhole').onclick=()=>map.flyTo({center:[editor.state.world.georeference.longitude_deg,editor.state.world.georeference.latitude_deg],zoom:wholeEarthZoom(),pitch:0,bearing:0,duration:700});
  document.getElementById('earthSite').onclick=()=>map.flyTo({center:[editor.state.world.georeference.longitude_deg,editor.state.world.georeference.latitude_deg],zoom:16,pitch:50,duration:900});
  mode.onchange=()=>window.simulatorEditorSwitchMapMode?.(mode.value);
  updateNote();
  initializeGlobal();
  if(mode.value==='real')loadRoadNetwork();
}catch(e){note.textContent='Mapový renderer nie je dostupný; lokálny glóbus ostáva funkčný. '+e.message;}
