"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  orientation?: "vertical" | "horizontal" | "both";
}

const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ className, children, orientation = "vertical", ...props }, ref) => {
    const scrollClass = cn(
      "relative overflow-hidden",
      orientation === "vertical" && "overflow-y-auto overflow-x-hidden",
      orientation === "horizontal" && "overflow-x-auto overflow-y-hidden",
      orientation === "both" && "overflow-auto",
      className
    );

    return (
      <div ref={ref} className={scrollClass} {...props}>
        {children}
      </div>
    );
  }
);

ScrollArea.displayName = "ScrollArea";

interface ScrollBarProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal";
  className?: string;
}

const ScrollBar = React.forwardRef<HTMLDivElement, ScrollBarProps>(
  ({ className, orientation = "vertical", ...props }, ref) => {
    const scrollbarClass = cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical" &&
        "h-full w-2.5 border-l border-l-transparent p-[1px]",
      orientation === "horizontal" &&
        "h-2.5 flex-col border-t border-t-transparent p-[1px]",
      className
    );

    const thumbClass = cn(
      "relative flex-1 rounded-full bg-border",
      orientation === "vertical" && "w-full min-h-[20px]",
      orientation === "horizontal" && "h-full min-w-[20px]"
    );

    return (
      <div ref={ref} className={scrollbarClass} {...props}>
        <div className={thumbClass} />
      </div>
    );
  }
);

ScrollBar.displayName = "ScrollBar";

export { ScrollArea, ScrollBar };
