'use strict';
// The editor remains the owner of unsaved scenario state. The technical page
// receives a bounded snapshot and sends only a small, validated edit patch.
(() => {
  const editor=window.simulatorEditor;
  if(!editor||!window.BroadcastChannel)return;
  const session=crypto.randomUUID();
  const channel=new BroadcastChannel('simulator-technical-parameters-v1');
  const link=document.getElementById('technicalPageLink');
  const view=document.getElementById('technicalView');
  const frame=document.getElementById('technicalFrame');
  link.href=`/technical-parameters.html?v=20261117-car-radio1&session=${encodeURIComponent(session)}`;
  function snapshot(){
    const S=editor.state,scenario=S.scenario,world=S.world,demand=S.demand;
    if(!scenario||!world||!demand)return null;
    const sat=scenario.satellite||{},env=sat.environment||null,roads=world.roads?.segments||[];
    const roadClasses={};let minSpeed=Infinity,maxSpeed=-Infinity,maxLanes=0;
    for(const road of roads){
      roadClasses[road.road_class||'neuvedená']=(roadClasses[road.road_class||'neuvedená']||0)+1;
      for(const direction of (road.oneway?['forward']:['forward','reverse'])){
        const speed=Number(road[`speed_${direction}_mps`]??road.speed_limit_mps);
        if(Number.isFinite(speed)){minSpeed=Math.min(minSpeed,speed);maxSpeed=Math.max(maxSpeed,speed);}
        maxLanes=Math.max(maxLanes,Number(road[`lanes_${direction}`]??road.lanes_each_direction)||0);
      }
    }
    return {scenario:{schema_version:scenario.schema_version,scenario_id:document.getElementById('scenarioId')?.value||scenario.scenario_id,
      mode:scenario.mode,time_policy:scenario.time_policy,seed:scenario.seed,ns3_run:scenario.ns3_run,
      sample_count:scenario.sample_count,utc_origin:scenario.utc_origin,radio:scenario.radio,
      engine:scenario.engine,
      denm_events:scenario.denm_events,
      source_id:scenario.source_id,rsu_id:scenario.rsu_id,alert_target_rsu:scenario.alert_target_rsu,
      node_policy:scenario.node_policy,link_policy:scenario.link_policy,
      link_policy_override:!!scenario.link_policy_override,
      satellite_enabled:Object.values(scenario.node_policy?.rsus||{}).some(x=>x.satellite_backhaul),
      satellite:{orbit_group:sat.orbit_group,orbit_snapshot:sat.orbit_snapshot,gateway:sat.gateway,
        mask_deg:sat.mask_deg,antenna_model:sat.antenna_model,terminal_mounts:sat.terminal_mounts,
        link_budget:sat.link_budget,catalog_ids:sat.catalog_ids||[],isls:sat.isls||[],
        initial_serving_sat:sat.initial_serving_sat,feeder_sat:sat.feeder_sat,
        handover_target_sat:sat.handover_target_sat,beam_gain_dbi:sat.beam_gain_dbi,
        ut_power_dbw:sat.ut_power_dbw,forward_isl_bps:sat.forward_isl_bps,
        reverse_isl_bps:sat.reverse_isl_bps,forward_queue_packets:sat.forward_queue_packets,
        reverse_queue_packets:sat.reverse_queue_packets,
        environment:env?{height_case:env.height_case,height_policy:env.height_policy,
          building_count:env.buildings?.length||0,terrain:{provider:env.sources?.terrain?.provider,
          width:env.terrain?.width,height:env.terrain?.height,step_m:env.terrain?.step_m},
          sources:env.sources,statistical_layers:env.statistical_layers,
          buildings:(env.buildings||[]).map(building=>({id:building.id,
            polygon_xy_m:building.polygon_xy_m,height_min_m:building.height_min_m,
            height_central_m:building.height_central_m,height_max_m:building.height_max_m,
            height_source:building.height_source,building_class:building.building_class}))}:null}},
      world:{map_source:world.map_source,width_m:world.width_m||world.extent_m,
        height_m:world.height_m||world.extent_m,georeference:world.georeference,
        simulation:world.simulation,roads:{nodes_count:world.roads?.nodes?.length||0,
          turn_rules:world.roads?.turn_rules||[],
          segments_count:roads.length,classes:roadClasses,
          segments:roads.map(road=>({id:road.id,name:road.name,road_class:road.road_class,
            osm_way_id:road.osm_way_id,from:road.from,to:road.to,oneway:!!road.oneway,
            speed_limit_mps:road.speed_limit_mps,lanes_each_direction:road.lanes_each_direction,
            speed_forward_mps:road.speed_forward_mps??road.speed_limit_mps,
            speed_reverse_mps:road.speed_reverse_mps??road.speed_limit_mps,
            lanes_forward:road.lanes_forward??road.lanes_each_direction,
            lanes_reverse:road.lanes_reverse??road.lanes_each_direction,
            length_m:road.shape?.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-road.shape[i][0],p[1]-road.shape[i][1]),0)||0})),
          speed_min_mps:Number.isFinite(minSpeed)?minSpeed:null,
          speed_max_mps:Number.isFinite(maxSpeed)?maxSpeed:null,
          max_lanes_per_direction:maxLanes},
        rsus:world.rsus,flows:world.flows,road_source:world.map_objects?.sources},
      demand:{kind:demand.kind,provenance:demand.provenance,vehicles:demand.vehicles.map(car=>({
        id:car.id,depart_s:car.depart_s,depart_speed_mps:car.depart_speed_mps,
        max_speed_mps:car.max_speed_mps,depart_speed_mode:car.depart_speed_mode,
        vehicle_model:car.vehicle_model,radio_model:car.radio_model,
        depart_pos_m:car.depart_pos_m,arrival_pos_m:car.arrival_pos_m,route:car.route,
        technologies:car.technologies}))},
      ui:{traffic_trip_percent:Number(document.getElementById('trafficTripPercent')?.value),
        spawn_count:Number(document.getElementById('spawnCount')?.value)},run_id:S.runId,live:true,
      dirty:S.dirty||document.getElementById('scenarioId')?.value!==scenario.scenario_id};
  }
  function send(){channel.postMessage({session,type:'snapshot',data:snapshot()});}
  function numeric(value,min,max,integer=false){
    if(typeof value!=='number'||!Number.isFinite(value)||value<min||value>max||integer&&!Number.isInteger(value))
      throw Error(`Hodnota musí byť v rozsahu ${min} až ${max}${integer?' a celé číslo':''}.`);
    return value;
  }
  function choice(value,options){if(!options.includes(value))throw Error('Neplatná voľba.');return value;}
  function byId(rows,id){const row=rows.find(item=>item.id===id);if(!row)throw Error(`Neznámy objekt ${id}.`);return row;}
  function patch(field,value){
    const S=editor.state,sc=S.scenario,sat=sc?.satellite;
    if(!sc||!S.world||!S.demand)throw Error('Scenár ešte nie je načítaný.');
    let orbital=false;
    if(field.startsWith('engine.')){
      const key=field.slice(7),defaults={dcc_enabled:false,dcc_low_cbr:.004,dcc_high_cbr:.012,
        dcc_mid_interval_ms:250,dcc_high_interval_ms:500,cam_distance_m:4,cam_speed_mps:.5,
        cam_heading_deg:4,cam_low_frequency_ms:500,cam_tgen_max_ms:1000,cam_periodic_repeat:3,
        cam_phase_cap_us:1000,
        car_antenna_height_m:1.5,rsu_antenna_min_height_m:5,rsu_roof_clearance_m:2,
        backhaul_forward_queue_packets:512,backhaul_reverse_queue_packets:512,
        backhaul_forward_service_us:1,backhaul_reverse_service_us:1,
        satellite_rtn_feeder_freq_hz:17700000000,satellite_ut_rx_temp_dbk:24.6,
        satellite_sat_user_rx_temp_dbk:28.4,satellite_gw_rx_temp_dbk:24.62,
        satellite_sat_queue_max_packets:10000,satellite_control_slot_ms:100,
        satellite_rtn_arq:false,satellite_fwd_acm:true,satellite_rtn_acm:true,
        satellite_default_fwd_modcod:'QPSK_1_TO_2',satellite_isl_speed_mps:299792458,
        satellite_terminal_fov_deg:70,satellite_handover_request_us:1000000,
        satellite_apply_us:2500000,satellite_burst_release_us:3500000};
      const bounds={dcc_low_cbr:[0,1],dcc_high_cbr:[0,1],dcc_mid_interval_ms:[100,1000],
        dcc_high_interval_ms:[100,1000],cam_distance_m:[0,100],cam_speed_mps:[0,20],
        cam_heading_deg:[0,180],cam_low_frequency_ms:[100,1000],cam_tgen_max_ms:[100,1000],
        cam_periodic_repeat:[1,20],cam_phase_cap_us:[0,1000],car_antenna_height_m:[.2,10],
        rsu_antenna_min_height_m:[.2,100],rsu_roof_clearance_m:[0,50],
        backhaul_forward_queue_packets:[1,1000],backhaul_reverse_queue_packets:[1,1000],
        backhaul_forward_service_us:[1,1000000],backhaul_reverse_service_us:[1,1000000],
        satellite_rtn_feeder_freq_hz:[1e9,5e10],satellite_ut_rx_temp_dbk:[0,60],
        satellite_sat_user_rx_temp_dbk:[0,60],satellite_gw_rx_temp_dbk:[0,60],
        satellite_sat_queue_max_packets:[1,100000],satellite_control_slot_ms:[10,1000],
        satellite_isl_speed_mps:[1e8,299792458],satellite_terminal_fov_deg:[1,180],
        satellite_handover_request_us:[1000000,10000000],satellite_apply_us:[2000001,14000000],
        satellite_burst_release_us:[3000000,15000000]};
      if(!Object.hasOwn(defaults,key))throw Error('Neznámy vstup enginu.');
      const next={...defaults,...sc.engine};
      if(sc.engine?.dcc_enabled===undefined)next.dcc_enabled=Boolean(sc.denm_events?.length);
      const integerKeys=new Set(['dcc_mid_interval_ms','dcc_high_interval_ms',
        'cam_low_frequency_ms','cam_tgen_max_ms','cam_periodic_repeat','cam_phase_cap_us',
        'backhaul_forward_queue_packets','backhaul_reverse_queue_packets',
        'backhaul_forward_service_us','backhaul_reverse_service_us',
        'satellite_sat_queue_max_packets','satellite_control_slot_ms',
        'satellite_handover_request_us','satellite_apply_us','satellite_burst_release_us']);
      if(typeof defaults[key]==='boolean')next[key]=choice(value,['yes','no'])==='yes';
      else if(key==='satellite_default_fwd_modcod')next[key]=choice(value,['QPSK_1_TO_2','QPSK_1_TO_4']);
      else next[key]=numeric(value,...bounds[key],integerKeys.has(key));
      if(next.dcc_low_cbr>=next.dcc_high_cbr||next.dcc_mid_interval_ms>next.dcc_high_interval_ms||
         next.cam_low_frequency_ms>next.cam_tgen_max_ms)throw Error('Prahy DCC a CAM musia byť vzostupné.');
      if(next.satellite_apply_us<=next.satellite_handover_request_us+1000000||
         next.satellite_burst_release_us<=next.satellite_apply_us+100000)
        throw Error('Satelitné časy musia nasledovať: prepnutie → aplikácia → uvoľnenie.');
      sc.engine=next;
    }else if(field==='link_policy_override'){
      sc.link_policy_override=choice(value,['profile','custom'])==='custom';
      if(!sc.link_policy_override)editor.refreshOrbits(true).catch(error=>editor.status(error.message));
      orbital=true;
    }else if(field==='seed'||field==='ns3_run'){
      sc[field]=numeric(value,1,2147483647,true);
      if(field==='seed')S.world.simulation.seed=value;
    }else if(field==='duration_s'){
      const minimum=Object.values(sc.node_policy?.rsus||{}).some(row=>row.satellite_backhaul)?6:2;
      S.world.simulation.duration_s=numeric(value,minimum,120,true);sc.sample_count=value*10;
      orbital=true;
    }else if(field.startsWith('vehicle_model.')){
      const key=field.split('.')[1],bounds={accel_mps2:[.1,10],decel_mps2:[.1,15],sigma:[0,1],
        length_m:[1,20],width_m:[.5,3],min_gap_m:[0,10],speed_factor:[.1,2],manual_max_speed_mps:[.1,60]};
      if(!bounds[key])throw Error('Neznámy parameter vozidla.');
      S.world.simulation.vehicle_model ||= {accel_mps2:2,decel_mps2:4.5,sigma:0,length_m:5,
        width_m:1.8,min_gap_m:2.5,speed_factor:1,manual_max_speed_mps:40};
      S.world.simulation.vehicle_model[key]=numeric(value,...bounds[key]);
    }else if(field==='radio.mode'){
      sc.radio.mode=choice(value,['urban_los','friis']);
      if(value==='friis')sc.radio.shadowing=false;
    }else if(field==='radio.tx_power_dbm'||field==='radio.noise_figure_db'){
      const max=field.endsWith('tx_power_dbm')?33:20;
      sc.radio[field.split('.')[1]]=numeric(value,0,max);
    }else if(field==='radio.rate_mbps'){
      sc.radio.rate_mbps=Number(choice(String(value),['3','6','12','24']));
    }else if(field==='radio.channel_number'){
      sc.radio.channel_number=Number(choice(String(value),['172','174','176','178','180','182','184']));
    }else if(field==='radio.tx_gain_dbi'||field==='radio.rx_gain_dbi'){
      sc.radio[field.split('.')[1]]=numeric(value,-20,20);
    }else if(field==='radio.shadowing'){
      if(value==='yes'&&sc.radio.mode==='friis')throw Error('Friis nepodporuje tieňovanie.');
      sc.radio.shadowing=choice(value,['yes','no'])==='yes';
    }else if(field==='source_id'){
      byId(S.demand.vehicles,value);
      const mode=sc.node_policy.cars[value]?.ground;
      if(mode==='off'||sc.satellite_enabled&&mode!=='all')throw Error('Referenčné auto CAM potrebuje zapnuté rádio do RSU.');
      sc.source_id=value;if(S.world.flows?.[0])S.world.flows[0].source=value;
    }else if(field==='rsu_id'||field==='alert_target_rsu'){
      if(value){byId(S.world.rsus,value);if(sc.node_policy.rsus[value]?.satellite_backhaul!==true)
        throw Error('Vyber RSU so zapnutým satelitným terminálom.');}
      if(field==='rsu_id'&&!value||field==='alert_target_rsu'&&value===sc.rsu_id)
        throw Error('Zdrojová a cieľová RSU musia byť rôzne.');
      sc[field]=value;orbital=true;
      if(field==='rsu_id'&&sc.alert_target_rsu===value){
        const active=S.world.rsus.filter(rsu=>sc.node_policy.rsus[rsu.id]?.satellite_backhaul);
        sc.alert_target_rsu=active.find(rsu=>rsu.id!==value)?.id||'';
      }
    }else if(field.startsWith('car:')){
      const [,id,key]=field.split(':'),car=byId(S.demand.vehicles,id);
      const maximum=car.max_speed_mps??(S.world.map_source==='osm_live'?car.depart_speed_mps:S.world.simulation.vehicle_model?.manual_max_speed_mps??40);
      const mode=car.depart_speed_mode??(S.world.map_source==='osm_live'?'max':'fixed');
      if(key==='speed_kmh'){
        const speed=numeric(value,.36,144)/3.6;
        if(mode==='fixed'&&car.depart_speed_mps>speed)throw Error('Maximum musí byť aspoň počiatočná rýchlosť.');
        car.max_speed_mps=speed;
      }else if(key==='initial_speed_kmh'){
        const speed=numeric(value,0,144)/3.6;
        if(speed>maximum)throw Error('Počiatočná rýchlosť presahuje maximum auta.');
        car.depart_speed_mps=speed;car.depart_speed_mode='fixed';
      }else if(key==='depart_speed_mode'){
        const next=choice(value,['max','fixed']);
        if(next==='fixed'&&car.depart_speed_mps>maximum)throw Error('Počiatočná rýchlosť presahuje maximum auta.');
        car.depart_speed_mode=next;
      }
      else if(key==='ground'){
        const mode=choice(value,['all','cars','off']);
        if(id===sc.source_id&&(mode==='off'||sc.satellite_enabled&&mode!=='all'))
          throw Error('Zdroj DENM musí vysielať do požadovanej vrstvy.');
        sc.node_policy.cars[id].ground=mode;
      }else if(key==='radio_reset'){
        if(value!=='yes')throw Error('Neplatná voľba profilu.');
        delete car.radio_model;
      }else if(['tx_power_dbm','noise_figure_db','tx_gain_dbi','rx_gain_dbi','antenna_height_m'].includes(key)){
        const ranges={tx_power_dbm:[0,33],noise_figure_db:[0,20],tx_gain_dbi:[-20,20],
          rx_gain_dbi:[-20,20],antenna_height_m:[.2,10]};
        car.radio_model ||= {};car.radio_model[key]=numeric(value,...ranges[key]);
      }else throw Error('Neznámy parameter auta.');
    }else if(field.startsWith('rsu:')){
      const [,id,key]=field.split(':'),rsu=byId(S.world.rsus,id);
      if(key==='radio_reset'){
        if(value!=='yes')throw Error('Neplatná voľba profilu.');
        delete rsu.radio_model;
      }else if(key==='antenna_auto'){
        if(value==='yes'){
          if(rsu.radio_model)delete rsu.radio_model.antenna_height_m;
          if(rsu.radio_model&&!Object.keys(rsu.radio_model).length)delete rsu.radio_model;
        }else if(value==='no'){
          rsu.radio_model ||= {};
          rsu.radio_model.antenna_height_m=sc.engine?.rsu_antenna_min_height_m??5;
        }else throw Error('Neplatná voľba výšky antény.');
      }else if(['tx_power_dbm','noise_figure_db','tx_gain_dbi','rx_gain_dbi','antenna_height_m'].includes(key)){
        const ranges={tx_power_dbm:[0,33],noise_figure_db:[0,20],tx_gain_dbi:[-20,20],rx_gain_dbi:[-20,20],antenna_height_m:[.2,100]};
        rsu.radio_model ||= {};rsu.radio_model[key]=numeric(value,...ranges[key]);
      }else if(key==='x_m'||key==='y_m'){
        rsu[key]=numeric(value,0,key==='x_m'?(S.world.width_m||S.world.extent_m):(S.world.height_m||S.world.extent_m));
        orbital=true;
      }else if(key==='mode'){
        const mode=choice(value,['both','ground','off']);
        if(mode==='both'&&sc.node_policy.cars[sc.source_id]?.ground!=='all')
          throw Error('Zdrojové auto musí komunikovať aj s RSU.');
        sc.node_policy.rsus[id]={ground:mode!=='off',satellite_backhaul:mode==='both'};
        if(mode!=='both'&&sat.terminal_mounts)delete sat.terminal_mounts[id];
        sc.satellite_enabled=Object.values(sc.node_policy.rsus).some(row=>row.satellite_backhaul);
        const active=S.world.rsus.filter(rsu=>sc.node_policy.rsus[rsu.id]?.satellite_backhaul).map(rsu=>rsu.id);
        if(active.length){
          if(!active.includes(sc.rsu_id))sc.rsu_id=active[0];
          if(!active.includes(sc.alert_target_rsu)||sc.alert_target_rsu===sc.rsu_id)
            sc.alert_target_rsu=active.find(other=>other!==sc.rsu_id)||'';
        }else{sc.rsu_id=S.world.rsus[0]?.id||'';sc.alert_target_rsu='';}
        if(sc.satellite_enabled&&S.world.simulation.duration_s<6){S.world.simulation.duration_s=6;sc.sample_count=60;}
        orbital=true;
      }else if(key==='mount_enabled'){
        if(sat.orbit_group!=='starlink'||!sc.node_policy.rsus[id]?.satellite_backhaul)
          throw Error('Smerová montáž je podporovaná len pre satelitnú RSU so Starlink FHP.');
        sat.terminal_mounts ||= {};
        if(value==='yes')sat.terminal_mounts[id] ||= {tilt_deg:8,azimuth_deg:0,frame:'north'};
        else if(value==='no')delete sat.terminal_mounts[id];
        else throw Error('Neplatná voľba montáže.');
        orbital=true;
      }else if(key==='tilt_deg'||key==='azimuth_deg'){
        if(!sat.terminal_mounts?.[id])throw Error('Najprv zapni smerovú montáž.');
        sat.terminal_mounts[id][key]=numeric(value,0,key==='tilt_deg'?180:359.999);orbital=true;
      }else throw Error('Neznámy parameter RSU.');
    }else if(field.startsWith('road:')){
      const [,id,key]=field.split(':'),road=byId(S.world.roads.segments,id);
      if(['speed_forward_mps','speed_reverse_mps'].includes(key)){
        if(key==='speed_reverse_mps'&&road.oneway)throw Error('Jednosmerná cesta nemá opačnú hranu SUMO.');
        const speed=numeric(value,1,40),direction=key==='speed_forward_mps'?'forward':'reverse';
        road[key]=speed;road[`speed_${direction}_source`]='manual';
        if(direction==='forward')road.speed_limit_mps=speed;
      }else if(['lanes_forward','lanes_reverse'].includes(key)){
        if(key==='lanes_reverse'&&road.oneway)throw Error('Jednosmerná cesta nemá opačnú hranu SUMO.');
        const lanes=numeric(value,1,6,true),direction=key==='lanes_forward'?'forward':'reverse';
        road[key]=lanes;road[`lanes_${direction}_source`]='manual';
        if(direction==='forward')road.lanes_each_direction=Math.min(3,lanes);
      }else throw Error('Neznámy parameter cesty.');
      S.inspectorKey=null;
    }else if(field.startsWith('denm:')){
      const [,indexText,key]=field.split(':'),event=sc.denm_events?.[Number(indexText)];
      if(!event)throw Error('Udalosť DENM neexistuje.');
      if(key==='source_id'){
        byId(S.demand.vehicles,value);
        const mode=sc.node_policy.cars[value]?.ground;
        if(mode==='off'||sc.satellite_enabled&&mode!=='all')throw Error('Auto s DENM potrebuje zapnuté rádio do RSU.');
        event.source_id=value;
      }else if(key==='operation'){
        event.operation=choice(value,['new','update','cancel']);
        if(value==='cancel')event.repetition_ms=0;
      }else{
        const ranges={at_s:[0,S.world.simulation.duration_s-.001,false],sequence:[0,65535,true],
          validity_s:[1,86400,true],radius_m:[1,1780,true],repetition_ms:[0,60000,true]};
        if(!ranges[key])throw Error('Neznámy parameter DENM.');
        if(key==='repetition_ms'&&value!==0&&value<100)throw Error('Opakovanie musí byť 0 alebo aspoň 100 ms.');
        event[key]=numeric(value,...ranges[key]);
      }
    }else if(field==='satellite.mask_deg')sat.mask_deg=numeric(value,0,89.999),orbital=true;
    else if(field.startsWith('satellite.gateway.')){
      const index=Number(field.split('.')[2]),limits=[[-90,90],[-180,180],[-500,9000]];
      if(!Number.isInteger(index)||index<0||index>2)throw Error('Neznáma súradnica brány.');
      sat.gateway[index]=numeric(value,...limits[index]);orbital=true;
    }else if(['beam_gain_dbi','ut_power_dbw','forward_isl_bps','reverse_isl_bps',
              'forward_queue_packets','reverse_queue_packets'].some(key=>field===`satellite.${key}`)){
      const key=field.split('.')[1],ranges={beam_gain_dbi:[-10,60,false],ut_power_dbw:[-50,20,false],
        forward_isl_bps:[100,1e10,true],reverse_isl_bps:[100,1e10,true],
        forward_queue_packets:[1,10000,true],reverse_queue_packets:[1,10000,true]};
      sat[key]=numeric(value,...ranges[key]);orbital=true;
    }else if(field.startsWith('link_policy.')){
      const key=field.split('.')[1],ranges={rf_hz:[1e9,5e10,false],compensation:[0,1,false],
        doppler_tolerance_hz:[0,1e7,false],zenith_cone_deg:[0,90,false],
        steering_rate_deg_s:[0,360,false],beam_half_angle_deg:[0,90,false]};
      if(!ranges[key])throw Error('Neznámy parameter satelitného terminálu.');
      sc.link_policy[key]=numeric(value,...ranges[key]);sc.link_policy_override=true;orbital=true;
    }else if(field.startsWith('building:')){
      const [,id,key]=field.split(':'),building=byId(sat?.environment?.buildings||[],id);
      if(!['height_min_m','height_central_m','height_max_m'].includes(key))throw Error('Neznámy parameter budovy.');
      const next={height_min_m:building.height_min_m,height_central_m:building.height_central_m,
        height_max_m:building.height_max_m,[key]:numeric(value,0,500)};
      if(next.height_min_m>next.height_central_m||next.height_central_m>next.height_max_m)
        throw Error('Musí platiť nízka ≤ stredná ≤ vysoká výška.');
      building[key]=value;building.height_source='manual_user';building.height_reference='edited_in_simulator';building.manual_edited=true;
      S.inspectorKey=null;orbital=true;
    }else if(field==='environment.height_case'){
      if(!sat.environment)throw Error('Scenár nemá pripravené budovy.');
      sat.environment.height_case=choice(value,['low','central','high']);orbital=true;
    }else throw Error('Tento parameter sa na technickej stránke nemení.');
    if(orbital){S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;}
    editor.markDirty();editor.status(`Zmenené: ${field}. Pred ďalším behom scenár ulož.`);
    send();
  }
  channel.onmessage=event=>{
    const message=event.data;if(!message||message.session!==session)return;
    if(message.type==='request')send();
    if(message.type==='export'){
      const S=editor.state;
      if(S.mapMode==='real')window.simulatorRealMapSyncActive?.();
      const scenario=structuredClone(S.scenario),world=structuredClone(S.world),demand=structuredClone(S.demand);
      scenario.scenario_id=document.getElementById('scenarioId')?.value||scenario.scenario_id;
      scenario.sample_count=world.simulation.duration_s*10;
      scenario.satellite_enabled=Object.values(scenario.node_policy?.rsus||{}).some(row=>row.satellite_backhaul);
      world.vehicles=structuredClone(demand.vehicles);
      if(world.flows?.[0])world.flows[0].source=scenario.source_id;
      channel.postMessage({session,type:'export',data:{scenario,world,demand}});
    }
    if(message.type==='patch')try{patch(message.field,message.value);}catch(error){
      channel.postMessage({session,type:'error',message:error.message});send();
    }
  };
  link.addEventListener('click',event=>{
    event.preventDefault();
    view.hidden=false;
    frame.src=link.href;
    document.body.classList.add('technical-open');
    setTimeout(send,200);
  });
  window.simulatorCloseTechnicalPage=()=>{
    view.hidden=true;
    frame.src='about:blank';
    document.body.classList.remove('technical-open');
    editor.render();
  };
  window.simulatorTechnicalSnapshot=snapshot;
  window.simulatorTechnicalRefresh=()=>{if(!view.hidden)send();};
})();
