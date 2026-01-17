"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { PLYLoader } from "three-stdlib";
import { DRACOLoader } from "three-stdlib";
import { getWorlds, World } from "../lib/api-client";

const SKIP_RATIO = 10;

export default function GameViewer() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [loading, setLoading] = useState(false);
    const [score, setScore] = useState(0);
    const [gameActive, setGameActive] = useState(false);
    const [isPaused, setIsPaused] = useState(true);
    const [uploadVisible, setUploadVisible] = useState(true);
    
    // Source selection state
    const [sourceMode, setSourceMode] = useState<'initial' | 'upload' | 'select'>('initial');
    const [worldsList, setWorldsList] = useState<World[]>([]);
    const [selectedWorld, setSelectedWorld] = useState<World | null>(null);
    const [loadingWorlds, setLoadingWorlds] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string>("");

    // Refs for game state to avoid closure staleness in loop
    const gameStateRef = useRef({
        gameActive: false,
        isPaused: true,
        score: 0,
        enemies: [] as THREE.Mesh[],
        keys: { w: false, a: false, s: false, d: false },
        lastSpawnTime: 0,
        camera: null as THREE.PerspectiveCamera | null,
        scene: null as THREE.Scene | null,
        renderer: null as THREE.WebGLRenderer | null,
    });

    useEffect(() => {
        if (!containerRef.current) return;

        // --- Init Three.js ---
        const width = 800; // Fixed size as per original, or could be responsive
        const height = 600;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x050505);
        scene.fog = new THREE.FogExp2(0x050505, 0.3);

        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 80);

        const renderer = new THREE.WebGLRenderer({
            antialias: false,
            powerPreference: "high-performance",
        });
        renderer.setSize(width, height);
        renderer.setPixelRatio(1);

        containerRef.current.appendChild(renderer.domElement);

        gameStateRef.current.scene = scene;
        gameStateRef.current.camera = camera;
        gameStateRef.current.renderer = renderer;

        // --- Inputs ---
        const handleKeyDown = (e: KeyboardEvent) => {
            const key = e.key.toLowerCase();
            if (key in gameStateRef.current.keys) {
                gameStateRef.current.keys[key as keyof typeof gameStateRef.current.keys] = true;
            }
        };

        const handleKeyUp = (e: KeyboardEvent) => {
            const key = e.key.toLowerCase();
            if (key in gameStateRef.current.keys) {
                gameStateRef.current.keys[key as keyof typeof gameStateRef.current.keys] = false;
            }
        };

        const handleMouseMove = (event: MouseEvent) => {
            if (gameStateRef.current.isPaused || !gameStateRef.current.gameActive) return;

            const sensitivity = 0.002;
            const movementX = event.movementX || 0;
            const movementY = event.movementY || 0;

            const qY = new THREE.Quaternion();
            qY.setFromAxisAngle(new THREE.Vector3(0, 1, 0), -movementX * sensitivity);
            camera.quaternion.premultiply(qY);

            const qX = new THREE.Quaternion();
            qX.setFromAxisAngle(new THREE.Vector3(1, 0, 0), -movementY * sensitivity);
            camera.quaternion.multiply(qX);
        };

        const handlePointerLockChange = () => {
            if (document.pointerLockElement === renderer.domElement) {
                gameStateRef.current.isPaused = false;
                setIsPaused(false);
            } else {
                gameStateRef.current.isPaused = true;
                setIsPaused(true);
            }
        };

        const handleMouseDown = (e: MouseEvent) => {
            if (!gameStateRef.current.isPaused && gameStateRef.current.gameActive && e.button === 0) {
                shoot();
            }
        }

        const handleClick = () => {
            if (gameStateRef.current.gameActive && gameStateRef.current.isPaused) {
                renderer.domElement.requestPointerLock();
            }
        }

        window.addEventListener("keydown", handleKeyDown);
        window.addEventListener("keyup", handleKeyUp);
        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("pointerlockchange", handlePointerLockChange);
        document.addEventListener("mousedown", handleMouseDown);
        renderer.domElement.addEventListener("click", handleClick);

        // --- Game Functions ---
        const spawnEnemy = (time: number) => {
            const state = gameStateRef.current;
            if (state.isPaused || !state.gameActive) return;
            if (time - state.lastSpawnTime < 1200) return;
            state.lastSpawnTime = time;

            const geometry = new THREE.BoxGeometry(0.06, 0.06, 0.06);
            const material = new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
            const enemy = new THREE.Mesh(geometry, material);

            const angle = Math.random() * Math.PI * 2;
            const radius = 2.0;
            const height = 0.2 + Math.random() * 0.4;

            enemy.position.set(
                camera.position.x + Math.cos(angle) * radius,
                height,
                camera.position.z + Math.sin(angle) * radius
            );
            scene.add(enemy);
            state.enemies.push(enemy);
        };

        const shoot = () => {
            const state = gameStateRef.current;
            const raycaster = new THREE.Raycaster();
            raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
            const intersects = raycaster.intersectObjects(state.enemies);

            if (intersects.length > 0) {
                const hitEnemy = intersects[0].object as THREE.Mesh;
                scene.remove(hitEnemy);
                state.enemies.splice(state.enemies.indexOf(hitEnemy), 1);
                state.score += 100;
                setScore(state.score);
            }
        };

        const updateGame = () => {
            const state = gameStateRef.current;
            if (state.isPaused || !state.gameActive) return;

            const speed = 0.015;
            for (let i = state.enemies.length - 1; i >= 0; i--) {
                const enemy = state.enemies[i];
                enemy.lookAt(camera.position);
                enemy.translateZ(speed);
                enemy.rotateZ(0.05);

                if (enemy.position.distanceTo(camera.position) < 0.1) {
                    scene.remove(enemy);
                    state.enemies.splice(i, 1);
                    state.score = Math.max(0, state.score - 50);
                    setScore(state.score);
                }
            }
        };

        const handleMovement = () => {
            const state = gameStateRef.current;
            if (state.isPaused || !state.gameActive) return;

            const moveSpeed = 0.04;
            const maxDistance = 0.8;
            const dir = new THREE.Vector3();
            const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
            const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
            forward.y = 0;
            right.y = 0;
            forward.normalize();
            right.normalize();

            if (state.keys.w) dir.add(forward);
            if (state.keys.s) dir.sub(forward);
            if (state.keys.d) dir.add(right);
            if (state.keys.a) dir.sub(right);

            if (dir.length() > 0) {
                dir.normalize().multiplyScalar(moveSpeed);
                const nextPos = camera.position.clone().add(dir);
                if (nextPos.length() < maxDistance) {
                    camera.position.add(dir);
                }
            }
        };

        // --- Loop ---
        let frameId = 0;
        const animate = (time: number) => {
            frameId = requestAnimationFrame(animate);
            handleMovement();
            spawnEnemy(time);
            updateGame();
            renderer.render(scene, camera);
        };
        animate(0);

        // Cleanup
        return () => {
            cancelAnimationFrame(frameId);
            window.removeEventListener("keydown", handleKeyDown);
            window.removeEventListener("keyup", handleKeyUp);
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("pointerlockchange", handlePointerLockChange);
            document.removeEventListener("mousedown", handleMouseDown);
            if (renderer.domElement) {
                renderer.domElement.removeEventListener("click", handleClick);
                renderer.domElement.remove();
            }
            renderer.dispose();
            // Dispose scene objects if needed, simplified here
        };
    }, []); // Run once on mount

    // --- API Functions ---
    const fetchWorlds = async () => {
        setLoadingWorlds(true);
        setErrorMessage("");
        try {
            const worlds = await getWorlds();
            setWorldsList(worlds);
            setSourceMode('select');
        } catch (error) {
            setErrorMessage(error instanceof Error ? error.message : "Failed to load worlds");
            console.error("Error fetching worlds:", error);
        } finally {
            setLoadingWorlds(false);
        }
    };

    const loadWorldFromApi = async (world: World) => {
        setLoading(true);
        setErrorMessage("");
        const state = gameStateRef.current;

        // Clear old non-enemy objects
        if (state.scene) {
            for (let i = state.scene.children.length - 1; i >= 0; i--) {
                const child = state.scene.children[i];
                if (!state.enemies.includes(child as THREE.Mesh)) {
                    state.scene.remove(child);
                    // Dispose geometry and material to free GPU memory
                    if (child instanceof THREE.Points || child instanceof THREE.Mesh) {
                        if (child.geometry) child.geometry.dispose();
                        if (child.material) {
                            if (Array.isArray(child.material)) {
                                child.material.forEach(m => m.dispose());
                            } else {
                                child.material.dispose();
                            }
                        }
                    }
                }
            }
        }

        try {
            const plyLoader = new PLYLoader();
            const plyUrls = world.ply_urls;
            
            // Parallel fetch all PLY files
            const fetchPromises = plyUrls.map(async (url) => {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`Failed to download PLY file: ${response.statusText}`);
                }
                return response.arrayBuffer();
            });

            const buffers = await Promise.all(fetchPromises);
            
            // Process each geometry
            const processAndAddGeometry = (originalGeometry: THREE.BufferGeometry) => {
                const positions = originalGeometry.attributes.position;
                const colors = originalGeometry.attributes.color;

                const newPositions = [];
                const newColors = [];

                for (let i = 0; i < positions.count; i += SKIP_RATIO) {
                    newPositions.push(positions.getX(i), positions.getY(i), positions.getZ(i));
                    if (colors) {
                        newColors.push(colors.getX(i), colors.getY(i), colors.getZ(i));
                    }
                }

                const simplifiedGeometry = new THREE.BufferGeometry();
                simplifiedGeometry.setAttribute(
                    "position",
                    new THREE.Float32BufferAttribute(newPositions, 3)
                );
                if (colors) {
                    simplifiedGeometry.setAttribute(
                        "color",
                        new THREE.Float32BufferAttribute(newColors, 3)
                    );
                }

                const material = new THREE.PointsMaterial({
                    vertexColors: !!colors,
                    color: 0xffffff,
                    size: 0.04,
                    sizeAttenuation: true,
                });

                const points = new THREE.Points(simplifiedGeometry, material);
                points.rotateX(-Math.PI / 2);
                points.rotateZ(-Math.PI / 2);

                if (state.scene) state.scene.add(points);
            };

            // Load and process all geometries
            buffers.forEach((buffer) => {
                const geometry = plyLoader.parse(buffer);
                processAndAddGeometry(geometry);
            });

            // Start game
            setLoading(false);
            setUploadVisible(false);
            setGameActive(true);
            setIsPaused(true);
            gameStateRef.current.gameActive = true;
            gameStateRef.current.isPaused = true;
            if (gameStateRef.current.camera) {
                gameStateRef.current.camera.position.set(0, 0.5, 0);
            }
        } catch (error) {
            setLoading(false);
            setErrorMessage(error instanceof Error ? error.message : "Failed to load world");
            console.error("Error loading world from API:", error);
        }
    };

    // --- File Upload Logic ---
    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        setLoading(true);
        let loadedCount = 0;
        const state = gameStateRef.current;

        // Clear old non-enemy objects
        if (state.scene) {
            for (let i = state.scene.children.length - 1; i >= 0; i--) {
                const child = state.scene.children[i];
                if (!state.enemies.includes(child as THREE.Mesh)) {
                    state.scene.remove(child);
                    // Dispose geometry and material to free GPU memory
                    if (child instanceof THREE.Points || child instanceof THREE.Mesh) {
                        if (child.geometry) child.geometry.dispose();
                        if (child.material) {
                            if (Array.isArray(child.material)) {
                                child.material.forEach(m => m.dispose());
                            } else {
                                child.material.dispose();
                            }
                        }
                    }
                }
            }
        }

        const plyLoader = new PLYLoader();
        const dracoLoader = new DRACOLoader();
        dracoLoader.setDecoderPath("https://www.gstatic.com/draco/versioned/decoders/1.5.6/"); // Use CDN for Draco

        const processAndAddGeometry = (originalGeometry: THREE.BufferGeometry) => {
            const positions = originalGeometry.attributes.position;
            const colors = originalGeometry.attributes.color;

            const newPositions = [];
            const newColors = [];

            for (let i = 0; i < positions.count; i += SKIP_RATIO) {
                newPositions.push(positions.getX(i), positions.getY(i), positions.getZ(i));
                if (colors) {
                    newColors.push(colors.getX(i), colors.getY(i), colors.getZ(i));
                }
            }

            const simplifiedGeometry = new THREE.BufferGeometry();
            simplifiedGeometry.setAttribute(
                "position",
                new THREE.Float32BufferAttribute(newPositions, 3)
            );
            if (colors) {
                simplifiedGeometry.setAttribute(
                    "color",
                    new THREE.Float32BufferAttribute(newColors, 3)
                );
            }

            const material = new THREE.PointsMaterial({
                vertexColors: !!colors,
                color: 0xffffff,
                size: 0.04,
                sizeAttenuation: true,
            });

            const points = new THREE.Points(simplifiedGeometry, material);
            points.rotateX(-Math.PI / 2);
            points.rotateZ(-Math.PI / 2);

            if (state.scene) state.scene.add(points);
        };

        Array.from(files).forEach((file) => {
            const reader = new FileReader();
            reader.onload = (event) => {
                if (!event.target?.result) return;
                const buffer = event.target.result as ArrayBuffer;

                const onGeometryReady = (geometry: THREE.BufferGeometry) => {
                    processAndAddGeometry(geometry);
                    loadedCount++;
                    if (loadedCount === files.length) {
                        setLoading(false);
                        setUploadVisible(false);
                        setGameActive(true);
                        setIsPaused(true);
                        gameStateRef.current.gameActive = true;
                        gameStateRef.current.isPaused = true; // Start paused, let user click to play
                        if (gameStateRef.current.camera) {
                            gameStateRef.current.camera.position.set(0, 0.5, 0);
                        }
                    }
                };

                if (file.name.endsWith(".ply")) {
                    setTimeout(() => {
                        onGeometryReady(plyLoader.parse(buffer));
                    }, 50);
                } else if (file.name.endsWith(".drc")) {
                    const blob = new Blob([buffer]);
                    const url = URL.createObjectURL(blob);
                    dracoLoader.load(url, (geometry) => {
                        onGeometryReady(geometry);
                        URL.revokeObjectURL(url);
                    });
                }
            };
            reader.readAsArrayBuffer(file);
        });
    };

    const handleStartClick = () => {
        if (gameStateRef.current.renderer) {
            gameStateRef.current.renderer.domElement.requestPointerLock();
        }
    };

    return (
        <div className="flex justify-center items-center h-screen bg-slate-950 text-cyan-50 select-none font-mono overflow-hidden relative">
            {/* Background Grid Effect */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />

            <div className="flex relative z-10 bg-slate-900/80 backdrop-blur-md p-6 rounded-xl border border-cyan-500/20 shadow-[0_0_50px_rgba(6,182,212,0.15)] gap-6">

                {/* Game Screen Container */}
                <div className="relative w-[800px] h-[600px] bg-black border border-cyan-900/50 shadow-inner rounded-sm overflow-hidden group">

                    {/* Corner Accents */}
                    <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-cyan-500/50 z-20 pointer-events-none" />
                    <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-cyan-500/50 z-20 pointer-events-none" />
                    <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-cyan-500/50 z-20 pointer-events-none" />
                    <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-cyan-500/50 z-20 pointer-events-none" />

                    {/* 3D Container */}
                    <div ref={containerRef} className="w-full h-full block" />

                    {/* Upload Overlay */}
                    {uploadVisible && (
                        <div className="absolute inset-0 bg-slate-950/90 flex flex-col justify-center items-center z-30 p-8 text-center backdrop-blur-sm">
                            {/* Initial: Choose Source */}
                            {sourceMode === 'initial' && (
                                <>
                                    <h2 className="text-cyan-400 text-3xl mb-2 font-bold tracking-widest uppercase drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                                        Initialize World
                                    </h2>
                                    <p className="text-slate-400 mb-8 text-sm">Choose your data source</p>

                                    <div className="flex flex-col gap-4 w-full max-w-md">
                                        <button
                                            onClick={() => setSourceMode('upload')}
                                            className="group relative px-8 py-4 bg-cyan-950/50 border border-cyan-500/50 hover:bg-cyan-900/50 hover:border-cyan-400 text-cyan-300 font-bold uppercase tracking-wider transition-all duration-300 hover:shadow-[0_0_20px_rgba(6,182,212,0.3)]"
                                        >
                                            <span className="relative z-10 flex items-center justify-center gap-2">
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                                                Upload Files
                                            </span>
                                        </button>

                                        <button
                                            onClick={fetchWorlds}
                                            disabled={loadingWorlds}
                                            className="group relative px-8 py-4 bg-green-950/50 border border-green-500/50 hover:bg-green-900/50 hover:border-green-400 text-green-300 font-bold uppercase tracking-wider transition-all duration-300 hover:shadow-[0_0_20px_rgba(34,197,94,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <span className="relative z-10 flex items-center justify-center gap-2">
                                                {loadingWorlds ? (
                                                    <>
                                                        <div className="w-5 h-5 border-2 border-green-300 border-t-transparent rounded-full animate-spin" />
                                                        Loading...
                                                    </>
                                                ) : (
                                                    <>
                                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                                                        Select Generated World
                                                    </>
                                                )}
                                            </span>
                                        </button>
                                    </div>

                                    {errorMessage && (
                                        <div className="mt-4 text-red-400 text-sm">
                                            {errorMessage}
                                        </div>
                                    )}
                                </>
                            )}

                            {/* Upload Mode */}
                            {sourceMode === 'upload' && (
                                <>
                                    <h2 className="text-cyan-400 text-3xl mb-2 font-bold tracking-widest uppercase drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                                        Upload Files
                                    </h2>
                                    <p className="text-slate-400 mb-8 text-sm">Upload point cloud data (.ply / .drc) to generate combat simulation.</p>

                                    <label htmlFor="file-input" className="group relative px-8 py-4 bg-cyan-950/50 border border-cyan-500/50 hover:bg-cyan-900/50 hover:border-cyan-400 text-cyan-300 font-bold uppercase tracking-wider cursor-pointer transition-all duration-300 hover:shadow-[0_0_20px_rgba(6,182,212,0.3)] clip-path-polygon">
                                        <span className="relative z-10 flex items-center gap-2">
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                                            Load Data
                                        </span>
                                    </label>
                                    <input
                                        id="file-input"
                                        type="file"
                                        accept=".ply,.drc"
                                        multiple
                                        className="hidden"
                                        onChange={handleFileUpload}
                                    />
                                    
                                    <button
                                        onClick={() => setSourceMode('initial')}
                                        className="mt-4 px-4 py-2 text-slate-400 hover:text-cyan-300 text-sm transition-colors"
                                    >
                                        ← Back
                                    </button>

                                    {loading && (
                                        <div className="mt-8 flex flex-col items-center">
                                            <div className="w-64 h-1 bg-slate-800 rounded-full overflow-hidden">
                                                <div className="w-full h-full bg-cyan-500 animate-progress-indeterminate origin-left" />
                                            </div>
                                            <p className="mt-2 text-cyan-500/70 text-xs animate-pulse">OPTIMIZING & LOADING NEURAL CLOUD...</p>
                                        </div>
                                    )}
                                </>
                            )}

                            {/* Select Mode: World Selection */}
                            {sourceMode === 'select' && (
                                <div className="w-full h-full flex flex-col">
                                    <h2 className="text-cyan-400 text-2xl mb-6 font-bold tracking-widest uppercase drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                                        Select Generated World
                                    </h2>

                                    <div className="flex-1 flex gap-6 overflow-hidden">
                                        {/* Left: Theme List */}
                                        <div className="w-1/3 flex flex-col gap-2 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-cyan-500/50 scrollbar-track-slate-800">
                                            <div className="text-cyan-500/70 text-xs uppercase tracking-widest mb-2">Available Themes</div>
                                            {worldsList.length === 0 ? (
                                                <div className="text-slate-500 text-sm">No worlds available</div>
                                            ) : (
                                                worldsList.map((world) => (
                                                    <button
                                                        key={world.id}
                                                        onClick={() => setSelectedWorld(world)}
                                                        className={`px-4 py-3 text-left border transition-all duration-200 ${
                                                            selectedWorld?.id === world.id
                                                                ? 'bg-cyan-900/50 border-cyan-400 text-cyan-100'
                                                                : 'bg-slate-900/50 border-slate-700 text-slate-300 hover:border-cyan-500/50'
                                                        }`}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            {selectedWorld?.id === world.id && (
                                                                <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                                                            )}
                                                            <div>
                                                                <div className="font-bold text-sm">{world.theme}</div>
                                                                <div className="text-xs text-slate-500">{new Date(world.created_at).toLocaleDateString()}</div>
                                                            </div>
                                                        </div>
                                                    </button>
                                                ))
                                            )}
                                        </div>

                                        {/* Right: PNG Preview */}
                                        <div className="flex-1 flex flex-col bg-slate-900/30 border border-slate-700 rounded p-4">
                                            <div className="text-cyan-500/70 text-xs uppercase tracking-widest mb-2">Preview</div>
                                            {selectedWorld ? (
                                                <div className="flex-1 flex items-center justify-center">
                                                    <img
                                                        src={selectedWorld.png_url}
                                                        alt={`${selectedWorld.theme} preview`}
                                                        className="max-w-full max-h-full object-contain rounded border border-cyan-500/20"
                                                    />
                                                </div>
                                            ) : (
                                                <div className="flex-1 flex items-center justify-center text-slate-600">
                                                    Select a theme to preview
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Bottom: Actions */}
                                    <div className="mt-6 flex gap-4 justify-between">
                                        <button
                                            onClick={() => {
                                                setSourceMode('initial');
                                                setSelectedWorld(null);
                                            }}
                                            className="px-6 py-3 bg-slate-800 border border-slate-600 text-slate-300 hover:border-slate-500 transition-all"
                                        >
                                            ← Back
                                        </button>

                                        <button
                                            onClick={() => selectedWorld && loadWorldFromApi(selectedWorld)}
                                            disabled={!selectedWorld || loading}
                                            className="px-8 py-3 bg-green-950/50 border border-green-500/50 hover:bg-green-900/50 hover:border-green-400 text-green-300 font-bold uppercase tracking-wider transition-all duration-300 hover:shadow-[0_0_20px_rgba(34,197,94,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {loading ? (
                                                <span className="flex items-center gap-2">
                                                    <div className="w-4 h-4 border-2 border-green-300 border-t-transparent rounded-full animate-spin" />
                                                    Loading...
                                                </span>
                                            ) : (
                                                'Load World'
                                            )}
                                        </button>
                                    </div>

                                    {errorMessage && (
                                        <div className="mt-4 text-red-400 text-sm text-center">
                                            {errorMessage}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Pause Overlay */}
                    {!uploadVisible && isPaused && (
                        <div
                            className="absolute inset-0 bg-slate-950/80 backdrop-blur-[2px] text-cyan-50 flex flex-col justify-center items-center z-20 cursor-pointer hover:bg-slate-950/70 transition-colors"
                            onClick={handleStartClick}
                        >
                            <h1 className="text-4xl mb-4 font-bold tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.3)]">
                                SYSTEM PAUSED
                            </h1>
                            <div className="px-6 py-2 border border-cyan-500/30 bg-cyan-950/30 rounded text-cyan-300 text-sm tracking-widest animate-pulse">
                                CLICK TO ENGAGE
                            </div>
                            <p className="mt-4 text-slate-500 text-xs">PRESS ESC TO ABORT/PAUSE</p>
                        </div>
                    )}

                    {/* Game UI */}
                    {!uploadVisible && !isPaused && (
                        <div className="absolute inset-0 pointer-events-none z-10 p-4">
                            {/* Reticle */}
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                                <div className="w-4 h-4 border border-red-500/80 rounded-full flex items-center justify-center">
                                    <div className="w-0.5 h-0.5 bg-red-400 rounded-full" />
                                </div>
                            </div>

                            {/* HUD Top Right */}
                            <div className="absolute top-4 right-4 flex flex-col items-end">
                                <div className="text-xs text-cyan-500/70 uppercase tracking-widest mb-1">Combat Score</div>
                                <div className="text-4xl font-black text-cyan-400 tracking-tighter drop-shadow-[0_0_5px_rgba(34,211,238,0.5)] tabular-nums">
                                    {score.toString().padStart(6, '0')}
                                </div>
                            </div>

                            {/* HUD Bottom Left */}
                            <div className="absolute bottom-4 left-4">
                                <div className="flex items-center gap-2 text-xs text-cyan-700">
                                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                    SYSTEM ONLINE
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Sidebar */}
                <div className="w-[300px] flex flex-col gap-4">
                    {/* Title Panel */}
                    <div className="bg-slate-800/50 p-5 rounded-lg border border-cyan-500/10 backdrop-blur-sm relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-cyan-500/10 to-transparent pointer-events-none" />
                        <h2 className="text-cyan-400 text-lg font-bold mb-2 uppercase tracking-wide border-b border-cyan-500/20 pb-2">
                            Mission Brief
                        </h2>
                        <p className="text-slate-400 text-xs leading-relaxed">
                            Navigate the <span className="text-cyan-200">Hunyuan 3D Point Cloud</span> digital construct. Eliminate recursive anomalies (Red Targets).
                            <br /><br />
                            Data optimization active: <span className="text-green-400">90% decimation</span> for performance.
                        </p>
                    </div>

                    {/* Controls Panel */}
                    <div className="bg-slate-800/50 p-5 rounded-lg border border-cyan-500/10 backdrop-blur-sm flex-1">
                        <h3 className="text-red-400 text-sm font-bold mb-4 uppercase tracking-wide border-b border-red-500/20 pb-2">
                            Manual Override
                        </h3>
                        <ul className="space-y-3">
                            <li className="flex items-center justify-between group">
                                <span className="text-slate-400 text-xs uppercase group-hover:text-cyan-300 transition-colors">Fire</span>
                                <span className="bg-slate-700/80 px-2 py-1 rounded text-[10px] font-bold text-slate-200 border border-slate-600 min-w-[50px] text-center">CLICK</span>
                            </li>
                            <li className="flex items-center justify-between group">
                                <span className="text-slate-400 text-xs uppercase group-hover:text-cyan-300 transition-colors">Pause</span>
                                <span className="bg-slate-700/80 px-2 py-1 rounded text-[10px] font-bold text-slate-200 border border-slate-600 min-w-[50px] text-center">ESC</span>
                            </li>
                            <li className="flex items-center justify-between group">
                                <span className="text-slate-400 text-xs uppercase group-hover:text-cyan-300 transition-colors">Look</span>
                                <span className="bg-slate-700/80 px-2 py-1 rounded text-[10px] font-bold text-slate-200 border border-slate-600 min-w-[50px] text-center">MOUSE</span>
                            </li>
                            <li className="flex items-center justify-between group">
                                <span className="text-slate-400 text-xs uppercase group-hover:text-cyan-300 transition-colors">Thrusters</span>
                                <span className="bg-slate-700/80 px-2 py-1 rounded text-[10px] font-bold text-slate-200 border border-slate-600 min-w-[50px] text-center">WASD</span>
                            </li>
                        </ul>
                    </div>

                    {/* Footer Status */}
                    <div className="text-[10px] text-slate-600 flex justify-between uppercase tracking-widest font-bold">
                        <span>Ver 2.5.0</span>
                        <span>Link: Stable</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
