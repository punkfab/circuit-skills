// Pan and zoom an <svg> by rewriting its viewBox: wheel or trackpad pinch zooms
// about the cursor, drag pans, double-click fits.

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export class PanZoom {
  private observer: ResizeObserver;
  private box: Box;
  private home: Box;
  private drag: { id: number; x: number; y: number; box: Box } | null = null;

  constructor(
    private svg: SVGSVGElement,
    home: Box,
  ) {
    this.home = { ...home };
    this.box = { ...home };
    this.apply();
    svg.addEventListener("wheel", (e) => this.onWheel(e), { passive: false });
    svg.addEventListener("pointerdown", (e) => this.onDown(e));
    svg.addEventListener("pointermove", (e) => this.onMove(e));
    svg.addEventListener("pointerup", (e) => this.onUp(e));
    svg.addEventListener("pointercancel", (e) => this.onUp(e));
    svg.addEventListener("dblclick", () => this.fit());
    this.observer = new ResizeObserver(() => this.apply());
    this.observer.observe(svg);
  }

  snapshot(): Box { return { ...this.box }; }
  restore(box: Box) { this.box = { ...box }; this.apply(); }
  dispose() { this.observer.disconnect(); }

  /** Show the whole home box. */
  fit() {
    this.box = { ...this.home };
    this.apply();
  }

  /** Centre on a point (in viewBox units), showing about `span` units across. */
  focus(x: number, y: number, span: number) {
    const aspect = this.box.h / this.box.w;
    this.box = { x: x - span / 2, y: y - (span * aspect) / 2, w: span, h: span * aspect };
    this.apply();
  }

  setHome(home: Box) {
    this.home = { ...home };
    this.fit();
  }

  /** Units of the viewBox per screen pixel (for sizing markers). */
  unitsPerPixel(): number {
    const r = this.svg.getBoundingClientRect();
    return r.width ? Math.max(this.box.w / r.width, this.box.h / Math.max(1, r.height)) : 1;
  }

  onChange: (() => void) | null = null;

  private apply() {
    const { x, y, w, h } = this.box;
    this.svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
    this.onChange?.();
  }

  /** Screen point -> viewBox point, honouring preserveAspectRatio="xMidYMid meet". */
  private toUnits(clientX: number, clientY: number): [number, number] {
    const r = this.svg.getBoundingClientRect();
    const scale = Math.max(this.box.w / r.width, this.box.h / r.height);
    const ox = (r.width * scale - this.box.w) / 2;
    const oy = (r.height * scale - this.box.h) / 2;
    return [this.box.x - ox + (clientX - r.left) * scale, this.box.y - oy + (clientY - r.top) * scale];
  }

  private onWheel(e: WheelEvent) {
    e.preventDefault();
    // Pinch arrives as ctrl+wheel with small deltas; a mouse wheel as larger steps.
    const k = Math.exp((e.ctrlKey ? e.deltaY * 0.01 : e.deltaY * 0.0015) * (e.deltaMode === 1 ? 16 : 1));
    const [ux, uy] = this.toUnits(e.clientX, e.clientY);
    const w = Math.min(this.home.w * 8, Math.max(this.home.w / 400, this.box.w * k));
    const s = w / this.box.w;
    this.box = { x: ux - (ux - this.box.x) * s, y: uy - (uy - this.box.y) * s, w, h: this.box.h * s };
    this.apply();
  }

  private onDown(e: PointerEvent) {
    if (e.button !== 0) return;
    this.drag = { id: e.pointerId, x: e.clientX, y: e.clientY, box: { ...this.box } };
    this.svg.setPointerCapture(e.pointerId);
    this.svg.classList.add("dragging");
  }

  private onMove(e: PointerEvent) {
    if (!this.drag || e.pointerId !== this.drag.id) return;
    const r = this.svg.getBoundingClientRect();
    const scale = Math.max(this.drag.box.w / r.width, this.drag.box.h / r.height);
    this.box = { ...this.drag.box, x: this.drag.box.x - (e.clientX - this.drag.x) * scale, y: this.drag.box.y - (e.clientY - this.drag.y) * scale };
    this.apply();
  }

  private onUp(e: PointerEvent) {
    if (!this.drag || e.pointerId !== this.drag.id) return;
    this.drag = null;
    this.svg.classList.remove("dragging");
  }
}
