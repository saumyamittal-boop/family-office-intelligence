import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { LinkProps } from "react-router-dom";
import { Icon } from "./Icon";
import type { IconName } from "./Icon";

type Variant = "primary" | "secondary" | "ghost";

type Common = { variant?: Variant; icon?: IconName; children?: ReactNode };

function classes(variant: Variant, iconOnly: boolean, extra?: string): string {
  return ["btn", `btn-${variant}`, iconOnly ? "btn-icon" : "", extra ?? ""].filter(Boolean).join(" ");
}

export function Button({
  variant = "secondary",
  icon,
  children,
  className,
  type = "button",
  ...rest
}: Common & ButtonHTMLAttributes<HTMLButtonElement>) {
  const iconOnly = icon !== undefined && children === undefined;
  return (
    <button type={type} className={classes(variant, iconOnly, className)} {...rest}>
      {icon && <Icon name={icon} size={18} />}
      {children}
    </button>
  );
}

export function ButtonLink({ variant = "secondary", icon, children, className, ...rest }: Common & LinkProps) {
  return (
    <Link className={classes(variant, false, className)} {...rest}>
      {icon && <Icon name={icon} size={18} />}
      {children}
    </Link>
  );
}
