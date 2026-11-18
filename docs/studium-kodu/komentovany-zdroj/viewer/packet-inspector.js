// Zobrazuje vybraný paket ako surové bajty a dekódované polia CAM/DENM či IP/UDP. Je to čítačka
// výstupu verifiera, nie nová simulácia komunikácie.
'use strict';
// Byte ranges are shown only where the framing is identifiable. CAM body fields
// share a bit-packed UPER byte range; semantic values come from pinned Vanetza.
(() => {
  const hex=bytes=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join(' ');
  const uint=(b,a,z)=>Array.from(b.slice(a,z)).reduce((v,n)=>v*256+n,0);
  const field=(name,start,end,value='')=>({name,start,end,value});
  // Prekladá potvrdené CAM bajty do čitateľných polí. ASN.1 UPER telo je bitovo balené, preto sa
  // pre viacero polí ukazuje spoločný interval bajtov; hodnoty musia pochádzať z dekódera Vanetza.
  function cam(b,offset=0,decoded=null){
    if(b.length-offset<8||b[offset]!==2||b[offset+1]!==2)return null;
    const fields=[
      field('Verzia ITS PDU',offset,offset+1,b[offset]),field('Typ správy · CAM',offset+1,offset+2,b[offset+1]),
      field('Station ID',offset+2,offset+6,uint(b,offset+2,offset+6)),
      field('generationDeltaTime · ms modulo 65 536',offset+6,offset+8,uint(b,offset+6,offset+8)),
    ];
    if(decoded){
      const exceptional={latitude_deg:['latitude_code',900000001],longitude_deg:['longitude_code',1800000001],
        altitude_m:['altitude_code',800001],heading_deg:['heading_code',3601],speed_mps:['speed_code',16383],
        vehicle_length_m:['vehicle_length_code',1023],vehicle_width_m:['vehicle_width_code',62],
        longitudinal_acceleration_mps2:['longitudinal_acceleration_code',161],yaw_rate_degps:['yaw_rate_code',32767]};
      const val=(key,unit='')=>{
        if(decoded[key]===undefined)return 'nedostupné';
        const rule=exceptional[key];if(rule&&decoded[rule[0]]===rule[1])return 'nedostupné';
        return `${decoded[key]}${unit}`;
      };
      const body=(name,value)=>fields.push(field(name+' · UPER bitové pole',offset+8,b.length,value));
      body('Typ stanice',`${val('station_type')} (${decoded.station_type===5?'osobné auto':'kód ETSI CDD'})`);
      body('Zemepisná šírka',val('latitude_deg',' ° WGS84'));
      body('Zemepisná dĺžka',val('longitude_deg',' ° WGS84'));
      body('Nadmorská výška',val('altitude_m',' m'));
      // Číselný kód 4095 znamená nedostupnú presnosť polohy, nie elipsu 40,95 m. Dekódovaný
      // predchádzajúci bod zobrazuje skutočnú relatívnu polohu a čas z CAM.
      body('Elipsa neistoty polohy',decoded.position_confidence_major_code===4095||decoded.position_confidence_minor_code===4095?'nedostupná':`${val('position_confidence_major_m',' m')} × ${val('position_confidence_minor_m',' m')}`);
      body('Presnosť výšky',decoded.altitude_confidence_code===15?'nedostupná':`ETSI kód ${val('altitude_confidence_code')}`);
      if(decoded.high_frequency_type===1){
        body('Smer vozidla',val('heading_deg',' ° od severu'));
        body('Presnosť smeru',decoded.heading_confidence_code===127?'nedostupná':`${val('heading_confidence_code')} × 0,1 °`);
        body('Rýchlosť',decoded.speed_code===16383?'nedostupná':decoded.speed_code===16382?'mimo rozsahu':`${val('speed_mps',' m/s')} (${(decoded.speed_mps*3.6).toFixed(2)} km/h)`);
        body('Presnosť rýchlosti',decoded.speed_confidence_code===127?'nedostupná':`${val('speed_confidence_code')} × 0,01 m/s`);
        body('Smer jazdy',decoded.drive_direction===0?'dopredu':`ETSI kód ${decoded.drive_direction}`);
        body('Dĺžka / šírka vozidla',`${val('vehicle_length_m',' m')} / ${val('vehicle_width_m',' m')}`);
        body('Pozdĺžne zrýchlenie',val('longitudinal_acceleration_mps2',' m/s²'));
        body('Presnosť zrýchlenia',decoded.longitudinal_acceleration_confidence_code===102?'nedostupná':`ETSI kód ${val('longitudinal_acceleration_confidence_code')}`);
        body('Zakrivenie dráhy',`${decoded.curvature_code===1023?'nedostupné':decoded.curvature_code===undefined?'nedostupné':`${decoded.curvature_code/10000} 1/m${decoded.curvature_code===0?' (priamo)':''}`} · presnosť ${decoded.curvature_confidence_code===7?'nedostupná':val('curvature_confidence_code')}`);
        body('Uhlová rýchlosť otáčania',val('yaw_rate_degps',' °/s'));
        body('Presnosť uhlovej rýchlosti',decoded.yaw_rate_confidence_code===8?'nedostupná':`ETSI kód ${val('yaw_rate_confidence_code')}`);
      }
      body('Nízkofrekvenčný kontajner',decoded.low_frequency_present?'prítomný':'neprítomný');
      if(decoded.low_frequency_present){
        body('Úloha vozidla',decoded.vehicle_role_code===0?'bežné vozidlo':`ETSI kód ${val('vehicle_role_code')}`);
        body('Vonkajšie svetlá · bitová maska',val('exterior_lights_hex'));
        body('Body histórie trasy',val('path_history_count'));
        if(decoded.path_history_count)body('Predošlý bod trasy',`${decoded.path_delta_latitude_e7/1e7}°, ${decoded.path_delta_longitude_e7/1e7}°, ${decoded.path_delta_altitude_cm/100} m · ${decoded.path_delta_time_10ms/100} s dozadu`);
      }
    }else fields.push(field('Bitovo balené telo CAM UPER',offset+8,b.length,'Dekóder nepotvrdil hodnoty'));
    return {name:'ETSI CAM · ASN.1 UPER'+(decoded?' · dekódované Vanetza':''),start:offset,end:b.length,fields};
  }
  // Rovnako spracúva DENM. Význam Action ID, času, platnosti a polohy číta z dekódovaného obsahu;
  // ak bajty alebo dekódovanie chýbajú, nesmie vymyslieť chýbajúce polia.
  function denm(b,offset=0,decoded=null){
    if(b.length-offset<6||b[offset]!==2||b[offset+1]!==1)return null;
    const fields=[field('Verzia ITS PDU',offset,offset+1,b[offset]),
      field('Typ správy · DENM',offset+1,offset+2,b[offset+1]),
      field('Station ID vysielajúceho uzla',offset+2,offset+6,uint(b,offset+2,offset+6))];
    const body=(name,value)=>fields.push(field(name+' · UPER bitové pole',offset+6,b.length,value));
    if(decoded){
      body('Action ID',`${decoded.originating_station_id} / ${decoded.sequence_number}`);
      body('Čas zistenia udalosti',`${decoded.detection_time_ms} ms od 1. 1. 2004`);
      body('Čas verzie správy',`${decoded.reference_time_ms} ms od 1. 1. 2004`);
      body('Platnosť',`${decoded.validity_s} s`);
      body('Opakovanie',decoded.transmission_interval_ms?`${decoded.transmission_interval_ms} ms`:'vypnuté');
      body('Operácia',decoded.termination===0?'zrušenie':decoded.termination===1?'negácia':'nová / aktualizácia');
      body('Udalosť',decoded.traffic_subcause===5?'dopravná zápcha':`ETSI podpríčina ${decoded.traffic_subcause}`);
      body('Poloha udalosti',`${decoded.latitude_deg}°, ${decoded.longitude_deg}° · ${decoded.altitude_m} m`);
      // Detail DENM zobrazuje prenesený kód 4095 ako nedostupnú presnosť a kód kvality 0 ako
      // nedostupnú kvalitu. Nevyvodzuje metre presnosti z presných syntetických súradníc.
      body('Presnosť polohy udalosti',decoded.position_confidence_major_code===4095&&decoded.position_confidence_minor_code===4095?'nedostupná':`ETSI kód ${decoded.position_confidence_major_code} / ${decoded.position_confidence_minor_code}`);
      body('Kvalita informácie',decoded.information_quality_code===0?'nedostupná':`ETSI kód ${decoded.information_quality_code}`);
      body('Detekčné zóny / trasy',`${decoded.detection_paths} trajektórií`);
    }else body('Telo DENM','Dekóder nepotvrdil hodnoty');
    return {name:'ETSI DENM · ASN.1 UPER'+(decoded?' · dekódované Vanetza':''),start:offset,end:b.length,fields};
  }
  // Rozpoznáva rámcovanie GeoNetworking/BTP, priamy CAM/DENM alebo IPv4/UDP a vracia hierarchiu
  // vrstiev. Ak rámec nepozná, ukáže raw bajty bez zavádzajúceho popisu.
  function groups(b,decoded=null,decodedDenm=null){
    const found=[];
    const denmPort=b.findIndex((value,i)=>value===0x07&&b[i+1]===0xd2&&b[i+2]===0&&b[i+3]===0&&b[i+4]===2&&b[i+5]===1);
    if(denmPort>=12){
      found.push({name:'GeoNetworking · Basic Header',start:0,end:4,fields:[field('GN verzia / ďalšia hlavička',0,1,`${b[0]>>4} / ${b[0]&15}`),field('Hop limit',3,4,b[3])]});
      found.push({name:'GeoNetworking · Common + GeoBroadcast',start:4,end:denmPort,fields:[field('Typ / podtyp hlavičky',5,6,`${b[5]>>4} / ${b[5]&15}`),field('Dĺžka payloadu',8,10,`${uint(b,8,10)} B`),field('Geografická oblasť a vektor vysielajúceho',12,denmPort,'GN GBC') ]});
      found.push({name:'BTP-B',start:denmPort,end:denmPort+4,fields:[field('Cieľový port · DENM',denmPort,denmPort+2,2002),field('Informácia portu',denmPort+2,denmPort+4,uint(b,denmPort+2,denmPort+4))]});
      found.push(denm(b,denmPort+4,decodedDenm));return found;
    }
    if(b.length>=44&&b[0]===0x11&&uint(b,40,42)===2001){
      found.push({name:'GeoNetworking · Basic Header',start:0,end:4,fields:[field('GN verzia / ďalšia hlavička',0,1,`${b[0]>>4} / ${b[0]&15}`),field('Rezervované',1,2,b[1]),field('Lifetime · kód ETSI',2,3,b[2]),field('Hop limit',3,4,b[3])]});
      found.push({name:'GeoNetworking · Common Header',start:4,end:12,fields:[field('Ďalší protokol',4,5,`kód ${b[4]>>4}`),field('Typ / podtyp hlavičky',5,6,`${b[5]>>4} / ${b[5]&15}`),field('Traffic Class',6,7,`0x${b[6].toString(16).padStart(2,'0')}`),field('Príznaky',7,8,`0x${b[7].toString(16).padStart(2,'0')}`),field('Dĺžka payloadu',8,10,`${uint(b,8,10)} B`),field('Max hop limit',10,11,b[10]),field('Rezervované',11,12,b[11])]});
      const signed=(a,z)=>{const n=uint(b,a,z),bits=(z-a)*8;return n>=2**(bits-1)?n-2**bits:n;};
      found.push({name:'GeoNetworking · Single Hop Header',start:12,end:40,fields:[field('Adresa · flags',12,14,`0x${hex(b.slice(12,14))}`),field('Adresa · MID',14,20,hex(b.slice(14,20))),field('GN timestamp · ms modulo 2³²',20,24,uint(b,20,24)),field('Zemepisná šírka',24,28,`${(signed(24,28)/1e7).toFixed(7)} °`),field('Zemepisná dĺžka',28,32,`${(signed(28,32)/1e7).toFixed(7)} °`),field('Rýchlosť / PAI',32,34,`${(uint(b,32,34)&0x7fff)/100} m/s · PAI ${(b[32]>>7)?'nastavené':'nenastavené'}`),field('Smer',34,36,`${(uint(b,34,36)/10).toFixed(1)} °`),field('DCC / rezerva',36,40,hex(b.slice(36,40)))]});
      found.push({name:'BTP-B',start:40,end:44,fields:[field('Cieľový port · CAM',40,42,uint(b,40,42)),field('Informácia portu',42,44,uint(b,42,44))]});
      found.push(cam(b,44,decoded)||{name:'Prenášaný obsah',start:44,end:b.length,fields:[field('Surové bajty',44,b.length)]});return found;
    }
    const directCam=cam(b,0,decoded);if(directCam)return [directCam];
    const directDenm=denm(b,0,decodedDenm);if(directDenm)return [directDenm];
    if(b.length>=20&&(b[0]>>4)===4){
      const ihl=(b[0]&15)*4;if(ihl>=20&&ihl<=b.length){
        const ip={name:'IPv4',start:0,end:ihl,fields:[field('Verzia / IHL',0,1),field('DSCP / ECN',1,2),field('Celková dĺžka',2,4,uint(b,2,4)),field('Identifikácia',4,6),field('Príznaky / fragment offset',6,8),field('TTL',8,9,b[8]),field('Protokol',9,10,b[9]),field('Checksum hlavičky',10,12),field('Zdrojová IP',12,16,Array.from(b.slice(12,16)).join('.')),field('Cieľová IP',16,20,Array.from(b.slice(16,20)).join('.'))]};
        if(ihl>20)ip.fields.push(field('IPv4 options',20,ihl));const out=[ip];
        if(b[9]===17&&b.length>=ihl+8){out.push({name:'UDP',start:ihl,end:ihl+8,fields:[field('Zdrojový port',ihl,ihl+2,uint(b,ihl,ihl+2)),field('Cieľový port',ihl+2,ihl+4,uint(b,ihl+2,ihl+4)),field('Dĺžka',ihl+4,ihl+6,uint(b,ihl+4,ihl+6)),field('Checksum',ihl+6,ihl+8)]});out.push(denm(b,ihl+8,decodedDenm)||cam(b,ihl+8,decoded)||{name:'UDP payload',start:ihl+8,end:b.length,fields:[field('Surový obsah',ihl+8,b.length)]});}
        else out.push({name:'IP payload',start:ihl,end:b.length,fields:[field('Surový obsah',ihl,b.length)]});return out;
      }
    }
    return [{name:'Surový obsah · neznáme rámcovanie',start:0,end:b.length,fields:[field('Bajty bez potvrdenej štruktúry',0,b.length)]}];
  }
  // Rozloží bajty na 16-bajtové riadky s offsetom a ASCII. Výber poľa zvýrazní zodpovedajúci
  // interval v hexdumpe, aby sa dalo prejsť od významu poľa k bajtom.
  function hexdump(b){
    const wrap=document.createElement('div');wrap.className='packet-hex';const spans=[];
    for(let offset=0;offset<b.length;offset+=16){
      const line=document.createElement('div'),address=document.createElement('b');address.textContent=offset.toString(16).padStart(4,'0')+'  ';line.append(address);
      const ascii=document.createElement('span');ascii.className='packet-ascii';let a='';
      for(let i=offset;i<Math.min(offset+16,b.length);i++){const item=document.createElement('span');item.textContent=b[i].toString(16).padStart(2,'0')+' ';item.dataset.byte=String(i);line.append(item);spans[i]=item;a+=b[i]>=32&&b[i]<127?String.fromCharCode(b[i]):'.';}
      ascii.textContent='  '+a;line.append(ascii);wrap.append(line);
    }
    return {wrap,highlight(start,end){spans.forEach((s,i)=>s.classList.toggle('selected-byte',i>=start&&i<end));}};
  }
  // Zostaví časovú os raw krokov jedného paketu. Každý krok má čas, uzol, etapu, prípadný dôvod a
  // dekódované bajty; skrátený zoznam krokov sa explicitne označí.
  function render(container,p,id){
    container.replaceChildren();const intro=document.createElement('p');intro.textContent=`ID ${id} · ${p.stages.length} zaznamenaných krokov. Rozklikni krok a bajtové pole.`;container.append(intro);
    if(p.truncated_stages){const warning=document.createElement('p');warning.textContent='Zoznam krokov bol skrátený; surové bajty zobrazených krokov sú úplné.';container.append(warning);}
    p.stages.forEach((stage,index)=>{
      const detail=document.createElement('details');detail.className='packet-stage';if(index===0)detail.open=true;
      const summary=document.createElement('summary');summary.textContent=`${(stage.time_us/1e6).toFixed(6)} s · ${stage.stage} · ${stage.node} · ${stage.bytes} B${stage.native_level?' IP':' '}${stage.reason?' · '+stage.reason:''}`;detail.append(summary);
      detail.addEventListener('toggle',()=>{if(!detail.open||detail.dataset.ready)return;detail.dataset.ready='1';
        // Vrstva SNS-3 poskytuje smer, uzol, MAC a UID. Úplné IP/UDP bajty sú zachytené iba pri
        // vstupe do SatNetDevice; pri PHY kroku ich rozhranie nevydáva za surový DVB rámec.
        // Používateľ preto vidí pôvod dát a hranicu dostupného rozkladu.
        if(stage.native_level){const note=document.createElement('p');note.textContent=`SNS-3 ${stage.native_event} · ${stage.native_level} · ${stage.native_direction} · packet UID ${stage.packet_uid} · MAC ${stage.mac}${stage.source?' · zdroj '+stage.source:''}${stage.destination?' · cieľ '+stage.destination:''}. ${stage.raw_hex?'Nižšie je IP/UDP datagram zachytený na vstupe do SNS-3.':'Táto vrstva zapisuje metadáta, nie úplné bajty DVB rámca.'}`;detail.append(note);}
        const raw=stage.raw_hex||'';if(!raw||raw.length%2||!/^[0-9a-f]*$/i.test(raw)){if(!stage.native_level){const note=document.createElement('p');note.textContent='Pre tento krok nie sú k dispozícii surové bajty.';detail.append(note);}return;}
        const bytes=Uint8Array.from(raw.match(/../g)||[],value=>parseInt(value,16)),dump=hexdump(bytes);
        if(bytes.length!==stage.bytes){const note=document.createElement('p');note.textContent=`Raw stopa obsahuje ${bytes.length} z ${stage.bytes} B; chýbajúce bajty nie sú dekódované.`;detail.append(note);}
        for(const layer of groups(bytes,stage.decoded_cam,stage.decoded_denm)){
          const section=document.createElement('details');section.className='packet-layer';const title=document.createElement('summary');title.textContent=`${layer.name} · bajty ${layer.start}–${Math.max(layer.start,layer.end-1)}`;section.append(title);
          const table=document.createElement('div');table.className='packet-fields';for(const f of layer.fields){if(f.end<=f.start)continue;const button=document.createElement('button');button.type='button';button.textContent=`${f.start}–${f.end-1} · ${f.name}${f.value!==''?' · '+f.value:''}`;button.title=hex(bytes.slice(f.start,f.end));button.onclick=()=>dump.highlight(f.start,f.end);table.append(button);}section.append(table);detail.append(section);
        }
        detail.append(dump.wrap);
      });container.append(detail);
    });
  }
  window.simulatorPacketInspector={render,groups};
})();
