import { useState } from "react";
import { ApiError } from "../api/client";
import type { HoldingsImport } from "../api/client";
import { useDeleteHoldingsImport, useHoldingsImports } from "../api/hooks";
import { cr } from "../format";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { QueryBlock } from "../ui/QueryBlock";
import { Banner } from "../ui/Status";

const when = (iso: string) => iso.slice(0, 10);

/** What has been imported, with a two-step delete. Deleting removes only that file's lines. */
export function ImportsList({ profileId }: { profileId: number }) {
  const query = useHoldingsImports(profileId);
  const remove = useDeleteHoldingsImport(profileId);
  const [asking, setAsking] = useState<number | null>(null);

  const columns: Column<HoldingsImport>[] = [
    { key: "l", header: "Import", rowHeader: true, cell: (i) => i.label },
    { key: "f", header: "File", cell: (i) => `${i.filename} (${i.file_kind === "xlsx" ? "Excel" : "CSV"})` },
    { key: "r", header: "Holdings", align: "right", cell: (i) => String(i.row_count) },
    { key: "t", header: "Total", align: "right", cell: (i) => cr(i.total_cr) },
    { key: "d", header: "Added", cell: (i) => when(i.created) },
    {
      key: "x", header: "Remove", align: "right",
      cell: (i) =>
        asking === i.id ? (
          <>
            <Button variant="primary" disabled={remove.isPending} onClick={() => remove.mutate(i.id, { onSuccess: () => setAsking(null) })} aria-label={`Yes, delete ${i.label}`}>
              Yes, delete
            </Button>{" "}
            <Button variant="ghost" onClick={() => setAsking(null)}>Keep</Button>
          </>
        ) : (
          <Button variant="ghost" icon="minus" onClick={() => setAsking(i.id)} aria-label={`Delete ${i.label}`}>Delete</Button>
        ),
    },
  ];

  return (
    <Card title="Your imports" subtitle="Everything below feeds the consolidated view. Delete an import to take its holdings out.">
      <QueryBlock query={query} label="Your imports" rows={3}>
        {(imports) =>
          imports.length === 0 ? (
            <p className="empty-note">Nothing imported for this family yet.</p>
          ) : (
            <div className="stack">
              <DataTable caption="Imports for this profile" columns={columns} rows={imports} rowKey={(i) => String(i.id)} />
              {remove.isError && (
                <Banner tone="bad" critical>{remove.error instanceof ApiError ? remove.error.message : "That import could not be deleted."}</Banner>
              )}
            </div>
          )
        }
      </QueryBlock>
    </Card>
  );
}
