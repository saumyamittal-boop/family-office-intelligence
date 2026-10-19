import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import { ErrorState, LoadingBlock } from "./States";

type QueryLike<T> = {
  data: T | undefined;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
};

/** Loading, error (with retry) and loaded states for one piece of data, so each module fails on its own. */
export function QueryBlock<T>({
  query,
  label,
  rows = 4,
  children,
}: {
  query: QueryLike<T>;
  label: string;
  rows?: number;
  children: (data: T) => ReactNode;
}) {
  if (query.data !== undefined) return <>{children(query.data)}</>;
  if (query.isError) {
    return (
      <ErrorState
        title={`${label} could not be loaded`}
        message={query.error instanceof ApiError ? query.error.message : "Something went wrong."}
        onRetry={() => void query.refetch()}
      />
    );
  }
  return <LoadingBlock label={`Loading ${label.toLowerCase()}`} rows={rows} />;
}
