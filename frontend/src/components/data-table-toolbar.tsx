"use client";

import type React from "react";
import type { Table } from "@tanstack/react-table";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTableViewOptions } from "@/components/data-table-view-options";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

interface DataTableToolbarProps<TData> {
  table: Table<TData>;
  searchPlaceholder?: string;
}

export function DataTableToolbar<TData>({
  table,
  searchPlaceholder = "Search...",
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0;
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Get the current search value from URL
  const currentSearch = searchParams.get("search") || "";

  // Local state for input value
  const [searchValue, setSearchValue] = useState(currentSearch);
  // State to track if we're currently debouncing
  const [debouncedSearchValue, setDebouncedSearchValue] =
    useState(currentSearch);

  // Update local state when URL param changes (e.g., on navigation)
  useEffect(() => {
    setSearchValue(currentSearch);
    setDebouncedSearchValue(currentSearch);
  }, [currentSearch]);

  // Debounce search updates
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchValue(searchValue);
    }, 100); // 100ms debounce delay

    return () => clearTimeout(timer);
  }, [searchValue]);

  // Update URL when debounced value changes
  useEffect(() => {
    if (debouncedSearchValue !== currentSearch) {
      const params = new URLSearchParams(searchParams.toString());

      if (debouncedSearchValue) {
        params.set("search", debouncedSearchValue);
      } else {
        params.delete("search");
      }

      router.push(`${pathname}?${params.toString()}`);
    }
  }, [debouncedSearchValue, currentSearch, router, pathname, searchParams]);

  // Handle search input change (update local state only)
  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchValue(e.target.value);
    },
    []
  );

  // Handle search reset
  const handleResetSearch = useCallback(() => {
    setSearchValue("");
  }, []);

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center space-x-2">
        <div className="relative w-[150px] lg:w-[250px]">
          <Input
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={handleSearchChange}
            className="h-8"
          />
          {searchValue && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute right-0 top-0 h-8 w-8 p-0"
              onClick={handleResetSearch}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Clear search</span>
            </Button>
          )}
        </div>
        {isFiltered && (
          <Button
            variant="ghost"
            onClick={() => table.resetColumnFilters()}
            className="h-8 px-2 lg:px-3"
          >
            Reset
            <X className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  );
}
