"use client";

import { useEffect, useRef, useState } from "react";
import { animate } from "framer-motion";

export function AnimatedNumber({
  value,
  format,
  className = "",
}: {
  value: number | null | undefined;
  format: (v: number) => string;
  className?: string;
}) {
  const [display, setDisplay] = useState<string>("—");
  const prev = useRef(0);

  useEffect(() => {
    if (value == null) {
      setDisplay("—");
      return;
    }
    const controls = animate(prev.current, value, {
      duration: 0.7,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(format(v)),
    });
    prev.current = value;
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <span className={className}>{display}</span>;
}
