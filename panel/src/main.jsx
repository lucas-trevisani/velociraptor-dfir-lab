import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, Database, Download, FileUp, KeyRound, Laptop, ListChecks, Lock, Plus, Search, ShieldCheck, Users } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      setError("Credenciais invalidas");
      return;
    }
    const data = await response.json();
    onLogin(data.access_token);
  }

  return (
    <main className="login-shell">
      <form className="login-panel" onSubmit={submit}>
        <div className="brand-row">
          <ShieldCheck size={32} />
          <span>Velo License</span>
        </div>
        <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Senha<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <p className="error">{error}</p>}
        <button type="submit"><Lock size={18} /> Entrar</button>
      </form>
    </main>
  );
}

function Stat({ icon: Icon, label, value }) {
  return <div className="stat"><Icon size={20} /><span>{label}</span><strong>{value ?? "-"}</strong></div>;
}

const views = {
  Dashboard: {
    description: "Visao geral operacional do licenciamento.",
    rows: [
      ["Clientes ativos", "monitorado", "usuarios autorizados", "Clientes"],
      ["Licencas expirando", "monitorado", "validade e bloqueios", "Licencas"],
      ["Hunts publicadas", "monitorado", "versoes assinadas", "Hunts"],
      ["Uploads recentes", "monitorado", "resultados recebidos", "Resultados"],
      ["Alertas de HWID", "monitorado", "dispositivos e resets", "Maquinas"]
    ],
    columns: ["Tipo", "Status", "Sinal", "Acao"]
  },
  Clientes: {
    description: "Usuarios cadastrados e status de acesso.",
    endpoint: "/api/admin/users",
    columns: ["ID", "Email", "Perfil", "Status", "Criado em"],
    map: (row) => [row.id, row.email, row.role, row.status, formatDate(row.created_at)]
  },
  Licencas: {
    description: "Chaves, validade e limite de maquinas.",
    endpoint: "/api/admin/licenses",
    columns: ["ID", "Chave", "Status", "Maquinas", "Expira em", "Acoes"],
    map: (row) => [shortId(row.id), row.key, row.status, row.max_devices, formatDate(row.expires_at)]
  },
  Maquinas: {
    description: "HWIDs registrados, plataforma e ultimo contato.",
    endpoint: "/api/admin/devices",
    columns: ["Hostname", "Plataforma", "Launcher", "Ultimo contato"],
    map: (row) => [row.hostname, row.platform, row.launcher_version, formatDate(row.last_seen_at)]
  },
  Hunts: {
    description: "Hunts armazenadas na VPS, assinadas e versionadas.",
    endpoint: "/api/admin/hunts",
    columns: ["ID", "Nome", "Versao", "Status", "SHA256"],
    map: (row) => [row.id, row.name, row.version, row.status, shortHash(row.sha256)]
  },
  Resultados: {
    description: "Resultados recebidos dos launchers autorizados.",
    endpoint: "/api/admin/results",
    columns: ["Resultado", "Device", "Hunt version", "Recebido em", "Acoes"],
    map: (row) => [shortHash(row.sha256), shortId(row.device_id), shortId(row.hunt_version_id), formatDate(row.created_at)]
  },
  Logs: {
    description: "Auditoria de autenticacao, downloads e operacoes.",
    endpoint: "/api/admin/logs",
    columns: ["Evento", "IP", "Payload", "Data"],
    map: (row) => [row.event, row.ip_address, JSON.stringify(row.payload), formatDate(row.created_at)]
  }
};

function formatDate(value) {
  if (!value || value === "sem validade" || value === "-") return value || "-";
  return new Date(value).toLocaleString("pt-BR");
}

function shortHash(value) {
  if (!value || value === "-") return "-";
  return `${value.slice(0, 12)}...`;
}

function shortId(value) {
  if (!value || value === "-") return "-";
  return value.slice(0, 8);
}

async function apiRequest(path, token, options = {}) {
  const headers = { ...(options.headers || {}), Authorization: `Bearer ${token}` };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) throw new Error(await response.text());
  return response;
}

function ActionPanel({ active, token, onRefresh }) {
  const [client, setClient] = useState({ email: "", password: "" });
  const [license, setLicense] = useState({ user_id: "", max_devices: 1, expires_at: "" });
  const [hunt, setHunt] = useState({ name: "", version: "1.0.0", file: null });
  const [message, setMessage] = useState("");

  async function createClient(event) {
    event.preventDefault();
    await apiRequest("/api/admin/users", token, { method: "POST", body: JSON.stringify({ ...client, role: "client" }) });
    setClient({ email: "", password: "" });
    setMessage("Cliente criado.");
    onRefresh();
  }

  async function createLicense(event) {
    event.preventDefault();
    const payload = {
      user_id: license.user_id,
      max_devices: Number(license.max_devices),
      expires_at: license.expires_at ? new Date(license.expires_at).toISOString() : null,
      allowed_hunts: []
    };
    await apiRequest("/api/admin/licenses", token, { method: "POST", body: JSON.stringify(payload) });
    setLicense({ user_id: "", max_devices: 1, expires_at: "" });
    setMessage("Licenca criada.");
    onRefresh();
  }

  async function uploadHunt(event) {
    event.preventDefault();
    const form = new FormData();
    form.append("name", hunt.name);
    form.append("version", hunt.version);
    form.append("file", hunt.file);
    await apiRequest("/api/admin/hunts", token, { method: "POST", body: form });
    setHunt({ name: "", version: "1.0.0", file: null });
    setMessage("Hunt enviada e assinada.");
    onRefresh();
  }

  if (active === "Clientes") {
    return (
      <form className="action-panel" onSubmit={createClient}>
        <input placeholder="email do cliente" value={client.email} onChange={(event) => setClient({ ...client, email: event.target.value })} />
        <input placeholder="senha inicial" value={client.password} onChange={(event) => setClient({ ...client, password: event.target.value })} />
        <button><Plus size={18} /> Novo Cliente</button>
        {message && <span>{message}</span>}
      </form>
    );
  }

  if (active === "Licencas") {
    return (
      <form className="action-panel" onSubmit={createLicense}>
        <input placeholder="ID completo do cliente" value={license.user_id} onChange={(event) => setLicense({ ...license, user_id: event.target.value })} />
        <input type="number" min="1" max="20" value={license.max_devices} onChange={(event) => setLicense({ ...license, max_devices: event.target.value })} />
        <input type="datetime-local" value={license.expires_at} onChange={(event) => setLicense({ ...license, expires_at: event.target.value })} />
        <button><KeyRound size={18} /> Nova Licenca</button>
        {message && <span>{message}</span>}
      </form>
    );
  }

  if (active === "Hunts") {
    return (
      <form className="action-panel" onSubmit={uploadHunt}>
        <input placeholder="nome da Hunt" value={hunt.name} onChange={(event) => setHunt({ ...hunt, name: event.target.value })} />
        <input placeholder="versao" value={hunt.version} onChange={(event) => setHunt({ ...hunt, version: event.target.value })} />
        <input type="file" onChange={(event) => setHunt({ ...hunt, file: event.target.files[0] })} />
        <button><FileUp size={18} /> Upload Hunt</button>
        {message && <span>{message}</span>}
      </form>
    );
  }

  return null;
}

function DataTable({ active, rows, loading, onOpen, token, onRefresh }) {
  const view = views[active];
  const data = active === "Dashboard" ? view.rows : rows.map(view.map);

  async function download(path, filename) {
    const response = await apiRequest(path, token);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function expireLicense(row) {
    await apiRequest(`/api/admin/licenses/${row.id}/expire`, token, { method: "POST" });
    onRefresh();
  }

  async function attachHunts(row) {
    const value = window.prompt("IDs completos das Hunts permitidas, separados por virgula");
    if (!value) return;
    const allowed_hunts = value.split(",").map((item) => item.trim()).filter(Boolean);
    await apiRequest(`/api/admin/licenses/${row.id}/hunts`, token, { method: "POST", body: JSON.stringify({ allowed_hunts }) });
    onRefresh();
  }

  return (
    <div className="table-panel">
      <div className="toolbar">
        <div className="search"><Search size={16} /><input placeholder={`Filtrar ${active.toLowerCase()}`} /></div>
      </div>
      <table>
        <thead><tr>{view.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>
          {loading && <tr><td colSpan={view.columns.length}>Carregando...</td></tr>}
          {!loading && data.length === 0 && <tr><td colSpan={view.columns.length}>Nenhum registro encontrado.</td></tr>}
          {!loading && data.map((row, index) => (
            <tr key={`${active}-${index}`}>
              {(active === "Dashboard" ? row.slice(0, 3) : row).map((cell, cellIndex) => (
                <td key={cellIndex}>
                  {cellIndex === 1 && ["Dashboard", "Licencas"].includes(active) ? <span className="pill">{cell}</span> : cell}
                </td>
              ))}
              {active === "Dashboard" && <td><button className="ghost" onClick={() => onOpen(row[3])}>Abrir</button></td>}
              {active === "Licencas" && (
                <td className="actions">
                  <button className="ghost" onClick={() => download(`/api/admin/licenses/${rows[index].id}/launcher`, `launcher-${rows[index].key}.zip`)}><Download size={16} /> Launcher</button>
                  <button className="ghost" onClick={() => attachHunts(rows[index])}>Hunts</button>
                  <button className="ghost" onClick={() => expireLicense(rows[index])}>Expirar</button>
                </td>
              )}
              {active === "Resultados" && <td><button className="ghost" onClick={() => download(`/api/admin/results/${rows[index].id}/file`, `resultado-${rows[index].id}.bin`)}><Download size={16} /> Baixar</button></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [dashboard, setDashboard] = useState({});
  const [active, setActive] = useState("Dashboard");
  const [rows, setRows] = useState([]);
  const [loadingRows, setLoadingRows] = useState(false);

  function refreshActive() {
    if (active === "Dashboard") {
      fetch(`${API_BASE}/api/admin/dashboard`, { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => response.ok ? response.json() : {})
        .then(setDashboard);
      return;
    }
    setLoadingRows(true);
    fetch(`${API_BASE}${views[active].endpoint}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : [])
      .then(setRows)
      .finally(() => setLoadingRows(false));
  }

  useEffect(() => {
    if (!token) return;
    localStorage.setItem("token", token);
    fetch(`${API_BASE}/api/admin/dashboard`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : {})
      .then(setDashboard);
  }, [token]);

  useEffect(() => {
    if (!token || active === "Dashboard") {
      setRows([]);
      return;
    }
    refreshActive();
  }, [active, token]);

  if (!token) return <Login onLogin={setToken} />;

  const nav = [
    ["Dashboard", Activity],
    ["Clientes", Users],
    ["Licencas", KeyRound],
    ["Maquinas", Laptop],
    ["Hunts", ListChecks],
    ["Resultados", Database],
    ["Logs", Search]
  ];

  return (
    <main className="app-shell">
      <aside>
        <div className="brand-row"><ShieldCheck size={28} /><span>Velo License</span></div>
        {nav.map(([item, Icon]) => (
          <button className={active === item ? "active" : ""} key={item} onClick={() => setActive(item)}><Icon size={18} />{item}</button>
        ))}
      </aside>
      <section className="workspace">
        <header>
          <div><h1>{active}</h1><p>{views[active].description}</p></div>
          <button className="danger" onClick={() => { localStorage.removeItem("token"); setToken(""); }}>Sair</button>
        </header>
        <div className="stats-grid">
          <Stat icon={Users} label="Clientes" value={dashboard.users} />
          <Stat icon={KeyRound} label="Licencas" value={dashboard.licenses} />
          <Stat icon={Laptop} label="Maquinas" value={dashboard.devices} />
          <Stat icon={ListChecks} label="Hunts" value={dashboard.hunts} />
          <Stat icon={Database} label="Resultados" value={dashboard.results} />
          <Stat icon={Search} label="Logs" value={dashboard.logs} />
        </div>
        <ActionPanel active={active} token={token} onRefresh={refreshActive} />
        <DataTable active={active} rows={rows} loading={loadingRows} onOpen={setActive} token={token} onRefresh={refreshActive} />
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
