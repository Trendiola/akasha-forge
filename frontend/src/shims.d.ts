/// <reference types="react-scripts" />

// Ambient shims for JS/JSX modules (shadcn/ui components and JS helpers)
// so TypeScript treats their exports as `any` without type-checking .jsx files.
declare module "@/components/ui/*";
declare module "@/lib/utils";
declare module "@/hooks/*";

declare module "*.css";
