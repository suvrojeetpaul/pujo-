import { useEffect, useState } from "react";
import { ArrowRight, Check, ExternalLink, MapPin, Pause, Play, Sparkles } from "lucide-react";
import heroImage from "./images/landing-durga.jpg";
import routeImageNorth from "./images/route-kolkata.jpg";
import routeImageSouth from "./images/pandal-lights.jpg";
import routeImageAlternate from "./images/wallpaper-durga.jpg";
import routeImageAltTwo from "./images/pandal-lights-alt.jpg";
import routeImageClassic from "./images/durga pujo.jpg";

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const API = (configuredApiUrl || (
  import.meta.env.DEV ? "http://127.0.0.1:8000/api" : `${window.location.origin}/api`
)).replace(/\/+$/, "");
type Region = "north" | "south";
type Route = { id: string; name: string; region: Region; description?: string; estimated_duration_minutes?: number; stop_count: number };
type Stop = { id: string; pandal_id: string; sequence: number; status: string; pandal: { name: string; address: string; description?: string } };
type Journey = { id: string; status: string; visited_count: number; total_count: number; stops: Stop[] };
const googleSearchUrl = (stop: Stop) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${stop.pandal.name}, ${stop.pandal.address}`)}`;
const googleDirectionsUrl = (from: Stop | undefined, to: Stop) => {
  const origin = from ? `${from.pandal.name}, ${from.pandal.address}` : "";
  return `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(`${to.pandal.name}, ${to.pandal.address}`)}&travelmode=walking`;
};

async function createGuestToken(): Promise<string> {
  const response = await fetch(`${API}/auth/guest`, { method: "POST" });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  const guest = await response.json();
  if (typeof guest.token !== "string" || !guest.token) throw new Error("Unable to create a guest session");
  localStorage.setItem("pujo_guest_token", guest.token);
  return guest.token;
}

async function readApiError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // The server may return a non-JSON error page during a deployment failure.
  }
  return `Request failed (${response.status})`;
}

async function api<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  let token = localStorage.getItem("pujo_guest_token");
  if (!token) {
    token = await createGuestToken();
  }
  const accessToken = token;
  if (!accessToken) throw new Error("Unable to create a guest session");
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}`, ...init?.headers },
  });
  if (response.status === 401 && retry) {
    localStorage.removeItem("pujo_guest_token");
    return api<T>(path, init, false);
  }
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.json();
}

export default function App() {
  const [region, setRegion] = useState<Region>("north");
  const [routes, setRoutes] = useState<Route[]>([]);
  const [journey, setJourney] = useState<Journey | null>(null);
  const [journeyRegion, setJourneyRegion] = useState<Region>("north");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Route[]>(`/routes?region=${region}`).then(setRoutes).catch((e) => setError(e.message));
  }, [region]);

  async function start(route: Route) {
    setBusy(true); setError("");
    try {
      setJourney(await api<Journey>("/journeys", { method: "POST", body: JSON.stringify({ route_id: route.id }) }));
      setJourneyRegion(route.region);
    }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function visit(stop: Stop) {
    if (!journey) return;
    setBusy(true); setError("");
    try { const result = await api<{ journey: Journey }>(`/journeys/${journey.id}/stops/${stop.pandal_id}/visit`, { method: "POST", body: JSON.stringify({ action_id: crypto.randomUUID() }) }); setJourney(result.journey); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const current = journey?.stops.find((stop) => stop.status === "current");
  const previous = current && journey ? journey.stops.find((stop) => stop.sequence === current.sequence - 1) : undefined;
  const routeImages = [routeImageNorth, routeImageSouth, routeImageAlternate, routeImageAltTwo, routeImageClassic, heroImage];
  const regionBackground = region === "north" ? routeImageNorth : routeImageSouth;
  const journeyBackground = journeyRegion === "north" ? routeImageAlternate : routeImageAltTwo;
  return <main>
    <header><div className="brand"><span className="brand-mark"><Sparkles size={18} /></span><span>PUJO PATH</span></div><span className="header-note">Your city. Your Pujo. Your path.</span><a className="header-link" href="#routes">Explore routes <ArrowRight size={15} /></a></header>
    <section className="hero" style={{ backgroundImage: `url("${regionBackground}")` }}>
      <div className="hero-shade" />
      <div className="hero-content"><p className="eyebrow">KOLKATA <span>•</span> DURGA PUJA</p><h1>Follow the rhythm<br /><em>of the city.</em></h1><p className="intro">Curated pandal-hopping routes for a beautiful, unhurried Puja journey.</p><a className="hero-cta" href="#routes">Find your route <ArrowRight size={17} /></a></div>
      <div className="hero-caption"><span>01</span><span className="caption-line" /><span>THE CITY IS WAITING</span></div>
    </section>
    {error && <div className="error">{error}</div>}
    {!journey ? <section className="content region-content" id="routes" style={{ backgroundImage: `linear-gradient(180deg, #fbf8f2f5 0%, #fbf8f2f8 42%, #fbf8f2 100%), url("${regionBackground}")` }}>
      <div className="region-tabs">{(["north", "south"] as Region[]).map((item) => <button type="button" aria-pressed={region === item} className={region === item ? "active" : ""} onClick={() => setRegion(item)} key={item}>{item} Kolkata</button>)}</div>
      <div className="section-heading"><div><p className="eyebrow">MAKE A DAY OF IT</p><h2>Choose your route<span>.</span></h2></div><p className="section-intro">Every route is a little different.<br />Every stop is worth the walk.</p></div>
      <div className="route-grid">{routes.map((route, index) => <article className="route-card" key={route.id}><div className="route-art" style={{ backgroundImage: `url("${routeImages[index % routeImages.length]}")` }}><div className="route-art-shade" /><span>{route.region === "north" ? "উত্তর" : "দক্ষিণ"}</span><small>{String(index + 1).padStart(2, "0")}</small></div><div className="route-card-body"><p className="eyebrow">{route.stop_count} STOPS <span>•</span> {route.estimated_duration_minutes ?? 0} MIN</p><h3>{route.name}</h3><p>{route.description ?? "A curated trail through Kolkata's most memorable Puja neighbourhoods."}</p><button disabled={busy} onClick={() => start(route)}>Begin journey <ArrowRight size={16} /></button></div></article>)}{!routes.length && <p>No published routes yet. Add route data through the admin import workflow.</p>}</div>
    </section> :     <section className="content journey" style={{ backgroundImage: `linear-gradient(110deg, #241014e8 0%, #241014c7 45%, #2410149e 100%), url("${journeyBackground}")` }}><div className="journey-top"><div><p className="eyebrow">YOUR JOURNEY</p><h2>{journey.status === "completed" ? "Journey complete" : "One stop at a time."}</h2></div><button className="secondary" onClick={() => setJourney(null)}><Pause size={16} /> Exit</button></div><div className="progress"><span style={{ width: `${journey.total_count ? journey.visited_count / journey.total_count * 100 : 0}%` }} /></div><p className="muted">{journey.visited_count} of {journey.total_count} pandals visited</p>{current ? <div className="current-stop"><div className="stop-icon"><MapPin /></div><p className="eyebrow">NEXT STOP • {current.sequence}</p><h2>{current.pandal.name}</h2><p>{current.pandal.address}</p><div className="map-actions"><a href={googleSearchUrl(current)} target="_blank" rel="noreferrer"><MapPin size={16} /> View on Google Maps <ExternalLink size={14} /></a><a href={googleDirectionsUrl(previous, current)} target="_blank" rel="noreferrer"><ArrowRight size={16} /> Get walking directions <ExternalLink size={14} /></a></div><button disabled={busy} onClick={() => visit(current)}><Check size={18} /> Mark as visited</button></div> : <div className="complete"><Sparkles /><h2>You explored the route.</h2><p>What a beautiful Puja journey.</p></div>}<div className="stop-list">{journey.stops.map((stop) => <div className={`stop ${stop.status}`} key={stop.id}><span>{stop.status === "visited" ? <Check size={15} /> : stop.sequence}</span><div><strong>{stop.pandal.name}</strong><small>{stop.status === "visited" ? "Visited" : stop.status}</small></div><a href={googleSearchUrl(stop)} target="_blank" rel="noreferrer" aria-label={`View ${stop.pandal.name} on Google Maps`}><MapPin size={15} /></a></div>)}</div></section>}
    <footer><Play size={14} /> <span>Built for curious travellers and Kolkata's biggest celebration.</span><span>PUJO PATH <b>2025</b></span></footer>
  </main>;
}
