"""serverkit-gpu extension tests.

Moved out of the ServerKit repo along with the extension (the extension now
lives in its own repository and ships as a runtime-ESM bundle). The nvidia-smi
parsing service + its blueprint live under backend/ and mount at /api/v1/gpu
via the manifest's entry_point + url_prefix (the same prefix the deleted core
route used, so the frontend is unchanged).

These tests still need the panel's Flask app + fixtures, so run them from a
ServerKit checkout — see tests/README.md.
"""
import importlib
import importlib.util
import json
import os
import sys
import types

import pytest

from app.services import plugin_service

SLUG = 'serverkit-gpu'
# realpath so a symlinked copy inside <panel>/backend/tests still resolves back
# to this repository root. SERVERKIT_GPU_DIR overrides when copied (not linked).
EXT_DIR = os.environ.get(
    'SERVERKIT_GPU_DIR',
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
)


def _load_ext():
    """Register this repo's backend/ as ``app.plugins.<slug>`` — mirrors how the
    panel loads an installed extension's backend at boot."""
    backend_dir = os.path.join(EXT_DIR, 'backend')
    assert os.path.isdir(backend_dir), f'extension backend not found at {backend_dir}'
    spec = importlib.util.spec_from_file_location(
        f'app.plugins.{SLUG}',
        os.path.join(backend_dir, '__init__.py'),
        submodule_search_locations=[backend_dir],
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[f'app.plugins.{SLUG}'] = pkg
    spec.loader.exec_module(pkg)
    svc_mod = importlib.import_module(f'app.plugins.{SLUG}.gpu_service')
    bp_mod = importlib.import_module(f'app.plugins.{SLUG}.gpu')
    return svc_mod, bp_mod


svc_mod, bp_mod = _load_ext()
GpuService = svc_mod.GpuService

SAMPLE = "0, NVIDIA GeForce RTX 3090, 15, 2048, 24576, 45, 120.50, 350.00, 30, 535.104.05\n"


def _fake_run(stdout, rc=0):
    return lambda *a, **k: types.SimpleNamespace(returncode=rc, stdout=stdout, stderr='')


# ---------------------------------------------------------------------------
# manifest + bridge wiring
# ---------------------------------------------------------------------------

def test_manifest_declares_bridge_and_sdk():
    with open(os.path.join(EXT_DIR, 'plugin.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    assert plugin_service._validate_manifest(manifest) is True
    assert manifest['name'] == SLUG
    assert manifest['category'] == 'monitoring'
    assert manifest['entry_point'] == 'gpu:gpu_bp'
    assert manifest['url_prefix'] == '/api/v1/gpu'
    # sdk_version drives the runtime SDK gate; it must satisfy the panel's SDK.
    from app.utils.sdk import SDK_VERSION, sdk_version_satisfies
    assert manifest['sdk_version']
    assert sdk_version_satisfies(manifest['sdk_version'], SDK_VERSION)
    # Runtime-ESM bundle, loaded by the no-rebuild frontend loader.
    assert manifest['frontend_entry'] == 'dist/index.mjs'
    routes = manifest['contributions']['routes']
    assert {'path': 'gpu', 'component': 'GpuMonitorPage'} in routes


def test_entry_point_resolves_to_blueprint():
    assert getattr(bp_mod, 'gpu_bp', None) is not None
    assert bp_mod.gpu_bp.name == 'gpu'


def test_frontend_exports_route_component():
    with open(os.path.join(EXT_DIR, 'frontend', 'runtime-entry.jsx'), encoding='utf-8') as f:
        src = f.read()
    assert 'GpuMonitorPage' in src


def test_core_gpu_module_is_gone():
    """The core page/blueprint/service were deleted — nothing should import them."""
    import importlib.util
    assert importlib.util.find_spec('app.api.gpu') is None
    assert importlib.util.find_spec('app.services.gpu_service') is None


# ---------------------------------------------------------------------------
# service: nvidia-smi parsing (moved from the core test)
# ---------------------------------------------------------------------------

class TestGpuService:
    def test_list_gpus_parses_a_row(self, monkeypatch):
        monkeypatch.setattr(GpuService, '_run', _fake_run(SAMPLE))
        gpus = GpuService.list_gpus()
        assert len(gpus) == 1
        g = gpus[0]
        assert g['index'] == 0
        assert g['name'] == 'NVIDIA GeForce RTX 3090'
        assert g['memory_total'] == 24576.0
        assert g['memory_percent'] == round(100 * 2048 / 24576, 1)
        assert g['driver_version'] == '535.104.05'

    def test_coerces_na_to_none(self, monkeypatch):
        line = "0, GPU, [N/A], 100, 1000, [N/A], 50, 100, [N/A], 535\n"
        monkeypatch.setattr(GpuService, '_run', _fake_run(line))
        g = GpuService.list_gpus()[0]
        assert g['utilization_gpu'] is None
        assert g['temperature'] is None
        assert g['fan_speed'] is None
        assert g['memory_percent'] == 10.0

    def test_available_false_on_nonzero_exit(self, monkeypatch):
        monkeypatch.setattr(GpuService, '_run', _fake_run('', rc=1))
        assert GpuService.available() is False

    def test_info_when_no_gpus(self, monkeypatch):
        monkeypatch.setattr(GpuService, '_run', _fake_run('', rc=1))
        info = GpuService.info()
        assert info['available'] is False
        assert info['gpus'] == [] and info['processes'] == []


# ---------------------------------------------------------------------------
# blueprint routes (registered like production does)
# ---------------------------------------------------------------------------

@pytest.fixture
def gpu_app(app):
    if 'gpu' not in app.blueprints:
        app.register_blueprint(bp_mod.gpu_bp, url_prefix='/api/v1/gpu')
    return app


@pytest.fixture
def gpu_client(gpu_app):
    return gpu_app.test_client()


def test_gpu_endpoint_returns_info(gpu_client, auth_headers, monkeypatch):
    monkeypatch.setattr(GpuService, 'list_gpus', classmethod(lambda cls: [{'index': 0, 'name': 'RTX 3090'}]))
    monkeypatch.setattr(GpuService, 'processes', classmethod(lambda cls: []))
    resp = gpu_client.get('/api/v1/gpu/', headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['available'] is True
    assert len(body['gpus']) == 1


def test_gpu_requires_auth(gpu_client):
    assert gpu_client.get('/api/v1/gpu/').status_code == 401
