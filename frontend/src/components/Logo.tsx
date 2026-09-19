export function Logo({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 36 36" className={className} aria-hidden="true">
      <rect width="36" height="36" rx="9" className="fill-zinc-950 dark:fill-white" />
      <g className="stroke-white dark:stroke-zinc-950" strokeWidth="2" strokeLinecap="round" fill="none">
        <path d="M18 5v8M14.5 7l7 4M14.5 11l7-4" strokeWidth="1.6" />
        <path d="M8 17h20" />
        <path d="M10 22h16" opacity=".75" />
        <path d="M12 27h12" opacity=".5" />
      </g>
    </svg>
  );
}
