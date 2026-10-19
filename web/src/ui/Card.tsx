import { createContext, useContext, useId } from "react";
import type { ReactNode } from "react";

/** The level of heading a Card's title uses. A dashboard module sets 3 so the cards inside it nest under the module's own h2. */
export const HeadingLevel = createContext<2 | 3>(2);

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
  const Heading = useContext(HeadingLevel) === 3 ? "h3" : "h2";
  return (
    <section className={`card ${className ?? ""}`} aria-labelledby={title ? titleId : undefined}>
      {(title || actions) && (
        <header className="card-head">
          <div>
            {title && <Heading id={titleId}>{title}</Heading>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
