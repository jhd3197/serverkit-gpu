"""NVIDIA GPU monitoring (serverkit-gpu extension).

Moved out of core as the first CORE_SLIM slice (plan 32 #7). Shells out to
``nvidia-smi`` (like the rest of the service layer) and degrades gracefully to
"no GPUs" when it isn't present, so the panel stays happy on GPU-less hosts.
"""
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

# (key, caster) in the same order as GPU_QUERY below.
GPU_FIELDS = [
    ('index', int),
    ('name', str),
    ('utilization_gpu', float),   # %
    ('memory_used', float),       # MiB
    ('memory_total', float),      # MiB
    ('temperature', float),       # C
    ('power_draw', float),        # W
    ('power_limit', float),       # W
    ('fan_speed', float),         # %
    ('driver_version', str),
]
GPU_QUERY = ('index,name,utilization.gpu,memory.used,memory.total,'
             'temperature.gpu,power.draw,power.limit,fan.speed,driver_version')

_NA = ('', '[N/A]', 'N/A', '[Not Supported]', '[Unknown Error]')


class GpuService:

    @staticmethod
    def _run(args, timeout=10):
        return subprocess.run(['nvidia-smi', *args], capture_output=True, text=True, timeout=timeout)

    @staticmethod
    def _coerce(value, caster):
        v = value.strip()
        if v in _NA:
            return None
        try:
            return caster(v)
        except (ValueError, TypeError):
            return v if caster is str else None

    @classmethod
    def available(cls):
        try:
            return cls._run(['--query-gpu=index', '--format=csv,noheader']).returncode == 0
        except Exception:
            return False

    @classmethod
    def list_gpus(cls):
        try:
            result = cls._run([f'--query-gpu={GPU_QUERY}', '--format=csv,noheader,nounits'])
            if result.returncode != 0:
                return []
        except Exception:
            return []

        gpus = []
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < len(GPU_FIELDS):
                continue
            gpu = {key: cls._coerce(raw, caster)
                   for (key, caster), raw in zip(GPU_FIELDS, parts)}
            if gpu.get('memory_total'):
                gpu['memory_percent'] = round(100.0 * (gpu.get('memory_used') or 0) / gpu['memory_total'], 1)
            gpus.append(gpu)
        return gpus

    @classmethod
    def _container_for_pid(cls, pid):
        """Best-effort: resolve a host PID to a Docker container name via its
        cgroup. Returns None when it can't be determined (or off Linux)."""
        if not pid:
            return None
        try:
            with open(f'/proc/{pid}/cgroup', 'r') as fh:
                match = re.search(r'docker[-/]([0-9a-f]{64})', fh.read())
            if not match:
                return None
            cid = match.group(1)[:12]
            out = subprocess.run(['docker', 'inspect', '-f', '{{.Name}}', cid],
                                 capture_output=True, text=True, timeout=5)
            return out.stdout.strip().lstrip('/') if out.returncode == 0 else cid
        except Exception:
            return None

    @classmethod
    def processes(cls):
        try:
            result = cls._run(['--query-compute-apps=gpu_uuid,pid,process_name,used_memory',
                               '--format=csv,noheader,nounits'])
            if result.returncode != 0:
                return []
        except Exception:
            return []

        procs = []
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 4:
                continue
            pid = cls._coerce(parts[1], int)
            procs.append({
                'gpu_uuid': parts[0],
                'pid': pid,
                'process_name': parts[2],
                'used_memory': cls._coerce(parts[3], float),
                'container': cls._container_for_pid(pid),
            })
        return procs

    @classmethod
    def info(cls):
        gpus = cls.list_gpus()
        return {
            'available': bool(gpus),
            'gpus': gpus,
            'processes': cls.processes() if gpus else [],
        }
