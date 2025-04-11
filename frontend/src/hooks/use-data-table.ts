"use client";

import {
  type ColumnDef,
  type ColumnFiltersState,
  type PaginationState,
  type SortingState,
  type VisibilityState,
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
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  pageCount?: number;
  manualPagination?: boolean;
  manualSorting?: boolean;
  onPaginationChange?: (pageIndex: number) => void;
  onPageSizeChange?: (pageSize: number) => void; // Add this prop
  onSortingChange?: (columnId: string, direction: "asc" | "desc") => void;
  initialState?: {
    pagination?: {
      pageIndex: number;
      pageSize: number;
    };
    sorting?: {
      id: string;
      desc: boolean;
    }[];
    columnVisibility?: VisibilityState;
    columnPinning?: {
      left?: string[];
      right?: string[];
    };
  };
  getRowId?: (row: TData) => string;
}

export function useDataTable<TData, TValue>({
  columns,
  data,
  pageCount = -1,
  manualPagination = false,
  manualSorting = false,
  onPaginationChange,
  onPageSizeChange, // Add this prop
  onSortingChange,
  initialState,
  getRowId,
}: UseDataTableProps<TData, TValue>) {
  const [rowSelection, setRowSelection] = React.useState({});
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>(initialState?.columnVisibility || {});
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    []
  );
  const [sorting, setSorting] = React.useState<SortingState>(
    initialState?.sorting ? initialState.sorting : []
  );
  const [pagination, setPagination] = React.useState<PaginationState>({
    pageIndex: initialState?.pagination?.pageIndex || 0,
    pageSize: initialState?.pagination?.pageSize || 10,
  });

  // Handle sorting changes
  React.useEffect(() => {
    if (manualSorting && onSortingChange && sorting.length > 0) {
      const { id, desc } = sorting[0];
      onSortingChange(id, desc ? "desc" : "asc");
    }
  }, [sorting, manualSorting, onSortingChange]);

  // Handle pagination changes
  React.useEffect(() => {
    if (manualPagination) {
      // Handle page index change
      if (onPaginationChange) {
        onPaginationChange(pagination.pageIndex + 1);
      }

      // Handle page size change
      if (
        onPageSizeChange &&
        pagination.pageSize !== initialState?.pagination?.pageSize
      ) {
        onPageSizeChange(pagination.pageSize);
      }
    }
  }, [
    pagination.pageIndex,
    pagination.pageSize,
    manualPagination,
    onPaginationChange,
    onPageSizeChange,
    initialState?.pagination?.pageSize,
  ]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination,
    },
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: manualPagination
      ? undefined
      : getPaginationRowModel(),
    getSortedRowModel: manualSorting ? undefined : getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    manualPagination,
    manualSorting,
    pageCount: pageCount > 0 ? pageCount : undefined,
    getRowId: getRowId,
    initialState: {
      columnPinning: initialState?.columnPinning,
    },
  });

  return {
    table,
    sorting,
    setSorting,
    columnFilters,
    setColumnFilters,
    columnVisibility,
    setColumnVisibility,
    rowSelection,
    setRowSelection,
    pagination,
    setPagination,
  };
}
