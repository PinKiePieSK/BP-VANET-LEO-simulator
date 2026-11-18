// Panel budovy upravuje pôdorys a tri výšky v scenári; tento objekt vstupuje do tienenia pozemného
// rádia aj satelitného výhľadu.
'use strict';
// User-drawn rectangular obstructions in the otherwise empty map.
(() => {
  const editor=window.simulatorEditor,S=editor.state,ns='http://www.w3.org/2000/svg';
  const extent=()=>S.world?.width_m||S.world?.extent_m||2000;
  const height=()=>S.world?.height_m||S.world?.extent_m||2000;
  const source=()=>S.scenario?.satellite?.environment;
  const list=()=>source()?.buildings||[];
  const find=id=>list().find(b=>b.id===id);
  // Vyhľadanie bodu v pôdoryse umožňuje vybrať aj budovu importovanú z OSM bez vytvorenia tisícov
  // položiek v hlavnom výbere.
  const at=p=>{
    for(const b of list()){
      const polygon=b.polygon_xy_m;if(!polygon?.length)continue;
      let inside=false;
      for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
        const a=polygon[i],z=polygon[j];
        if((a[1]>p.y)!==(z[1]>p.y)&&p.x<(z[0]-a[0])*(p.y-a[1])/(z[1]-a[1])+a[0])inside=!inside;
      }
      if(inside)return b;
    }
    return null;
  };
  const dimensions=b=>({x:(b.polygon_xy_m[0][0]+b.polygon_xy_m[2][0])/2,
    y:(b.polygon_xy_m[0][1]+b.polygon_xy_m[2][1])/2,
    width:b.polygon_xy_m[1][0]-b.polygon_xy_m[0][0],
    length:b.polygon_xy_m[2][1]-b.polygon_xy_m[1][1],height:b.height_central_m});
  function ensure(){
    if(S.mapMode!=='empty'||!S.scenario?.satellite)throw Error('Budovy možno kresliť v prázdnom svete.');
    if(source()?.sources?.osm?.provider==='manual-editor-v1')return source();
    const cols=75+Math.ceil((extent()-2000)/30),rows=75+Math.ceil((height()-2000)/30);
    S.scenario.satellite.environment={schema_version:1,georeference:structuredClone(S.world.georeference),width_m:extent(),height_m:height(),
      buildings:[],terrain:{origin_xy_m:[-120,-120],step_m:30,width:cols,height:rows,elevation_m:Array(cols*rows).fill(0)},
      height_policy:'user_dimensions',height_case:'central',uncertain_route_policy:'optimistic_with_uncertainty_flag',
      statistical_layers:{vegetation:{recommendation:'ITU-R P.833-10',status:'not_modelled',assumed_loss_db_interval:null},
        weather:{recommendation:'ITU-R P.618-14',status:'not_modelled',assumed_loss_db_interval:null}},
      sources:{osm:{provider:'manual-editor-v1',sha256:null},terrain:{provider:'synthetic-flat-zero-height',tiles:[]},retrieved_utc:new Date().toISOString()}};
    return source();
  }
  // Prevádza veľkosť, orientáciu a výšku ručne vloženej budovy na geometriu. Táto geometria neskôr
  // vstupuje do pozemného tienenia aj kontroly satelitného výhľadu.
  function setRectangle(b,x,y,width,length,roofHeight){
    if(![x,y,width,length,roofHeight].every(Number.isFinite)||width<2||length<2||roofHeight<1||roofHeight>500||
       x-width/2<0||x+width/2>extent()||y-length/2<0||y+length/2>height())
      throw Error('Budova musí mať rozmery aspoň 2 m, výšku 1–500 m a celá ležať vo výreze.');
    b.polygon_xy_m=[[x-width/2,y-length/2],[x+width/2,y-length/2],[x+width/2,y+length/2],[x-width/2,y+length/2]]
      .map(p=>p.map(v=>Math.round(v*100)/100));
    b.height_min_m=b.height_central_m=b.height_max_m=Math.round(roofHeight*100)/100;
  }
  function add(p){
    const env=ensure();let n=0;while(env.buildings.some(b=>b.id===`manual-building-${n}`))n++;
    const b={id:`manual-building-${n}`,polygon_xy_m:[],height_min_m:10,height_central_m:10,height_max_m:10,
      height_source:'manual_user',height_reference:'user-drawn rectangle',building_class:'unspecified'};
    setRectangle(b,Math.max(10,Math.min(extent()-10,p.x)),Math.max(10,Math.min(height()-10,p.y)),20,20,10);
    env.buildings.push(b);S.selected={type:'building',id:b.id};S.inspectorKey=null;
    editor.rebuildObjectPicker();editor.markDirty();editor.status(`Budova ${b.id} má pôdorys 20 × 20 m a výšku 10 m. Rozmery zmeníš vpravo.`);
  }
  function render(){
    const group=document.getElementById('mapBuildings');if(!group)return;group.replaceChildren();
    for(const b of S.mapMode==='empty'?list():S.selected?.type==='building'?[find(S.selected.id)].filter(Boolean):[]){
      if(S.mapMode==='real'){
        const polygon=document.createElementNS(ns,'polygon');polygon.setAttribute('points',b.polygon_xy_m.map(([x,y])=>`${x},${height()-y}`).join(' '));
        for(const [key,value] of Object.entries({fill:'#a7807077',stroke:'#ffe08a','stroke-width':3,
          'vector-effect':'non-scaling-stroke','data-type':'building','data-id':b.id}))polygon.setAttribute(key,String(value));
        group.append(polygon);continue;
      }
      const d=dimensions(b),r=document.createElementNS(ns,'rect');
      for(const [key,value] of Object.entries({x:d.x-d.width/2,y:height()-d.y-d.length/2,width:d.width,height:d.length,
        fill:'#a78070',stroke:S.selected?.id===b.id?'#ffe08a':'#f5c2a3','stroke-width':2,
        'vector-effect':'non-scaling-stroke','data-type':'building','data-id':b.id}))r.setAttribute(key,String(value));
      group.append(r);
    }
  }
  // Ovládacie prvky menia konkrétnu budovu scenára. Zmena výšky alebo pôdorysu sa prejaví až v
  // nasledujúcom behu; starý replay patrí k starému vstupu.
  function renderInspector(box,b){
    const manual=source()?.sources?.osm?.provider==='manual-editor-v1';
    const tabs=document.createElement('div');tabs.className='car-inspector-tabs';
    const geometry=document.createElement('section'),heights=document.createElement('section');
    geometry.className=heights.className='car-inspector-page';
    const buttons=['Pôdorys','Výška a model'].map(label=>{const button=document.createElement('button');button.type='button';button.textContent=label;tabs.append(button);return button;});
    const show=index=>{geometry.hidden=index!==0;heights.hidden=index!==1;buttons.forEach((button,i)=>{button.classList.toggle('active',i===index);button.setAttribute('aria-pressed',String(i===index));});};
    buttons.forEach((button,i)=>button.onclick=()=>show(i));box.append(tabs,geometry,heights);show(0);
    const field=(parent,label,current,min,max,onchange)=>{const row=document.createElement('label'),input=document.createElement('input');
      row.textContent=label;input.type='number';input.step='any';input.min=String(min);input.max=String(max);input.value=String(current);
      input.onchange=()=>{const value=Number(input.value);if(!input.value.trim()||!Number.isFinite(value)||value<min||value>max){input.value=String(current);return editor.status(`${label}: rozsah ${min} až ${max}.`);}
        try{onchange(value);S.inspectorKey=null;editor.markDirty();window.simulatorEarthRefreshLayers?.();}catch(error){input.value=String(current);editor.status(error.message);}};
      row.append(input);parent.append(row);};
    const info=(parent,label,value)=>{const p=document.createElement('p');p.className='car-fixed-input';const strong=document.createElement('strong');strong.textContent=`${label}: `;p.append(strong,document.createTextNode(String(value)));parent.append(p);};
    info(geometry,'ID',b.id);
    if(manual){
      const d=dimensions(b);for(const [key,label,min,max] of [['x','Stred X · m',0,extent()],['y','Stred Y · m',0,height()],['width','Šírka · m',2,extent()],['length','Dĺžka · m',2,height()]])
        field(geometry,label,d[key],min,max,value=>{const next={...dimensions(b),[key]:value},low=b.height_min_m,high=b.height_max_m;
          setRectangle(b,next.x,next.y,next.width,next.length,next.height);b.height_min_m=low;b.height_max_m=high;});
    }else{
      info(geometry,'Pôvod',b.height_source||'OSM');
      const points=document.createElement('div');points.className='building-points';geometry.append(points);
      b.polygon_xy_m.forEach((point,index)=>{
        const heading=document.createElement('h4');heading.textContent=`Bod ${index+1}`;points.append(heading);
        for(const axis of [0,1])field(points,axis===0?'X · m':'Y · m',point[axis],-500,(axis===0?extent():height())+500,value=>{
          const copy=b.polygon_xy_m.map(row=>[...row]);copy[index][axis]=Math.round(value*100)/100;
          if(index===0&&copy.length>3&&copy.at(-1)[0]===point[0]&&copy.at(-1)[1]===point[1])copy[copy.length-1]=[...copy[0]];
          b.polygon_xy_m=copy;b.manual_edited=true;
        });
      });
    }
    const heightCase=document.createElement('label'),heightSelect=document.createElement('select');
    heightCase.textContent='Účinný variant výšky';
    for(const [value,label] of [['low','Nízka'],['central','Stredná'],['high','Vysoká']])heightSelect.append(new Option(label,value));
    heightSelect.value=source()?.height_case||'central';
    heightSelect.onchange=()=>{source().height_case=heightSelect.value;S.inspectorKey=null;editor.markDirty();};
    heightCase.append(heightSelect);heights.append(heightCase);
    for(const [key,label] of [['height_min_m','Nízka výška · m'],['height_central_m','Stredná výška · m'],['height_max_m','Vysoká výška · m']])
      field(heights,label,b[key]??b.height_min_m,0,500,value=>{const low=key==='height_min_m'?value:b.height_min_m,
        center=key==='height_central_m'?value:b.height_central_m,high=key==='height_max_m'?value:b.height_max_m;
        if(low>center||center>high)throw Error('Musí platiť nízka ≤ stredná ≤ vysoká výška.');b[key]=value;
        b.height_source='manual_user';b.height_reference='edited_in_simulator';b.manual_edited=true;});
    info(heights,'Trieda budovy',b.building_class||'neuvedená');
    const remove=document.createElement('button');remove.type='button';remove.className='subtle';remove.textContent='Odstrániť budovu';
    remove.onclick=()=>{const env=source();env.buildings=env.buildings.filter(row=>row.id!==b.id);
      if(!manual){env.manual_removed_buildings ||= [];if(!env.manual_removed_buildings.includes(b.id))env.manual_removed_buildings.push(b.id);}
      if(manual&&!env.buildings.length)delete S.scenario.satellite.environment;
      else env.building_count=env.buildings.length;
      S.selected=null;S.inspectorKey=null;editor.rebuildObjectPicker();editor.markDirty();};box.append(remove);
  }
  window.simulatorBuildings={list,find,at,add,render,renderInspector};
})();
