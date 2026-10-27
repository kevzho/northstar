"use client";

/**
 * The enter transition every route gets, defined once.
 *
 * WHY A TEMPLATE AND NOT experimental.viewTransition. Next 16 ships a
 * `viewTransition` config flag that wires React's ViewTransition component into
 * the router, which would be the tidier answer, but it needs React's canary
 * channel and this app is on 19.2.4 stable. Upgrading React to canary 19 days
 * before a submission deadline, with a demo video still to record, buys a
 * slightly nicer crossfade at the cost of every other thing React touches.
 *
 * `template.tsx` is the stable equivalent: Next renders it between the layout
 * and the page and gives it a fresh key per navigation, so an enter animation
 * fires on every route change without a line of per-page code. One file, 22
 * routes.
 *
 * THE MOTION IS DELIBERATELY SMALL. 180ms and a 6px rise. A page transition is
 * latency the user did not ask for: anything long enough to admire is long
 * enough to be in the way, and this product's job is getting a student to a
 * deadline, not performing for them. The rise is upward because content arrives
 * from where the eye already is.
 *
 * REDUCED MOTION IS HANDLED, NOT MENTIONED. MotionConfig reducedMotion="user"
 * makes the library honour the OS setting, so a student who has asked their
 * machine to stop animating things gets an instant swap rather than a shorter
 * animation. The landing page already wraps itself the same way.
 */

import { MotionConfig, motion } from "motion/react";

export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18, ease: [0.22, 0.61, 0.36, 1] }}
      >
        {children}
      </motion.div>
    </MotionConfig>
  );
}
