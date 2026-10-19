import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: string;
  /** Numbers line up on the right. */
  align?: "left" | "right";
  /** The first column of each row is its row header, so screen readers announce "Debt, 34.3%". */
  rowHeader?: boolean;
  cell: (row: T) => ReactNode;
};

/** A real table with a caption and header scopes. Charts use it as their text alternative. */
export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
}: {
  caption: string;
  columns: readonly Column<T>[];
  rows: readonly T[];
  rowKey: (row: T) => string;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={c.align === "right" ? "num" : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) =>
                c.rowHeader ? (
                  <th key={c.key} scope="row">
                    {c.cell(row)}
                  </th>
                ) : (
                  <td key={c.key} className={c.align === "right" ? "num" : undefined}>
                    {c.cell(row)}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
