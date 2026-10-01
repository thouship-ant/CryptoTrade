'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
} from '@/components/ui/pagination';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

function getPageWindow(current, total, size = 5) {
  if (total <= size) return Array.from({ length: total }, (_, i) => i + 1);
  let start = Math.max(1, current - Math.floor(size / 2));
  let end = start + size - 1;
  if (end > total) {
    end = total;
    start = end - size + 1;
  }
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

// Page-size dropdown shared by every paginated table. Only rendered when the caller
// passes pageSize/onPageSizeChange - purely additive, existing TablePagination callers
// that don't pass them are unaffected.
function PageSizeSelect({ pageSize, onPageSizeChange, pageSizeOptions }) {
  return (
    <Select value={String(pageSize)} onValueChange={(v) => onPageSizeChange(Number(v))}>
      <SelectTrigger className="h-8 w-[110px] sm:h-9 text-xs sm:text-sm gap-1">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {pageSizeOptions.map((size) => (
          <SelectItem key={size} value={String(size)}>
            {size} / page
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// Shared 5-box windowed pagination (Trade History, Symbol P&L, Admin Cashfree tab, ...),
// with an optional page-size dropdown when pageSize/onPageSizeChange are provided.
// PaginationLink renders as a plain <a>, so every click must preventDefault.
export default function TablePagination({
  page,
  totalPages,
  onPageChange,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [5, 10, 20, 50],
}) {
  const showPageSize = typeof pageSize === 'number' && typeof onPageSizeChange === 'function';
  // totalPages > 1 (not `totalPages && totalPages > 1`) - when totalPages is 0, that
  // `&&` short-circuits to the number 0 instead of false, and React renders a bare "0"
  // for any falsy-but-not-false/null/undefined JSX child.
  const showPager = totalPages > 1;

  if (!showPager && !showPageSize) return null;

  const pages = showPager ? getPageWindow(page, totalPages, 5) : [];

  const go = (target) => (e) => {
    e.preventDefault();
    if (target >= 1 && target <= totalPages && target !== page) onPageChange(target);
  };

  return (
    <div className="flex flex-col-reverse items-center justify-center gap-3 sm:flex-row sm:justify-between">
      {showPageSize ? (
        <PageSizeSelect pageSize={pageSize} onPageSizeChange={onPageSizeChange} pageSizeOptions={pageSizeOptions} />
      ) : (
        <div className="hidden sm:block sm:w-[110px]" />
      )}

      {showPager && (
        <Pagination className="sm:w-auto">
          <PaginationContent className="flex-wrap justify-center gap-1">
            <PaginationItem>
              <PaginationLink
                href="#"
                aria-label="Previous page"
                size="icon"
                className={`h-8 w-8 sm:h-9 sm:w-9 ${page <= 1 ? 'pointer-events-none opacity-40' : ''}`}
                onClick={go(page - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </PaginationLink>
            </PaginationItem>

            {pages[0] > 1 && (
              <PaginationItem className="hidden sm:block">
                <PaginationLink href="#" className="h-8 w-8 sm:h-9 sm:w-9 text-xs sm:text-sm" onClick={go(1)}>
                  1
                </PaginationLink>
              </PaginationItem>
            )}

            {pages.map((p) => (
              <PaginationItem key={p}>
                <PaginationLink
                  href="#"
                  isActive={p === page}
                  className="h-8 w-8 sm:h-9 sm:w-9 text-xs sm:text-sm"
                  onClick={go(p)}
                >
                  {p}
                </PaginationLink>
              </PaginationItem>
            ))}

            {pages[pages.length - 1] < totalPages && (
              <PaginationItem className="hidden sm:block">
                <PaginationLink href="#" className="h-8 w-8 sm:h-9 sm:w-9 text-xs sm:text-sm" onClick={go(totalPages)}>
                  {totalPages}
                </PaginationLink>
              </PaginationItem>
            )}

            <PaginationItem>
              <PaginationLink
                href="#"
                aria-label="Next page"
                size="icon"
                className={`h-8 w-8 sm:h-9 sm:w-9 ${page >= totalPages ? 'pointer-events-none opacity-40' : ''}`}
                onClick={go(page + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </PaginationLink>
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      {showPageSize && <div className="hidden sm:block sm:w-[110px]" />}
    </div>
  );
}
