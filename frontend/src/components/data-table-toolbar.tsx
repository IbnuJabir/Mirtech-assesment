"use client";

import type React from "react";
import type { Column, Table } from "@tanstack/react-table";
import { Check, Filter, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTableViewOptions } from "@/components/data-table-view-options";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { DataTableDateFilter } from "@/components/data-table-date-filter";
import { DataTableFacetedFilter } from "@/components/data-table-faceted-filter";
import { DataTableSliderFilter } from "@/components/data-table-slider-filter";

interface DataTableToolbarProps<TData> {
  table: Table<TData>;
  searchPlaceholder?: string;
  categories?: {
    label: string;
    value: string;
    icon?: React.ComponentType<{ className?: string }>;
  }[];
}

export function DataTableToolbar<TData>({
  table,
  searchPlaceholder = "Search...",
  categories = [],
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0;
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Get the current search value from URL
  const currentSearch = searchParams.get("search") || "";

  // Get the current category filter from URL
  const currentCategory = searchParams.get("category") || "";

  // Local state for input value
  const [searchValue, setSearchValue] = useState(currentSearch);
  // State to track if we're currently debouncing
  const [debouncedSearchValue, setDebouncedSearchValue] =
    useState(currentSearch);

  // State for selected categories
  const [selectedCategory, setSelectedCategory] = useState(currentCategory);

  // Get all columns that can be filtered
  const columns = useMemo(
    () => table.getAllColumns().filter((column) => column.getCanFilter()),
    [table]
  );

  // Update local state when URL param changes (e.g., on navigation)
  useEffect(() => {
    setSearchValue(currentSearch);
    setDebouncedSearchValue(currentSearch);
    setSelectedCategory(currentCategory);
  }, [currentSearch, currentCategory]);

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

  // Handle category selection
  const handleCategorySelect = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());

      if (value === selectedCategory) {
        // If clicking the same category, deselect it
        params.delete("category");
        setSelectedCategory("");
      } else {
        // Otherwise select the new category
        params.set("category", value);
        setSelectedCategory(value);
      }

      // Reset to page 1 when changing filters
      params.set("page", "1");

      router.push(`${pathname}?${params.toString()}`);
    },
    [selectedCategory, searchParams, router, pathname]
  );

  // Handle reset all filters
  const handleResetAll = useCallback(() => {
    const params = new URLSearchParams();

    // Keep other params that aren't filters
    for (const [key, value] of Array.from(searchParams.entries())) {
      if (!["search", "category", "page"].includes(key)) {
        params.set(key, value);
      }
    }

    // Reset to page 1
    params.set("page", "1");

    router.push(`${pathname}?${params.toString()}`);
    setSearchValue("");
    setSelectedCategory("");
    table.resetColumnFilters();
  }, [searchParams, router, pathname, table]);

  const hasActiveFilters = !!searchValue || !!selectedCategory || isFiltered;

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center justify-between py-4">
      <div className="flex flex-1 flex-wrap items-center space-x-2">
        <div className="relative w-full sm:w-[250px] lg:w-[300px]">
          <Input
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={handleSearchChange}
            className="h-9"
          />
          {searchValue && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute right-0 top-0 h-9 w-9 p-0"
              onClick={handleResetSearch}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Clear search</span>
            </Button>
          )}
        </div>

        {/* Column Filters */}
        {columns.map((column) => (
          <DataTableToolbarFilter key={column.id} column={column} />
        ))}

        {categories.length > 0 && (
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="h-9 border-dashed">
                <Filter className="mr-2 h-4 w-4" />
                Category
                {selectedCategory && (
                  <>
                    <Separator orientation="vertical" className="mx-2 h-4" />
                    <Badge
                      variant="secondary"
                      className="rounded-sm px-1 font-normal"
                    >
                      {categories.find((c) => c.value === selectedCategory)
                        ?.label || selectedCategory}
                    </Badge>
                  </>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0" align="start">
              <Command>
                <CommandInput placeholder="Search category..." />
                <CommandList>
                  <CommandEmpty>No category found.</CommandEmpty>
                  <CommandGroup>
                    {categories.map((category) => {
                      const isSelected = selectedCategory === category.value;
                      return (
                        <CommandItem
                          key={category.value}
                          onSelect={() => handleCategorySelect(category.value)}
                          className="flex items-center"
                        >
                          <div
                            className={cn(
                              "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                              isSelected
                                ? "bg-primary text-primary-foreground"
                                : "opacity-50 [&_svg]:invisible"
                            )}
                          >
                            <Check className={cn("h-4 w-4")} />
                          </div>
                          {category.icon && (
                            <category.icon className="mr-2 h-4 w-4 text-muted-foreground" />
                          )}
                          <span>{category.label}</span>
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                  {selectedCategory && (
                    <>
                      <CommandSeparator />
                      <CommandGroup>
                        <CommandItem
                          onSelect={() =>
                            handleCategorySelect(selectedCategory)
                          }
                          className="justify-center text-center"
                        >
                          Clear filter
                        </CommandItem>
                      </CommandGroup>
                    </>
                  )}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        )}

        {hasActiveFilters && (
          <Button
            variant="ghost"
            onClick={handleResetAll}
            className="h-9 px-2 lg:px-3"
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

// Added from paste.txt - Column filter component
interface DataTableToolbarFilterProps<TData> {
  column: Column<TData>;
}

function DataTableToolbarFilter<TData>({
  column,
}: DataTableToolbarFilterProps<TData>) {
  const columnMeta = column.columnDef.meta;

  const onFilterRender = useCallback(() => {
    if (!columnMeta?.variant) return null;

    switch (columnMeta.variant) {
      case "text":
        return (
          <Input
            placeholder={columnMeta.placeholder ?? columnMeta.label}
            value={(column.getFilterValue() as string) ?? ""}
            onChange={(event) => column.setFilterValue(event.target.value)}
            className="h-8 w-40 lg:w-56"
          />
        );

      case "number":
        return (
          <div className="relative">
            <Input
              type="number"
              inputMode="numeric"
              placeholder={columnMeta.placeholder ?? columnMeta.label}
              value={(column.getFilterValue() as string) ?? ""}
              onChange={(event) => column.setFilterValue(event.target.value)}
              className={cn("h-8 w-[120px]", columnMeta.unit && "pr-8")}
            />
            {columnMeta.unit && (
              <span className="absolute top-0 right-0 bottom-0 flex items-center rounded-r-md bg-accent px-2 text-muted-foreground text-sm">
                {columnMeta.unit}
              </span>
            )}
          </div>
        );

      case "range":
        return (
          <DataTableSliderFilter
            column={column}
            title={columnMeta.label ?? column.id}
          />
        );

      case "date":
      case "dateRange":
        return (
          <DataTableDateFilter
            column={column}
            title={columnMeta.label ?? column.id}
            multiple={columnMeta.variant === "dateRange"}
          />
        );

      case "select":
      case "multiSelect":
        return (
          <DataTableFacetedFilter
            column={column}
            title={columnMeta.label ?? column.id}
            options={columnMeta.options ?? []}
            multiple={columnMeta.variant === "multiSelect"}
          />
        );

      default:
        return null;
    }
  }, [column, columnMeta]);

  return onFilterRender();
}
