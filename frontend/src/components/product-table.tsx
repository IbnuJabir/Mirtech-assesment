"use client";

import { DataTable } from "@/components/data-table";
import { DataTableColumnHeader } from "@/components/data-table-column-header";
import { DataTableToolbar } from "@/components/data-table-toolbar";
import { DataTableSkeleton } from "@/components/data-table-skeleton";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDataTable } from "@/hooks/use-data-table";

import type { Column, ColumnDef } from "@tanstack/react-table";
import {
  CheckCircle,
  DollarSign,
  MoreHorizontal,
  ShoppingCart,
  Tag,
} from "lucide-react";
import { parseAsArrayOf, parseAsString, useQueryState } from "nuqs";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchProducts } from "@/services/product-service";
import type { Product } from "@/types/product";

export function ProductTable() {
  // URL query parameters
  const [page, setPage] = useQueryState("page", parseAsString.withDefault("1"));
  const [limit, setLimit] = useQueryState(
    "limit",
    parseAsString.withDefault("10")
  );
  const [sortBy, setSortBy] = useQueryState(
    "sort_by",
    parseAsString.withDefault("id")
  );
  const [sortOrder, setSortOrder] = useQueryState(
    "sort_order",
    parseAsString.withDefault("asc")
  );
  const [search] = useQueryState("search", parseAsString.withDefault(""));
  const [category] = useQueryState(
    "category",
    parseAsArrayOf(parseAsString).withDefault([])
  );

  // Convert query parameters to the format expected by the API
  const queryParams = React.useMemo(() => {
    return {
      page: Number.parseInt(page),
      limit: Number.parseInt(limit),
      sort_by: sortBy,
      sort_order: sortOrder as "asc" | "desc",
      search: search || undefined,
      category: category.length > 0 ? category[0] : undefined,
    };
  }, [page, limit, sortBy, sortOrder, search, category]);

  // Fetch products using React Query
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["products", queryParams],
    queryFn: () => fetchProducts(queryParams),
    // keepPreviousData: true,
  });

  // Define table columns
  const columns = React.useMemo<ColumnDef<Product>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected() ||
              (table.getIsSomePageRowsSelected() && "indeterminate")
            }
            onCheckedChange={(value) =>
              table.toggleAllPageRowsSelected(!!value)
            }
            aria-label="Select all"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        ),
        size: 32,
        enableSorting: false,
        enableHiding: false,
      },
      {
        id: "id",
        accessorKey: "id",
        header: ({ column }: { column: Column<Product, unknown> }) => (
          <DataTableColumnHeader column={column} title="ID" />
        ),
        cell: ({ cell }) => <div>#{cell.getValue<number>()}</div>,
        size: 60,
      },
      {
        id: "name",
        accessorKey: "name",
        header: ({ column }: { column: Column<Product, unknown> }) => (
          <DataTableColumnHeader column={column} title="Name" />
        ),
        cell: ({ cell }) => (
          <div className="font-medium">{cell.getValue<string>()}</div>
        ),
        enableColumnFilter: true
      },
      {
        id: "category",
        accessorKey: "category",
        header: ({ column }: { column: Column<Product, unknown> }) => (
          <DataTableColumnHeader column={column} title="Category" />
        ),
        cell: ({ cell }) => {
          const category = cell.getValue<string>();
          return (
            <Badge variant="outline" className="capitalize">
              <Tag className="mr-1 h-3 w-3" />
              {category}
            </Badge>
          );
        },
        meta: {
          label: "Category",
          variant: "select",
          options: [
            // This would ideally be populated dynamically from your categories
            { label: "Electronics", value: "electronics", icon: CheckCircle },
            { label: "Clothing", value: "clothing", icon: CheckCircle },
            { label: "Home", value: "home", icon: CheckCircle },
            { label: "Books", value: "books", icon: CheckCircle },
            { label: "Toys", value: "toys", icon: CheckCircle },
          ],
        },
        enableColumnFilter: true,
      },
      {
        id: "price",
        accessorKey: "price",
        header: ({ column }: { column: Column<Product, unknown> }) => (
          <DataTableColumnHeader column={column} title="Price" />
        ),
        cell: ({ cell }) => {
          const price = cell.getValue<number>();
          return (
            <div className="flex items-center gap-1">
              <DollarSign className="size-4" />
              {price.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
          );
        },
      },
      {
        id: "stock_quantity",
        accessorKey: "stock_quantity",
        header: ({ column }: { column: Column<Product, unknown> }) => (
          <DataTableColumnHeader column={column} title="Stock" />
        ),
        cell: ({ cell }) => {
          const stock = cell.getValue<number>();
          return (
            <div className="flex items-center gap-1">
              <ShoppingCart className="size-4" />
              {stock}
            </div>
          );
        },
      },
      {
        id: "actions",
        cell: function Cell() {
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="sr-only">Open menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>View Details</DropdownMenuItem>
                <DropdownMenuItem>Edit</DropdownMenuItem>
                <DropdownMenuItem variant="destructive">
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
        size: 32,
      },
    ],
    []
  );

  // Handle pagination
  const handlePaginationChange = React.useCallback(
    (newPage: number) => {
      setPage(newPage.toString());
    },
    [setPage]
  );

  // Handle page size change
  const handlePageSizeChange = React.useCallback(
    (newPageSize: number) => {
      setLimit(newPageSize.toString());
      // Reset to page 1 when changing page size to avoid being on a non-existent page
      setPage("1");
    },
    [setLimit, setPage]
  );

  // Handle sorting - UPDATED
  const handleSortingChange = React.useCallback(
    (columnId: string, direction: "asc" | "desc") => {
      setSortBy(columnId);
      setSortOrder(direction);
    },
    [setSortBy, setSortOrder]
  );

  // Initialize the data table
  const { table } = useDataTable({
    data: data?.data || [],
    columns,
    pageCount: data ? Math.ceil(data.total_count / data.limit) : 1,
    manualPagination: true,
    manualSorting: true,
    onPaginationChange: handlePaginationChange,
    onPageSizeChange: handlePageSizeChange,
    onSortingChange: handleSortingChange,
    initialState: {
      pagination: {
        pageIndex: Number.parseInt(page) - 1,
        pageSize: Number.parseInt(limit),
      },
      sorting: [{ id: sortBy, desc: sortOrder === "desc" }],
      columnPinning: { left: ["select"], right: ["actions"] },
    },
    getRowId: (row) => row.id.toString(),
  });

  // Render loading state
  if (isLoading) {
    return (
      <DataTableSkeleton columnCount={7} rowCount={Number.parseInt(limit)} />
    );
  }

  // Render error state
  if (isError) {
    return (
      <div className="flex justify-center p-8 text-red-500">
        Error loading products:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  return (
    <div className="data-table-container">
      <DataTable table={table}>
        <DataTableToolbar table={table} searchPlaceholder="Search ..." />
      </DataTable>
    </div>
  );
}
