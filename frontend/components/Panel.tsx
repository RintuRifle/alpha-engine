"use client";

import { motion } from "framer-motion";

export function Panel({
  title,
  right,
  children,
  className = "",
  delay = 0,
}: {
  title?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      className={`panel ${className}`}
    >
      {(title || right) && (
        <header className="flex items-center justify-between px-3 py-2 border-b border-line">
          <h3 className="microlabel">{title}</h3>
          {right}
        </header>
      )}
      <div className="p-3">{children}</div>
    </motion.section>
  );
}
