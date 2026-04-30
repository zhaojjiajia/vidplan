const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { URL } = require('node:url');
const { DatabaseSync } = require('node:sqlite');

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';
const ROOT_DIR = __dirname;
const DATA_DIR = path.join(ROOT_DIR, 'data');
const DB_PATH = path.join(DATA_DIR, 'garden.db');
const COOKIE_NAME = 'garden_visitor';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
const COOKIE_SECRET = process.env.GARDEN_COOKIE_SECRET || 'change-this-before-production';
const VIDPLAN_JWT_SECRET = process.env.VIDPLAN_JWT_SECRET
  || process.env.DJANGO_SECRET_KEY
  || 'dev-insecure-change-me';
const OPTIONAL_PETAL_COUNT = 7;
const FINGERPRINT_VERSION = 'v1';
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mp3': 'audio/mpeg',
  '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml; charset=utf-8'
};
const PETAL_PALETTE_COUNT = 6;
const STEM_SHAPE_COUNT = 3;

fs.mkdirSync(DATA_DIR, { recursive: true });

const db = new DatabaseSync(DB_PATH);
db.exec(`
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;
  PRAGMA busy_timeout = 5000;

  CREATE TABLE IF NOT EXISTS visitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    client_id_hash TEXT,
    fingerprint_hash TEXT,
    fingerprint_version TEXT,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS flowers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id INTEGER NOT NULL UNIQUE,
    x_ratio REAL NOT NULL,
    y_ratio REAL NOT NULL,
    size INTEGER NOT NULL,
    flip INTEGER NOT NULL,
    palette_index INTEGER NOT NULL,
    stem_index INTEGER NOT NULL,
    hidden_petals TEXT NOT NULL,
    dimmed_petals TEXT NOT NULL,
    sway_angle REAL NOT NULL,
    sway_duration REAL NOT NULL,
    sway_delay REAL NOT NULL,
    sway_lift REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS plant_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    flower_id INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (visitor_id, idempotency_key),
    FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
    FOREIGN KEY (flower_id) REFERENCES flowers(id) ON DELETE SET NULL
  );
`);

ensureVisitorSchema();

function ensureVisitorSchema() {
  const columns = db.prepare('PRAGMA table_info(visitors)').all();
  const columnNames = new Set(columns.map(function (column) {
    return column.name;
  }));

  if (!columnNames.has('client_id_hash')) {
    db.exec('ALTER TABLE visitors ADD COLUMN client_id_hash TEXT');
  }
  if (!columnNames.has('fingerprint_hash')) {
    db.exec('ALTER TABLE visitors ADD COLUMN fingerprint_hash TEXT');
  }
  if (!columnNames.has('fingerprint_version')) {
    db.exec('ALTER TABLE visitors ADD COLUMN fingerprint_version TEXT');
  }

  db.exec(`
    CREATE UNIQUE INDEX IF NOT EXISTS idx_visitors_client_id_hash
    ON visitors(client_id_hash)
    WHERE client_id_hash IS NOT NULL;

    CREATE INDEX IF NOT EXISTS idx_visitors_fingerprint_hash
    ON visitors(fingerprint_hash);
  `);
}

const findVisitorByHashStmt = db.prepare(`
  SELECT id, token_hash, client_id_hash, fingerprint_hash, fingerprint_version, created_at, last_seen_at
  FROM visitors
  WHERE token_hash = ?
`);
const insertVisitorStmt = db.prepare(`
  INSERT INTO visitors (
    token_hash,
    client_id_hash,
    fingerprint_hash,
    fingerprint_version,
    created_at,
    last_seen_at
  ) VALUES (?, ?, ?, ?, ?, ?)
`);
const updateVisitorTokenStmt = db.prepare(`
  UPDATE visitors
  SET token_hash = ?, last_seen_at = ?
  WHERE id = ?
`);
const updateVisitorSeenStmt = db.prepare(`
  UPDATE visitors
  SET last_seen_at = ?
  WHERE id = ?
`);
const findVisitorByClientIdStmt = db.prepare(`
  SELECT id, token_hash, client_id_hash, fingerprint_hash, fingerprint_version, created_at, last_seen_at
  FROM visitors
  WHERE client_id_hash = ?
`);
const findVisitorByFingerprintStmt = db.prepare(`
  SELECT
    v.id,
    v.token_hash,
    v.client_id_hash,
    v.fingerprint_hash,
    v.fingerprint_version,
    v.created_at,
    v.last_seen_at,
    f.id AS flower_id
  FROM visitors v
  LEFT JOIN flowers f ON f.visitor_id = v.id
  WHERE v.fingerprint_hash = ? AND v.fingerprint_version = ?
  ORDER BY CASE WHEN f.id IS NULL THEN 1 ELSE 0 END ASC, v.id DESC
  LIMIT 1
`);
const getVisitorFlowerStmt = db.prepare(`
  SELECT *
  FROM flowers
  WHERE visitor_id = ?
`);
const insertFlowerStmt = db.prepare(`
  INSERT INTO flowers (
    visitor_id,
    x_ratio,
    y_ratio,
    size,
    flip,
    palette_index,
    stem_index,
    hidden_petals,
    dimmed_petals,
    sway_angle,
    sway_duration,
    sway_delay,
    sway_lift,
    created_at
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);
const getFlowerByIdStmt = db.prepare(`
  SELECT *
  FROM flowers
  WHERE id = ?
`);
const listAllFlowersStmt = db.prepare(`
  SELECT *
  FROM flowers
  ORDER BY id ASC
`);
const listFlowersAfterStmt = db.prepare(`
  SELECT *
  FROM flowers
  WHERE id > ?
  ORDER BY id ASC
`);
const countFlowersStmt = db.prepare(`
  SELECT COUNT(*) AS count
  FROM flowers
`);
const latestFlowerIdStmt = db.prepare(`
  SELECT COALESCE(MAX(id), 0) AS latest_id
  FROM flowers
`);
const findPlantRequestStmt = db.prepare(`
  SELECT id, visitor_id, idempotency_key, flower_id, created_at
  FROM plant_requests
  WHERE visitor_id = ? AND idempotency_key = ?
`);
const insertPlantRequestStmt = db.prepare(`
  INSERT OR IGNORE INTO plant_requests (visitor_id, idempotency_key, flower_id, created_at)
  VALUES (?, ?, ?, ?)
`);
const updatePlantRequestFlowerStmt = db.prepare(`
  UPDATE plant_requests
  SET flower_id = ?
  WHERE visitor_id = ? AND idempotency_key = ?
`);

function nowIso() {
  return new Date().toISOString();
}

function parseCookies(cookieHeader) {
  const cookies = {};
  if (!cookieHeader) {
    return cookies;
  }

  cookieHeader.split(';').forEach(function (part) {
    const index = part.indexOf('=');
    if (index === -1) {
      return;
    }
    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    cookies[key] = decodeURIComponent(value);
  });
  return cookies;
}

function setCookie(res, name, value, options) {
  const parts = [`${name}=${encodeURIComponent(value)}`];

  if (options.maxAge) {
    parts.push(`Max-Age=${options.maxAge}`);
  }
  if (options.httpOnly) {
    parts.push('HttpOnly');
  }
  if (options.sameSite) {
    parts.push(`SameSite=${options.sameSite}`);
  }
  if (options.secure) {
    parts.push('Secure');
  }
  parts.push(`Path=${options.path || '/'}`);

  res.setHeader('Set-Cookie', parts.join('; '));
}

function signToken(token) {
  return crypto.createHmac('sha256', COOKIE_SECRET).update(token).digest('base64url');
}

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

function base64UrlDecode(value) {
  const normalized = String(value || '').replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4);
  return Buffer.from(padded, 'base64');
}

function verifyVidPlanJwt(rawToken) {
  if (!rawToken) {
    return null;
  }

  const parts = String(rawToken).split('.');
  if (parts.length !== 3) {
    return null;
  }

  const signingInput = `${parts[0]}.${parts[1]}`;
  const expected = crypto
    .createHmac('sha256', VIDPLAN_JWT_SECRET)
    .update(signingInput)
    .digest('base64url');

  try {
    const left = Buffer.from(parts[2]);
    const right = Buffer.from(expected);
    if (left.length !== right.length || !crypto.timingSafeEqual(left, right)) {
      return null;
    }
  } catch (error) {
    return null;
  }

  try {
    const payload = JSON.parse(base64UrlDecode(parts[1]).toString('utf8'));
    const exp = Number(payload.exp || 0);
    if (exp && exp * 1000 < Date.now()) {
      return null;
    }
    return payload;
  } catch (error) {
    return null;
  }
}

function getVidPlanUserId(req) {
  const auth = String(req.headers.authorization || '');
  const match = auth.match(/^Bearer\s+(.+)$/i);
  const payload = verifyVidPlanJwt(match ? match[1] : '');
  if (!payload || payload.user_id == null) {
    return '';
  }
  return String(payload.user_id);
}

function verifySignedToken(rawValue) {
  if (!rawValue) {
    return null;
  }

  const parts = rawValue.split('.');
  if (parts.length !== 2) {
    return null;
  }

  const token = parts[0];
  const signature = parts[1];
  const expected = signToken(token);

  try {
    const left = Buffer.from(signature);
    const right = Buffer.from(expected);
    if (left.length !== right.length || !crypto.timingSafeEqual(left, right)) {
      return null;
    }
    return token;
  } catch (error) {
    return null;
  }
}

function issueVisitorToken(req, res) {
  const token = crypto.randomBytes(24).toString('hex');
  const signedValue = `${token}.${signToken(token)}`;
  const isSecure = req.headers['x-forwarded-proto'] === 'https';

  setCookie(res, COOKIE_NAME, signedValue, {
    maxAge: COOKIE_MAX_AGE,
    httpOnly: true,
    sameSite: 'Lax',
    secure: isSecure,
    path: '/'
  });

  return token;
}

function withWriteTransaction(work) {
  db.exec('BEGIN IMMEDIATE');
  try {
    const result = work();
    db.exec('COMMIT');
    return result;
  } catch (error) {
    try {
      db.exec('ROLLBACK');
    } catch (rollbackError) {
      // 这里忽略回滚失败，保留原始异常更有价值。
    }
    throw error;
  }
}

function getIdentityHeaders(req) {
  const rawClientId = req.headers['x-client-id'];
  const rawFingerprintHash = req.headers['x-fingerprint-hash'];
  const rawFingerprintVersion = req.headers['x-fingerprint-version'];

  return {
    clientIdHash: rawClientId ? hashToken(String(rawClientId)) : null,
    fingerprintHash: rawFingerprintHash ? String(rawFingerprintHash) : null,
    fingerprintVersion: rawFingerprintVersion ? String(rawFingerprintVersion) : FINGERPRINT_VERSION
  };
}

function updateVisitorIdentity(visitorId, identity) {
  const updates = [];
  const values = [];

  if (identity.clientIdHash) {
    updates.push('client_id_hash = ?');
    values.push(identity.clientIdHash);
  }
  if (identity.fingerprintHash) {
    updates.push('fingerprint_hash = ?');
    values.push(identity.fingerprintHash);
    updates.push('fingerprint_version = ?');
    values.push(identity.fingerprintVersion);
  }

  updates.push('last_seen_at = ?');
  values.push(nowIso());
  values.push(visitorId);

  db.prepare(`
    UPDATE visitors
    SET ${updates.join(', ')}
    WHERE id = ?
  `).run(...values);
}

function bindFreshTokenToVisitor(req, res, visitorId) {
  const newToken = issueVisitorToken(req, res);
  updateVisitorTokenStmt.run(hashToken(newToken), nowIso(), visitorId);
}

function getOrCreateVisitor(req, res) {
  const vidPlanUserId = getVidPlanUserId(req);
  if (vidPlanUserId) {
    const visitor = createVisitorRecord(`vidplan-user:${vidPlanUserId}`, {
      fingerprintVersion: 'vidplan-jwt'
    });
    updateVisitorSeenStmt.run(nowIso(), visitor.id);
    return findVisitorByHashStmt.get(visitor.token_hash);
  }

  const cookies = parseCookies(req.headers.cookie);
  const signedValue = cookies[COOKIE_NAME];
  const token = verifySignedToken(signedValue);
  const now = nowIso();
  const identity = getIdentityHeaders(req);

  if (token) {
    const tokenHash = hashToken(token);
    const visitor = findVisitorByHashStmt.get(tokenHash);
    if (visitor) {
      if (identity.clientIdHash || identity.fingerprintHash) {
        updateVisitorIdentity(visitor.id, identity);
        return findVisitorByHashStmt.get(tokenHash);
      }
      updateVisitorSeenStmt.run(now, visitor.id);
      return visitor;
    }
  }

  if (identity.clientIdHash) {
    const visitorByClientId = findVisitorByClientIdStmt.get(identity.clientIdHash);
    if (visitorByClientId) {
      updateVisitorIdentity(visitorByClientId.id, identity);
      bindFreshTokenToVisitor(req, res, visitorByClientId.id);
      return findVisitorByClientIdStmt.get(identity.clientIdHash);
    }
  }

  if (identity.fingerprintHash) {
    const visitorByFingerprint = findVisitorByFingerprintStmt.get(
      identity.fingerprintHash,
      identity.fingerprintVersion
    );
    if (visitorByFingerprint) {
      updateVisitorIdentity(visitorByFingerprint.id, identity);
      bindFreshTokenToVisitor(req, res, visitorByFingerprint.id);
      if (identity.clientIdHash) {
        return findVisitorByClientIdStmt.get(identity.clientIdHash);
      }
      return findVisitorByFingerprintStmt.get(identity.fingerprintHash, identity.fingerprintVersion);
    }
  }

  const newToken = issueVisitorToken(req, res);
  const newHash = hashToken(newToken);
  insertVisitorStmt.run(
    newHash,
    identity.clientIdHash,
    identity.fingerprintHash,
    identity.fingerprintVersion,
    now,
    now
  );
  return findVisitorByHashStmt.get(newHash);
}

function createVisitorRecord(token, identity) {
  const rawToken = token || crypto.randomBytes(24).toString('hex');
  const tokenHash = hashToken(rawToken);
  const now = nowIso();
  const existingVisitor = findVisitorByHashStmt.get(tokenHash);
  const identityInfo = identity || {};

  if (existingVisitor) {
    return existingVisitor;
  }

  insertVisitorStmt.run(
    tokenHash,
    identityInfo.clientIdHash || null,
    identityInfo.fingerprintHash || null,
    identityInfo.fingerprintVersion || FINGERPRINT_VERSION,
    now,
    now
  );
  return findVisitorByHashStmt.get(tokenHash);
}

function normalizeRatio(value, fallback) {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return fallback;
  }
  if (num < 0) {
    return 0;
  }
  if (num > 1) {
    return 1;
  }
  return num;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomFloat(min, max, digits) {
  return Number((min + Math.random() * (max - min)).toFixed(digits));
}

function shuffleArray(list) {
  const next = list.slice();
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const temp = next[i];
    next[i] = next[j];
    next[j] = temp;
  }
  return next;
}

function buildPetalVisibility() {
  const optionalIndexes = Array.from({ length: OPTIONAL_PETAL_COUNT }, function (_, index) {
    return index;
  });
  const shuffled = shuffleArray(optionalIndexes);
  const hiddenCount = Math.floor(Math.random() * 4);
  const hiddenPetals = shuffled.slice(0, hiddenCount);
  const dimmedPetals = [];

  shuffled.slice(hiddenCount).forEach(function (index) {
    if (Math.random() > 0.65) {
      dimmedPetals.push(index);
    }
  });

  return {
    hidden_petals: JSON.stringify(hiddenPetals),
    dimmed_petals: JSON.stringify(dimmedPetals)
  };
}

function getExistingFlowers() {
  return listAllFlowersStmt.all();
}

function computeDistanceScore(candidate, flowers) {
  if (!flowers.length) {
    return Infinity;
  }

  let nearest = Infinity;
  flowers.forEach(function (flower) {
    const dx = (candidate.x_ratio - flower.x_ratio) / candidate.min_spacing_x;
    const dy = (candidate.y_ratio - flower.y_ratio) / candidate.min_spacing_y;
    const distance = Math.hypot(dx, dy);
    if (distance < nearest) {
      nearest = distance;
    }
  });

  return nearest;
}

function pickFlowerPosition(requestedX, requestedY, size) {
  const existingFlowers = getExistingFlowers();
  const minSpacingX = Math.max(size / 1400, 0.072);
  const minSpacingY = Math.max(size / 900, 0.11);
  const centerX = 0.08 + normalizeRatio(requestedX, Math.random()) * 0.84;
  const centerY = 0.05 + normalizeRatio(requestedY, Math.random()) * 0.82;
  let bestCandidate = {
    x_ratio: centerX,
    y_ratio: centerY,
    min_spacing_x: minSpacingX,
    min_spacing_y: minSpacingY
  };
  let bestScore = computeDistanceScore(bestCandidate, existingFlowers);

  if (bestScore >= 1) {
    return bestCandidate;
  }

  for (let i = 0; i < 24; i += 1) {
    const angle = (Math.PI * 2 * i) / 24;
    const radius = 0.018 + i * 0.0065;
    const candidate = {
      x_ratio: Math.min(0.92, Math.max(0.08, centerX + Math.cos(angle) * radius)),
      y_ratio: Math.min(0.87, Math.max(0.05, centerY + Math.sin(angle) * radius)),
      min_spacing_x: minSpacingX,
      min_spacing_y: minSpacingY
    };
    const score = computeDistanceScore(candidate, existingFlowers);
    if (score > bestScore) {
      bestCandidate = candidate;
      bestScore = score;
    }
    if (score >= 1) {
      return candidate;
    }
  }

  return bestCandidate;
}

function buildFlowerPayload(xRatio, yRatio) {
  const size = randomInt(112, 128);
  const position = pickFlowerPosition(xRatio, yRatio, size);
  const petals = buildPetalVisibility();

  return {
    x_ratio: position.x_ratio,
    y_ratio: position.y_ratio,
    size,
    flip: Math.random() > 0.5 ? 1 : 0,
    palette_index: randomInt(0, PETAL_PALETTE_COUNT - 1),
    stem_index: randomInt(0, STEM_SHAPE_COUNT - 1),
    hidden_petals: petals.hidden_petals,
    dimmed_petals: petals.dimmed_petals,
    sway_angle: randomFloat(1.8, 3.6, 2),
    sway_duration: randomFloat(5.0, 7.1, 2),
    sway_delay: randomFloat(-4.0, 0, 2),
    sway_lift: randomFloat(0.8, 2.2, 2),
    created_at: nowIso()
  };
}

function serializeFlower(row) {
  return {
    id: row.id,
    visitor_id: row.visitor_id,
    x_ratio: Number(row.x_ratio),
    y_ratio: Number(row.y_ratio),
    size: Number(row.size),
    flip: Number(row.flip) === 1,
    palette_index: Number(row.palette_index),
    stem_index: Number(row.stem_index),
    hidden_petals: JSON.parse(row.hidden_petals || '[]'),
    dimmed_petals: JSON.parse(row.dimmed_petals || '[]'),
    sway_angle: Number(row.sway_angle),
    sway_duration: Number(row.sway_duration),
    sway_delay: Number(row.sway_delay),
    sway_lift: Number(row.sway_lift),
    created_at: row.created_at
  };
}

function buildViewer(visitorId) {
  const flower = getVisitorFlowerStmt.get(visitorId);
  return {
    can_plant: !flower,
    flower_id: flower ? flower.id : null
  };
}

function readJsonBody(req) {
  return new Promise(function (resolve, reject) {
    let raw = '';

    req.on('data', function (chunk) {
      raw += chunk;
      if (raw.length > 1024 * 64) {
        reject(new Error('请求体过大'));
        req.destroy();
      }
    });

    req.on('end', function () {
      if (!raw) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(new Error('请求体不是有效的 JSON'));
      }
    });

    req.on('error', reject);
  });
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store'
  });
  res.end(body);
}

function sendText(res, statusCode, message) {
  res.writeHead(statusCode, {
    'Content-Type': 'text/plain; charset=utf-8'
  });
  res.end(message);
}

function serveStaticFile(req, res, pathname) {
  const relativePath = pathname === '/' ? '/index.html' : pathname;
  const normalizedPath = path.normalize(relativePath)
    .replace(/^(\.\.[/\\])+/, '')
    .replace(/^[/\\]+/, '');
  const filePath = path.join(ROOT_DIR, normalizedPath);

  if (!filePath.startsWith(ROOT_DIR)) {
    sendText(res, 403, 'Forbidden');
    return;
  }

  fs.readFile(filePath, function (error, data) {
    if (error) {
      if (pathname !== '/' && pathname !== '/index.html') {
        sendText(res, 404, 'Not Found');
        return;
      }

      fs.readFile(path.join(ROOT_DIR, 'index.html'), function (fallbackError, fallbackData) {
        if (fallbackError) {
          sendText(res, 500, 'Server Error');
          return;
        }
        res.writeHead(200, { 'Content-Type': MIME_TYPES['.html'] });
        res.end(fallbackData);
      });
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      'Content-Type': MIME_TYPES[ext] || 'application/octet-stream'
    });
    res.end(data);
  });
}

function getGardenSnapshot(afterId, visitorId) {
  const count = countFlowersStmt.get().count;
  const latestId = latestFlowerIdStmt.get().latest_id;
  const rows = afterId > 0 ? listFlowersAfterStmt.all(afterId) : listAllFlowersStmt.all();

  return {
    success: true,
    count,
    latest_id: latestId,
    flowers: rows.map(serializeFlower),
    viewer: buildViewer(visitorId)
  };
}

function createFlowerForVisitor(visitorId, idempotencyKey, requestedX, requestedY) {
  return withWriteTransaction(function () {
    const existingRequest = findPlantRequestStmt.get(visitorId, idempotencyKey);
    if (existingRequest && existingRequest.flower_id) {
      const flower = getFlowerByIdStmt.get(existingRequest.flower_id);
      return {
        status: 'duplicate_request',
        flower
      };
    }

    const existingFlower = getVisitorFlowerStmt.get(visitorId);
    if (existingFlower) {
      if (!existingRequest) {
        insertPlantRequestStmt.run(visitorId, idempotencyKey, existingFlower.id, nowIso());
      } else if (!existingRequest.flower_id) {
        updatePlantRequestFlowerStmt.run(existingFlower.id, visitorId, idempotencyKey);
      }

      return {
        status: 'already_planted',
        flower: existingFlower
      };
    }

    if (!existingRequest) {
      insertPlantRequestStmt.run(visitorId, idempotencyKey, null, nowIso());
    }

    const flowerPayload = buildFlowerPayload(requestedX, requestedY);
    const result = insertFlowerStmt.run(
      visitorId,
      flowerPayload.x_ratio,
      flowerPayload.y_ratio,
      flowerPayload.size,
      flowerPayload.flip,
      flowerPayload.palette_index,
      flowerPayload.stem_index,
      flowerPayload.hidden_petals,
      flowerPayload.dimmed_petals,
      flowerPayload.sway_angle,
      flowerPayload.sway_duration,
      flowerPayload.sway_delay,
      flowerPayload.sway_lift,
      flowerPayload.created_at
    );

    updatePlantRequestFlowerStmt.run(Number(result.lastInsertRowid), visitorId, idempotencyKey);

    return {
      status: 'created',
      flower: getFlowerByIdStmt.get(Number(result.lastInsertRowid))
    };
  });
}

async function handleApiRequest(req, res, url) {
  const visitor = getOrCreateVisitor(req, res);

  if (req.method === 'GET' && url.pathname === '/api/health') {
    sendJson(res, 200, { success: true });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/api/garden') {
    const afterId = Math.max(0, Number(url.searchParams.get('after_id') || 0));
    sendJson(res, 200, getGardenSnapshot(afterId, visitor.id));
    return;
  }

  if (req.method === 'POST' && url.pathname === '/api/flowers') {
    const idempotencyKey = req.headers['x-idempotency-key'];
    if (!idempotencyKey || String(idempotencyKey).trim().length < 8) {
      sendJson(res, 400, {
        success: false,
        message: '缺少有效的幂等键'
      });
      return;
    }

    const body = await readJsonBody(req);
    const xRatio = normalizeRatio(body.x_ratio, Math.random());
    const yRatio = normalizeRatio(body.y_ratio, Math.random());
    const result = createFlowerForVisitor(visitor.id, String(idempotencyKey), xRatio, yRatio);
    const count = countFlowersStmt.get().count;
    const latestId = latestFlowerIdStmt.get().latest_id;

    sendJson(res, result.status === 'created' ? 201 : 200, {
      success: true,
      status: result.status,
      count,
      latest_id: latestId,
      flower: serializeFlower(result.flower),
      viewer: buildViewer(visitor.id)
    });
    return;
  }

  sendJson(res, 404, {
    success: false,
    message: '接口不存在'
  });
}

const server = http.createServer(async function (req, res) {
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

    if (url.pathname.startsWith('/api/')) {
      await handleApiRequest(req, res, url);
      return;
    }

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      sendText(res, 405, 'Method Not Allowed');
      return;
    }

    serveStaticFile(req, res, url.pathname);
  } catch (error) {
    console.error(error);
    sendJson(res, 500, {
      success: false,
      message: '服务器内部错误'
    });
  }
});

if (require.main === module) {
  server.listen(PORT, HOST, function () {
    console.log(`共享花园已启动: http://${HOST}:${PORT}`);
  });
}

module.exports = {
  db,
  server,
  getOrCreateVisitor,
  createVisitorRecord,
  createFlowerForVisitor,
  getGardenSnapshot,
  serializeFlower
};
