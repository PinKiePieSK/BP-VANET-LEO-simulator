#!/usr/bin/env python3
"""Validate, run and verify current ground or integrated ns-3 scenarios."""
from __future__ import annotations
import argparse,copy,json,math,os,re,tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from simulator_platform import ROOT, sha
from simulator_clock import EXPERIMENT_START_S as START_S, SCHEMA_VERSION, TIME_POLICY
from simulator_sumo import validate as validate_world
from simulator_ground_runner import run as run_ground,validate_config as ground_validate
from simulator_ground_verifier import verify as verify_ground
from simulator_link_policy_defaults import LINK_POLICY
from simulator_inputs import project_input,ground_config
from simulator_engine_controls import effective as engine_controls
from simulator_orbit_source import config_for, validate_pin
from simulator_time_visibility import calculate as visibility_timeline
from simulator_satellite_runner import run as run_native_editor
from simulator_satellite_verifier import verify as verify_native_editor
from simulator_antenna_envelope import validate_mounts
from simulator_local_environment import validate_environment
from simulator_ground_obstructions import export_bytes as ground_obstruction_bytes, write as write_ground_obstructions

RUNS=ROOT/'results/simulations'
GROUP_REFERENCE={'iridium-NEXT':'config/orbit-iridium-reference.json',
                 'globalstar':'config/orbit-globalstar-reference.json',
                 'starlink':'config/orbit-starlink-reference.json'}
ID=re.compile(r'^[a-z][a-z0-9-]{2,47}$')
NAMES={'schema_version','scenario_id','world_template','demand','source_id','rsu_id','seed','ns3_run',
       'utc_origin','sample_count','radio','mode','satellite'}
def full_duration(s):
    return s.get('schema_version')==SCHEMA_VERSION and s.get('time_policy')==TIME_POLICY


def runtime_inputs(s,out):
    """Use the same t=0 for SUMO mobility and ns-3/SNS-3 packets."""
    world=load(ROOT/s['world_template'])
    demand=load(ROOT/s['demand'])
    runtime=copy.deepcopy(s)
    if full_duration(s):
        duration=world['simulation']['duration_s']
        world['simulation']['duration_s']=round(START_S+duration+.3,1)
        demand=copy.deepcopy(demand)
        for vehicle in demand['vehicles']:
            vehicle['depart_s']=round(vehicle['depart_s']+START_S,1)
        world['vehicles']=copy.deepcopy(demand['vehicles'])
        runtime['demand']=str((out/'inputs/demand.json').relative_to(ROOT))
    world['simulation'].update(seed=s['seed'],utc_origin=s['utc_origin'],step_s=.1)
    return world,demand,runtime

@contextmanager
def experiment_clock(s):
    key='SIM_LOGICAL_END_US'
    previous=os.environ.get(key)
    if full_duration(s):os.environ[key]=str((START_S*10+s['sample_count'])*100000)
    try:yield
    finally:
        if previous is None:os.environ.pop(key,None)
        else:os.environ[key]=previous
SOURCES=('tools/simulator_cli.py','tools/simulator_sumo.py','tools/simulator_mobility_export.py',
         'tools/simulator_ground_runner.py','tools/simulator_ground_verifier.py','src/vanet-ground-network.cc',
         'tools/simulator_inputs.py','tools/simulator_engine_controls.py',
         'tools/simulator_rsu_radio.py','tools/simulator_car_radio.py','src/rsu-radio-config.h',
         'tools/simulator_clock.py','tools/simulator_platform.py',
         'tools/simulator_coordinates.py','tools/simulator_packet_trace.py')

def need(x,why):
    if not x:raise ValueError(why)
def native_satellite(s):
    """True only for the supported integrated WAVE/SNS-3 execution."""
    return (s['satellite_enabled'] and isinstance(s['satellite'],dict) and
            s['satellite'].get('dynamic_physical') is True)

def unified_policy(s,cars,rsus):
    policy=s['node_policy']
    need(type(policy) is dict and set(policy)=={'cars','rsus'} and
         type(policy['cars']) is dict and type(policy['rsus']) is dict and
         set(policy['cars'])==set(cars) and set(policy['rsus'])==set(rsus),
         'Nastavenia komunikácie musia obsahovať každé auto a RSU')
    for node,row in policy['cars'].items():
        need(type(row) is dict and set(row)=={'ground'} and
             row['ground'] in ('all','cars','off'),
             f'{node}: neplatné nastavenie komunikácie')
    for node,row in policy['rsus'].items():
        need(type(row) is dict and set(row)=={'ground','satellite_backhaul'} and
             type(row['ground']) is bool and type(row['satellite_backhaul']) is bool and
             (row['ground'] or not row['satellite_backhaul']),
             f'{node}: neplatné nastavenie RSU')
    enabled=any(row['satellite_backhaul'] for row in policy['rsus'].values())
    need(s['satellite_enabled'] is enabled,'Satelitná vetva musí vyplývať z nastavení zariadení')
def load(p):return json.loads(Path(p).read_text())
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def template(s,world,obstructions=None):
    config=ground_config(s,world)
    if 'denm_events' in s:
        config['denm_events']=s['denm_events']
        config['utc_origin']=s['utc_origin']
    if obstructions is not None:
        config['cases'][0]['radio_mode']='urban_osm_building'
        config['cases'][0]['obstructions']=str(obstructions.relative_to(ROOT))
    # Each sample is 100 ms apart. Spread transmissions within its first 90 ms
    # so large fleets cannot send an old waypoint after the next position update.
    fleet=len(load(ROOT/s['demand'])['vehicles'])+len(load(world)['rsus'])
    config['phase_us']=min(config['phase_us'],max(1,90000//(fleet+1)))
    if 'node_policy' in s: config['node_policy']=s['node_policy']
    return config

def orbit_group(s):
    sat=s.get('satellite')
    return sat.get('orbit_group','iridium-NEXT') if sat else None

def preflight(s):
    """Reject unsupported schemas before generating mobility or packets."""
    required=NAMES|{'alert_target_rsu','link_policy','satellite_enabled','time_policy','node_policy','denm_events'}
    need(type(s) is dict and required<=set(s) and set(s)<=required|{'engine','link_policy_override'} and s.get('schema_version')==SCHEMA_VERSION and
         s.get('mode')=='unified' and s.get('time_policy')==TIME_POLICY and
         type(s.get('scenario_id')) is str and ID.fullmatch(s['scenario_id']),
         'Simulátor vyžaduje jednotný scenár verzie 7')
    engine_controls(s)
    need(type(s.get('link_policy_override', False)) is bool, 'Neplatný režim satelitného terminálu')
    events=s['denm_events']
    need(type(events) is list and len(events)<=64,'DENM udalosti môžu tvoriť najviac 64 položiek')
    need(all(type(event) is dict and
             {'at_s','sequence','operation','validity_s','radius_m','repetition_ms'}<=set(event) and
             type(event['at_s']) in (int,float) and math.isfinite(event['at_s']) and
             type(event['sequence']) is int and
             type(event.get('source_id',s['source_id'])) is str for event in events),
         'DENM udalosť potrebuje zdrojové auto a platný čas')
    seen=set();active=set();first_at={};first_validity={};previous={}
    for event in sorted(events,key=lambda row:(row['at_s'],row.get('source_id',s['source_id']))):
        source=event.get('source_id',s['source_id'])
        action=(source,event['sequence'])
        need(type(event) is dict and set(event) in ({'at_s','sequence','operation','validity_s','radius_m','repetition_ms'},
                                                    {'source_id','at_s','sequence','operation','validity_s','radius_m','repetition_ms'}) and
             type(source) is str and bool(source) and
             type(event['at_s']) in (int,float) and math.isfinite(event['at_s']) and
             type(event['sequence']) is int and 0<=event['sequence']<=65535 and
             event['operation'] in ('new','update','cancel') and
             type(event['validity_s']) is int and 1<=event['validity_s']<=86400 and
             type(event['radius_m']) is int and 1<=event['radius_m']<=1780 and
             type(event['repetition_ms']) is int and
             (event['repetition_ms']==0 or 100<=event['repetition_ms']<=60000) and
             event['at_s']>previous.get(action,-1) and
             (event['operation']=='new' and action not in seen or
              event['operation'] in ('update','cancel') and action in active and
              event['at_s']<first_at[action]+first_validity[action]),
             'DENM udalosť, čas alebo životný cyklus je neplatný')
        if event['operation']=='new':
            seen.add(action);active.add(action)
            first_at[action]=event['at_s'];first_validity[action]=event['validity_s']
        if event['operation']=='cancel':active.remove(action)
        previous[action]=event['at_s']

    world_path=project_input(s['world_template'])
    demand_path=project_input(s['demand'])
    world=load(world_path);demand=load(demand_path)
    need(type(demand) is dict and set(demand)=={'schema_version','kind','provenance','vehicles'} and
         demand['schema_version']==1 and demand['kind'] in ('synthetic_trips','measured_trips') and
         type(demand['provenance']) is str and bool(demand['provenance'].strip()),
         'Neplatné vstupné trasy')
    if demand['kind']=='measured_trips':
        need(demand['provenance'].startswith('https://'),'Merané trasy vyžadujú zdrojový odkaz')
    need(type(s['seed']) is int and 1<=s['seed']<2**31 and
         type(s['ns3_run']) is int and 1<=s['ns3_run']<2**31 and
         type(s['sample_count']) is int and 20<=s['sample_count']<=1200,
         'Neplatný seed, číslo behu alebo počet vzoriek')
    need(type(s['utc_origin']) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',s['utc_origin']),
         'Neplatný čas UTC')
    datetime.strptime(s['utc_origin'],'%Y-%m-%dT%H:%M:%SZ')
    radio=s['radio']
    need(type(radio) is dict and {'mode','tx_power_dbm','noise_figure_db'}<=set(radio) and
         set(radio)<={'mode','tx_power_dbm','noise_figure_db','rate_mbps','channel_number','tx_gain_dbi','rx_gain_dbi','shadowing'} and
         radio['mode'] in ('urban_los','friis') and
         all(type(radio[key]) in (float,int) and math.isfinite(radio[key]) for key in ('tx_power_dbm','noise_figure_db')) and
         0<=radio['tx_power_dbm']<=33 and 0<=radio['noise_figure_db']<=20 and
         type(radio.get('rate_mbps',6)) is int and radio.get('rate_mbps',6) in (3,6,12,24) and
         type(radio.get('channel_number',180)) is int and radio.get('channel_number',180) in (172,174,176,178,180,182,184) and
         all(type(radio.get(key,0)) in (int,float) and math.isfinite(radio.get(key,0)) and
             -20<=radio.get(key,0)<=20 for key in ('tx_gain_dbi','rx_gain_dbi')) and
         type(radio.get('shadowing',False)) is bool and
         (radio['mode']!='friis' or not radio.get('shadowing',False)),
         'Neplatné parametre pozemného rádia')
    world['vehicles']=demand['vehicles']
    world['simulation'].update(seed=s['seed'],utc_origin=s['utc_origin'],step_s=.1)
    validate_world(world)
    duration=world['simulation']['duration_s']
    need(type(duration) is int and 2<=duration<=120 and s['sample_count']==duration*10,
         'Pohyb a komunikácia musia trvať rovnako, 2–120 s')
    need(all(0<=event['at_s']<duration for event in events),'DENM je mimo dĺžky simulácie')
    need(all(vehicle['depart_s']==0 for vehicle in demand['vehicles']),
         'Všetky autá musia byť pripravené v čase 0 s')
    cars=[item['id'] for item in world['vehicles']]
    rsus=[item['id'] for item in world['rsus']]
    need(len(cars)>=2 and len(rsus)<=512 and s['source_id'] in cars and
         ((not rsus and s['rsu_id']=='') or (rsus and s['rsu_id'] in rsus)) and
         all('its_g5' in item['technologies'] for item in world['vehicles']+world['rsus']),
         'Scenár potrebuje aspoň dve autá, platnú zdrojovú stanicu a najviac 512 RSU')
    unified_policy(s,cars,rsus)
    need(all(event.get('source_id',s['source_id']) in cars and
             s['node_policy']['cars'][event.get('source_id',s['source_id'])]['ground']!='off'
             for event in events),'Zdroj každého DENM musí byť auto so zapnutým rádiom')
    need(s['node_policy']['cars'][s['source_id']]['ground']!='off',
         'Zdroj DENM musí mať zapnuté pozemné rádio')
    ground_validate(template(s,world_path))

    policy=s['link_policy']
    need(type(s['alert_target_rsu']) is str and
         type(policy) is dict and set(policy)==set(LINK_POLICY) and
         all(type(value) in (int,float) and math.isfinite(value) for value in policy.values()) and
         1e9<=policy['rf_hz']<=5e10 and 0<=policy['compensation']<=1 and
         0<=policy['doppler_tolerance_hz']<=1e7 and 0<=policy['zenith_cone_deg']<=90 and
         0<=policy['steering_rate_deg_s']<=360 and 0<=policy['beam_half_angle_deg']<=90,
         'Neplatné parametre satelitného terminálu')
    satellite=s['satellite']
    if isinstance(satellite,dict) and 'environment' in satellite:
        environment=satellite['environment']
        validate_environment(environment,world['georeference'])
        need((environment.get('width_m',environment.get('extent_m',2000)),
              environment.get('height_m',environment.get('extent_m',2000)))==
             (world.get('width_m',world.get('extent_m',2000)),
              world.get('height_m',world.get('extent_m',2000))),
             'Rozsah budov a mapy sa musí zhodovať')
    if s['satellite_enabled']:
        need(duration>=6,'Satelitný beh potrebuje aspoň 6 s')
        rsu_policy=s['node_policy']['rsus']
        need(rsus and rsu_policy[s['rsu_id']]['ground'] and rsu_policy[s['rsu_id']]['satellite_backhaul'],
             'Zdrojová RSU potrebuje pozemné rádio a satelitný terminál')
        need(s['node_policy']['cars'][s['source_id']]['ground']=='all',
             'Zdrojové auto musí vedieť vysielať do RSU')
        need(all(s['node_policy']['cars'][event.get('source_id',s['source_id'])]['ground']=='all'
                 for event in events),'Auto s DENM cez satelit musí vedieť vysielať do RSU')
        need(not s['alert_target_rsu'] or
             s['alert_target_rsu'] in rsus and s['alert_target_rsu']!=s['rsu_id'] and
             rsu_policy[s['alert_target_rsu']]['ground'] and
             rsu_policy[s['alert_target_rsu']]['satellite_backhaul'],
             'Cieľová RSU musí byť iná aktívna RSU so satelitným terminálom')
        fields={'catalog_ids','isls','initial_serving_sat','handover_target_sat','feeder_sat',
                'gateway','mask_deg','beam_gain_dbi','ut_power_dbw','forward_isl_bps',
                'reverse_isl_bps','forward_queue_packets','reverse_queue_packets',
                'orbit_group','orbit_snapshot','dynamic_physical','antenna_model',
                'terminal_mounts','environment','link_budget'}
        need(type(satellite) is dict and set(satellite)<=fields and
             {'orbit_group','orbit_snapshot','dynamic_physical','gateway','mask_deg'}<=set(satellite) and
             satellite['dynamic_physical'] is True and satellite['orbit_snapshot'] is not None and
             orbit_group(s) in GROUP_REFERENCE,
             'Satelitný beh potrebuje orbitálny archív, bránu a fyzikálny model')
        if 'antenna_model' in satellite:
            need(satellite['antenna_model']=='public-v1','Neznámy anténny profil')
        if 'terminal_mounts' in satellite:
            need(satellite.get('antenna_model')=='public-v1','Montáž vyžaduje anténny profil')
            owners={name:'rsu' for name,row in rsu_policy.items() if row['satellite_backhaul']}
            validate_mounts(orbit_group(s),satellite['terminal_mounts'],owners)
        if 'link_budget' in satellite:
            from simulator_link_budget import validate_assumptions
            validate_assumptions(satellite['link_budget'])
        validate_pin(satellite['orbit_snapshot'],orbit_group(s))
        need(type(satellite['mask_deg']) in (int,float) and math.isfinite(satellite['mask_deg']) and
             0<=satellite['mask_deg']<90 and type(satellite['gateway']) is list and
             len(satellite['gateway'])==3 and
             all(type(value) in (int,float) and math.isfinite(value) for value in satellite['gateway']) and
             -90<=satellite['gateway'][0]<=90 and -180<=satellite['gateway'][1]<=180,
             'Neplatná poloha brány alebo výšková maska')
        config_for(orbit_group(s),satellite,s['utc_origin'],10+duration)
    else:
        need(all(not row['satellite_backhaul'] for row in s['node_policy']['rsus'].values()),
             'Satelitná vetva musí zodpovedať nastaveniu RSU')
    plan={'scenario_id':s['scenario_id'],'cars':len(cars),'rsus':len(rsus),
          'radio_nodes':len(cars)+len(rsus),'car_ids':cars,'rsu_ids':rsus,
          'mode':'unified','satellites':0,'geometry':None,
          'execution':'single_ns3_sns3_packet_process' if s['satellite_enabled'] else 'native_ground_packets_per_device',
          'limitations':['generic DVB; no operator modem' if s['satellite_enabled'] else 'ground ITS-G5 model',
                         'no unbounded runtime or memory guarantee'],
          'node_policy':s['node_policy']}
    if s['satellite_enabled']:
        plan.update(orbit_group=orbit_group(s),orbit_snapshot=satellite['orbit_snapshot'],
                    satellites=validate_pin(satellite['orbit_snapshot'],orbit_group(s))['groups'][orbit_group(s)]['objects'],
                    orbit_catalogue_scope='archived pool selects the native SNS-3 topology',
                    service_packet_backend='native_sns3_generic_dvb',
                    antenna_model=satellite.get('antenna_model'),
                    terminal_mounts=satellite.get('terminal_mounts',{}))
    return plan

def run(path,out):
    """Create one immutable output directory and audit it before accepting it."""
    out=out.resolve()
    need(out.parent==RUNS and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',out.name),
         'Výstup musí byť v results/simulations')
    need(not out.exists(),'Výstup už existuje')
    s=load(path);plan=preflight(s);inp=out/'inputs'
    out.mkdir(parents=True);write(inp/'scenario.json',s)
    # SUMO positions and CAM/DENM bytes are prepared before ns-3 starts.
    w,d,runtime=runtime_inputs(s,out)
    obstruction_file=inp/'ground-obstructions.csv'
    ground_environment=(s['satellite'] or {}).get('environment')
    if ground_environment and ground_environment['buildings']:
        write_ground_obstructions(ground_environment,obstruction_file)
    write(inp/'world.json',w)
    write(inp/'demand.json',d)
    write(inp/'ground.json',template(runtime,inp/'world.json',
                                     obstruction_file if obstruction_file.is_file() else None))
    if native_satellite(s):
        # Ground WAVE and satellite DVB execute in one native ns-3 process.
        # Accept the result only after the independent raw trace verifier passes.
        orbit=config_for(orbit_group(s),s['satellite'],s['utc_origin'])
        write(inp/'orbit-reference.json',orbit)
        with experiment_clock(s):
            run_native_editor(s,out,load(inp/'ground.json'),orbit)
        verified=verify_native_editor(out)
        waypoint=out/'native/baseline/waypoints.csv'
        timeline=visibility_timeline(s,waypoint)
        write(out/'physical-timeline.json',timeline)
        plan['active_satellites']=verified['satellites']
        result={'native_packet_backend':verified}
        files=['inputs/scenario.json','inputs/world.json','inputs/ground.json',
               'inputs/demand.json','inputs/orbit-reference.json',
               'native/editor-manifest.json','physical-timeline.json']
        if obstruction_file.is_file():files.append('inputs/ground-obstructions.csv')
        names=('tools/simulator_cli.py','tools/simulator_satellite_runner.py','tools/simulator_satellite_verifier.py',
               'tools/simulator_message_verifier.py','tools/simulator_cam_decode.py','tools/simulator_denm_decode.py',
               'src/vanet-leo-network.cc',
               'tools/simulator_satellite_inputs.py','tools/simulator_orbits.py',
               'tools/simulator_build.py','tools/simulator_clock.py','tools/simulator_platform.py',
               'tools/simulator_coordinates.py','tools/simulator_packet_trace.py',
               'tools/simulator_ground_runner.py',
               'tools/simulator_sumo.py','tools/simulator_mobility_export.py',
               'tools/simulator_time_visibility.py','tools/simulator_orbit_source.py',
               'tools/simulator_engine_controls.py','tools/simulator_rsu_radio.py','tools/simulator_car_radio.py',
               'src/rsu-radio-config.h')
        if (ROOT/'src/satellite-link-condition.h').is_file():
            names+=('src/satellite-link-condition.h',)
        m={'schema_version':7,'scenario':s,'plan':plan,
           'sources':{name:sha(ROOT/name) for name in names},
           'files':{name:sha(out/name) for name in files},'result':result}
        write(out/'run-manifest.json',m)
        return {'status':'PASS','plan':plan,'result':result}
    ground=out/'ground'
    # Ground-only runs use the WAVE packet engine without an SNS-3 instance.
    with experiment_clock(s):run_ground(inp/'ground.json',ground)
    g=verify_ground(ground)
    result=g
    files=['inputs/scenario.json','inputs/world.json','inputs/ground.json',
           'inputs/demand.json','ground/run-manifest.json']
    if obstruction_file.is_file():files.append('inputs/ground-obstructions.csv')
    names=SOURCES
    m={'schema_version':6,'scenario':s,'plan':plan,'sources':{x:sha(ROOT/x) for x in names},'files':{x:sha(out/x) for x in files},'result':result}
    # Every branch already returns a verified result. A separate `verify` command
    # still performs the complete independent audit of this new manifest.
    write(out/'run-manifest.json',m);return {'status':'PASS','plan':plan,'result':result}

def verify(out):
    out=out.resolve();need(out.parent==RUNS,'Beh leží mimo výsledkov simulátora');m=load(out/'run-manifest.json');s=load(out/'inputs/scenario.json')
    if m['schema_version']==7:
        need(native_satellite(s) and not (out/'service-model').exists(),
             'Natívny manifest nesmie používať servisný fallback')
        plan=preflight(s)
        verified=verify_native_editor(out)
        plan['active_satellites']=verified['satellites']
        result={'native_packet_backend':verified}
        names=('tools/simulator_cli.py','tools/simulator_satellite_runner.py','tools/simulator_satellite_verifier.py',
               'tools/simulator_message_verifier.py','tools/simulator_cam_decode.py','tools/simulator_denm_decode.py',
               'src/vanet-leo-network.cc',
               'tools/simulator_satellite_inputs.py','tools/simulator_orbits.py',
               'tools/simulator_build.py','tools/simulator_clock.py','tools/simulator_platform.py',
               'tools/simulator_coordinates.py','tools/simulator_packet_trace.py',
               'tools/simulator_ground_runner.py',
               'tools/simulator_sumo.py','tools/simulator_mobility_export.py',
               'tools/simulator_time_visibility.py','tools/simulator_orbit_source.py',
               'tools/simulator_engine_controls.py','tools/simulator_rsu_radio.py','tools/simulator_car_radio.py',
               'src/rsu-radio-config.h')
        if m['sources'].get('src/satellite-link-condition.h'):
            names+=('src/satellite-link-condition.h',)
        files=['inputs/scenario.json','inputs/world.json','inputs/ground.json',
               'inputs/demand.json','inputs/orbit-reference.json',
               'native/editor-manifest.json','physical-timeline.json']
        if (out/'inputs/ground-obstructions.csv').is_file():
            files.append('inputs/ground-obstructions.csv')
            need((out/'inputs/ground-obstructions.csv').read_bytes()==
                 ground_obstruction_bytes(s['satellite']['environment']),
                 'Natívne tienenie sa líši od scenára')
        sources={name:sha(ROOT/name) for name in names}
        need(m['scenario']==s and m['plan']==plan and m['result']==result and
             m['sources']==sources and
             set(m['files'])==set(files) and
             all(sha(out/name)==m['files'][name] for name in files),
             'Natívne vstupy, zdroje alebo výsledok sa zmenili')
        w,d,runtime=runtime_inputs(s,out)
        obstruction=out/'inputs/ground-obstructions.csv'
        expected_ground=template(runtime,out/'inputs/world.json',
                                 obstruction if obstruction.is_file() else None)
        need(load(out/'inputs/world.json')==w and load(out/'inputs/demand.json')==d and
             load(out/'inputs/ground.json')==expected_ground and
             load(out/'inputs/orbit-reference.json')==config_for(orbit_group(s),s['satellite'],s['utc_origin']),
             'Natívne vstupy sa líšia od konfigurácie editora')
        need(load(out/'physical-timeline.json')==visibility_timeline(s,out/'native/baseline/waypoints.csv'),
             'Natívny fyzikálny časový náhľad sa zmenil')
        return {'status':'PASS','plan':plan,'result':result}
    if m['schema_version']==6 and not native_satellite(s):
        plan=preflight(s)
        need(s['schema_version']==SCHEMA_VERSION and not s['satellite_enabled'],
             'Neplatný aktuálny pozemný manifest')
        names=SOURCES
        files=['inputs/scenario.json','inputs/world.json','inputs/ground.json',
               'inputs/demand.json','ground/run-manifest.json']
        obstruction=out/'inputs/ground-obstructions.csv'
        if obstruction.is_file():files.append('inputs/ground-obstructions.csv')
        sources={name:sha(ROOT/name) for name in names}
        need(m['scenario']==s and m['plan']==plan and m['sources']==sources and
             set(m['files'])==set(files) and all(sha(out/name)==m['files'][name] for name in files),
             'Pozemný scenár, zdroje alebo manifest sa zmenili')
        world,demand,runtime=runtime_inputs(s,out)
        need(load(out/'inputs/world.json')==world and
             load(out/'inputs/demand.json')==demand and
            load(out/'inputs/ground.json')==template(runtime,out/'inputs/world.json',
                                                    obstruction if obstruction.is_file() else None),
             'Pozemné vstupy sa líšia od scenára')
        result=verify_ground(out/'ground')
        need(json.loads(json.dumps(result))==m['result'],'Pozemný výsledok sa zmenil')
        return {'status':'PASS','plan':plan,'result':result}
    raise ValueError('Výsledok nepatrí k aktuálnemu paketovému behu simulátora')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('preflight','run'):
        x=sub.add_parser(name);x.add_argument('scenario',type=Path)
        if name=='run':x.add_argument('output',type=Path)
    x=sub.add_parser('verify');x.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(preflight(load(a.scenario)) if a.command=='preflight' else run(a.scenario,a.output) if a.command=='run' else verify(a.output),sort_keys=True))
