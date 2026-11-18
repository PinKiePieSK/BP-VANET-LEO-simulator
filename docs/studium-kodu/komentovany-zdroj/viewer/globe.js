// Glóbus, orbitálny náhľad a synchronizácia pohybu satelitov s replay. Vizualizuje archív
// konštelácie; sám nerozhoduje, ktorý satelit prijal paket.
'use strict';
// Natural Earth 1:110m land outlines (public domain); orbit geometry comes from the local OMM archive.
// Tento objekt drží iba stav zobrazenia: otočenie, zoom, čas animácie, predpovedané polohy a
// informáciu, či sa má sledovať replay. Nie je zdrojom fyzikálneho rozhodnutia o satelitnom
// pakete.
const globe={lon:17.1077,lat:48.1486,zoom:1,time:0,playing:false,followReplay:false,playStartedAt:0,drag:null,motion:null,land:null,pending:false,last:0,loading:null,loadingKey:null,motionRequest:0};
const ORBIT_PREVIEW_SECONDS=10;
// Glóbus teraz zobrazuje satelity pri tom istom UTC ako prvá vzorka SUMO a ns-3. Posun o 10 s sa
// používa iba pri interpretácii historickej schémy 6.
const previewUtc=()=>S.scenario?.utc_origin?new Date(Date.parse(S.scenario.utc_origin)+(globe.time+(S.scenario.schema_version<7?10:0))*1000).toISOString().slice(0,19).replace('T',' ')+' UTC':'';
window.simulatorGlobeState=globe;
const globeCanvas=$('orbitGlobe');
const rad=Math.PI/180;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const degLon=x=>((x+180)%360+360)%360-180;
// Určuje východ, sever a smer k pozorovateľovi pre aktuálne otočenie glóbusu. Chyba v tomto
// základe by spôsobila posun satelitných bodov oproti planéte.
function globeBasis(){let lon=globe.lon*rad,lat=globe.lat*rad,cl=Math.cos(lon),sl=Math.sin(lon),ct=Math.cos(lat),st=Math.sin(lat);return {east:[-sl,cl,0],north:[-st*cl,-st*sl,ct],front:[ct*cl,ct*sl,st]};}
function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
// `globeSize()` zistí skutočnú veľkosť kresliaceho plátna a mierku.
function globeSize(){let r=globeCanvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(1,Math.round(r.width*dpr)),h=Math.max(1,Math.round(r.height*dpr));if(globeCanvas.width!==w||globeCanvas.height!==h){globeCanvas.width=w;globeCanvas.height=h;}return {w,h,cx:w/2,cy:h/2,radius:Math.min(w,h)*.43*globe.zoom};}
function globeUnit(lon,lat){lon*=rad;lat*=rad;let c=Math.cos(lat);return [c*Math.cos(lon),c*Math.sin(lon),Math.sin(lat)];}
// Z geometrie satelitu a minimálneho elevačného uhla vypočíta iba vizuálny obrys pokrytia. Nie je
// to operátorova skutočná oblasť služby ani automatický dôkaz paketovej dostupnosti.
function envelopeFootprint(id,xyz,minElevation){
  // Spherical intersection with Earth. For Iridium/Globalstar the horizon is
  // an upper bound; the actual multi-beam contour is not public per satellite.
  const radius=6371.0,orbit=Math.hypot(...xyz);
  if(orbit<=radius)return null;
  const limit=Math.acos(radius/orbit),target=Math.max(0,minElevation)*rad;
  let low=0,high=limit;
  for(let i=0;i<32;i++){let mid=(low+high)/2,elevation=Math.atan2(orbit*Math.cos(mid)-radius,orbit*Math.sin(mid));if(elevation>=target)low=mid;else high=mid;}
  const angle=low,lat0=Math.atan2(xyz[2],Math.hypot(xyz[0],xyz[1])),lon0=Math.atan2(xyz[1],xyz[0]);
  const ring=[];
  for(let i=0;i<=72;i++){const bearing=2*Math.PI*i/72;
    const latitude=Math.asin(Math.sin(lat0)*Math.cos(angle)+Math.cos(lat0)*Math.sin(angle)*Math.cos(bearing));
    const longitude=lon0+Math.atan2(Math.sin(bearing)*Math.sin(angle)*Math.cos(lat0),Math.cos(angle)-Math.sin(lat0)*Math.sin(latitude));
    ring.push([longitude/rad,latitude/rad]);}
  return {type:'Feature',properties:{id,kind:minElevation>0?'published_elevation_envelope':'geometric_horizon_upper_bound'},geometry:{type:'Polygon',coordinates:[ring]}};
}
function project(unit,basis,geo){let z=dot(unit,basis.front);return {x:geo.cx+geo.radius*dot(unit,basis.east),y:geo.cy-geo.radius*dot(unit,basis.north),front:z>=0};}
function projectLonLat(lon,lat,basis,geo){return project(globeUnit(lon,lat),basis,geo);}
// Z WGS84 miesta a lokálnej pozície RSU vypočíta ECEF súradnice v kilometroch. Používa elipsoid
// WGS84 (`e2`) a lokálne posuny východ/sever; výstup obsahuje aj jednotkové osi na výpočet
// elevácie satelitu.
function siteEcef(){
 const geo=S.world?.georeference;if(!geo)return null;
 const rsu=S.world?.rsus?.find(r=>r.id===S.scenario?.rsu_id)||{x_m:geo.anchor_x_m,y_m:geo.anchor_y_m};
 let lat=geo.latitude_deg*rad,lon=geo.longitude_deg*rad,h=geo.height_m/1000;
 let s=Math.sin(lat),c=Math.cos(lat),cl=Math.cos(lon),sl=Math.sin(lon),e2=6.69437999014e-3,n=6378.137/Math.sqrt(1-e2*s*s);
 const eastOffset=(rsu.x_m-geo.anchor_x_m)/1000,northOffset=(rsu.y_m-geo.anchor_y_m)/1000;
 let xyz=[(n+h)*c*cl-sl*eastOffset-s*cl*northOffset,(n+h)*c*sl+cl*eastOffset-s*sl*northOffset,(n*(1-e2)+h)*s+c*northOffset];
 const p=S.orbitPreview?.site;if(p){lat=p.lat*rad;lon=p.lon*rad;h=(p.height_m??geo.height_m)/1000;s=Math.sin(lat);c=Math.cos(lat);cl=Math.cos(lon);sl=Math.sin(lon);n=6378.137/Math.sqrt(1-e2*s*s);xyz=[(n+h)*c*cl,(n+h)*c*sl,(n*(1-e2)+h)*s];}
 return {xyz,up:[c*cl,c*sl,s],east:[-sl,cl,0],north:[-s*cl,-s*sl,c],sinMask:Math.sin((S.scenario?.satellite?.mask_deg??10)*rad)};
}
// Vyberie dvojicu orbitálnych vzoriek okolo aktuálneho času náhľadu. Medzi nimi sa poloha
// interpoluje, aby desaťsekundový náhľad nepreskakoval po krokoch.
function motionFrame(){let m=globe.motion;if(!m)return null;let frames=m.frames,i=0;while(i+1<frames.length&&frames[i+1].time_s<globe.time)i++;let a=frames[i],b=frames[Math.min(i+1,frames.length-1)],alpha=a===b?0:(globe.time-a.time_s)/(b.time_s-a.time_s);return {a:a.xyz_km,b:b.xyz_km,alpha,ids:m.catalog_ids};}
// Pri prehrávaní používa orbitálne vzorky konkrétneho overeného behu. Predbežný náhľad a replay
// nesmú miešať rôzne epochy.
function replaySatelliteXyz(id){
 if(!globe.followReplay)return null;
 const samples=S.replay?.satelliteByCatalog?.get(id);if(!samples?.length)return null;
 let lo=0,hi=samples.length-1,t=S.time;
 while(lo<hi){let mid=(lo+hi+1)>>1;if(samples[mid].time_us<=t)lo=mid;else hi=mid-1;}
 const a=samples[lo],b=samples[Math.min(lo+1,samples.length-1)];
 if(!a.xyz_km)return null;
 if(a===b||!b.xyz_km)return a.xyz_km;
 const f=clamp((t-a.time_us)/(b.time_us-a.time_us),0,1);
 return a.xyz_km.map((v,i)=>v+(b.xyz_km[i]-v)*f);
}
// `drawLand(ctx,path,geo)` vykresľuje prvok rozhrania.
function drawLand(ctx,path,geo){if(!globe.land)return;ctx.fillStyle='#245056';ctx.strokeStyle='#648688';ctx.lineWidth=Math.max(.8,geo.w/1200);ctx.beginPath();path(globe.land);ctx.fill();ctx.stroke();}
function drawGraticule(ctx,path,geo){ctx.strokeStyle='#3f6970';ctx.lineWidth=Math.max(.7,geo.w/1200);ctx.beginPath();path(d3.geoGraticule10());ctx.stroke();}
// Kreslí Zem, súradnicovú sieť, miesto pokusu, satelity a ich obálky na canvas. Farba satelitu
// odlišuje geometrický kandidát od vybraného paketového podgrafu; kresba sama o sebe nemení
// výsledok ns-3.
function drawGlobe(){
  globe.pending=false;
  const ctx=globeCanvas.getContext('2d'),geo=globeSize(),basis=globeBasis();
  ctx.clearRect(0,0,geo.w,geo.h);
  ctx.save();
  ctx.beginPath();ctx.arc(geo.cx,geo.cy,geo.radius,0,Math.PI*2);
  ctx.fillStyle='#14313d';ctx.fill();ctx.clip();
  const projection=d3.geoOrthographic().rotate([-globe.lon,-globe.lat]).translate([geo.cx,geo.cy]).scale(geo.radius).clipAngle(90);
  const path=d3.geoPath(projection,ctx);
  drawGraticule(ctx,path,geo);drawLand(ctx,path,geo);
  ctx.restore();
  ctx.strokeStyle='#82ada8';ctx.lineWidth=Math.max(1.5,geo.w/500);
  ctx.beginPath();ctx.arc(geo.cx,geo.cy,geo.radius,0,Math.PI*2);ctx.stroke();

  const frame=motionFrame(),site=siteEcef();
  const active=new Set(S.replay?.trace_kind==='native/baseline'?
    (S.replay.satellites||[]).map(row=>row.catalog_id):
    S.orbitDirty?[]:S.scenario?.satellite?.catalog_ids||[]);
  const total=frame?.ids.length||S.orbitPreview?.eligible_count||0;
  const dense=total>1000,satLayer=$('layerSat').checked;
  const dots=[[],[],[],[]]; // other, above mask, physical candidate, active packet graph
  const physical=globe.motion?.physical_profile||S.orbitPreview?.physical_profile;
  let visible=0,possible=0,front=0;
  // Pre jednu družicu vyhodnotí eleváciu nad miestom, fyzikálnu masku a premietnutie na prednú
  // pologuľu glóbusu. Priradí bod do farebnej skupiny. Ide o vizuálnu predpoveď; paketový podgraf
  // sa berie zo scenára alebo overeného replay.
  function collect(id,xyz,staticVisible,staticPhysical){
    const size=Math.hypot(...xyz),unit=xyz.map(v=>v/size),p=project(unit,basis,geo);
    let isVisible=staticVisible,isPhysical=staticPhysical;
    if(site&&frame){
      const rx=xyz[0]-site.xyz[0],ry=xyz[1]-site.xyz[1],rz=xyz[2]-site.xyz[2],range=Math.hypot(rx,ry,rz);
      const sine=(rx*site.up[0]+ry*site.up[1]+rz*site.up[2])/range;
      const elevation=Math.asin(clamp(sine,-1,1))/rad;
      isVisible=sine>=site.sinMask;
      isPhysical=isVisible&&elevation>=Math.max(physical?.minimum_elevation_deg??0,90-(physical?.terminal_zenith_limit_deg??90));
    }
    if(isVisible)visible++;
    if(isPhysical)possible++;
    if(!p.front)return;
    front++;
    dots[active.has(id)?3:isPhysical?2:isVisible?1:0].push(p);
  }
  if(satLayer){
    if(frame){
      for(let i=0;i<frame.ids.length;i++){
        const a=frame.a[i],b=frame.b[i],t=frame.alpha;
        collect(frame.ids[i],replaySatelliteXyz(frame.ids[i])||[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t],false,false);
      }
    }else if(S.orbitPreview){
      for(const p of S.orbitPreview.positions)collect(p.id,p.xyz_km||globeUnit(p.lon,p.lat).map(v=>v*7000),p.visible_site,p.physical_site);
    }
    // Dense groups use crisp one-pixel points; a translucent subpixel dot made Starlink look empty.
    ctx.fillStyle=dense?'#9bb8ba':'#8eaeb2';ctx.globalAlpha=dense?.56:.85;
    if(dense){for(const p of dots[0])ctx.fillRect(Math.round(p.x)-1,Math.round(p.y)-1,2,2);}
    else{for(const p of dots[0]){ctx.beginPath();ctx.arc(p.x,p.y,Math.max(2.2,geo.w/500),0,Math.PI*2);ctx.fill();}}
    ctx.fillStyle='#6ce0cc';ctx.globalAlpha=.92;
    for(const p of dots[1]){ctx.beginPath();ctx.arc(p.x,p.y,Math.max(1.8,geo.w/470),0,Math.PI*2);ctx.fill();}
    ctx.fillStyle='#6ce0cc';ctx.globalAlpha=.95;
    for(const p of dots[2]){ctx.beginPath();ctx.arc(p.x,p.y,Math.max(3,geo.w/240),0,Math.PI*2);ctx.fill();}
    ctx.fillStyle='#f4d278';ctx.globalAlpha=1;
    for(const p of dots[3]){ctx.beginPath();ctx.arc(p.x,p.y,Math.max(3,geo.w/240),0,Math.PI*2);ctx.fill();}
  }
  ctx.globalAlpha=1;
  const anchor=S.world?.georeference;
  if(anchor){
    const p=projectLonLat(anchor.longitude_deg,anchor.latitude_deg,basis,geo);
    if(p.front){
      ctx.fillStyle='#f4b65c';ctx.strokeStyle='#fff2d6';ctx.lineWidth=Math.max(1.5,geo.w/600);
      ctx.beginPath();ctx.arc(p.x,p.y,Math.max(5,geo.w/130),0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.font=`${Math.max(11,geo.w/58)}px system-ui`;ctx.fillStyle='#ffe2aa';ctx.fillText('miesto pokusu',p.x+10,p.y-10);
    }
  }
  const utc=previewUtc();
  $('orbitTimeLabel').textContent=globe.time.toLocaleString('sk-SK',{maximumFractionDigits:1})+' s';
  $('orbitTime').value=String(globe.time);
  $('orbitInfo').textContent=!total?(S.orbitLoading?'Načítavam konšteláciu…':S.orbitError||(!S.scenario?.satellite?'Vyber konšteláciu.':!S.world?.rsus?.length?'Pridaj auto alebo RSU, aby sa určila viditeľnosť satelitov.':'Načítaj satelitný scenár alebo náhľad pohybu.')):!satLayer?
    `${total.toLocaleString('sk-SK')} platných objektov · vrstva satelitov je vypnutá`:
    `${total.toLocaleString('sk-SK')} platných objektov · ${visible} nad maskou · ${possible} vo verejnej fyzikálnej obálke · ${front} na viditeľnej pologuli · ${utc}`;
}
window.renderGlobe=()=>{if(window.simulatorEarthReady){window.renderEarthMap?.();return;}if(!globe.pending){globe.pending=true;requestAnimationFrame(drawGlobe);}};
window.resetGlobeMotion=(keepMotion=false)=>{if(!keepMotion){globe.motionRequest++;globe.motion=null;globe.loading=null;globe.loadingKey=null;S.orbitLoading=false;}globe.playing=false;globe.followReplay=false;globe.time=0;$('orbitPlay').disabled=false;$('orbitTime').disabled=false;$('orbitStartUtc').disabled=false;$('orbitPlay').textContent='▶ Ukážka 10 s';$('orbitTime').max=String(ORBIT_PREVIEW_SECONDS);window.syncGlobeSite?.();window.syncGlobeStart?.();window.renderGlobe();};
window.simulatorSyncReplayOrbit=()=>{
 if(!S.replay)return;
 globe.playing=false;globe.followReplay=true;globe.time=S.time/1e6;
 $('orbitPlay').disabled=!!S.playing;$('orbitTime').disabled=!!S.playing;
 $('orbitStartUtc').disabled=!!S.playing;
 $('orbitPlay').textContent='▶ Ukážka 10 s';$('orbitTime').max=String(S.replay.max/1e6);
 window.renderGlobe();
};
window.syncGlobeSite=()=>{};
window.syncGlobeStart=()=>{if(!S.scenario?.utc_origin)return;const start=Date.parse(S.scenario.utc_origin)+(S.scenario.schema_version<7?10000:0);$('orbitStartUtc').value=new Date(start).toISOString().slice(0,19);};
$('orbitStartUtc').addEventListener('change',()=>{
 try{
  if(!S.scenario)throw Error('Najprv načítaj scenár.');
  const chosen=Date.parse($('orbitStartUtc').value+'Z');
  if(!Number.isFinite(chosen))throw Error('Zadaj platný dátum a čas UTC.');
  const origin=new Date(chosen-(S.scenario.schema_version<7?10000:0)).toISOString().replace('.000Z','Z');
  if(origin===S.scenario.utc_origin)return;
  S.scenario.utc_origin=origin;S.orbitPreview=null;S.orbitDirty=true;S.orbitRequest++;S.orbitError='';
  markDirty();$('orbitSelectionInfo').textContent='Nový začiatok pokusu: prepočítavam viditeľnosť konštelácie od času 0 s.';
  if(S.scenario.satellite&&(S.world.rsus.length||S.demand.vehicles.length))refreshOrbits(true).catch(error);
  else window.previewGlobeConstellation?.().catch(error);
 }catch(e){error(e);window.syncGlobeStart();}
});
// Zmení miesto simulácie po kliknutí na glóbus a spustí obnovenie miestnych ciest a orbitálneho
// náhľadu. Dôležité je udržať rovnakú WGS84 polohu pre mapu, anténu aj satelitnú viditeľnosť.
function updateSite(lat,lon,height,forceReload=false){
 if(!S.world)return;
 if(!Number.isFinite(lat)||lat< -90||lat>90||!Number.isFinite(lon)||lon< -180||lon>180||!Number.isFinite(height)||height< -500||height>9000)throw Error('Miesto: šírka −90…90°, dĺžka −180…180°, výška −500…9000 m.');
 let p=S.world.georeference,changed=p.latitude_deg!==lat||p.longitude_deg!==lon||p.height_m!==height;
 if(!changed&&!forceReload)return;
 p.latitude_deg=lat;p.longitude_deg=lon;p.height_m=height;
 if(S.mapMode==='real')window.simulatorEditorClearRealSite?.();
 S.routeTargetCar=null;S.routeTargetGroup=false;S.orbitPreview=null;S.orbitRequest++;S.orbitDirty=!!S.scenario?.satellite;S.orbitLoading=false;S.orbitError='';
 window.syncGlobeSite();markDirty(S.mapMode==='real');
 $('orbitSelectionInfo').textContent='Miesto sa zmenilo. Automaticky prepočítam viditeľné satelity.';
 window.simulatorEarthFollowSite?.();
 if(S.mapMode==='real')window.simulatorEarthLoadRoadNetwork?.(true);
 window.renderGlobe();
 if(S.scenario?.satellite&&(S.world.rsus.length||S.demand.vehicles.length))refreshOrbits(true).catch(error);else window.previewGlobeConstellation?.().catch(error);
}
window.updateGlobeSite=updateSite;
window.simulatorSitePlacement={place(lat,lon){updateSite(Math.round(lat*1e6)/1e6,Math.round(lon*1e6)/1e6,S.world.georeference.height_m,true);status(`Miesto pokusu: ${lat.toFixed(5)}°, ${lon.toFixed(5)}°.`);return true;}};
window.simulatorOrbitMapData=()=>{
  const frame=motionFrame(),site=siteEcef(),active=new Set(S.replay?.trace_kind==='native/baseline'?
    (S.replay.satellites||[]).map(row=>row.catalog_id):
    S.orbitDirty?[]:S.scenario?.satellite?.catalog_ids||[]);
  const physical=globe.motion?.physical_profile||S.orbitPreview?.physical_profile;
  const features=[],sky=[],footprints=[];let visible=0,possible=0;
  function collect(id,lon,lat,xyz,staticVisible,staticPhysical){
    let above=staticVisible,within=staticPhysical;
    if(site&&xyz){const direction=xyz.map((v,i)=>v-site.xyz[i]),range=Math.hypot(...direction),up=direction.reduce((v,x,i)=>v+x*site.up[i],0)/range;above=up>=site.sinMask;
      const elevation=Math.asin(clamp(up,-1,1))/rad;
      within=above&&elevation>=Math.max(physical?.minimum_elevation_deg??0,90-(physical?.terminal_zenith_limit_deg??90));
      if(above){const east=direction.reduce((v,x,i)=>v+x*site.east[i],0),north=direction.reduce((v,x,i)=>v+x*site.north[i],0);sky.push({id,az:(Math.atan2(east,north)*180/Math.PI+360)%360,el:elevation,physical:within,active:active.has(id)});}}
    if(above)visible++;
    if(within)possible++;
    if(active.has(id)&&xyz){const footprint=envelopeFootprint(id,xyz,physical?.minimum_elevation_deg??0);if(footprint)footprints.push(footprint);}
    features.push({type:'Feature',properties:{id,kind:active.has(id)?within?'active':'active_outside':within?'physical':above?'visible':'other'},geometry:{type:'Point',coordinates:[lon,lat]}});
  }
  if(frame){
    for(let i=0;i<frame.ids.length;i++){
      const a=frame.a[i],b=frame.b[i],t=frame.alpha,xyz=replaySatelliteXyz(frame.ids[i])||[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
      collect(frame.ids[i],Math.atan2(xyz[1],xyz[0])/rad,Math.atan2(xyz[2],Math.hypot(xyz[0],xyz[1]))/rad,xyz,false,false);
    }
  }else if(S.orbitPreview){for(const p of S.orbitPreview.positions)collect(p.id,p.lon,p.lat,p.xyz_km||null,p.visible_site,p.physical_site);}
  return {features,sky,footprints,visible,possible,time:globe.time,utc:previewUtc()};
};
function globePointer(e){let rect=globeCanvas.getBoundingClientRect(),geo=globeSize(),x=(e.clientX-rect.left)*geo.w/rect.width,y=(e.clientY-rect.top)*geo.h/rect.height,u=(x-geo.cx)/geo.radius,v=(geo.cy-y)/geo.radius,d=u*u+v*v;if(d>1)return null;let b=globeBasis(),z=Math.sqrt(1-d),p=[0,1,2].map(i=>b.east[i]*u+b.north[i]*v+b.front[i]*z);return {lon:degLon(Math.atan2(p[1],p[0])/rad),lat:Math.asin(clamp(p[2],-1,1))/rad};}
globeCanvas.addEventListener('pointerdown',e=>{if(e.button===2){globe.drag={x:e.clientX,y:e.clientY,lon:globe.lon,lat:globe.lat};globeCanvas.setPointerCapture(e.pointerId);e.preventDefault();}});
globeCanvas.addEventListener('pointermove',e=>{if(!globe.drag)return;let radius=Math.min(globeCanvas.clientWidth,globeCanvas.clientHeight)*.43*globe.zoom;globe.lon=degLon(globe.drag.lon-(e.clientX-globe.drag.x)*90/radius);globe.lat=clamp(globe.drag.lat+(e.clientY-globe.drag.y)*90/radius,-89.9,89.9);window.renderGlobe();});
globeCanvas.addEventListener('pointerup',e=>{if(e.button===2||globe.drag)globe.drag=null;});globeCanvas.addEventListener('pointercancel',()=>globe.drag=null);globeCanvas.addEventListener('contextmenu',e=>e.preventDefault());
globeCanvas.addEventListener('click',e=>{if(e.button!==0||S.replay)return;let p=globePointer(e);if(!p)return;try{window.simulatorSitePlacement.place(p.lat,p.lon);}catch(err){error(err);}});
globeCanvas.addEventListener('wheel',e=>{e.preventDefault();globe.zoom=clamp(globe.zoom*(e.deltaY>0?.9:1.1),.65,2.6);window.renderGlobe();},{passive:false});
// Žiada krátku časovú predpoveď pre animáciu konštelácie. Predpoveď sa počíta pre vybraný UTC
// začiatok; nepoužíva sa namiesto dlhého simulačného behu.
async function loadGlobeMotion(duration=ORBIT_PREVIEW_SECONDS){
 if(!S.scenario||!S.world)return null;
 const group=$('constellation').value,utc=S.scenario.utc_origin,pin=S.scenario.satellite?.orbit_snapshot?.manifest_sha256||'legacy',key=`${group}:${utc}:${duration}:${pin}`;
 if(globe.motion&&globe.motion.group===group&&globe.motion.utc_origin===utc&&globe.motion.duration_s===duration&&(pin==='legacy'||globe.motion.snapshot_manifest_sha256===pin))return globe.motion;
 if(globe.loading&&globe.loadingKey===key)return globe.loading;
 const request=++globe.motionRequest;
 const pending=post('/api/simulator/editor/orbit-motion',{group,scenario:S.scenario,duration_s:duration}).then(m=>{
  if(request!==globe.motionRequest||group!==$('constellation').value||utc!==S.scenario?.utc_origin||pin!==(S.scenario?.satellite?.orbit_snapshot?.manifest_sha256||'legacy'))return null;
  globe.motion=m;window.renderGlobe();return m;
 }).finally(()=>{if(globe.loading===pending){globe.loading=null;globe.loadingKey=null;}});
 globe.loading=pending;globe.loadingKey=key;return pending;
}
window.simulatorLoadReplayOrbit=async()=>{
 if(!S.replay||!S.scenario?.satellite)return;
 const runId=S.runId,duration=Math.max(2,Math.ceil(S.replay.max/1e6));
 S.orbitLoading=true;window.simulatorSyncReplayOrbit();
 try{const motion=await loadGlobeMotion(duration);if(runId!==S.runId||!S.replay||!motion)return;S.orbitLoading=false;window.simulatorSyncReplayOrbit();}
 catch(e){if(runId===S.runId){S.orbitLoading=false;S.orbitError=`Dráhy replay sa nenačítali: ${e.message||e}`;window.renderGlobe();}throw e;}
};
window.simulatorEnsureReplayOrbit=()=>{
 if(!S.replay||!S.scenario?.satellite||globe.playing)return;
 const duration=Math.max(2,Math.ceil(S.replay.max/1e6));
 if(globe.motion?.duration_s===duration&&globe.motion?.group===$('constellation').value&&globe.motion?.utc_origin===S.scenario.utc_origin&&(!S.scenario.satellite?.orbit_snapshot||globe.motion.snapshot_manifest_sha256===S.scenario.satellite.orbit_snapshot.manifest_sha256))return;
 if(globe.loadingKey===`${$('constellation').value}:${S.scenario.utc_origin}:${duration}:${S.scenario.satellite?.orbit_snapshot?.manifest_sha256||'legacy'}`)return;
 window.simulatorLoadReplayOrbit().catch(error);
};
window.previewGlobeConstellation=async()=>{
 if(!S.scenario||!S.world)return;
 const request=++S.orbitRequest;
 S.orbitLoading=true;S.orbitError='';$('orbitSelectionInfo').textContent='Načítavam geometrický náhľad konštelácie…';window.renderGlobe();
 try{
  const motion=await loadGlobeMotion();if(request!==S.orbitRequest||!motion)return;
  S.orbitLoading=false;
  $('orbitSelectionInfo').textContent=`${motion.catalog_ids.length.toLocaleString('sk-SK')} družíc v archíve.`;
  window.renderGlobe();
 }catch(e){if(request===S.orbitRequest){S.orbitLoading=false;S.orbitError=`Konštelácia sa nenačítala: ${e.message||e}`;$('orbitSelectionInfo').textContent=S.orbitError;window.renderGlobe();}throw e;}
};
if(S.scenario?.satellite&&!S.orbitLoading&&!S.orbitPreview&&!globe.motion)window.previewGlobeConstellation().catch(error);
$('orbitPlay').onclick=async()=>{if(S.playing)return;try{if(!globe.playing){const group=$('constellation').value;globe.followReplay=false;globe.time=0;$('orbitTime').max=String(ORBIT_PREVIEW_SECONDS);$('orbitPlay').textContent='Načítavam dráhy…';const motion=await loadGlobeMotion();if(!motion||group!==$('constellation').value||S.playing)return;globe.playStartedAt=performance.now();globe.last=0;globe.playing=true;$('orbitPlay').textContent='❚❚ Zastaviť';window.renderGlobe();}else{globe.playing=false;$('orbitPlay').textContent='▶ Ukážka 10 s';if(S.replay){window.simulatorSyncReplayOrbit();window.simulatorEnsureReplayOrbit();}else window.renderGlobe();}}catch(e){globe.playing=false;$('orbitPlay').textContent='▶ Ukážka 10 s';error(e);}};
$('orbitTime').oninput=async()=>{if(S.playing)return;if(S.replay&&!globe.playing){S.time=Number($('orbitTime').value)*1e6;$('time').value=Math.round(1000*(S.time-S.replay.min)/(S.replay.max-S.replay.min));showTime();return;}globe.time=Number($('orbitTime').value);globe.playing=false;globe.followReplay=false;$('orbitPlay').textContent='▶ Ukážka 10 s';try{await loadGlobeMotion();}catch(e){error(e);}window.renderGlobe();};
// Čas prehliadača posúva len vizuálnu ukážku. Počas replay sa predbežná ukážka zastaví a satelity
// sa hýbu podľa uloženého času simulácie.
function orbitTick(now){if(globe.playing&&globe.motion){globe.time=((now-globe.playStartedAt)/1000)%ORBIT_PREVIEW_SECONDS;if(now-globe.last>=33){globe.last=now;window.renderGlobe();}}requestAnimationFrame(orbitTick);}requestAnimationFrame(orbitTick);
fetch('/globe-land.json').then(r=>{if(!r.ok)throw Error('Earth outlines unavailable');return r.json();}).then(data=>{globe.land=data;window.renderGlobe();}).catch(()=>window.renderGlobe());
new ResizeObserver(()=>window.renderGlobe()).observe(globeCanvas);
