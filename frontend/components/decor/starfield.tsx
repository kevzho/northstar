"use client";

/**
 * Three.js starfield — the sky behind the landing page.
 *
 * ~1,400 white points on three depth shells drift slowly toward the viewer
 * and lean a few degrees with the pointer, so the page floats in a sky that
 * is alive but never busy. Monochrome by design: brightness varies, hue
 * never does.
 *
 * Behavior notes:
 * - Renders nothing until mounted (no SSR canvas), and the page imports it
 *   through next/dynamic so three.js stays out of the initial bundle.
 * - prefers-reduced-motion: renders a single static frame, no loop.
 * - Pixel ratio capped at 2; everything disposed on unmount.
 */

import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function Starfield({ className }: { className?: string }) {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      60,
      mount.clientWidth / mount.clientHeight,
      0.1,
      120,
    );
    camera.position.z = 40;

    const renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: true,
      powerPreference: "low-power",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    // Deterministic star placement: mulberry32, same seed as the horizon
    // waves, so the sky is Northstar's own rather than random each visit.
    let s = 20261103;
    const rand = () => {
      s += 0x6d2b79f5;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    // Soft circular sprite so points render as glows, not squares.
    const sprite = document.createElement("canvas");
    sprite.width = 64;
    sprite.height = 64;
    const ctx = sprite.getContext("2d");
    if (ctx) {
      const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
      gradient.addColorStop(0, "rgba(255,255,255,1)");
      gradient.addColorStop(0.4, "rgba(255,255,255,0.5)");
      gradient.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 64, 64);
    }
    const starTexture = new THREE.CanvasTexture(sprite);

    const shells: THREE.Points[] = [];
    const geometries: THREE.BufferGeometry[] = [];
    const materials: THREE.PointsMaterial[] = [];

    // Three depth shells: far/dim/small → near/bright/large. Sparse enough
    // that the sky stays behind the words, never on top of them.
    const shellSpecs = [
      { count: 420, spread: 90, size: 0.5, opacity: 0.28 },
      { count: 230, spread: 70, size: 0.8, opacity: 0.45 },
      { count: 80, spread: 50, size: 1.2, opacity: 0.7 },
    ];

    for (const spec of shellSpecs) {
      const positions = new Float32Array(spec.count * 3);
      for (let i = 0; i < spec.count; i += 1) {
        positions[i * 3] = (rand() - 0.5) * spec.spread * 2;
        positions[i * 3 + 1] = (rand() - 0.5) * spec.spread * 1.2;
        positions[i * 3 + 2] = -rand() * 80;
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(positions, 3),
      );
      const material = new THREE.PointsMaterial({
        color: 0xf2f2f2,
        map: starTexture,
        size: spec.size,
        sizeAttenuation: true,
        transparent: true,
        opacity: spec.opacity,
        depthWrite: false,
      });
      const points = new THREE.Points(geometry, material);
      scene.add(points);
      shells.push(points);
      geometries.push(geometry);
      materials.push(material);
    }

    let pointerX = 0;
    let pointerY = 0;
    function onPointerMove(event: PointerEvent) {
      pointerX = (event.clientX / window.innerWidth - 0.5) * 2;
      pointerY = (event.clientY / window.innerHeight - 0.5) * 2;
    }

    function onResize() {
      if (!mount) return;
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    }

    let frame = 0;
    let raf = 0;
    function tick() {
      frame += 1;
      // Slow drift toward the viewer, wrapped so the sky never empties.
      for (let i = 0; i < shells.length; i += 1) {
        const shell = shells[i];
        shell.position.z = ((frame * 0.008 * (i + 1)) % 80);
        if (shell.position.z > 40) shell.position.z -= 80;
      }
      // Pointer lean, eased so it feels like weight rather than tracking.
      camera.rotation.y += (pointerX * -0.03 - camera.rotation.y) * 0.05;
      camera.rotation.x += (pointerY * -0.02 - camera.rotation.x) * 0.05;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    }

    window.addEventListener("resize", onResize);
    if (reduceMotion) {
      renderer.render(scene, camera);
    } else {
      window.addEventListener("pointermove", onPointerMove);
      raf = requestAnimationFrame(tick);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointerMove);
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) material.dispose();
      starTexture.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={mountRef} aria-hidden="true" className={className} />;
}
