/**
 * Langent Nebula — Three.js 3D Vector Universe
 * ================================================
 * Renders vector embeddings as cosmic nebula point clouds.
 * UMAP-reduced 3D coordinates from ChromaDB.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
// ─── Globals ─────────────────────────────
var scene, camera, renderer, controls;
var pointCloud = null;
var graphGroup = null;
var crossLinksGroup = null;
var raycaster, mouse;
var allPoints = [];
var highlightedIds = new Set();
var nodePositions = {}; // Global node positions map
var pointPositions = {}; // Global point positions map
var ws = null;
var clock = null;

const COLORS = {
    '.md': new THREE.Color(0xb794f4),  // Vibrant Lavender
    '.txt': new THREE.Color(0xd6bcfa), // Light Lavender
    '.pdf': new THREE.Color(0x9f7aea), // True Purple
    '.csv': new THREE.Color(0x805ad5), // Deep Purple
    '.json': new THREE.Color(0x6b46c1), // Dark Purple
    '.yaml': new THREE.Color(0xb388ff), // Bright Lavender
    default: new THREE.Color(0xdcd3ff), // Soft Lavender
};

const GRAPH_LABEL_COLORS = {
    Identity: 0xd6bcfa,
    Domain: 0xe9d8fd,
    Technology: 0xb794f4,
    Company: 0x9f7aea,
    Achievement: 0x805ad5,
    Role: 0xb388ff,
    Value: 0xffccff,
    default: 0xdcd3ff,
};

// ─── Startup ─────────────────────────────
function startup() {
    try {
        console.log("🌌 Nebula: Initializing...");
        setConnectionStatus('loading');
        init();
        animate();
        loadNebula();
        connectWebSocket();
    } catch (err) {
        console.error('Nebula Critical Error:', err);
        showHUDError(err.message);
    }
}

if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', startup);
} else {
    startup();
}

function showHUDError(msg) {
    const el = document.getElementById('connection-status');
    el.textContent = '❌ Error: ' + msg;
    el.style.color = '#ff4444';

    const hoverInfo = document.getElementById('hover-info');
    hoverInfo.textContent = "Check browser console for details. " + msg;
}


function init() {
    // Clock init
    clock = new THREE.Clock();

    // Scene
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000005, 0.004);

    // Camera
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.set(60, 40, 80);

    // Renderer
    const canvas = document.getElementById('nebula-canvas');
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000005);

    // Controls (orbit around the nebula)
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = 0.5;
    controls.zoomSpeed = 0.8;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.3;

    // Raycaster for hover/click
    raycaster = new THREE.Raycaster();
    raycaster.params.Points.threshold = 1.5;
    mouse = new THREE.Vector2();

    // Ambient starfield background
    createStarfield();

    // Core glow (center of universe)
    createCoreGlow();

    // Events
    window.addEventListener('resize', onResize);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('click', onClick);
    document.getElementById('search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doSearch();
    });
}

// ─── Background Stars ────────────────────
function createStarfield() {
    const geo = new THREE.BufferGeometry();
    const count = 8000;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
        const i3 = i * 3;
        positions[i3] = (Math.random() - 0.5) * 800;
        positions[i3 + 1] = (Math.random() - 0.5) * 800;
        positions[i3 + 2] = (Math.random() - 0.5) * 800;

        const brightness = 0.3 + Math.random() * 0.7;
        colors[i3] = brightness;
        colors[i3 + 1] = brightness;
        colors[i3 + 2] = brightness * (0.8 + Math.random() * 0.4);
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
        size: 0.6,
        vertexColors: true,
        transparent: true,
        opacity: 0.6,
        sizeAttenuation: true,
    });

    scene.add(new THREE.Points(geo, mat));
}

// ─── Core Glow ───────────────────────────
function createCoreGlow() {
    const geo = new THREE.SphereGeometry(2, 32, 32);
    const mat = new THREE.MeshBasicMaterial({
        color: 0xb794f4,
        transparent: true,
        opacity: 0.15,
    });
    const core = new THREE.Mesh(geo, mat);
    scene.add(core);

    // Glow sphere
    const glowMat = new THREE.MeshBasicMaterial({
        color: 0x805ad5,
        transparent: true,
        opacity: 0.04,
    });
    const glow = new THREE.Mesh(new THREE.SphereGeometry(8, 32, 32), glowMat);
    scene.add(glow);
}

// ─── Load Nebula Data ────────────────────
async function loadNebula() {
    try {
        const resp = await fetch('/api/nebula');
        const data = await resp.json();
        renderPointCloud(data.points);
        renderGraph(data.graph);
        renderCrossLinks(data.cross_links);
        updateStats(data.stats);
        setConnectionStatus('connected');
    } catch (err) {
        console.error('Failed to load nebula:', err);
        setConnectionStatus('error');
    }
}

// ─── Render Point Cloud ──────────────────
function renderPointCloud(points) {
    console.log(`🌌 Rendering ${points?.length || 0} points...`);
    if (pointCloud) scene.remove(pointCloud);
    allPoints = points;

    if (!points || points.length === 0) {
        console.warn("No points to render.");
        return;
    }

    const count = points.length;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
        const p = points[i];
        const i3 = i * 3;

        positions[i3] = p.x;
        positions[i3 + 1] = p.y;
        positions[i3 + 2] = p.z;

        // Color by file extension
        const ext = (p.source || '').split('.').pop();
        const color = COLORS['.' + ext] || COLORS.default;

        // Special Highlight for Alex AI / 이용욱 (Hot Pink)
        const preview = (p.document_preview || '').toLowerCase();
        const isAlex = preview.includes('alex ai') || preview.includes('이용욱');
        const hotPink = new THREE.Color(0xff69b4);

        if (highlightedIds.has(p.id)) {
            colors[i3] = 1.0;
            colors[i3 + 1] = 1.0;
            colors[i3 + 2] = 1.0;
        } else if (isAlex) {
            colors[i3] = hotPink.r;
            colors[i3 + 1] = hotPink.g;
            colors[i3 + 2] = hotPink.b;
        } else {
            colors[i3] = color.r;
            colors[i3 + 1] = color.g;
            colors[i3 + 2] = color.b;
        }

        // Store positions for cross-linking
        pointPositions[p.id] = new THREE.Vector3(p.x, p.y, p.z);
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Fallback to simple PointsMaterial for stability
    const mat = new THREE.PointsMaterial({
        size: 1.5,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        sizeAttenuation: true
    });

    pointCloud = new THREE.Points(geo, mat);
    scene.add(pointCloud);
    console.log("✅ Point cloud added to scene.");
}

// ─── Render Graph Overlay ────────────────
function renderGraph(graphData) {
    if (graphGroup) scene.remove(graphGroup);
    graphGroup = new THREE.Group();
    nodePositions = {}; // Reset

    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return;
    const count = graphData.nodes.length;

    // Position graph nodes in a spherical shell around the point cloud
    graphData.nodes.forEach((node, i) => {
        const phi = Math.acos(-1 + (2 * i) / count);
        const theta = Math.sqrt(count * Math.PI) * phi;
        const r = 45 + Math.random() * 10;

        const x = r * Math.cos(theta) * Math.sin(phi);
        const y = r * Math.sin(theta) * Math.sin(phi);
        const z = r * Math.cos(phi);

        nodePositions[node.id] = new THREE.Vector3(x, y, z);

        // Node sphere
        const color = GRAPH_LABEL_COLORS[node.label] || GRAPH_LABEL_COLORS.default;
        const geo = new THREE.SphereGeometry(0.8, 12, 12);
        const mat = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.6,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(x, y, z);
        mesh.userData = node;
        graphGroup.add(mesh);
    });

    // Edges
    graphData.edges.forEach((edge) => {
        const src = nodePositions[edge.source];
        const dst = nodePositions[edge.target];
        if (!src || !dst) return;

        const geo = new THREE.BufferGeometry().setFromPoints([src, dst]);
        const mat = new THREE.LineBasicMaterial({
            color: 0xd6bcfa,
            transparent: true,
            opacity: 0.45,
        });
        graphGroup.add(new THREE.Line(geo, mat));
    });

    scene.add(graphGroup);
}

// ─── Search ──────────────────────────────
window.doSearch = async function () {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    try {
        const resp = await fetch(`/api/nebula/search?q=${encodeURIComponent(query)}&top_k=20`);
        const data = await resp.json();

        // Highlight results
        allPoints = data.points; // Update with latest points from server
        highlightedIds = new Set(data.results.map(r => r.id));
        renderPointCloud(allPoints);

        // Show Results Panel
        const panel = document.getElementById('results-panel');
        const list = document.getElementById('results-list');
        list.innerHTML = '';
        panel.classList.remove('hidden');

        data.results.forEach(res => {
            const item = document.createElement('div');
            item.className = 'result-item';
            const source = res.metadata?.source || 'unknown';
            const preview = (res.document || res.preview || '').substring(0, 80);

            item.innerHTML = `
                <div class="title">${source}</div>
                <div class="meta">${preview}...</div>
            `;

            item.onclick = () => {
                showInfo(res.id, source, res.document || res.preview || '');
                flyToPoint(res.id);
            };
            list.appendChild(item);
        });

        document.getElementById('hover-info').textContent =
            `Found ${data.results.length} results for "${query}"`;
    } catch (err) {
        console.error('Search error:', err);
    }
};

window.closeResults = function () {
    document.getElementById('results-panel').classList.add('hidden');
};

function flyToPoint(id) {
    const pos = pointPositions[id];
    if (!pos) return;

    // Stop auto-rotate
    controls.autoRotate = false;

    // Tween-like movement using controls.target
    const targetPos = new THREE.Vector3(pos.x, pos.y, pos.z);

    // We use a simple approach: move target and camera
    // For a smoother experience, we can just update controls.target
    controls.target.copy(targetPos);

    // Position camera at a comfortable distance
    const offset = new THREE.Vector3(15, 10, 15);
    camera.position.copy(targetPos).add(offset);

    camera.lookAt(targetPos);
}

// ─── Ingest ──────────────────────────────
window.doIngest = async function () {
    document.getElementById('ingest-btn').textContent = '⏳ Ingesting...';
    try {
        const resp = await fetch('/api/ingest', { method: 'POST' });
        const data = await resp.json();
        document.getElementById('hover-info').textContent =
            `Ingested: ${data.files_scanned} files → ${data.vectors_added} vectors`;
        // Reload nebula
        await loadNebula();
    } catch (err) {
        console.error('Ingest error:', err);
    }
    document.getElementById('ingest-btn').textContent = '📥 Ingest';
};

window.doLink = async function () {
    const btn = document.getElementById('link-btn');
    btn.textContent = '⏳ Linking...';
    try {
        const resp = await fetch('/api/link', { method: 'POST' });
        const data = await resp.json();
        document.getElementById('hover-info').textContent =
            `Linked ${data.chunks_linked} chunks to graph entities!`;
        await loadNebula();
    } catch (err) {
        console.error('Link error:', err);
    }
    btn.textContent = '🔗 Link';
};

window.closeInfo = function () {
    document.getElementById('info-panel').classList.add('hidden');
};

// ─── Hover / Click ───────────────────────
function onMouseMove(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    if (pointCloud) {
        const intersects = raycaster.intersectObject(pointCloud);
        if (intersects.length > 0) {
            const idx = intersects[0].index;
            if (idx < allPoints.length) {
                const p = allPoints[idx];
                document.getElementById('hover-info').textContent =
                    `📄 ${p.source || 'unknown'} — ${p.preview?.substring(0, 60) || ''}...`;
                document.body.style.cursor = 'pointer';
            }
        } else {
            document.body.style.cursor = 'default';
        }
    }
}

function onClick(event) {
    raycaster.setFromCamera(mouse, camera);
    if (pointCloud) {
        const intersects = raycaster.intersectObject(pointCloud);
        if (intersects.length > 0) {
            const idx = intersects[0].index;
            if (idx < allPoints.length) {
                const p = allPoints[idx];
                showInfo(p.id, p.source, p.preview);
                controls.autoRotate = false;
            }
        }
    }
}

function showInfo(title, source, preview) {
    document.getElementById('info-title').textContent = title;
    document.getElementById('info-source').textContent = `📂 ${source}`;
    document.getElementById('info-preview').textContent = preview;
    document.getElementById('info-panel').classList.remove('hidden');
}

// ─── Render Cross-Links ───────────────────
function renderCrossLinks(links) {
    if (crossLinksGroup) scene.remove(crossLinksGroup);
    crossLinksGroup = new THREE.Group();

    if (!links || links.length === 0) return;
    console.log(`🔗 Rendering ${links.length} cross-links...`);

    links.forEach(link => {
        const ptPos = pointPositions[link.source];
        const nodePos = nodePositions[link.target];
        if (!ptPos || !nodePos) return;

        const geo = new THREE.BufferGeometry().setFromPoints([ptPos, nodePos]);
        const mat = new THREE.LineBasicMaterial({
            color: 0xd6bcfa,
            transparent: true,
            opacity: 0.35,
        });
        crossLinksGroup.add(new THREE.Line(geo, mat));
    });

    scene.add(crossLinksGroup);
}

// ─── WebSocket ───────────────────────────
function connectWebSocket() {
    try {
        ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onopen = () => setConnectionStatus('connected');
        ws.onclose = () => {
            setConnectionStatus('disconnected');
            setTimeout(connectWebSocket, 3000);
        };
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'nebula_update') {
                renderPointCloud(msg.data.points);
                renderGraph(msg.data.graph);
                updateStats(msg.data.stats);
            }
        };
    } catch (e) {
        setConnectionStatus('error');
    }
}

// ─── Helpers ─────────────────────────────
function updateStats(stats) {
    document.getElementById('stat-vectors').textContent = `${stats.total_vectors} vectors`;
    document.getElementById('stat-nodes').textContent = `${stats.total_graph_nodes} nodes`;
    document.getElementById('stat-edges').textContent = `${stats.total_graph_edges} edges`;
}

function setConnectionStatus(status) {
    const el = document.getElementById('connection-status');
    if (status === 'connected') {
        el.textContent = '● Connected';
        el.style.color = '#00ff88';
    } else if (status === 'loading') {
        el.textContent = '● Loading Universe...';
        el.style.color = '#00f0ff';
    } else if (status === 'disconnected') {
        el.textContent = '○ Disconnected';
        el.style.color = '#ff6644';
    } else {
        el.textContent = '○ Error';
        el.style.color = '#ff4444';
    }
}

function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// ─── Animation Loop ─────────────────────

function animate() {
    requestAnimationFrame(animate);
    if (!clock || !renderer || !scene || !camera) return;

    var elapsed = clock.getElapsedTime();

    controls.update();

    // Pulse point cloud shader
    if (pointCloud && pointCloud.material.uniforms && pointCloud.material.uniforms.time) {
        pointCloud.material.uniforms.time.value = elapsed;
    }

    // Slowly rotate graph overlay
    if (graphGroup) {
        graphGroup.rotation.y = elapsed * 0.02;
    }

    renderer.render(scene, camera);
}
