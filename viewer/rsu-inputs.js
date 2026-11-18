'use strict';
(() => {
  const editor=window.simulatorEditor,S=editor.state;
  let active='ground';
  const width=()=>S.world.width_m||S.world.extent_m;
  const height=()=>S.world.height_m||S.world.extent_m;
  function render(root,rsu){
    const id=rsu.id,policy=S.scenario.node_policy.rsus[id],sat=S.scenario.satellite;
    const tabs=document.createElement('div');tabs.className='car-inspector-tabs';
    const ground=document.createElement('section'),other=document.createElement('section');
    ground.className=other.className='car-inspector-page';
    const buttons=['Uzol a ns-3','SNS-3 a správy'].map(title=>{const button=document.createElement('button');button.type='button';button.textContent=title;tabs.append(button);return button;});
    const show=tab=>{active=tab;ground.hidden=tab!=='ground';other.hidden=tab!=='other';buttons.forEach((button,index)=>{const selected=(index===0?'ground':'other')===tab;button.classList.toggle('active',selected);button.setAttribute('aria-pressed',String(selected));});};
    buttons[0].onclick=()=>show('ground');buttons[1].onclick=()=>show('other');root.append(tabs,ground,other);show(active);
    const fixed=(box,label,value)=>{const row=document.createElement('p');row.className='car-fixed-input';const title=document.createElement('strong');title.textContent=`${label}: `;row.append(title,document.createTextNode(String(value)));box.append(row);};
    const number=(box,label,value,min,max,change)=>{const row=document.createElement('label'),input=document.createElement('input');row.textContent=label;input.type='number';input.step='any';input.min=String(min);input.max=String(max);input.value=String(value);input.onchange=()=>{
      const next=Number(input.value);if(!input.value.trim()||!Number.isFinite(next)||next<min||next>max){input.value=String(value);return editor.status(`${label}: rozsah ${min} až ${max}.`);}
      change(next);S.inspectorKey=null;editor.markDirty();
    };row.append(input);box.append(row);};
    const select=(box,label,value,options,change)=>{const row=document.createElement('label'),input=document.createElement('select');row.textContent=label;for(const [key,title] of options)input.append(new Option(title,key));input.value=value;input.onchange=()=>{change(input.value);S.inspectorKey=null;editor.markDirty();};row.append(input);box.append(row);};
    fixed(ground,'ID',id);
    number(ground,'X · m',rsu.x_m,0,width(),value=>{rsu.x_m=value;S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;});
    number(ground,'Y · m',rsu.y_m,0,height(),value=>{rsu.y_m=value;S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;});
    select(ground,'Pozemné ITS-G5',policy.ground?'yes':'no',[['yes','Zapnuté'],['no','Vypnuté']],value=>{
      if(value==='no'&&policy.satellite_backhaul){policy.satellite_backhaul=false;delete sat?.terminal_mounts?.[id];}
      policy.ground=value==='yes';editor.syncSatelliteEndpoints();editor.renderDurationControls();S.orbitDirty=true;
    });
    fixed(ground,'Anténa · min. výška',`${S.scenario.engine?.rsu_antenna_min_height_m??5} m`);
    fixed(ground,'Nad strechou',`${S.scenario.engine?.rsu_roof_clearance_m??2} m`);
    const radio=rsu.radio_model||{},shared=S.scenario.radio;
    const heading=document.createElement('h4');heading.textContent='Rádio tohto RSU';ground.append(heading);
    for(const [key,label,min,max] of [
      ['tx_power_dbm','Výkon · dBm',0,33],['noise_figure_db','Šumové číslo · dB',0,20],
      ['tx_gain_dbi','Zisk TX · dBi',-20,20],['rx_gain_dbi','Zisk RX · dBi',-20,20]])
      number(ground,label,radio[key]??shared[key]??0,min,max,value=>{rsu.radio_model||={};rsu.radio_model[key]=value;});
    select(ground,'Výška antény',radio.antenna_height_m===undefined?'auto':'own',
      [['auto','Podľa strechy / minima'],['own','Vlastná hodnota']],value=>{
        if(value==='auto'){if(rsu.radio_model)delete rsu.radio_model.antenna_height_m;}
        else {rsu.radio_model||={};rsu.radio_model.antenna_height_m=S.scenario.engine?.rsu_antenna_min_height_m??5;}
        if(rsu.radio_model&&!Object.keys(rsu.radio_model).length)delete rsu.radio_model;
      });
    if(radio.antenna_height_m!==undefined)number(ground,'Výška antény · m',radio.antenna_height_m,.2,100,value=>{rsu.radio_model.antenna_height_m=value;});
    if(rsu.radio_model){const reset=document.createElement('button');reset.type='button';reset.className='subtle';reset.textContent='Predvolené rádio';
      reset.onclick=()=>{delete rsu.radio_model;S.inspectorKey=null;editor.markDirty();};ground.append(reset);}
    fixed(ground,'Technológie',rsu.technologies.join(', '));
    select(other,'Satelitný backhaul',policy.satellite_backhaul?'yes':'no',[['yes','Zapnutý'],['no','Vypnutý']],value=>{
      if(value==='yes'&&!policy.ground){editor.status('Satelitná RSU potrebuje zapnuté ITS-G5.');S.inspectorKey=null;editor.render();return;}
      policy.satellite_backhaul=value==='yes';if(value==='no')delete sat?.terminal_mounts?.[id];
      if(value==='yes'&&S.world.simulation.duration_s<6){S.world.simulation.duration_s=6;S.scenario.sample_count=60;}
      editor.syncSatelliteEndpoints();editor.renderDurationControls();S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;
      if(value==='yes')editor.refreshOrbits(true).catch(error=>editor.status(error.message));
    });
    if(policy.satellite_backhaul){
      select(other,'Zdrojová RSU',S.scenario.rsu_id===id?'yes':'no',[['no','Nie'],['yes','Áno']],value=>{if(value==='yes'){S.scenario.rsu_id=id;editor.syncSatelliteEndpoints();}});
      select(other,'Cieľová RSU',S.scenario.alert_target_rsu===id?'yes':'no',[['no','Nie'],['yes','Áno']],value=>{if(value==='yes'&&id!==S.scenario.rsu_id)S.scenario.alert_target_rsu=id;else if(value==='yes')editor.status('Zdrojová a cieľová RSU musia byť rôzne.');});
      if(sat?.orbit_group==='starlink'){
        const mount=sat.terminal_mounts?.[id];
        select(other,'Vlastná montáž',mount?'yes':'no',[['no','Predvolená zvislá'],['yes','Vlastný náklon']],value=>{
          sat.terminal_mounts ||= {};if(value==='yes')sat.terminal_mounts[id] ||= {tilt_deg:8,azimuth_deg:0,frame:'north'};
          else delete sat.terminal_mounts[id];S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;
        });
        if(mount){number(other,'Náklon · °',mount.tilt_deg,0,180,value=>{mount.tilt_deg=value;S.orbitDirty=true;});
          number(other,'Azimut · °',mount.azimuth_deg,0,359.999,value=>{mount.azimuth_deg=value;S.orbitDirty=true;});}
      }
    }
    const remove=document.createElement('button');remove.type='button';remove.className='subtle';remove.textContent='Odstrániť RSU';root.append(remove);
    remove.onclick=()=>{S.world.rsus=S.world.rsus.filter(item=>item.id!==id);delete S.scenario.node_policy.rsus[id];delete sat?.terminal_mounts?.[id];
      editor.syncSatelliteEndpoints();S.selected=null;S.inspectorKey=null;S.orbitDirty=true;S.orbitPreview=null;S.orbitRequest++;
      editor.rebuildObjectPicker();editor.renderDurationControls();editor.markDirty();};
  }
  window.simulatorRsuInputs={render};
})();
