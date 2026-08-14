"use client";

/**
 * Three.js sky — stars, galaxies, and planets behind the landing page.
 *
 * Three depth shells of soft star sprites drift slowly toward the viewer;
 * two faint spiral galaxies rotate almost imperceptibly; two shaded planets
 * (one ringed) hang in the middle distance. The camera leans a few degrees
 * with the pointer. Monochrome by design — brightness varies, hue never
 * does — and the `ink` prop flips the sky between starlight-on-black and
 * ink-on-paper for the light theme.
 *
 * Behavior notes:
 * - Renders nothing until mounted (no SSR canvas), and the page imports it
 *   through next/dynamic so three.js stays out of the initial bundle.
 * - prefers-reduced-motion: renders a single static frame, no loop.
 * - Pixel ratio capped at 2; everything disposed on unmount.
 */

import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function Starfield({
  className,
  ink = false,
}: {
  className?: string;
  /** true renders dark bodies for the light theme. */
  ink?: boolean;
}) {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const base = ink ? 0x141414 : 0xf2f2f2;
    const spriteRGB = ink ? "0,0,0" : "255,255,255";

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      60,
      mount.clientWidth / mount.clientHeight,
      0.1,
      160,
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

    const disposables: { dispose: () => void }[] = [renderer];

    // Deterministic placement: mulberry32, same seed as the horizon waves,
    // so the sky is Northstar's own rather than random each visit.
    let s = 20261103;
    const rand = () => {
      s += 0x6d2b79f5;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };

    function radialSprite(size: number, stops: [number, string][]) {
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        const g = ctx.createRadialGradient(
          size / 2, size / 2, 0,
          size / 2, size / 2, size / 2,
        );
        for (const [offset, color] of stops) g.addColorStop(offset, color);
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, size, size);
      }
      const texture = new THREE.CanvasTexture(canvas);
      disposables.push(texture);
      return texture;
    }

    // --- Stars: soft round glows on three depth shells -------------------
    const starTexture = radialSprite(64, [
      [0, `rgba(${spriteRGB},1)`],
      [0.4, `rgba(${spriteRGB},0.5)`],
      [1, `rgba(${spriteRGB},0)`],
    ]);

    const shells: THREE.Points[] = [];
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
      geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      const material = new THREE.PointsMaterial({
        color: base,
        map: starTexture,
        size: spec.size,
        sizeAttenuation: true,
        transparent: true,
        opacity: spec.opacity,
        depthWrite: false,
      });
      disposables.push(geometry, material);
      const points = new THREE.Points(geometry, material);
      scene.add(points);
      shells.push(points);
    }

    // --- Galaxies: two faint spirals painted on distant planes -----------
    function galaxyTexture() {
      const size = 256;
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.translate(size / 2, size / 2);
        // Core glow
        const core = ctx.createRadialGradient(0, 0, 0, 0, 0, size * 0.16);
        core.addColorStop(0, `rgba(${spriteRGB},0.9)`);
        core.addColorStop(1, `rgba(${spriteRGB},0)`);
        ctx.fillStyle = core;
        ctx.fillRect(-size / 2, -size / 2, size, size);
        // Two spiral arms drawn as fading dots along a logarithmic curve
        for (const armOffset of [0, Math.PI]) {
          for (let i = 0; i < 220; i += 1) {
            const progress = i / 220;
            const angle = armOffset + progress * 3.6 * Math.PI * 0.62;
            const radius = 6 + progress * size * 0.42;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius * 0.62;
            const alpha = 0.34 * (1 - progress) * (0.5 + rand() * 0.5);
            ctx.fillStyle = `rgba(${spriteRGB},${alpha.toFixed(3)})`;
            const dot = 1 + rand() * 2.1;
            ctx.beginPath();
            ctx.arc(x, y, dot, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      const texture = new THREE.CanvasTexture(canvas);
      disposables.push(texture);
      return texture;
    }

    const galaxies: THREE.Mesh[] = [];
    const galaxySpecs = [
      { x: -46, y: 20, z: -70, scale: 34, tilt: 0.9, opacity: 0.34 },
      { x: 52, y: -18, z: -85, scale: 26, tilt: -0.6, opacity: 0.26 },
    ];
    for (const spec of galaxySpecs) {
      const geometry = new THREE.PlaneGeometry(spec.scale, spec.scale);
      const material = new THREE.MeshBasicMaterial({
        map: galaxyTexture(),
        transparent: true,
        opacity: spec.opacity,
        depthWrite: false,
      });
      disposables.push(geometry, material);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(spec.x, spec.y, spec.z);
      mesh.rotation.x = spec.tilt;
      scene.add(mesh);
      galaxies.push(mesh);
    }

    // --- Planets: two shaded spheres, one ringed -------------------------
    const keyLight = new THREE.DirectionalLight(0xffffff, ink ? 1.6 : 2.4);
    keyLight.position.set(-30, 22, 20);
    scene.add(keyLight);
    scene.add(new THREE.AmbientLight(0xffffff, ink ? 0.7 : 0.25));

    const planetMaterial = new THREE.MeshStandardMaterial({
      color: ink ? 0xdcdcdc : 0x8a8a8a,
      roughness: 0.9,
      metalness: 0,
    });
    disposables.push(planetMaterial);

    const planets: THREE.Mesh[] = [];

    const planetA = new THREE.Mesh(
      new THREE.SphereGeometry(3.2, 40, 40),
      planetMaterial,
    );
    disposables.push(planetA.geometry);
    planetA.position.set(18, 26, -58);
    scene.add(planetA);
    planets.push(planetA);

    const planetB = new THREE.Mesh(
      new THREE.SphereGeometry(1.9, 36, 36),
      planetMaterial,
    );
    disposables.push(planetB.geometry);
    planetB.position.set(-60, -36, -60);
    scene.add(planetB);
    planets.push(planetB);

    const ringGeometry = new THREE.RingGeometry(2.9, 4.4, 64);
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: base,
      transparent: true,
      opacity: 0.32,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    disposables.push(ringGeometry, ringMaterial);
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.position.copy(planetB.position);
    ring.rotation.x = Math.PI / 2.4;
    ring.rotation.y = 0.35;
    scene.add(ring);

    // --- Interaction and loop -------------------------------------------
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
      // Slow star drift toward the viewer, wrapped so the sky never empties.
      for (let i = 0; i < shells.length; i += 1) {
        const shell = shells[i];
        shell.position.z = ((frame * 0.008 * (i + 1)) % 80);
        if (shell.position.z > 40) shell.position.z -= 80;
      }
      // Galaxies rotate on geological time; planets barely turn.
      galaxies[0].rotation.z += 0.0004;
      galaxies[1].rotation.z -= 0.0003;
      for (const planet of planets) planet.rotation.y += 0.0008;
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
      for (const disposable of disposables) disposable.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [ink]);

  return <div ref={mountRef} aria-hidden="true" className={className} />;
}
