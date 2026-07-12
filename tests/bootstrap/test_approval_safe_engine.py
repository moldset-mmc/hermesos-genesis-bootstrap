from __future__ import annotations
import importlib.util, json, shutil, subprocess, sys
from pathlib import Path

TEST_FILE=Path(__file__).resolve()
ROOT=TEST_FILE.parents[1] if (TEST_FILE.parents[1]/'bootstrap_engine').is_dir() else TEST_FILE.parents[2]/'bootstrap'
ENGINE=ROOT/'bootstrap_engine'/'genesis_bootstrap_v2.py'
BUNDLE=ROOT.parent/'HERMESOS_GENESIS_SOURCE_BUNDLE_v0.2'
if not BUNDLE.is_dir():
    BUNDLE=ROOT.parent/'source_bundle'/'HERMESOS_GENESIS_SOURCE_BUNDLE_v0.2'

spec=importlib.util.spec_from_file_location('engine',ENGINE)
mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

def test_patch_paths_keep_non_prefixed_agent_path():
    paths=mod.patch_paths(BUNDLE/'04_MODIFIED_UPSTREAM_PATCHES'/'001_all_upstream_modifications.patch')
    assert len(paths)==15
    assert paths[0]=='agent/background_review.py'
    assert all(not p.startswith('ent/') for p in paths)

def test_redaction_never_keeps_secret_value():
    payload={'secret_references':{'OPENROUTER_API_KEY':'env:OPENROUTER_API_KEY'},'ordinary':'ok'}
    rendered=json.dumps(mod.redact(payload))
    assert 'OPENROUTER_API_KEY' not in rendered
    assert '<REDACTED_REFERENCE>' in rendered

def test_live_apply_is_refused_before_mutation(tmp_path:Path):
    cfg={'GENESIS_PACKAGE_ROOT':str(BUNDLE),'HKP_CANONICAL_ROOT':'E:/HKP','HKP_EVIDENCE_ROOT':str(tmp_path/'evidence'),'HKP_POLICY_ROOT':'E:/HKP/Specification Layer','HERMES_HOME':str(tmp_path/'home'),'HERMES_PROFILE_ROOT':str(tmp_path/'home/profiles'),'HERMES_RUNTIME_ROOT':str(tmp_path/'runtime'),'PROJECT_WORKSPACE_ROOT':str(tmp_path/'workspace'),'LIVE_TARGET':True,'secret_references':{'OPENROUTER_API_KEY':'env:OPENROUTER_API_KEY','TELEGRAM_BOT_TOKEN_ASSISTANT':'env:TELEGRAM_BOT_TOKEN_ASSISTANT'}}
    p=tmp_path/'cfg.json';p.write_text(json.dumps(cfg))
    r=subprocess.run([sys.executable,str(ENGINE),'APPLY','--config',str(p),'--disposable-target'])
    assert r.returncode==2
    assert not (tmp_path/'runtime').exists()

def test_preflight_blocks_dirty_target_before_mutation():
    source=ENGINE.read_text(encoding='utf-8')
    assert (ROOT/'manifests'/'installation_manifest.json').is_file()
    assert 'PRE_APPLY_ATOMIC_PREFLIGHT' in source
    assert 'dirty_target' in source
    assert 'if self.preflight()!=0: return 2' in source
    assert "cmd(['git','reset','--hard'" not in source

def test_apply_checks_profile_payload_before_snapshot():
    source=ENGINE.read_text(encoding='utf-8')
    preflight_idx=source.index('if self.preflight()!=0: return 2')
    prepared_idx=source.index("prepared=self.ws/'prepared_profile_payload_v2'")
    snapshot_idx=source.index('snap,meta=self._snapshot(m)')
    assert preflight_idx < prepared_idx < snapshot_idx
    assert "prepared profile payload missing; run PREPARE before APPLY" in source

def test_profile_collision_is_part_of_preflight_collisions():
    source=ENGINE.read_text(encoding='utf-8')
    assert "h/'profiles'/'hermesos'" in source

def test_integrated_source_bundle_does_not_use_runtime_overlay():
    source=ENGINE.read_text(encoding='utf-8')
    manifest=json.loads((ROOT/'manifests'/'installation_manifest.json').read_text(encoding='utf-8'))
    assert manifest['runtime_source_mode']=='INTEGRATED'
    assert 'implementation_corrections' not in source
    assert 'HKP-INT-006' in (BUNDLE/'03_NEW_RUNTIME_FILES'/'gateway'/'governance_status.py').read_text(encoding='utf-8')
