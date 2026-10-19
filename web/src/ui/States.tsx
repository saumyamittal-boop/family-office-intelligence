import type { ReactNode } from "react";
import { Button } from "./Button";
import { Icon } from "./Icon";
import type { IconName } from "./Icon";

/** Placeholder shapes while data loads. Decorative: the surrounding LoadingBlock carries the announcement. */
export function Skeleton({ height = "1rem", width = "100%" }: { height?: string; width?: string }) {
  return <span className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function LoadingBlock({ label = "Loading", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="state state-loading" role="status" aria-busy="true">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height="1.1rem" width={i === rows - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
}

export function EmptyState({
  icon = "info",
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="state state-empty">
      <span className="state-icon">
        <Icon name={icon} size={28} />
      </span>
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="state state-error" role="alert">
      <span className="state-icon">
        <Icon name="error" size={28} />
      </span>
      <h2>{title}</h2>
      <p>{message}</p>
      {onRetry && (
        <Button variant="primary" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
