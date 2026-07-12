#!/usr/bin/env python3
"""HermesOS Genesis bootstrap approval-safe engine.

Modes are separated so discovery, planning, preflight, mutation and rollback
are independently inspectable.  LIVE_TARGET_INSPECTION is strictly read-only.
APPLY refuses a live target and requires a passing atomic preflight first.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
from typing import Any

MODES=("INSPECT","LIVE_TARGET_INSPECTION","PLAN","PLAN_LIVE","VALIDATE_PACKAGE","PREFLIGHT","PREPARE","APPLY","VALIDATE","ROLLBACK","STATUS")
BINDINGS=("GENESIS_PACKAGE_ROOT","HKP_CANONICAL_ROOT","HKP_EVIDENCE_ROOT","HKP_POLICY_ROOT","HERMES_HOME","HERMES_PROFILE_ROOT","HERMES_RUNTIME_ROOT","PROJECT_WORKSPACE_ROOT")
SECRET_REFERENCE_KEYS=("OPENROUTER_API_KEY","TELEGRAM_BOT_TOKEN_ASSISTANT")
SENSITIVE_KEYS=re.compile(r"(?i)(secret|token|password|api[_-]?key|credential)")

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def jload(p:Path, fallback=None): return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else fallback
def digest(p:Path):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""): h.update(c)
 return h.hexdigest()
def cmd(args,cwd=None):
 try:
  p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  return {"command":args,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
 except FileNotFoundError as exc:
  return {"command":args,"returncode":127,"stdout":"","stderr":str(exc)}
def patch_paths(patch:Path):
 """Return exact diff paths; accepts both a/foo and foo header styles."""
 out=[]
 for line in patch.read_text(encoding="utf-8").splitlines():
  if not line.startswith("diff --git "): continue
  parts=line.split()
  if len(parts)!=4: raise ValueError(f"malformed diff header: {line}")
  path=parts[2]
  out.append(path[2:] if path.startswith("a/") else path)
 return out
def redact(value:Any, key=""):
 if SENSITIVE_KEYS.search(key): return "<REDACTED_REFERENCE>"
 if isinstance(value,dict): return {k:redact(v,k) for k,v in value.items()}
 if isinstance(value,list): return [redact(v,key) for v in value]
 return value

class Engine:
 def __init__(self,a):
   self.a=a; self.cfg=jload(Path(a.config)); self.ws=Path(self.cfg["PROJECT_WORKSPACE_ROOT"]); self.ev=Path(self.cfg["HKP_EVIDENCE_ROOT"])
   self.package_root=Path(__file__).resolve().parents[1]
   self.ws.mkdir(parents=True,exist_ok=True); self.ev.mkdir(parents=True,exist_ok=True)
   self.state_path=self.ws/"state"/"bootstrap_state_v2.json"; self.state_path.parent.mkdir(parents=True,exist_ok=True); self.state=jload(self.state_path,{"schema":"bootstrap-state-v2","history":[]})
 def save(self): self.state_path.write_text(json.dumps(self.state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 def emit(self,phase,result,details):
  record={"schema":"hermesos.genesis.evidence.v0.2","timestamp_utc":utc(),"phase":phase,"result":result,"inputs":redact(self.cfg),"details":redact(details)}
  # Per-run evidence is mutable operational output. It is kept outside the
  # immutable approval manifest; approved static evidence remains at evidence/.
  run_dir=self.ev/'runtime'; run_dir.mkdir(parents=True,exist_ok=True)
  p=run_dir/f"{phase.lower()}.json"; p.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
  self.state["history"].append({"phase":phase,"result":result,"evidence":str(p),"at":record["timestamp_utc"]}); self.save(); return p
 def manifest(self): return jload(self.package_root/"manifests"/"installation_manifest.json")
 def bindings_missing(self): return [k for k in BINDINGS if not self.cfg.get(k)]
 def secret_reference_failures(self):
  refs=self.cfg.get("secret_references",{}); bad=[]
  for key in SECRET_REFERENCE_KEYS:
   v=refs.get(key)
   if not isinstance(v,str) or not re.fullmatch(r"(?:env|vault):[A-Za-z_][A-Za-z0-9_/-]*",v): bad.append(key)
  return bad
 def target_info(self):
  r=Path(self.cfg["HERMES_RUNTIME_ROOT"]); is_git=cmd(["git","rev-parse","--is-inside-work-tree"],r)
  info={"runtime_path":str(r),"exists":r.is_dir(),"git":is_git["returncode"]==0 and is_git["stdout"].strip()=="true","hermes_home":self.cfg.get('HERMES_HOME'),"profile_root":self.cfg.get('HERMES_PROFILE_ROOT')}
  if info['git']:
   info['head']=cmd(["git","rev-parse","HEAD"],r); info['status']=cmd(["git","status","--porcelain=v1"],r)
  pp=r/"pyproject.toml"
  info['package_version']=re.search(r'^version\s*=\s*"([^"]+)"',pp.read_text(encoding='utf-8'),re.M).group(1) if pp.is_file() and re.search(r'^version\s*=\s*"([^"]+)"',pp.read_text(encoding='utf-8'),re.M) else None
  return info
 def inspect(self):
  d=self.target_info(); d["bindings_missing"]=self.bindings_missing(); d["secret_reference_failures"]=self.secret_reference_failures()
  return 0 if self.emit("INSPECT","PASS" if not d['bindings_missing'] else "BLOCKED",d) else 0
 def live_target_inspection(self):
  d=self.target_info(); m=self.manifest(); classification='TARGET_IDENTIFIED'; reasons=[]
  if not d['exists'] or not d['git']: classification='BLOCKED'; reasons.append('runtime target is absent or not a git worktree')
  else:
   if d.get('status',{}).get('stdout','').strip(): classification='DIRTY'; reasons.append('target git status is not empty')
   head=d.get('head',{}).get('stdout','').strip()
   if head!=m['upstream']['pinned_commit'] or d.get('package_version')!='0.18.0': classification='BASELINE_MISMATCH'; reasons.append('commit or package version differs from supported baseline')
   if not reasons: classification='COMPATIBLE'
  d.update({'classification':classification,'reasons':reasons,'expected_modified_files':m['patch']['affected_upstream_paths'],'expected_boot_probe':m['runtime_support']['boot_probe']['destination'],'runtime_source_mode':m['runtime_source_mode'],'compatibility':{'expected_commit':m['upstream']['pinned_commit'],'expected_version':'0.18.0'},'collisions':self._collisions(m)})
  self.emit('LIVE_TARGET_INSPECTION',classification,d); return 0 if classification in {'COMPATIBLE','TARGET_IDENTIFIED'} else 2
 def validate_package(self):
  b=Path(self.cfg['GENESIS_PACKAGE_ROOT']); failures=[]; n=0
  for line in (b/'09_BUNDLE_METADATA'/'SHASUMS.sha256').read_text().splitlines():
   h,rel=line.split(' *./',1); n+=1; p=b/rel
   if not p.is_file() or digest(p)!=h: failures.append(rel)
  self.emit('VALIDATE_PACKAGE','PASS' if not failures else 'BLOCKED',{'records':n,'failures':failures}); return 0 if not failures else 2
 def _collisions(self,m):
  r=Path(self.cfg['HERMES_RUNTIME_ROOT']); h=Path(self.cfg['HERMES_HOME']); collisions=[]
  for name in m['custom_runtime_files']['agent']:
   if (r/'agent'/name).exists(): collisions.append(str(r/'agent'/name))
  for name in m['custom_runtime_files']['gateway']:
   if (r/'gateway'/name).exists(): collisions.append(str(r/'gateway'/name))
  if (r/'hkp'/'hkp').exists(): collisions.append(str(r/'hkp'/'hkp'))
  if (h/'scripts'/'hkp_boot_probe.py').exists(): collisions.append(str(h/'scripts'/'hkp_boot_probe.py'))
  if (h/'profiles'/'hermesos').exists(): collisions.append(str(h/'profiles'/'hermesos'))
  return collisions
 def payload_inventory(self):
  inv=jload(self.package_root/'manifests'/'custom_payload_inventory.json'); b=Path(self.cfg['GENESIS_PACKAGE_ROOT']); actual=sorted(str(p.relative_to(b/'03_NEW_RUNTIME_FILES')).replace('\\','/') for p in (b/'03_NEW_RUNTIME_FILES').rglob('*.py'))
  expected=sorted(inv['files']); missing=sorted(set(expected)-set(actual)); unexpected=sorted(set(actual)-set(expected)); checksum_fail=[]
  sums={line.split(' *./',1)[1]:line.split(' *./',1)[0] for line in (b/'09_BUNDLE_METADATA'/'SHASUMS.sha256').read_text().splitlines()}
  for rel in expected:
   key='03_NEW_RUNTIME_FILES/'+rel; p=b/key
   if not p.is_file() or sums.get(key)!=digest(p): checksum_fail.append(rel)
  return {'expected':expected,'actual':actual,'missing':missing,'unexpected':unexpected,'checksum_failures':checksum_fail,'source_mode':'integrated'}
 def authority_check(self):
  root=Path(self.cfg['HKP_CANONICAL_ROOT']); manifest=root/'HKP_INTEGRITY_MANIFEST_v6.0.json'; policy=root/'Specification Layer'/'HKP_ACTION_POLICY_STATE_v1.0.json'
  failures=[]; data=None
  try: data=json.loads(manifest.read_text(encoding='utf-8'))
  except Exception: failures.append('authority_manifest_unreadable')
  if data and (data.get('manifest_id')!='HKP-INT-006' or data.get('schema_version')!='1.0'): failures.append('authority_manifest_incompatible')
  if not policy.is_file(): failures.append('policy_path_missing')
  return {'root':str(root),'manifest':str(manifest),'policy':str(policy),'failures':failures}
 def preflight(self):
  m=self.manifest(); r=Path(self.cfg['HERMES_RUNTIME_ROOT']); b=Path(self.cfg['GENESIS_PACKAGE_ROOT']); patch=b/'04_MODIFIED_UPSTREAM_PATCHES'/'001_all_upstream_modifications.patch'
  paths=patch_paths(patch); expected=m['patch']['affected_upstream_paths']; failures=[]
  info=self.target_info(); head=info.get('head',{}).get('stdout','').strip()
  if head!=m['upstream']['pinned_commit']: failures.append('baseline_commit')
  if info.get('package_version')!='0.18.0': failures.append('package_version')
  if not info.get('git'): failures.append('not_git_target')
  if info.get('status',{}).get('stdout','').strip(): failures.append('dirty_target')
  if paths!=expected: failures.append('patch_path_mismatch')
  if cmd(['git','apply','-p0','--check',str(patch)],r)['returncode']!=0: failures.append('patch_not_applicable')
  for rel in paths:
   if not (r/rel).is_file(): failures.append(f'missing_patch_target:{rel}')
  for p in (b/'03_NEW_RUNTIME_FILES').rglob('*.py'):
   if not p.is_file(): failures.append(f'missing_custom_source:{p}')
  if self._collisions(m): failures.append('destination_collision')
  if self.bindings_missing(): failures.append('missing_bindings')
  if self.secret_reference_failures(): failures.append('invalid_secret_references')
  package_failures=[]
  for line in (b/'09_BUNDLE_METADATA'/'SHASUMS.sha256').read_text().splitlines():
   h,rel=line.split(' *./',1); q=b/rel
   if not q.is_file() or digest(q)!=h: package_failures.append(rel)
  if package_failures: failures.append('source_bundle_integrity')
  payload=self.payload_inventory()
  if payload['missing'] or payload['unexpected'] or payload['checksum_failures']: failures.append('custom_payload_inventory')
  authority=self.authority_check()
  if authority['failures']: failures.append('authority_binding')
  snapshot=self.ws/'rollback'/'snapshots'; snapshot.mkdir(parents=True,exist_ok=True)
  writable=os.access(snapshot,os.W_OK)
  if not writable: failures.append('backup_location_not_writable')
  d={'target':info,'patch_paths':paths,'expected_paths':expected,'collisions':self._collisions(m),'payload_inventory':payload,'authority':authority,'backup_root':str(snapshot),'failures':failures,'zero_mutation_guarantee':not failures}
  self.emit('PRE_APPLY_ATOMIC_PREFLIGHT','PASS' if not failures else 'BLOCKED',d)
  return 0 if not failures else 2
 def plan(self, live=False):
  m=self.manifest(); b=Path(self.cfg['GENESIS_PACKAGE_ROOT']); paths=patch_paths(b/'04_MODIFIED_UPSTREAM_PATCHES'/'001_all_upstream_modifications.patch')
  plan={'schema':'hermesos.genesis.live-mutation-plan.v0.2' if live else 'hermesos.genesis.disposable-mutation-plan.v0.2','created_utc':utc(),'target':self.target_info(),'files_modify':paths,'files_add':{'agent':m['custom_runtime_files']['agent'],'gateway':m['custom_runtime_files']['gateway'],'hkp':'hkp/hkp','boot_probe':'<HERMES_HOME>/scripts/hkp_boot_probe.py'},'runtime_source_mode':'integrated','preflight_required':'PRE_APPLY_ATOMIC_PREFLIGHT=PASS','rollback':'snapshot-based deterministic restore; no git reset --hard for live','validation_contract':'docs/VALIDATION_CONTRACT_ALIGNMENT.md','live_apply_authorized':False}
  p=self.ws/'manifests'/('LIVE_TARGET_MUTATION_PLAN.json' if live else 'mutation_plan.json'); p.write_text(json.dumps(redact(plan),indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); self.emit('LIVE_TARGET_MUTATION_PLAN' if live else 'PLAN','PASS',{'plan':str(p),'paths':paths}); return 0
 def plan_live(self):
  if not self.cfg.get('LIVE_TARGET'):
   self.emit('LIVE_TARGET_MUTATION_PLAN','BLOCKED',{'reason':'PLAN_LIVE requires LIVE_TARGET=true'}); return 2
  inspections=[x for x in self.state['history'] if x['phase']=='LIVE_TARGET_INSPECTION']
  if not inspections or inspections[-1]['result']!='COMPATIBLE':
   self.emit('LIVE_TARGET_MUTATION_PLAN','BLOCKED',{'reason':'a current COMPATIBLE LIVE_TARGET_INSPECTION is required'}); return 2
  return self.plan(live=True)
 def prepare(self):
  if self.cfg.get('LIVE_TARGET') or not self.a.disposable_target:
   self.emit('PREPARE','BLOCKED',{'reason':'PREPARE creates only workspace payload; live target or missing disposable flag is prohibited'}); return 2
  dst=self.ws/'prepared_profile_payload_v2'; src=Path(self.cfg['GENESIS_PACKAGE_ROOT'])/'01_PROFILE_IDENTITY'
  if dst.exists(): shutil.rmtree(dst)
  shutil.copytree(src,dst); self.emit('PREPARE','PASS',{'prepared_payload':str(dst),'profile_provisioning':'not executed'}); return 0
 def _snapshot(self,m):
  r=Path(self.cfg['HERMES_RUNTIME_ROOT']); h=Path(self.cfg['HERMES_HOME']); root=self.ws/'rollback'/'snapshots'/dt.datetime.now().strftime('%Y%m%dT%H%M%S%f'); root.mkdir(parents=True)
  modified=m['patch']['affected_upstream_paths']; records=[]
  for rel in modified:
   src=r/rel; dst=root/'modified'/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); records.append({'path':rel,'sha256':digest(src)})
  support=[h/'scripts'/'hkp_boot_probe.py',h/'profiles'/'hermesos']
  support_records=[]
  for src in support:
   if src.exists():
    dst=root/'support'/src.name
    if src.is_dir(): shutil.copytree(src,dst)
    else: dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    support_records.append(str(src))
  meta={'pre_head':cmd(['git','rev-parse','HEAD'],r)['stdout'].strip(),'pre_status':cmd(['git','status','--porcelain=v1'],r)['stdout'],'modified':records,'support':support_records,'added':[]}
  (root/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n'); return root,meta
 def apply(self):
  if self.cfg.get('LIVE_TARGET') or not self.a.disposable_target: self.emit('APPLY','BLOCKED',{'reason':'live apply prohibited; disposable flag required'}); return 2
  if self.preflight()!=0: return 2
  prepared=self.ws/'prepared_profile_payload_v2'; profile=Path(self.cfg['HERMES_HOME'])/'profiles'/'hermesos'
  if not prepared.is_dir(): self.emit('APPLY','BLOCKED',{'reason':'prepared profile payload missing; run PREPARE before APPLY'}); return 2
  if profile.exists(): self.emit('APPLY','BLOCKED',{'reason':'profile collision before mutation','profile':str(profile)}); return 2
  m=self.manifest(); r=Path(self.cfg['HERMES_RUNTIME_ROOT']); h=Path(self.cfg['HERMES_HOME']); b=Path(self.cfg['GENESIS_PACKAGE_ROOT']); snap,meta=self._snapshot(m)
  patch=b/'04_MODIFIED_UPSTREAM_PATCHES'/'001_all_upstream_modifications.patch'; result=cmd(['git','apply','-p0',str(patch)],r)
  if result['returncode']!=0: self.emit('APPLY','FAIL',{'apply':result,'snapshot':str(snap)}); return 2
  added=[]
  for src,dst in [(b/'03_NEW_RUNTIME_FILES'/'agent',r/'agent'),(b/'03_NEW_RUNTIME_FILES'/'gateway',r/'gateway'),(b/'03_NEW_RUNTIME_FILES'/'hkp'/'hkp',r/'hkp'/'hkp')]:
   for p in src.rglob('*.py'):
    q=dst/p.relative_to(src); q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q); added.append(str(q))
  probe=h/'scripts'/'hkp_boot_probe.py'; probe.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(b/'03_NEW_RUNTIME_FILES'/'scripts'/'hkp_boot_probe.py',probe); added.append(str(probe))
  profile.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(prepared,profile); added.append(str(profile))
  meta['added']=added; (snap/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n'); self.state['active_snapshot']=str(snap); self.save(); self.emit('APPLY','PASS',{'snapshot':str(snap),'added_files':added,'profile_provisioned':str(profile)}); return 0
 def rollback(self):
  snap=Path(self.state.get('active_snapshot',''))
  if not snap.is_dir(): self.emit('ROLLBACK','BLOCKED',{'reason':'no active snapshot'}); return 2
  meta=jload(snap/'snapshot.json'); r=Path(self.cfg['HERMES_RUNTIME_ROOT']); h=Path(self.cfg['HERMES_HOME'])
  for x in meta['added']:
   p=Path(x)
   if p.exists() and p.is_file(): p.unlink()
  for item in meta['modified']:
   src=snap/'modified'/item['path']; dst=r/item['path']; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
  # restore or remove support artifacts deterministically
  probe=h/'scripts'/'hkp_boot_probe.py'; prior_probe=snap/'support'/'hkp_boot_probe.py'
  if prior_probe.exists(): probe.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(prior_probe,probe)
  elif probe.exists(): probe.unlink()
  profile=h/'profiles'/'hermesos'; prior_profile=snap/'support'/'hermesos'
  if prior_profile.exists():
   if profile.exists(): shutil.rmtree(profile)
   shutil.copytree(prior_profile,profile)
  elif profile.exists(): shutil.rmtree(profile)
  status=cmd(['git','status','--porcelain=v1'],r)
  clean=not status['stdout'].strip()
  if clean:
   self.state.pop('active_snapshot',None); self.save()
  self.emit('ROLLBACK','PASS' if clean else 'FAIL',{'snapshot':str(snap),'post_status':status}); return 0 if clean else 2
 def validate(self):
  package_rc=self.validate_package(); payload=self.payload_inventory(); authority=self.authority_check()
  failures=[]
  if package_rc: failures.append('source_bundle_integrity')
  if payload['missing'] or payload['unexpected'] or payload['checksum_failures']: failures.append('custom_payload_inventory')
  if authority['failures']: failures.append('authority_binding')
  self.emit('VALIDATE','PASS' if not failures else 'FAIL',{'executed_checks':{'package_integrity':package_rc==0,'custom_payload_inventory':not (payload['missing'] or payload['unexpected'] or payload['checksum_failures']),'authority_binding':not authority['failures']},'failures':failures,'not_executed_live_checks':['gateway_external_start','live_permissions_matrix','live_subagent_isolation']}); return 0 if not failures else 2
 def status(self): print(json.dumps(redact(self.state),indent=2,ensure_ascii=False)); return 0

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=MODES);p.add_argument('--config',required=True);p.add_argument('--disposable-target',action='store_true');a=p.parse_args();e=Engine(a); return getattr(e,a.mode.lower())()
if __name__=='__main__': raise SystemExit(main())
