// Simulador local del servidor de Ctrl-P en línea: ejecuta Codigo.gs TAL CUAL con Drive, propiedades,
// cache, candado y la verificacion de Google imitados en memoria. Solo para pruebas.
// Uso: node simulador.js <puerto> <ruta Codigo.gs>
// Los "id_token" de prueba tienen la forma  PRUEBA:<correo>  (o PRUEBA_VENCIDO:<correo>).
const http = require("http");
const fs = require("fs");
const vm = require("vm");
const crypto = require("crypto");

const puerto = Number(process.argv[2] || 8790);
const codigo = fs.readFileSync(process.argv[3], "utf8");
const ADMIN = process.env.CTRLP_SIM_ADMIN || "admin@prueba.com";
const CLIENTE = "cliente-prueba.apps.googleusercontent.com";

let nid = 1;
class Archivo {
  constructor(nombre, bytes, padre) { this.id = "a" + (nid++); this.nombre = nombre; this.bytes = bytes; this.padre = padre; this.basura = false; }
  getId() { return this.id; }
  getName() { return this.nombre; }
  getBlob() { const b = this.bytes; return { getBytes: () => Array.from(b), getDataAsString: () => Buffer.from(b).toString("utf8") }; }
  setContent(t) { this.bytes = Buffer.from(t, "utf8"); return this; }
  setTrashed(v) { this.basura = !!v; }
}
class Carpeta {
  constructor(nombre) { this.id = "c" + (nid++); this.nombre = nombre; this.carpetas = []; this.archivos = []; carpetas[this.id] = this; }
  getId() { return this.id; }
  getFoldersByName(n) { return iter(this.carpetas.filter(c => c.nombre === n)); }
  createFolder(n) { const c = new Carpeta(n); this.carpetas.push(c); return c; }
  getFilesByName(n) { return iter(this.archivos.filter(a => a.nombre === n && !a.basura)); }
  createFile(a, b, c) {
    let f;
    if (typeof a === "string") f = new Archivo(a, Buffer.from(b, "utf8"), this);
    else f = new Archivo(a.nombre, Buffer.from(a.bytes), this);
    this.archivos.push(f); return f;
  }
}
function iter(l) { let i = 0; return { hasNext: () => i < l.length, next: () => l[i++] }; }
const carpetas = {};
const raiz = new Carpeta("Mi unidad");
const props = {};
const cache = {};
let llamadasToken = 0;
const correos = [];

const contexto = {
  DriveApp: {
    getRootFolder: () => raiz,
    getFolderById: (id) => { if (!carpetas[id]) throw new Error("No existe"); return carpetas[id]; },
  },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] || null, setProperty: (k, v) => { props[k] = v; } }) },
  CacheService: { getScriptCache: () => ({ get: k => cache[k] || null, put: (k, v) => { cache[k] = v; } }) },
  MailApp: { sendEmail: (o) => { correos.push({ to: o.to, subject: o.subject, largo: o.body.length, adjuntos: (o.attachments || []).length }); } },
  LockService: { getScriptLock: () => ({ waitLock: () => {}, releaseLock: () => {} }) },
  ContentService: {
    MimeType: { JSON: "json" },
    createTextOutput: (t) => ({ texto: t, setMimeType() { return this; } }),
  },
  UrlFetchApp: {
    fetch: (url) => {
      llamadasToken++;
      const tok = decodeURIComponent(url.split("id_token=")[1]);
      const [tipo, correo] = tok.split(":");
      if (tipo === "PRUEBA") {
        const cuerpo = { aud: CLIENTE, email: correo, email_verified: "true", exp: String(Math.floor(Date.now() / 1000) + 3600) };
        return { getResponseCode: () => 200, getContentText: () => JSON.stringify(cuerpo) };
      }
      return { getResponseCode: () => 400, getContentText: () => "{\"error\":\"invalid_token\"}" };
    },
  },
  Utilities: {
    DigestAlgorithm: { SHA_256: "sha256" },
    computeDigest: (alg, txt) => Array.from(crypto.createHash("sha256").update(txt, "utf8").digest()),
    base64EncodeWebSafe: (b) => Buffer.from(b).toString("base64url"),
    base64Encode: (b) => Buffer.from(b).toString("base64"),
    base64Decode: (s) => Array.from(Buffer.from(s, "base64")),
    newBlob: (bytes, tipo, nombre) => ({ nombre, bytes: Buffer.from(bytes) }),
    getUuid: () => crypto.randomUUID(),
    formatDate: (d) => d.toISOString().replace("T", " ").substring(0, 19),
  },
  JSON, Math, Date, Number, String, Object, Error, Array, encodeURIComponent,
};
vm.createContext(contexto);
vm.runInContext(codigo.replace(/var ADMIN_EMAIL = "[^"]*";/, `var ADMIN_EMAIL = "${ADMIN}";`)
                      .replace(/var CLIENT_ID = "[^"]*";/, `var CLIENT_ID = "${CLIENTE}";`), contexto);

http.createServer((req, res) => {
  let cuerpo = "";
  req.on("data", (c) => (cuerpo += c));
  req.on("end", () => {
    let salida;
    if (req.method === "GET" && req.url.startsWith("/estado")) {
      salida = JSON.stringify({ llamadasToken, correos, archivos: Object.values(carpetas).reduce((n, c) => n + c.archivos.filter(a => !a.basura).length, 0) });
    } else if (req.method === "GET") {
      salida = contexto.doGet().texto;
    } else {
      salida = contexto.doPost({ postData: { contents: cuerpo } }).texto;
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(salida);
  });
}).listen(puerto, "127.0.0.1", () => console.log("simulador en " + puerto));
