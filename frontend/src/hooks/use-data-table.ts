"use client";

import {
  type Updater,
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState,
  type PaginationState,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import * as React from "react";

interface UseDataTableProps<TData, TValue> {
  data: TData[];
  columns: ColumnDef<TData, TValue>[];
  pageCount?: number;
  manualPagination?: boolean;
  manualSorting?: boolean;
  onPaginationChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  onSortingChange?: (columnId: string, direction: "asc" | "desc") => void;
  initialState?: {
    pagination?: {
      pageIndex?: number;
      pageSize?: number;
    };
    sorting?: SortingState;
    columnVisibility?: VisibilityState;
    columnFilters?: ColumnFiltersState;
    columnPinning?: {
      left?: string[];
      right?: string[];
    };
  };
  getRowId?: (row: TData) => string;
}

export function useDataTable<TData, TValue>({
  data,
  columns,
  pageCount = -1,
  manualPagination = false,
  manualSorting = false,
  onPaginationChange,
  onPageSizeChange,
  onSortingChange,
  initialState,
  getRowId,
}: UseDataTableProps<TData, TValue>) {
  const [rowSelection, setRowSelection] = React.useState({});
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>(initialState?.columnVisibility || {});
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    initialState?.columnFilters || []
  );
  const [sorting, setSorting] = React.useState<SortingState>(
    initialState?.sorting || []
  );

  // Handle pagination change
  const handlePaginationChange = React.useCallback(
    (updaterOrValue: Updater<PaginationState>) => {
      if (manualPagination && onPaginationChange) {
        // If it's a function, call it with the current state to get the new value
        const newState =
          typeof updaterOrValue === "function"
            ? updaterOrValue(table.getState().pagination)
            : updaterOrValue;

        // Call the callback with the new page index + 1 (API uses 1-based indexing)
        onPaginationChange(newState.pageIndex + 1);

        // If page size changed and we have a handler for it
        if (
          onPageSizeChange &&
          newState.pageSize !== table.getState().pagination.pageSize
        ) {
          onPageSizeChange(newState.pageSize);
        }
      }
    },
    [manualPagination, onPaginationChange, onPageSizeChange]
  );

  // Handle sorting change
  const handleSortingChange = React.useCallback(
    (updaterOrValue: Updater<SortingState>) => {
      if (manualSorting && onSortingChange) {
        // If it's a function, call it with the current state to get the new value
        const newSorting =
          typeof updaterOrValue === "function"
            ? updaterOrValue(sorting)
            : updaterOrValue;

        if (newSorting.length > 0) {
          const { id, desc } = newSorting[0];
          onSortingChange(id, desc ? "desc" : "asc");
        } else if (sorting.length > 0) {
          // If sorting is being cleared, reset to default
          onSortingChange("id", "asc");
        }
      }

      // Update local state regardless
      setSorting(updaterOrValue);
    },
    [manualSorting, onSortingChange, sorting]
  );

  const table = useReactTable({
    data,
    columns,
    pageCount: pageCount,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination: {
        pageIndex: initialState?.pagination?.pageIndex || 0,
        pageSize: initialState?.pagination?.pageSize || 10,
      },
    },
    enableRowSelection: true,
    manualPagination,
    manualSorting,
    onPaginationChange: handlePaginationChange,
    onSortingChange: handleSortingChange,
    onRowSelectionChange: setRowSelection,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    getRowId,
    initialState: {
      pagination: initialState?.pagination,
      columnPinning: initialState?.columnPinning,
    },
  });

  return { table };
}
