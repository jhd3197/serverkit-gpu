// GPU Monitor page — the serverkit-gpu extension's UI. Imports come from the
// runtime SDK (PageTopbar, KpiBand, api, useToast — externalized to the panel's
// singletons at build time); EmptyState + Button are local stand-ins rendering
// the same host design-system classes (see ./primitives.jsx).
import { useState, useEffect, useCallback } from 'react';
import { Cpu, RefreshCw, Thermometer, Zap, Fan } from 'lucide-react';
import { PageTopbar, KpiBand, api, useToast } from 'serverkit-sdk';
import { EmptyState, Button } from './primitives.jsx';

function clampPercent(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return 0;
    return Math.min(100, Math.max(0, n));
}

function utilTone(percent) {
    if (percent >= 85) return 'is-red';
    if (percent >= 60) return 'is-amber';
    return 'is-green';
}

function formatMib(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    if (n >= 1024) return `${(n / 1024).toFixed(1)} GiB`;
    return `${Math.round(n)} MiB`;
}

const GpuCard = ({ gpu }) => {
    const util = clampPercent(gpu.utilization_gpu);
    const memPercent = clampPercent(
        gpu.memory_percent != null
            ? gpu.memory_percent
            : (gpu.memory_total ? (gpu.memory_used / gpu.memory_total) * 100 : 0)
    );

    return (
        <div className="gpu-card">
            <div className="gpu-card__head">
                <div className="gpu-card__title">
                    <Cpu size={16} />
                    <span className="gpu-card__name">{gpu.name || `GPU ${gpu.index}`}</span>
                </div>
                <span className="gpu-card__index">#{gpu.index}</span>
            </div>

            <div className="gpu-card__bars">
                <div className="gpu-bar">
                    <div className="gpu-bar__head">
                        <span className="gpu-bar__label">GPU Utilization</span>
                        <span className="gpu-bar__value">{util}%</span>
                    </div>
                    <div className="gpu-bar__track">
                        <div className={`gpu-bar__fill ${utilTone(util)}`} style={{ width: `${util}%` }} />
                    </div>
                </div>

                <div className="gpu-bar">
                    <div className="gpu-bar__head">
                        <span className="gpu-bar__label">VRAM</span>
                        <span className="gpu-bar__value">
                            {formatMib(gpu.memory_used)} / {formatMib(gpu.memory_total)} ({Math.round(memPercent)}%)
                        </span>
                    </div>
                    <div className="gpu-bar__track">
                        <div className={`gpu-bar__fill ${utilTone(memPercent)}`} style={{ width: `${memPercent}%` }} />
                    </div>
                </div>
            </div>

            <div className="gpu-stats">
                <div className="gpu-stat">
                    <Thermometer size={14} />
                    <span className="gpu-stat__label">Temp</span>
                    <span className="gpu-stat__value">
                        {gpu.temperature != null ? `${gpu.temperature}°C` : '—'}
                    </span>
                </div>
                <div className="gpu-stat">
                    <Zap size={14} />
                    <span className="gpu-stat__label">Power</span>
                    <span className="gpu-stat__value">
                        {gpu.power_draw != null ? `${Math.round(gpu.power_draw)}W` : '—'}
                        {gpu.power_limit != null && (
                            <span className="gpu-stat__sub"> / {Math.round(gpu.power_limit)}W</span>
                        )}
                    </span>
                </div>
                <div className="gpu-stat">
                    <Fan size={14} />
                    <span className="gpu-stat__label">Fan</span>
                    <span className="gpu-stat__value">
                        {gpu.fan_speed != null ? `${gpu.fan_speed}%` : '—'}
                    </span>
                </div>
                <div className="gpu-stat">
                    <Cpu size={14} />
                    <span className="gpu-stat__label">Driver</span>
                    <span className="gpu-stat__value">{gpu.driver_version || '—'}</span>
                </div>
            </div>
        </div>
    );
};

const GpuMonitor = () => {
    const toast = useToast();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const load = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true);
        try {
            const result = await api.getGpuInfo();
            setData(result);
        } catch (err) {
            if (isRefresh) toast.error(err.message || 'Failed to load GPU info');
            console.error('Failed to load GPU info:', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [toast]);

    useEffect(() => { load(); }, [load]);

    const gpus = data?.gpus || [];
    const processes = data?.processes || [];

    return (
        <div className="page-container gpu-page">
            <PageTopbar
                icon={<Cpu size={18} />}
                title="GPU Monitor"
                meta={data?.available ? `${gpus.length} GPU${gpus.length !== 1 ? 's' : ''}` : undefined}
                actions={
                    <Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing}>
                        <RefreshCw size={15} />
                        {refreshing ? 'Refreshing…' : 'Refresh'}
                    </Button>
                }
            />

            {loading ? (
                <EmptyState loading title="Loading GPU data" />
            ) : !data?.available ? (
                <EmptyState
                    icon={Cpu}
                    size="lg"
                    title="No NVIDIA GPU detected"
                    description="This host has no NVIDIA GPU, or the NVIDIA drivers / nvidia-smi are not available."
                />
            ) : (
                <>
                    {/* Custom live-meter tiles kept per Plan 20 Decision 5 — band supplies grid/spacing only */}
                    <KpiBand max={5}>
                        {gpus.map((gpu) => (
                            <GpuCard key={gpu.index} gpu={gpu} />
                        ))}
                    </KpiBand>

                    <div className="gpu-procs">
                        <div className="gpu-procs__head">
                            <h2>GPU Processes</h2>
                            <span className="text-muted">{processes.length} running</span>
                        </div>
                        <table className="sk-dtable gpu-procs__table">
                            <thead>
                                <tr>
                                    <th>PID</th>
                                    <th>Process</th>
                                    <th>Container</th>
                                    <th>VRAM</th>
                                </tr>
                            </thead>
                            <tbody>
                                {processes.map((proc, i) => (
                                    <tr key={`${proc.pid}-${i}`}>
                                        <td className="sk-cell-mono">{proc.pid}</td>
                                        <td>{proc.process_name || '—'}</td>
                                        <td>{proc.container || '—'}</td>
                                        <td className="sk-cell-mono">{formatMib(proc.used_memory)}</td>
                                    </tr>
                                ))}
                                {processes.length === 0 && (
                                    <tr>
                                        <td colSpan={4} className="text-center text-muted">No active GPU processes</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    );
};

export default GpuMonitor;
