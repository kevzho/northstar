'use client';
/**
 * Vendored from motion-primitives (ibelick/motion-primitives, MIT), with the
 * polymorphic `as` prop dropped, every call site here renders a span, and
 * React 19's types reject the original `motion.create(as)` cast.
 */
import { cn } from '@/lib/utils';
import { SpringOptions, motion, useSpring, useTransform } from 'motion/react';
import { useEffect } from 'react';

export type AnimatedNumberProps = {
  value: number;
  className?: string;
  springOptions?: SpringOptions;
};

export function AnimatedNumber({
  value,
  className,
  springOptions,
}: AnimatedNumberProps) {
  const spring = useSpring(value, springOptions);
  const display = useTransform(spring, (current) =>
    Math.round(current).toLocaleString()
  );

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return (
    <motion.span className={cn('tabular-nums', className)}>
      {display}
    </motion.span>
  );
}
