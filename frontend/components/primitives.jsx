// Local stand-ins for the two host components this page needs that are NOT on
// the serverkit-sdk surface (EmptyState, Button). They render the same host
// design-system classes (.btn-*, .empty-state, .skeleton) the core components
// emit, so the page looks identical without importing host internals — which a
// runtime-ESM bundle cannot do.
import { Inbox } from 'lucide-react';

// Mirrors frontend/src/components/ui/button.jsx's variant/size -> class map.
const VARIANT_CLASSES = {
    default: 'btn-primary',
    primary: 'btn-primary',
    destructive: 'btn-danger',
    danger: 'btn-danger',
    outline: 'btn-secondary',
    secondary: 'btn-soft',
    ghost: 'btn-ghost',
    link: 'btn-link',
};
const SIZE_CLASSES = { sm: 'btn-sm', icon: 'btn-icon' };

export function Button({ variant = 'default', size, className = '', children, ...props }) {
    const classes = [
        'btn',
        VARIANT_CLASSES[variant] || 'btn-primary',
        SIZE_CLASSES[size] || '',
        className,
    ].filter(Boolean).join(' ');
    return (
        <button type="button" className={classes} {...props}>
            {children}
        </button>
    );
}

// Mirrors the host Skeleton's rendered markup (span.skeleton.skeleton--*).
function Skeleton({ variant = 'line', width }) {
    return (
        <span
            className={`skeleton skeleton--${variant}`}
            style={width != null ? { width: typeof width === 'number' ? `${width}px` : width } : undefined}
            aria-hidden="true"
        />
    );
}

// Mirrors frontend/src/components/EmptyState.jsx's rendered markup so the host
// .empty-state / .skeleton-panel styles apply unchanged.
export function EmptyState({
    icon: Icon = Inbox,
    title = 'No items found',
    description = '',
    action = null,
    size = 'default',
    loading = false,
}) {
    if (loading) {
        return (
            <div
                className={`empty-state empty-state--${size} empty-state--loading`}
                role="status"
                aria-busy="true"
                aria-label={title || 'Loading'}
            >
                <div className="skeleton-panel">
                    <div className="skeleton-panel__head">
                        <Skeleton variant="avatar" />
                        <div className="skeleton-panel__head-text">
                            <Skeleton variant="title" width="42%" />
                            <Skeleton variant="line" width="26%" />
                        </div>
                    </div>
                    <div className="skeleton-panel__cards">
                        <Skeleton variant="card" />
                        <Skeleton variant="card" />
                        <Skeleton variant="card" />
                    </div>
                    <div className="skeleton-panel__rows">
                        <Skeleton variant="line" width="100%" />
                        <Skeleton variant="line" width="92%" />
                        <Skeleton variant="line" width="76%" />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={`empty-state empty-state--${size}`}>
            <div className="empty-state__icon">
                <Icon size={size === 'lg' ? 64 : 48} />
            </div>
            <h3 className="empty-state__title">{title}</h3>
            {description && (
                <p className="empty-state__description">{description}</p>
            )}
            {action && (
                <div className="empty-state__action">{action}</div>
            )}
        </div>
    );
}
