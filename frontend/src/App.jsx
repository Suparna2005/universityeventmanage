import { useEffect, useState } from "react";
import { getDatabaseHealth, getHealth } from "./services/api";
import "./styles.css";

export default function App() {
  const [health, setHealth] = useState(null);
  const [database, setDatabase] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setError("Backend is not reachable yet."));
    getDatabaseHealth().then(setDatabase).catch(() => setDatabase({ status: "error", message: "PostgreSQL is unavailable" }));
  }, []);

  const connected = database?.status === "success";
  return (
    <main className="shell">
      <nav className="nav"><strong>UEP</strong><span>University Event Platform</span><span className="nav-link">Foundation preview</span></nav>
      <section className="hero" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">Campus life, better connected</p>
          <h1 id="page-title">Every event can become a lasting part of student life.</h1>
          <p className="lede">One secure workspace for clubs, students, coordinators, attendance, certificates, and participation.</p>
          <div className="actions"><button type="button">Explore events</button><a href="http://localhost:8000/docs">Open API docs</a></div>
        </div>
        <aside className="signal"><p className="eyebrow">System signal</p><div className={`signal-dot ${connected ? "ready" : ""}`} /><h2>{database ? (connected ? "PostgreSQL connected" : "API online") : "Checking connection"}</h2><p>{database ? database.message : error || "Connecting to the platform service."}</p></aside>
      </section>
      <section className="features" aria-label="Platform capabilities"><article><b>01</b><h2>Gather</h2><p>Publish clubs, workshops, seminars, and campus events in one calendar.</p></article><article><b>02</b><h2>Welcome</h2><p>Issue secure tickets and keep check-in quick, private, and duplicate-free.</p></article><article><b>03</b><h2>Recognize</h2><p>Turn verified participation into certificates and meaningful hours.</p></article></section>
    </main>
  );
}
