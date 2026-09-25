import { MercatorCoordinate, type CustomLayerInterface, type CustomRenderMethodInput, type Map as WorldMap } from 'maplibre-gl';
import * as THREE from 'three';
import type { WorldAtom } from './atomsAdapter';

// MapLibre owns the camera. This custom layer shares its WebGL context and depth buffer.
export class ThreeAtoms implements CustomLayerInterface {
  id = 'punkto-atoms';
  type = 'custom' as const;
  renderingMode = '3d' as const;
  private map!: WorldMap;
  private renderer!: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.Camera();
  private origin = MercatorCoordinate.fromLngLat([12.5683, 55.6761]);
  private unit = this.origin.meterInMercatorCoordinateUnits();
  private root = new THREE.Group();
  private targets: THREE.Mesh[] = [];
  private selected: string | null = null;
  private projectionReady = false;
  private sphere = new THREE.SphereGeometry(1, 24, 16);
  private column = new THREE.CylinderGeometry(1, 1, 1, 16);
  private ring = new THREE.TorusGeometry(1, 0.025, 8, 48);

  onAdd(map: WorldMap, gl: WebGLRenderingContext | WebGL2RenderingContext) {
    this.map = map;
    this.renderer = new THREE.WebGLRenderer({ canvas: map.getCanvas(), context: gl, antialias: true });
    this.renderer.autoClear = false;
    this.scene.add(this.root, new THREE.AmbientLight(0xffffff, 2));
    const light = new THREE.DirectionalLight(0xffeedb, 3);
    light.position.set(-200, -300, 500);
    this.scene.add(light);
  }

  setAtoms(atoms: WorldAtom[]) {
    this.clear();
    for (const atom of atoms) {
      const coordinate = MercatorCoordinate.fromLngLat([atom.x, atom.y]);
      const group = new THREE.Group();
      group.position.set((coordinate.x - this.origin.x) / this.unit, (coordinate.y - this.origin.y) / this.unit, 0);
      // Adjust metre units for each atom's latitude; altitude is always metres above flat ground.
      group.scale.setScalar(coordinate.meterInMercatorCoordinateUnits() / this.unit);
      const orb = new THREE.Mesh(this.sphere, new THREE.MeshStandardMaterial({
        color: atom.color, emissive: atom.color, emissiveIntensity: 0.65, roughness: 0.35, metalness: 0.15,
      }));
      orb.position.z = atom.altitudeM;
      orb.userData.atom = atom;
      group.add(orb);
      this.targets.push(orb);
      const halo = new THREE.Mesh(this.sphere, new THREE.MeshBasicMaterial({ color: atom.color, transparent: true, opacity: 0.09, depthWrite: false, side: THREE.BackSide }));
      halo.position.z = atom.altitudeM;
      halo.userData.halo = true;
      group.add(halo);
      const beam = new THREE.Mesh(this.column, new THREE.MeshBasicMaterial({ color: atom.color, transparent: true, opacity: 0.3, depthWrite: false }));
      beam.rotation.x = Math.PI / 2;
      beam.scale.set(0.6, atom.altitudeM, 0.6);
      beam.position.z = atom.altitudeM / 2;
      group.add(beam);
      const ring = new THREE.Mesh(this.ring, new THREE.MeshBasicMaterial({ color: atom.color, transparent: true, opacity: 0.45, depthWrite: false }));
      ring.position.z = 0.25;
      ring.scale.setScalar(7);
      group.add(ring);
      this.root.add(group);
    }
    this.map?.triggerRepaint();
  }

  select(id: string | null) { this.selected = id; this.map?.triggerRepaint(); }

  pick(x: number, y: number): WorldAtom | undefined {
    if (!this.projectionReady) return;
    const canvas = this.map.getCanvas();
    const nx = x / canvas.clientWidth * 2 - 1;
    const ny = 1 - y / canvas.clientHeight * 2;
    const inverse = this.camera.projectionMatrix.clone().invert();
    const near = new THREE.Vector3(nx, ny, -1).applyMatrix4(inverse);
    const far = new THREE.Vector3(nx, ny, 1).applyMatrix4(inverse);
    const ray = new THREE.Raycaster(near, far.sub(near).normalize());
    // Intersect real 3D spheres, including their modest halo for easier touch selection.
    const hit = ray.intersectObjects(this.root.children, true).find(h => h.object.userData.atom || h.object.userData.halo);
    if (!hit) return;
    return hit.object.userData.atom ?? hit.object.parent?.children.find(child => child.userData.atom)?.userData.atom;
  }

  render(_gl: WebGLRenderingContext | WebGL2RenderingContext, args: CustomRenderMethodInput) {
    const model = new THREE.Matrix4().makeTranslation(this.origin.x, this.origin.y, this.origin.z)
      .scale(new THREE.Vector3(this.unit, this.unit, this.unit));
    this.camera.projectionMatrix.fromArray(args.defaultProjectionData.mainMatrix).multiply(model);
    this.projectionReady = true;
    // Keep distant objects readable while preserving their true altitude and geographic position.
    const radius = Math.max(2.5, Math.min(18, 4 * 2 ** (15 - this.map.getZoom())));
    for (const orb of this.targets) {
      const selected = orb.userData.atom.id === this.selected;
      orb.scale.setScalar(radius * (selected ? 1.3 : 1));
      (orb.material as THREE.MeshStandardMaterial).emissiveIntensity = selected ? 1.4 : 0.65;
      orb.parent!.children.find(child => child.userData.halo)!.scale.setScalar(radius * (selected ? 2.4 : 1.9));
    }
    this.renderer.resetState();
    this.renderer.render(this.scene, this.camera);
  }

  private clear() {
    this.root.traverse(object => {
      if (object instanceof THREE.Mesh) {
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach(material => material.dispose());
      }
    });
    this.root.clear();
    this.targets = [];
  }
  onRemove() {
    this.clear();
    this.sphere.dispose(); this.column.dispose(); this.ring.dispose();
    this.renderer.dispose();
  }
}
