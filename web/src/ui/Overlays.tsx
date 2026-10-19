import * as Dialog from "@radix-ui/react-dialog";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Icon } from "./Icon";
import type { IconName } from "./Icon";

/** A panel that slides in from the side with the detail behind a number. Focus is trapped and restored; Esc closes it. */
export function SidePanel({
  open,
  onOpenChange,
  title,
  description,
  children,
  side = "right",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  side?: "right" | "left";
}) {
  // Panels are opened from ordinary buttons, not Radix triggers, so remember the opener and give focus back to it.
  const opener = useRef<HTMLElement | null>(null);
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content
          className={`panel panel-${side}`}
          onOpenAutoFocus={() => {
            opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            opener.current?.focus();
          }}
        >
          <div className="panel-head">
            <Dialog.Title asChild>
              <h2>{title}</h2>
            </Dialog.Title>
            <Dialog.Close className="btn btn-ghost btn-icon" aria-label="Close panel">
              <Icon name="close" size={18} />
            </Dialog.Close>
          </div>
          {description ? (
            <Dialog.Description className="panel-desc">{description}</Dialog.Description>
          ) : (
            <Dialog.Description className="sr-only">{title}</Dialog.Description>
          )}
          <div className="panel-body">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** An icon-only button. The label is both its accessible name and its tooltip. */
export function IconButton({
  label,
  icon,
  ...rest
}: { label: string; icon: IconName } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button type="button" className="btn btn-ghost btn-icon" aria-label={label} {...rest}>
          <Icon name={icon} size={20} />
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="tooltip" sideOffset={6}>
          {label}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export const TooltipProvider = Tooltip.Provider;

export function Menu({ trigger, label, children }: { trigger: ReactNode; label: string; children: ReactNode }) {
  return (
    <Dropdown.Root>
      <Dropdown.Trigger className="btn btn-ghost" aria-label={label}>
        {trigger}
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content className="menu" align="end" sideOffset={6}>
          {children}
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <Dropdown.Label className="menu-label">{children}</Dropdown.Label>;
}

export function MenuItem({ icon, children, onSelect }: { icon?: IconName; children: ReactNode; onSelect: () => void }) {
  return (
    <Dropdown.Item className="menu-item" onSelect={onSelect}>
      {icon && <Icon name={icon} size={18} />}
      {children}
    </Dropdown.Item>
  );
}

export function MenuSeparator() {
  return <Dropdown.Separator className="menu-sep" />;
}

export function MenuRadioGroup<T extends string>({
  value,
  onValueChange,
  options,
}: {
  value: T;
  onValueChange: (value: T) => void;
  options: readonly { value: T; label: string; icon: IconName }[];
}) {
  return (
    <Dropdown.RadioGroup value={value} onValueChange={(v) => onValueChange(v as T)}>
      {options.map((o) => (
        <Dropdown.RadioItem key={o.value} value={o.value} className="menu-item">
          <Icon name={o.icon} size={18} />
          {o.label}
          <Dropdown.ItemIndicator className="menu-check">
            <Icon name="success" size={16} />
          </Dropdown.ItemIndicator>
        </Dropdown.RadioItem>
      ))}
    </Dropdown.RadioGroup>
  );
}
