"""GPU Monitor API endpoints (serverkit-gpu extension).

Mounted under ``/api/v1/gpu`` via the manifest's ``entry_point`` + ``url_prefix``
(the same prefix the core route used, so the frontend is unchanged — decision D9).
Thin routing layer over :class:`GpuService`; read-only metrics, JWT-protected.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from .gpu_service import GpuService

gpu_bp = Blueprint('gpu', __name__)


@gpu_bp.route('/', methods=['GET'])
@jwt_required()
def gpu_info():
    """Per-GPU stats (utilization, VRAM, temperature, power, fan, driver) plus
    the GPU compute processes, with best-effort container resolution."""
    return jsonify(GpuService.info())
