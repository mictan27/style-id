/**
 * A fake style.id API backed by fixtures exported from the real FastAPI service
 * (`services/api/scripts/export_mobile_fixtures.py`). Pure TypeScript with no React
 * Native imports, so Jest (screen tests) and Playwright (web screenshots) share it.
 */
import fixtures from './fixtures/api.json';

export interface FakeResponse {
  status: number;
  body: unknown;
}

export interface FakeCall {
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
}

type Handler = FakeResponse | ((call: FakeCall) => FakeResponse);

const key = (method: string, path: string) => `${method.toUpperCase()} ${path}`;

export function fixtureRoutes(): Map<string, FakeResponse> {
  return new Map(fixtures.routes.map((r) => [key(r.method, r.path), { status: r.status, body: r.body }]));
}

/** A fixture body by method and path; throws if the fixture file has no such route. */
export function fixture<T = unknown>(method: string, path: string): T {
  const hit = fixtureRoutes().get(key(method, path));
  if (!hit) throw new Error(`No fixture for ${key(method, path)}`);
  return hit.body as T;
}

export class FakeApi {
  private routes = new Map<string, Handler>(fixtureRoutes());
  readonly calls: FakeCall[] = [];

  /** Replace or add a route, e.g. `api.set('GET', '/v1/closet/garments', { status: 200, body: [] })`. */
  set(method: string, path: string, handler: Handler): this {
    this.routes.set(key(method, path), handler);
    return this;
  }

  reset(): void {
    this.routes = new Map(fixtureRoutes());
    this.calls.length = 0;
  }

  handle(call: FakeCall): FakeResponse {
    this.calls.push(call);
    const handler = this.routes.get(key(call.method, call.path));
    if (!handler) return { status: 404, body: { detail: `fake API has no route for ${key(call.method, call.path)}` } };
    return typeof handler === 'function' ? handler(call) : handler;
  }

  callsTo(method: string, path: string): FakeCall[] {
    return this.calls.filter((c) => key(c.method, c.path) === key(method, path));
  }
}
