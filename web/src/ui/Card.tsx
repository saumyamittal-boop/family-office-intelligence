import { useId } from "react";
import type { ReactNode } from "react";

/** A titled region. The title names the region for screen-reader landmark navigation. */
export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const titleId = useId();
  return (
    <section className={`card ${className ?? ""}`} aria-labelledby={title ? titleId : undefined}>
      {(title || actions) && (
        <header className="card-head">
          <div>
            {title && <h2 id={titleId}>{title}</h2>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
