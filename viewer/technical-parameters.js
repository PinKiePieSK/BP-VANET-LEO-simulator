'use strict';
(() => {
  const $=id=>document.getElementById(id);
  const session=new URLSearchParams(location.search).get('session');
  const channel=window.BroadcastChannel?new BroadcastChannel('simulator-technical-parameters-v1'):null;
  $('backLink').addEventListener('click',event=>{
    if(window.parent!==window&&typeof window.parent.simulatorCloseTechnicalPage==='function'){
      event.preventDefault();window.parent.simulatorCloseTechnicalPage();
    }
  });
  let model=null,current=null,live=false,pending=null,notice='';
  const filters={},pages={},opened={};
  const fmt=n=>Number.isFinite(Number(n))?Number(n).toLocaleString('sk-SK',{maximumFractionDigits:3}):'—';
  const value=v=>v===undefined||v===null||v===''?'—':typeof v==='boolean'?(v?'áno':'nie'):Array.isArray(v)?v.join(' · '):typeof v==='object'?JSON.stringify(v):String(v);
  const status=t=>{$('pageStatus').textContent=t;};
  async function get(url){const r=await fetch(url);const body=await r.json();if(!r.ok)throw Error(body.reason||body.error||`HTTP ${r.status}`);return body;}
  function request(){if(session&&channel)channel.postMessage({session,type:'request'});}
  function group(title){const el=document.createElement('section');el.className='technical-group';const h=document.createElement('h2');h.textContent=title;const grid=document.createElement('div');grid.className='sections';el.append(h,grid);$('sections').append(el);return grid;}
  function section(title,parent){const el=document.createElement('section');el.className='section';const h=document.createElement('h3');h.textContent=title;el.append(h);parent.append(el);return el;}
  function row(parent,name,shown,kind='source',note='',edit=null){
    const el=document.createElement('div');el.className='param';const label=document.createElement('span');label.className='name';label.textContent=name;
    const val=document.createElement('span');val.className='value';
    if(edit&&live&&channel&&session){
      const input=document.createElement(edit.options?'select':'input');
      if(edit.options){for(const [key,text] of edit.options)input.add(new Option(text,key));input.value=String(shown);}
      else {input.type='number';input.min=edit.min;input.max=edit.max;input.step=edit.step||1;input.value=edit.value??shown;}
      input.setAttribute('aria-label',name);
      let timer=null,lastSent=null;
      const commit=()=>{
        if(timer){clearTimeout(timer);timer=null;}
        const changed=edit.options?input.value:Number(input.value);
        if(!edit.options&&(input.value.trim()===''||!Number.isFinite(changed)||changed<edit.min||changed>edit.max||edit.integer&&!Number.isInteger(changed))){render();status(`Neplatná hodnota: ${name}.`);return;}
        if(changed===lastSent||changed===shown)return;lastSent=changed;
        pending={field:edit.field,old:shown};channel.postMessage({session,type:'patch',field:edit.field,value:changed});status(`Mením ${name} v otvorenom editore…`);
      };
      input.addEventListener('change',commit);
      if(!edit.options){input.addEventListener('blur',commit);input.addEventListener('input',()=>{if(timer)clearTimeout(timer);timer=setTimeout(commit,500);});}
      val.append(input);
    }else val.textContent=value(shown);
    if(note){const small=document.createElement('small');small.textContent=note;val.append(small);}
    const tag=document.createElement('span');tag.className=`tag ${edit&&live?'editable':kind}`;
    tag.textContent=edit&&live?'Tu':{editable:'Tu',elsewhere:'Simulátor',derived:'Odvodené',fixed:'Pevné',assumed:'Predpoklad',source:'Zdroj'}[kind]||kind;
    el.append(label,val,tag);parent.append(el);
  }
  function detail(parent,title,data){if(data===undefined||data===null)return;const el=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=title;pre.textContent=JSON.stringify(data,null,2);el.append(summary,pre);parent.append(el);}
  function catalogue(parent,key,title,items,searchText,draw){
    const sectionEl=document.createElement('details');sectionEl.className='catalogue';
    sectionEl.open=!!opened[key];
    const summary=document.createElement('summary');summary.textContent=`${title} · ${items.length}`;
    sectionEl.append(summary);parent.append(sectionEl);
    const tools=document.createElement('div');tools.className='catalogue-tools';
    const search=document.createElement('input');search.type='search';search.placeholder='Hľadať podľa ID alebo názvu';search.setAttribute('aria-label',`Hľadať: ${title}`);search.value=filters[key]||'';
    const count=document.createElement('span'),previous=document.createElement('button'),next=document.createElement('button');
    previous.type=next.type='button';previous.textContent='←';next.textContent='→';
    const content=document.createElement('div');tools.append(search,previous,count,next);sectionEl.append(tools,content);
    const refresh=()=>{
      const query=(filters[key]||'').toLocaleLowerCase('sk-SK');
      const matches=query?items.filter(item=>searchText(item).toLocaleLowerCase('sk-SK').includes(query)):items;
      const last=Math.max(0,Math.ceil(matches.length/25)-1);pages[key]=Math.min(pages[key]||0,last);
      const page=pages[key],start=page*25;content.replaceChildren();
      for(const item of matches.slice(start,start+25))draw(content,item);
      count.textContent=matches.length?`${start+1}–${Math.min(start+25,matches.length)} / ${matches.length}`:'0 / 0';
      previous.disabled=page===0;next.disabled=page===last;
    };
    search.oninput=()=>{filters[key]=search.value;pages[key]=0;refresh();};
    previous.onclick=()=>{pages[key]--;refresh();};next.onclick=()=>{pages[key]++;refresh();};
    sectionEl.addEventListener('toggle',()=>{opened[key]=sectionEl.open;if(sectionEl.open)refresh();});
    if(sectionEl.open)refresh();
  }
  function roadStats(roads){
    if(!roads)return {segments_count:0,nodes_count:0,classes:{}};
    if(!roads.segments)return roads;
    const segments=roads.segments,classes={};let low=Infinity,high=-Infinity,lanes=0,directed=0,oneway=0;
    for(const road of segments){
      classes[road.road_class||'neuvedená']=(classes[road.road_class||'neuvedená']||0)+1;
      if(road.oneway)oneway++;
      for(const direction of (road.oneway?['forward']:['forward','reverse'])){
        directed++;
        const speed=Number(road[`speed_${direction}_mps`]??road.speed_limit_mps);
        if(Number.isFinite(speed)){low=Math.min(low,speed);high=Math.max(high,speed);}
        lanes=Math.max(lanes,Number(road[`lanes_${direction}`]??road.lanes_each_direction)||0);
      }
    }
    return {segments_count:segments.length,nodes_count:roads.nodes?.length||roads.nodes_count||0,classes,turn_rules:roads.turn_rules||[],directed_edges_count:directed,oneway_count:oneway,speed_min_mps:Number.isFinite(low)?low:null,speed_max_mps:Number.isFinite(high)?high:null,max_lanes_per_direction:lanes};
  }
  function enabled(sc){if(sc.satellite_enabled)return true;return Object.values(sc.node_policy?.rsus||{}).some(x=>x.satellite_backhaul);}
  function render(){
    if(!current||!model)return;
    const {scenario:sc,world,demand}=current;
    const width=world.width_m||world.extent_m||2000,height=world.height_m||world.extent_m||2000;
    const sat=sc.satellite||{},env=sat.environment||{},geo=world.georeference||{};
    const roads=roadStats(world.roads),cars=demand.vehicles||[],rsus=world.rsus||[];
    const profile=model.physical_profiles?.[sat.orbit_group]||{};
    const satellite=Boolean(sc.satellite_enabled||Object.values(sc.node_policy?.rsus||{}).some(x=>x.satellite_backhaul));
    const denm=sc.denm_events||[],engine={...model.engine_defaults,...sc.engine};
    if(sc.engine?.dcc_enabled===undefined)engine.dcc_enabled=Boolean(denm.length);
    const vehicle={...model.sumo_vehicle,...world.simulation?.vehicle_model};
    $('scenarioTitle').textContent=sc.scenario_id||'Nový scenár';
    $('sections').replaceChildren();

    const overviewGroup=group('Scenár a spoločný čas');
    const timing=section('Čas a opakovateľnosť',overviewGroup);
    row(timing,'Dĺžka · s',world.simulation?.duration_s,'source','Rovnaké trvanie pohybu, komunikácie a replay.',{field:'duration_s',min:satellite?6:2,max:120,integer:true});
    const origin=Date.parse(sc.utc_origin||'');
    row(timing,'Začiatok UTC',Number.isFinite(origin)?new Date(origin+model.start_offset_s*1000).toISOString():'—','elsewhere');
    row(timing,'Vzorky pre paketový beh',sc.sample_count,'derived','Dĺžka × 10 vzoriek/s.');
    row(timing,'Krok polohy',`${fmt(world.simulation?.step_s??model.sample_step_s)} s`,'fixed');
    row(timing,'Seed',sc.seed,'source','',{field:'seed',min:1,max:2147483647,integer:true});
    row(timing,'ns-3 run',sc.ns3_run,'source','',{field:'ns3_run',min:1,max:2147483647,integer:true});
    row(timing,'Režim',sc.mode,'fixed');
    row(timing,'Aktuálny overený beh',current.run_id||'—','derived');

    const sumoGroup=group('SUMO · doprava a pohyb');
    const environment=section('Mapa a pohyb',sumoGroup);
    row(environment,'Mapa',world.map_source==='osm_live'?'OpenStreetMap':'Ručná','elsewhere');
    row(environment,'Pracovný výrez',`${fmt(width)} × ${fmt(height)} m`,'elsewhere');
    row(environment,'Stred WGS84',`${fmt(geo.latitude_deg)}°, ${fmt(geo.longitude_deg)}°`,'elsewhere');
    row(environment,'Autá / RSU',`${fmt(cars.length)} / ${fmt(rsus.length)}`,'derived');
    row(environment,'Jazdné úseky',fmt(roads.segments_count),'derived');
    row(environment,'Vstupné smerové hrany',fmt(roads.directed_edges_count),'derived');
    row(environment,'Jednosmerné úseky',fmt(roads.oneway_count),'derived');
    row(environment,'Najviac pruhov v jednom smere',fmt(roads.max_lanes_per_direction),'derived');
    row(environment,'Zakázané smerové odbočenia',fmt(roads.turn_rules?.length||0),'source','road.con.xml uvádza všetky povolené prechody medzi smerovými hranami a vylučuje tieto zákazy aj priame otočenie na tej istej ceste.');
    row(environment,'Rýchlosť ciest',roads.speed_min_mps!=null?`${fmt(roads.speed_min_mps*3.6)}–${fmt(roads.speed_max_mps*3.6)} km/h`:'—','source');
    row(environment,'Budovy',fmt(env.building_count??env.buildings?.length??0),'source');
    if(env.height_case)row(environment,'Účinný variant výšok',env.height_case,'source','',
      {field:'environment.height_case',options:[['low','Nízky'],['central','Stredný'],['high','Vysoký']]});
    row(environment,'Dopravný vstup',demand.kind==='measured_trips'?'Merané trasy':'Generované trasy','source');
    row(environment,'Pôvod trás',demand.provenance,'source');
    if(live){
      row(environment,'Generátor · počet áut',current.ui?.spawn_count,'elsewhere','Ovláda iba ďalšie generovanie, nie už vytvorený beh.');
      row(environment,'Generátor · cieľ dĺžky jazdy',`${fmt(current.ui?.traffic_trip_percent)} %`,'elsewhere','Ovláda iba ďalšie generovanie trás.');
    }
    detail(environment,'Zdroj cestnej siete',world.road_source);

    const mobility=section('Vozidlá a cesty',sumoGroup);
    row(mobility,'Krok SUMO · s',world.simulation?.step_s??model.sample_step_s,'fixed');
    row(mobility,'Dopravný seed',sc.seed,'derived','Rovnaký seed je zapísaný do SUMO.');
    row(mobility,'Normalizácia súradníc v netconvert','vypnutá','fixed','--offset.disable-normalization=true; miestne X/Y zostávajú vo vstupnej sústave.');
    row(mobility,'Výsledná cestná sieť','vytvorí netconvert','derived','road.net.xml obsahuje skutočné križovatky a môže zaokrúhliť rýchlosť či geometriu zo vstupných XML.');
    if(roads.turn_rules?.length)detail(mobility,'Zakázané odbočenia pre road.con.xml',roads.turn_rules);
    for(const [name,key,min,max,step] of [
      ['Zrýchlenie · m/s²','accel_mps2',.1,10,.1],['Brzdenie · m/s²','decel_mps2',.1,15,.1],
      ['Náhodnosť vodiča σ','sigma',0,1,.01],['Dĺžka auta · m','length_m',1,20,.1],
      ['Šírka auta · m','width_m',.5,3,.1],['Minimálny odstup · m','min_gap_m',0,10,.1],
      ['Faktor rýchlosti','speed_factor',.1,2,.01]])
      row(mobility,name,vehicle[key],'source','',{field:`vehicle_model.${key}`,min,max,step});
    row(mobility,'Odchodový pruh','best','fixed');
    row(mobility,'Pozícia po dosiahnutí cieľa','auto zostáva v SUMO do konca komunikačného okna','fixed');
    catalogue(mobility,'cars','Autá',cars,car=>car.id+' '+car.route?.map(h=>h.segment).join(' '),(box,car)=>{
      const group=document.createElement('div');group.className='catalogue-item';box.append(group);
      const h=document.createElement('h3');h.textContent=car.id;group.append(h);
      const maximum=car.max_speed_mps??(world.map_source==='osm_live'?car.depart_speed_mps:vehicle.manual_max_speed_mps);
      row(group,'Maximálna rýchlosť · km/h',Math.round(maximum*360)/100,'source','',{field:`car:${car.id}:speed_kmh`,min:.36,max:144,step:0.1});
      const speedMode=car.depart_speed_mode??(world.map_source==='osm_live'?'max':'fixed');
      row(group,'Rýchlosť pri štarte',speedMode,'source','',{field:`car:${car.id}:depart_speed_mode`,options:[['max','Automatická · max'],['fixed','Vlastná hodnota']]});
      row(group,'Počiatočná rýchlosť · km/h',Math.round(car.depart_speed_mps*360)/100,'source',speedMode==='max'?'Použije sa po prepnutí na vlastnú hodnotu.':'',{field:`car:${car.id}:initial_speed_kmh`,min:0,max:144,step:0.1});
      row(group,'Model auta',car.vehicle_model?'vlastné hodnoty':'predvolené hodnoty','derived');
      for(const [name,key] of [
        ['Zrýchlenie · m/s²','accel_mps2'],['Brzdenie · m/s²','decel_mps2'],
        ['Náhodnosť vodiča σ','sigma'],['Dĺžka auta · m','length_m'],
        ['Šírka auta · m','width_m'],['Minimálny odstup · m','min_gap_m'],
        ['Faktor rýchlosti','speed_factor']])
        row(group,name,car.vehicle_model?.[key]??vehicle[key],car.vehicle_model?.[key]===undefined?'derived':'source');
      row(group,'Odchod · s',car.depart_s,'fixed','V aktuálnom zjednotenom behu všetky autá štartujú v čase 0.');
      row(group,'Počiatočná poloha na ceste · m',car.depart_pos_m??0,'elsewhere');
      row(group,'Cieľová poloha na ceste · m',car.arrival_pos_m??'koniec posledného úseku','elsewhere');
      row(group,'Technológie vo vstupnom JSON',car.technologies||[],'source','Schéma vyžaduje ITS-G5; skutočné zapnutie rádia určuje politika uzla.');
      row(group,'Úseky trasy',car.route?.length||0,'source');
      detail(group,'Celá trasa',car.route);
    });
    catalogue(mobility,'roads','Cesty',world.roads?.segments||[],road=>`${road.id} ${road.name||''} ${road.road_class||''}`,(box,road)=>{
      const group=document.createElement('div');group.className='catalogue-item';box.append(group);
      const h=document.createElement('h3');h.textContent=`${road.name||road.id} · ${road.id}`;group.append(h);
      row(group,'Trieda',road.road_class||'—','elsewhere','Používa ju generátor áut; nie je atribútom hrany SUMO.');
      row(group,'Dĺžka · m',fmt(road.length_m??0),'derived');
      row(group,'Smer',road.oneway?'jednosmerná':'obojsmerná','source');
      row(group,'Limit začiatok → koniec · m/s',road.speed_forward_mps??road.speed_limit_mps,'source','Presný vstup road.edg.xml; výsledný road.net.xml môže hodnotu zaokrúhliť.',{field:`road:${road.id}:speed_forward_mps`,min:1,max:40,step:'any'});
      row(group,'Pruhy začiatok → koniec',road.lanes_forward??road.lanes_each_direction,'source','',{field:`road:${road.id}:lanes_forward`,min:1,max:6,integer:true});
      if(!road.oneway){
        row(group,'Limit koniec → začiatok · m/s',road.speed_reverse_mps??road.speed_limit_mps,'source','Presný vstup road.edg.xml; výsledný road.net.xml môže hodnotu zaokrúhliť.',{field:`road:${road.id}:speed_reverse_mps`,min:1,max:40,step:'any'});
        row(group,'Pruhy koniec → začiatok',road.lanes_reverse??road.lanes_each_direction,'source','',{field:`road:${road.id}:lanes_reverse`,min:1,max:6,integer:true});
      }
      row(group,'Uzly',`${road.from} → ${road.to}`,'source');
      if(road.osm_way_id)row(group,'OSM way',road.osm_way_id,'elsewhere','ID zdroja OSM, nie atribút hrany SUMO.');
    });

    const ns3Group=group('ns-3 · pozemná rádiová sieť');
    const ground=section('ITS-G5 / OCB',ns3Group);
    row(ground,'Prenos','ITS-G5 · 802.11p OCB · 10 MHz','fixed');
    row(ground,'PHY rýchlosť · Mb/s',String(sc.radio?.rate_mbps??6),'source','',
      {field:'radio.rate_mbps',options:[['3','3'],['6','6'],['12','12'],['24','24']]});
    row(ground,'Frekvencia · GHz',(5000+5*(sc.radio?.channel_number??180))/1000,'derived');
    row(ground,'Kanál 10 MHz',String(sc.radio?.channel_number??180),'source','',
      {field:'radio.channel_number',options:[172,174,176,178,180,182,184].map(x=>[String(x),String(x)])});
    row(ground,'Model šírenia',env.building_count>0?'urban_osm_building':sc.radio?.mode||'—','derived');
    row(ground,'Zvolený model',sc.radio?.mode||'—','source',sat.environment?.building_count?'Pri budovách sa účinne použije urban_osm_building.':'',{field:'radio.mode',options:[['urban_los','Mestský LOS'],['friis','Friis']]});
    row(ground,'Výkon vysielača · dBm',sc.radio?.tx_power_dbm,'source','',{field:'radio.tx_power_dbm',min:0,max:33,step:0.1});
    row(ground,'Šumové číslo · dB',sc.radio?.noise_figure_db,'source','',{field:'radio.noise_figure_db',min:0,max:20,step:0.1});
    row(ground,'Zisk vysielacej antény · dBi',sc.radio?.tx_gain_dbi??0,'source','',{field:'radio.tx_gain_dbi',min:-20,max:20,step:.1});
    row(ground,'Zisk prijímacej antény · dBi',sc.radio?.rx_gain_dbi??0,'source','',{field:'radio.rx_gain_dbi',min:-20,max:20,step:.1});
    row(ground,'Tieňovanie kanála',sc.radio?.shadowing?'yes':'no','source','',
      {field:'radio.shadowing',options:[['no','Nie'],['yes','Áno']]});
    for(const [key,label,min,max,step] of [
      ['car_antenna_height_m','Anténa auta · m',.2,10,.1],
      ['rsu_antenna_min_height_m','Min. anténa RSU · m',.2,100,.1],
      ['rsu_roof_clearance_m','Anténa RSU nad strechou · m',0,50,.1]])
      row(ground,label,engine[key],'source','',{field:`engine.${key}`,min,max,step});
    row(ground,'Horný limit posunu uzla · µs',engine.cam_phase_cap_us,'source','',{field:'engine.cam_phase_cap_us',min:0,max:1000,integer:true});
    row(ground,'Účinný posun uzla · µs',Math.min(engine.cam_phase_cap_us,Math.max(1,Math.floor(90000/(cars.length+rsus.length+1)))),'derived');
    row(ground,'Prenosová šírka kanála · MHz',model.ground_channel_width_mhz,'fixed');
    catalogue(ground,'rsu-phy','Rádiové profily RSU',rsus,rsu=>rsu.id,(box,rsu)=>{
      const item=document.createElement('div');item.className='catalogue-item';box.append(item);
      const heading=document.createElement('h3');heading.textContent=rsu.id;item.append(heading);
      const own=rsu.radio_model||{};
      row(item,'Profil',rsu.radio_model?'vlastný':'spoločný','source');
      if(rsu.radio_model)row(item,'Obnoviť spoločný profil','no','source','',
        {field:`rsu:${rsu.id}:radio_reset`,options:[['no','Ponechať vlastný'],['yes','Predvolené']]});
      for(const [key,label,min,max] of [
        ['tx_power_dbm','Výkon · dBm',0,33],['noise_figure_db','Šumové číslo · dB',0,20],
        ['tx_gain_dbi','Zisk TX · dBi',-20,20],['rx_gain_dbi','Zisk RX · dBi',-20,20]])
        row(item,label,own[key]??sc.radio[key]??0,'source',own[key]===undefined?'spoločný profil':'vlastný profil',
          {field:`rsu:${rsu.id}:${key}`,min,max,step:.1});
      row(item,'Výška antény podľa strechy',own.antenna_height_m===undefined?'yes':'no','source','',
        {field:`rsu:${rsu.id}:antenna_auto`,options:[['yes','Áno'],['no','Nie']]});
      if(own.antenna_height_m!==undefined)
        row(item,'Vlastná výška · m',own.antenna_height_m,'source','',{field:`rsu:${rsu.id}:antenna_height_m`,min:.2,max:100,step:.1});
    });
    if(env.buildings?.length)catalogue(ground,'buildings','Budovy v kanáli',env.buildings,building=>`${building.id} ${building.building_class||''}`,(box,building)=>{
      const item=document.createElement('div');item.className='catalogue-item';box.append(item);
      const heading=document.createElement('h3');heading.textContent=building.id;item.append(heading);
      row(item,'Trieda',building.building_class||'—','source');
      for(const [key,label] of [['height_min_m','Nízka výška · m'],['height_central_m','Stredná výška · m'],['height_max_m','Vysoká výška · m']])
        row(item,label,building[key],'source','',{field:`building:${building.id}:${key}`,min:0,max:500,step:.1});
      row(item,'Zdroj výšky',building.height_source||'—','source');
      detail(item,'Body pôdorysu · X/Y m',building.polygon_xy_m);
    });
    const appGroup=group('Aplikačná konfigurácia komunikácie');
    const participants=section('Uzly a smerovanie',appGroup);
    const carOptions=cars.map(car=>[car.id,car.id]);
    if(carOptions.length)row(participants,'Referenčné auto CAM',sc.source_id,'source','',{field:'source_id',options:carOptions});
    catalogue(participants,'car-radios','Rádiá áut',cars,car=>car.id,(box,car)=>{
      const group=document.createElement('div');group.className='catalogue-item';box.append(group);
      const h=document.createElement('h3');h.textContent=car.id;group.append(h);
      row(group,'ITS-G5',sc.node_policy?.cars?.[car.id]?.ground||'all','source','',{field:`car:${car.id}:ground`,options:[['all','Autá aj RSU'],['cars','Iba autá'],['off','Vypnuté']]});
      const own=car.radio_model||{};
      row(group,'Rádiový profil',car.radio_model?'vlastný':'spoločný','derived');
      if(car.radio_model)row(group,'Obnoviť spoločný profil','no','source','',
        {field:`car:${car.id}:radio_reset`,options:[['no','Ponechať vlastný'],['yes','Predvolené']]});
      for(const [key,label,min,max,shared] of [
        ['tx_power_dbm','Výkon · dBm',0,33,sc.radio.tx_power_dbm],
        ['noise_figure_db','Šumové číslo · dB',0,20,sc.radio.noise_figure_db],
        ['tx_gain_dbi','Zisk TX · dBi',-20,20,sc.radio.tx_gain_dbi??0],
        ['rx_gain_dbi','Zisk RX · dBi',-20,20,sc.radio.rx_gain_dbi??0],
        ['antenna_height_m','Výška antény · m',.2,10,engine.car_antenna_height_m]])
        row(group,label,own[key]??shared,'source',own[key]===undefined?'spoločný profil':'vlastný profil',
          {field:`car:${car.id}:${key}`,min,max,step:.1});
    });
    catalogue(participants,'rsu-radios','RSU',rsus,rsu=>rsu.id,(box,rsu)=>{
      const group=document.createElement('div');group.className='catalogue-item';box.append(group);
      const h=document.createElement('h3');h.textContent=rsu.id;group.append(h);
      const policy=sc.node_policy?.rsus?.[rsu.id]||{};
      const mode=policy.satellite_backhaul?'both':policy.ground?'ground':'off';
      row(group,'Komunikácia',mode,'source','',{field:`rsu:${rsu.id}:mode`,options:[['both','ITS-G5 + satelit'],['ground','Iba ITS-G5'],['off','Vypnutá']]});
      row(group,'X · m',rsu.x_m,'source','',{field:`rsu:${rsu.id}:x_m`,min:0,max:width,step:0.1});
      row(group,'Y · m',rsu.y_m,'source','',{field:`rsu:${rsu.id}:y_m`,min:0,max:height,step:0.1});
      row(group,'Technológie vo vstupnom JSON',rsu.technologies||[],'source','Schéma vyžaduje ITS-G5; skutočné zapnutie rádia určuje politika uzla.');
    });

    const cam=section('CAM a DCC',appGroup);
    row(cam,'DCC',engine.dcc_enabled?'yes':'no','source','',
      {field:'engine.dcc_enabled',options:[['no','Vypnuté'],['yes','Zapnuté']]});
    for(const [key,label,min,max,step,integer] of [
      ['dcc_low_cbr','DCC nízky prah CBR',0,1,.001,false],
      ['dcc_high_cbr','DCC vysoký prah CBR',0,1,.001,false],
      ['dcc_mid_interval_ms','DCC stredný interval · ms',100,1000,1,true],
      ['dcc_high_interval_ms','DCC vysoký interval · ms',100,1000,1,true],
      ['cam_distance_m','CAM zmena polohy · m',0,100,.1,false],
      ['cam_speed_mps','CAM zmena rýchlosti · m/s',0,20,.1,false],
      ['cam_heading_deg','CAM zmena smeru · °',0,180,.1,false],
      ['cam_low_frequency_ms','CAM nízkofrekvenčná časť · ms',100,1000,1,true],
      ['cam_tgen_max_ms','CAM max. interval · ms',100,1000,1,true],
      ['cam_periodic_repeat','CAM počet periodických opakovaní',1,20,1,true]])
      row(cam,label,engine[key],'source','',{field:`engine.${key}`,min,max,step,integer});
    row(cam,'Vstupná vzorka CAM',`${fmt(model.sample_step_s)} s`,'fixed');
    row(cam,'Počet kontrol CAM na auto',sc.sample_count,'derived');
    row(cam,'CAM','jednoskoková správa vozidla','fixed');
    row(cam,'DENM',`${denm.length} naplánovaných udalostí`,'source');
    const alerts=section('Výstraha DENM',appGroup);
    row(alerts,'Typ udalosti','trafficCondition · trafficJam','fixed');
    row(alerts,'Zdrojové autá',Array.from(new Set(denm.map(event=>event.source_id||sc.source_id))).join(', ')||'žiadne','derived');
    row(alerts,'GeoNetworking','geografický broadcast · najviac 3 skoky','fixed');
    row(alerts,'Zdrojová RSU',sc.rsu_id||'—','source');
    row(alerts,'Cieľová RSU',sc.alert_target_rsu||'—','source');
    catalogue(alerts,'denm','Udalosti',denm,event=>`${event.operation} ${event.sequence} ${event.at_s}`,(box,event)=>{
      const index=denm.indexOf(event),group=document.createElement('div');group.className='catalogue-item';box.append(group);
      const h=document.createElement('h3');h.textContent=`${index+1}. action ${event.sequence}`;group.append(h);
      row(group,'Vysiela auto',event.source_id||sc.source_id,'source','',{field:`denm:${index}:source_id`,options:carOptions});
      row(group,'Operácia',event.operation,'source','',{field:`denm:${index}:operation`,options:[['new','Nová'],['update','Aktualizácia'],['cancel','Zrušenie']]});
      for(const [key,label,min,max,step] of [
        ['at_s','Čas od štartu · s',0,world.simulation.duration_s-.001,.001],
        ['sequence','Action sequence',0,65535,1],['validity_s','Platnosť · s',1,86400,1],
        ['radius_m','Geografický polomer · m',1,1780,1],['repetition_ms','Opakovanie · ms; 0 = vypnuté',0,60000,100]])
        row(group,label,event[key],'source','',{field:`denm:${index}:${key}`,min,max,step,integer:key!=='at_s'});
    });

    const snsGroup=group('SNS-3 · satelitná sieť');
    const orbital=section('Konštelácia a paketová vetva',snsGroup);
    row(orbital,'Stav',satellite?'zapnutá':'vypnutá','derived');
    if(satellite){
      row(orbital,'Konštelácia',sat.orbit_group||'—','elsewhere');
      row(orbital,'Orbitálny archív',sat.orbit_snapshot?.path||sat.orbit_snapshot||'—','source');
      row(orbital,'Výber paketovej topológie',live?'automatický pri spustení z editora':sat.catalog_ids?.length?'explicitný vstup':'automatický','derived','Editor pred uložením vyberie jednu družicu pre aktívne RSU a bránu.');
      row(orbital,'Katalógové ID vo vstupnom JSON',sat.catalog_ids?.length?sat.catalog_ids:'automatický výber','source','Editor pri spustení nahradí explicitný zoznam automatickým výberom.');
      row(orbital,'ISL spojenia',sat.isls?.length?sat.isls:'žiadne','source');
      if(sat.catalog_ids?.length){
        row(orbital,'Počiatočná družica · index',sat.initial_serving_sat,'source');
        row(orbital,'Feeder družica · index',sat.feeder_sat,'source');
        row(orbital,'Cieľ handoveru · index',sat.handover_target_sat,'source');
      }
      row(orbital,'Terminál',profile.terminal||'—','source');
      row(orbital,'Skutočne odovzdaný uplink · GHz',sc.link_policy.rf_hz/1e9,'source','Frekvencia odovzdaná natívnemu SNS-3 runneru.');
      row(orbital,'Odovzdaný downlink · GHz',profile.user_downlink_hz/1e9,'derived','Z verejného profilu zvolenej konštelácie.');
      row(orbital,'Minimálna elevácia',`${fmt(profile.minimum_elevation_deg)}°`,'source');
      row(orbital,'Maska scenára · °',sat.mask_deg,'source','Účinný limit je maximum masky a verejne doloženého limitu terminálu.',{field:'satellite.mask_deg',min:0,max:89.999,step:0.1});
      row(orbital,'Účinná minimálna elevácia · °',Math.max(sat.mask_deg,profile.minimum_elevation_deg,90-profile.terminal_zenith_limit_deg),'derived');
      if(Array.isArray(sat.gateway))for(const [index,label,min,max] of [[0,'Brána · šírka °',-90,90],[1,'Brána · dĺžka °',-180,180],[2,'Brána · výška m',-500,9000]])
        row(orbital,label,sat.gateway[index],'source','',{field:`satellite.gateway.${index}`,min,max,step:.0001});
      const active=rsus.filter(rsu=>sc.node_policy?.rsus?.[rsu.id]?.satellite_backhaul).map(rsu=>rsu.id);
      row(orbital,'Zdrojová RSU',sc.rsu_id,'source','',{field:'rsu_id',options:active.map(id=>[id,id])});
      row(orbital,'Cieľová RSU',sc.alert_target_rsu||'','source','',{field:'alert_target_rsu',options:active.filter(id=>id!==sc.rsu_id).map(id=>[id,id])});
      row(orbital,'Paketový model','SNS-3 3.38 · generický DVB','fixed');
      row(orbital,'Žiadosť o prepnutie · µs',engine.satellite_handover_request_us,'assumed','',
        {field:'engine.satellite_handover_request_us',min:1000000,max:10000000,integer:true});
      row(orbital,'Aplikácia ISL profilu · µs',engine.satellite_apply_us,'assumed','',
        {field:'engine.satellite_apply_us',min:2000001,max:14000000,integer:true});
      // The runner passes --satellite_burst=0. Showing its dormant release
      // timestamp as an editable control would imply an effect it cannot have.
      row(orbital,'Dávkovanie aplikačných správ','vypnuté','fixed');
      for(const [key,label,max] of [
        ['backhaul_forward_queue_packets','RSU → satelit · front paketov',1000],
        ['backhaul_reverse_queue_packets','Satelit → RSU · front paketov',1000],
        ['backhaul_forward_service_us','RSU → satelit · obsluha µs',1000000],
        ['backhaul_reverse_service_us','Satelit → RSU · obsluha µs',1000000]])
        row(orbital,label,engine[key],'source','',{field:`engine.${key}`,min:1,max,integer:true});
      row(orbital,'Výkon terminálu · dBW',sat.ut_power_dbw,'source','',{field:'satellite.ut_power_dbw',min:-50,max:20,step:.1});
      row(orbital,'Zisk modelového lúča · dBi',sat.beam_gain_dbi,'assumed','Diagnostický zisk generickej anténnej predlohy.',{field:'satellite.beam_gain_dbi',min:-10,max:60,step:.1});
      for(const [key,label] of [['forward_isl_bps','ISL dopredná kapacita · bit/s'],['reverse_isl_bps','ISL spätná kapacita · bit/s'],
        ['forward_queue_packets','Dopredný front · pakety'],['reverse_queue_packets','Spätný front · pakety']])
        row(orbital,label,sat[key],'source',sat.isls?.length?'':'Pri jednej družici tento parameter nemá aktívny ISL spoj.',
          {field:`satellite.${key}`,min:key.endsWith('_bps')?100:1,max:key.endsWith('_bps')?1e10:10000,integer:true});
    }

    if(satellite){
      const link=section('Terminál a fyzikálne podmienky',snsGroup);
      const policy=sc.link_policy||{};
      row(link,'Režim terminálu',sc.link_policy_override?'custom':'profile','source','',
        {field:'link_policy_override',options:[['profile','Predvolené podľa profilu'],['custom','Vlastné hodnoty']]});
      row(link,'Polovičný zorný uhol montáže · °',sat.orbit_group==='starlink'?engine.satellite_terminal_fov_deg:180,'assumed',
        sat.orbit_group==='starlink'?'':'Pri tejto konštelácii je terminál všesmerový.',
        sat.orbit_group==='starlink'?{field:'engine.satellite_terminal_fov_deg',min:1,max:180,step:.1}:null);
      for(const [key,label,min,max,step,note] of [
        ['rf_hz','Nosná uplinku · Hz',1e9,5e10,1000000,'Skutočný vstup natívneho kanála.'],
        ['compensation','Kompenzácia Dopplera · podiel',0,1,.01,'Predpoklad výskumného modelu.'],
        ['doppler_tolerance_hz','Tolerancia zvyškového Dopplera · Hz',0,1e7,100,'Predpoklad výskumného modelu.'],
        ['zenith_cone_deg','Zenitový kužeľ · °',0,90,.1,'Zorný rozsah terminálu.'],
        ['steering_rate_deg_s','Rýchlosť smerovania · °/s',0,360,.1,'Predpoklad výskumného modelu.'],
        ['beam_half_angle_deg','Polovičný uhol prijatia · °',0,90,.1,'Predpoklad modelu terminálu, nie aktívny lúč operátora.']])
        row(link,label,policy[key],'assumed',note,{field:`link_policy.${key}`,min,max,step});
      row(link,'Tienenie budovami',sat.environment?.building_count?`${sat.environment.building_count} budov`:'bez lokálnych budov','derived');
      if(sat.environment?.building_count){
        row(link,'Variant výšky budov',sat.environment.height_case||'central','source','',{field:'environment.height_case',options:[['low','Nízky'],['central','Stredný'],['high','Vysoký']]});
        detail(link,'Zdroj výšok a terénu',sat.environment);
      }
      if(sat.orbit_group==='starlink')catalogue(link,'mounts','Montáž terminálov RSU',rsus.filter(r=>sc.node_policy?.rsus?.[r.id]?.satellite_backhaul),rsu=>rsu.id,(box,rsu)=>{
        const mount=sat.terminal_mounts?.[rsu.id],group=document.createElement('div');group.className='catalogue-item';box.append(group);
        const h=document.createElement('h3');h.textContent=rsu.id;group.append(h);
        row(group,'Smerová montáž',mount?'yes':'no','assumed','',{field:`rsu:${rsu.id}:mount_enabled`,options:[['no','Predvolená zvislá'],['yes','Nastavená montáž']]});
        if(mount){
          row(group,'Náklon · °',mount.tilt_deg,'assumed','',{field:`rsu:${rsu.id}:tilt_deg`,min:0,max:180,step:.1});
          row(group,'Azimut · °',mount.azimuth_deg,'assumed','',{field:`rsu:${rsu.id}:azimuth_deg`,min:0,max:359.999,step:.1});
        }
      });
      detail(link,'Diagnostický link budget · neovláda natívny paketový kanál',sat.link_budget);
      for(const [key,label,min,max,step,integer] of [
        ['satellite_rtn_feeder_freq_hz','Feeder uplink · Hz',1e9,5e10,1e6,false],
        ['satellite_ut_rx_temp_dbk','Teplota prijímača UT · dBK',0,60,.01,false],
        ['satellite_sat_user_rx_temp_dbk','Teplota družice · dBK',0,60,.01,false],
        ['satellite_gw_rx_temp_dbk','Teplota prijímača brány · dBK',0,60,.01,false],
        ['satellite_sat_queue_max_packets','Front družice · pakety',1,100000,1,true],
        ['satellite_control_slot_ms','Riadiaci slot · ms',10,1000,1,true],
        ['satellite_isl_speed_mps','Rýchlosť šírenia ISL · m/s',1e8,299792458,1,false]])
        row(link,label,engine[key],'assumed','',{field:`engine.${key}`,min,max,step,integer});
      row(link,'Predvolená forward modulácia',engine.satellite_default_fwd_modcod,'assumed','',
        {field:'engine.satellite_default_fwd_modcod',options:[['QPSK_1_TO_2','QPSK 1/2'],['QPSK_1_TO_4','QPSK 1/4']]});
      for(const [key,label] of [['satellite_rtn_arq','Return ARQ'],['satellite_fwd_acm','Forward ACM'],['satellite_rtn_acm','Return ACM']])
        row(link,label,engine[key]?'yes':'no','assumed','',{field:`engine.${key}`,options:[['yes','Áno'],['no','Nie']]});
    }

    const limits=section('Rozsah modelu',group('Hranice modelu'));
    row(limits,'Pozemný backend','ns-3.38 · WAVE/OCB','fixed');
    row(limits,'Satelitný backend',satellite?'ten istý ns-3 proces · SNS-3 3.38':'nepoužíva sa','fixed');
    row(limits,'Satelitné modemy operátorov','nemodelované','fixed');
    row(limits,'Generovanie DENM','udalosť scenára','fixed');
    row(limits,'Dopravné reakcie na DENM','nemodelované','fixed');
    row(limits,'Výsledok nad obzorom','fyzikálny kandidát, nie potvrdená služba','fixed');
    status(live?(current.dirty?'Neuložené zmeny':'Aktuálny scenár'):'Uložený scenár');
  }
  async function saved(id){const data=await get(`/api/simulator/editor/source?scenario=${encodeURIComponent(id)}`);current=data;live=false;render();}
  function download(data){
    const blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=`${data.scenario?.scenario_id||'simulator'}-vstupy.json`;
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  $('exportInputs').onclick=()=>{
    if(!current)return status('Najprv načítaj scenár.');
    if(live&&channel&&session)channel.postMessage({session,type:'export'});
    else download({scenario:current.scenario,world:current.world,demand:current.demand});
  };
  $('savedScenarios').onchange=async()=>{const id=$('savedScenarios').value;if(!id)return;try{await saved(id);}catch(error){status(error.message);}};
  $('liveButton').onclick=()=>{if(!session||!channel)return status('Otvor technické parametre z editora simulátora.');status('Čakám na otvorený editor…');request();};
  if(channel)channel.onmessage=event=>{const msg=event.data;if(!msg||msg.session!==session)return;if(msg.type==='snapshot'&&msg.data){current=msg.data;live=true;pending=null;render();if(notice){status(notice);notice='';}}else if(msg.type==='error'){notice=msg.message||'Zmena sa nepodarila.';pending=null;request();}else if(msg.type==='export'&&msg.data)download(msg.data);};
  if(!session)$('liveButton').disabled=true;
  (async()=>{try{model=await get('/api/simulator/technical-model');model.sumo_vehicle ||= {accel_mps2:2,decel_mps2:4.5,sigma:0,length_m:5,width_m:1.8,min_gap_m:2.5,speed_factor:1,manual_max_speed_mps:40};model.dcc_policy ||= {low_cbr:.004,high_cbr:.012,mid_interval_ms:250,high_interval_ms:500};const list=await get('/api/simulator/scenarios');for(const id of list.scenarios||[])$('savedScenarios').add(new Option(id,id));request();if(!session)status('Vyber uložený scenár alebo otvor túto stránku zo simulátora.');else{setTimeout(()=>{if(!live)request();},400);setTimeout(()=>{if(!live)status('Editor neodpovedá. Otvor stránku zo simulátora alebo vyber uložený scenár.');},1800);}}catch(error){status(`Parametre sa nepodarilo načítať: ${error.message}`);}})();
})();
