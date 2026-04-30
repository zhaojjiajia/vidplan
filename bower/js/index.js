// 共享花园前端：
// 1. 页面初始化时从后端拉取全局花园。
// 2. 点击时向后端提交一次种花请求。
// 3. 后端以访客 Cookie 为准，限制每位访客只种一次。

(function () {
  'use strict';

  const garden = document.getElementById('garden');
  const roseBackLayer = document.getElementById('roseBackLayer');
  const roseFrontLayer = document.getElementById('roseFrontLayer');
  const counterEl = document.getElementById('counter');
  const hintEl = document.querySelector('.hint');
  const roseTemplate = document.getElementById('roseTemplate');
  const plantingAudio = new Audio('music.mp3');

  const API_GARDEN_URL = '/api/garden';
  const API_PLANT_URL = '/api/flowers';
  const HINT_FADE_DURATION_MS = 2500;
  const SUCCESS_HINT_HOLD_MS = 1400;
  const BLOOM_TRIGGER_DELAY_MS = 520;
  const GARDEN_POLL_INTERVAL_MS = 4000;
  const CLIENT_ID_STORAGE_KEY = 'garden_client_id';
  const IDB_NAME = 'garden-identity';
  const IDB_STORE = 'kv';
  const FINGERPRINT_VERSION = 'v1';
  const DEFAULT_HINT_TEXT = '轻点此间，让一朵玫瑰为你盛开';
  const PLANTED_HINT_TEXT = '且待春风翻旧页，邀君同赏满庭芳';
  const ERROR_HINT_TEXT = '风声稍迟，唯余这园中孤意，且等风声续上旧章';
  const AUTH_READY_TIMEOUT_MS = 900;
  const PETAL_GRADIENT_RULES = {
    'gradient-0': ['light', 'shadow'],
    'gradient-1': ['light', 'shadow'],
    'gradient-2': ['light', 'shadow'],
    'gradient-4': ['mid', 'shadow'],
    'gradient-6': ['core', 'mid'],
    'gradient-7': ['light', 'shadow'],
    'gradient-8': ['core', 'mid'],
    'gradient-9': ['shadow', 'mid'],
    'gradient-10': ['mid', 'shadow'],
    'gradient-11': ['mid', 'core'],
    'gradient-12': ['light', 'shadow']
  };
  const PETAL_PALETTES = [
    { light: '#ffe3ea', mid: '#f26c8f', shadow: '#bf3b60', core: '#8f1d3b' },
    { light: '#fffef9', mid: '#f5efe2', shadow: '#d8d0c0', core: '#b7ae9f' },
    { light: '#fdf0f4', mid: '#f7d4de', shadow: '#e7a6b6', core: '#cb8799' },
    { light: '#fff1ea', mid: '#f8d8cd', shadow: '#e8b1a3', core: '#cb8f83' },
    { light: '#fdf0f7', mid: '#f4d4e3', shadow: '#e2a8bf', core: '#c687a0' },
    { light: '#fff4ed', mid: '#f7dccd', shadow: '#e4b49e', core: '#c9947d' }
  ];
  const STEM_SHAPES = [
    {
      from: 'M 79.864 165.164 C 78.245 194.101 78.607 224.431 80.568 257.623 L 88.417 257.623 C 89.642 224.503 89.356 194.162 87.114 165.955 C 86.478 157.949 80.766 156.405 79.864 165.164 Z',
      to: 'M 78.312 165.164 C 76.989 193.769 77.439 223.807 80.496 257.161 L 88.742 257.161 C 90.043 223.285 89.967 193.491 88.553 166.027 C 88.083 157.188 80.097 155.91 78.312 165.164 Z'
    },
    {
      from: 'M 80.226 165.164 C 73.184 191.165 68.538 223.607 71.757 257.515 L 80.002 257.515 C 86.212 226.653 88.715 196.031 86.947 165.955 C 86.48 158.003 81.865 156.442 80.226 165.164 Z',
      to: 'M 78.782 165.164 C 70.951 191.015 65.787 223.381 68.587 257.011 L 76.978 257.011 C 84.987 225.667 88.888 195.432 88.273 165.811 C 88.103 157.56 81.013 155.514 78.782 165.164 Z'
    },
    {
      from: 'M 79.286 165.164 C 82.906 193.909 87.968 224.83 94.058 257.353 L 102.339 257.353 C 100.453 225.449 95.808 194.894 87.631 165.883 C 85.523 158.408 80.832 156.334 79.286 165.164 Z',
      to: 'M 77.986 165.164 C 81.915 193.818 87.633 224.147 95.719 256.857 L 104.133 256.857 C 101.188 224.301 95.818 194.09 86.801 165.631 C 84.383 158.002 80.197 155.956 77.986 165.164 Z'
    }
  ];

  let flowerCount = 0;
  let W = window.innerWidth;
  let H = window.innerHeight;
  let latestFlowerId = 0;
  let canPlant = true;
  let isSubmitting = false;
  let hintDismissed = false;
  let initialized = false;
  let hasPlantedThisSession = false;
  let pollTimer = null;
  let hintTimer = null;
  let hideHintTimer = null;
  let transientHintActive = false;
  let visitorIdentity = {
    clientId: '',
    fingerprintHash: '',
    fingerprintVersion: FINGERPRINT_VERSION
  };
  let vidPlanAccessToken = '';
  let authReadyResolver = null;
  const renderedFlowers = new Map();

  plantingAudio.preload = 'auto';
  plantingAudio.loop = true;
  plantingAudio.volume = 0.32;

  function setCounter(count) {
    flowerCount = count;
    counterEl.textContent = '🌹 ' + count + ' 朵玫瑰绽放';
    counterEl.classList.add('visible');
  }

  function setHintText(text) {
    if (!hintEl) {
      return;
    }
    hintEl.textContent = text;
  }

  function showPlantableHint() {
    if (!hintEl || hintDismissed) {
      return;
    }

    hintEl.style.display = 'block';
    hintEl.style.opacity = '1';
    hintEl.style.transition = '';
    hintEl.style.animation = 'hintFade 4s ease-in-out infinite';
    setHintText(DEFAULT_HINT_TEXT);
  }

  function showPlantedHint() {
    if (!hintEl) {
      return;
    }

    hintEl.style.display = 'block';
    hintEl.style.animation = 'none';
    hintEl.style.transition = '';
    hintEl.style.opacity = '2';
    setHintText(PLANTED_HINT_TEXT);
  }

  function showErrorHint() {
    if (!hintEl) {
      return;
    }

    hintEl.style.display = 'block';
    hintEl.style.animation = 'none';
    hintEl.style.transition = '';
    hintEl.style.opacity = '0.86';
    setHintText(ERROR_HINT_TEXT);
  }

  function dismissHintSlowly() {
    if (!hintEl || hintDismissed) {
      return;
    }

    if (hintTimer) {
      clearTimeout(hintTimer);
      hintTimer = null;
    }
    if (hideHintTimer) {
      clearTimeout(hideHintTimer);
      hideHintTimer = null;
    }
    hintDismissed = true;
    transientHintActive = false;
    hintEl.style.animation = 'none';
    hintEl.style.opacity = '1';
    hintEl.style.transition = 'opacity ' + (HINT_FADE_DURATION_MS / 1000) + 's ease';
    requestAnimationFrame(function () {
      hintEl.style.opacity = '0';
    });
    hideHintTimer = setTimeout(function () {
      hintEl.style.display = 'none';
      hideHintTimer = null;
    }, HINT_FADE_DURATION_MS);
  }

  function showTransientHint(text, holdMs) {
    if (!hintEl) {
      return;
    }

    if (hintTimer) {
      clearTimeout(hintTimer);
      hintTimer = null;
    }
    if (hideHintTimer) {
      clearTimeout(hideHintTimer);
      hideHintTimer = null;
    }
    hintDismissed = false;
    transientHintActive = true;
    hintEl.style.display = 'block';
    hintEl.style.animation = 'none';
    hintEl.style.transition = '';
    hintEl.style.opacity = '1';
    setHintText(text);

    hintTimer = setTimeout(function () {
      hintTimer = null;
      dismissHintSlowly();
    }, holdMs);
  }

  function hideHintImmediately() {
    if (!hintEl) {
      return;
    }
    if (hintTimer) {
      clearTimeout(hintTimer);
      hintTimer = null;
    }
    if (hideHintTimer) {
      clearTimeout(hideHintTimer);
      hideHintTimer = null;
    }
    hintDismissed = true;
    transientHintActive = false;
    hintEl.style.animation = 'none';
    hintEl.style.transition = '';
    hintEl.style.opacity = '0';
    hintEl.style.display = 'none';
  }

  function syncViewerState(viewer, options) {
    if (!viewer) {
      return;
    }

    canPlant = !!viewer.can_plant;
    if (canPlant) {
      showPlantableHint();
      return;
    }

    if (options && options.justPlanted) {
      hasPlantedThisSession = true;
      dismissHintSlowly();
      return;
    }

    if (transientHintActive) {
      return;
    }

    hideHintImmediately();
  }

  function getAudioEngine() {
    return plantingAudio;
  }

  function playPlantingMusic() {
    const audio = getAudioEngine();
    if (!audio || !audio.paused) {
      return;
    }

    audio.play().catch(function () {
      // 浏览器如果临时拦截播放，这里静默失败，下一次用户交互还会再尝试。
    });
  }

  function applySway(svg, flip, flower) {
    svg.classList.add('is-swaying');
    svg.style.setProperty('--flip-transform', flip ? 'scaleX(-1)' : 'scaleX(1)');
    svg.style.setProperty('--sway-angle', flower.sway_angle + 'deg');
    svg.style.setProperty('--sway-duration', flower.sway_duration + 's');
    svg.style.setProperty('--sway-delay', flower.sway_delay + 's');
    svg.style.setProperty('--sway-lift', flower.sway_lift + 'px');
  }

  function prepareSvg(svg, uid) {
    const gradients = svg.querySelectorAll('.g');
    gradients.forEach(function (gradient) {
      const baseId = gradient.getAttribute('data-id');
      gradient.setAttribute('id', uid + '-' + baseId);
    });

    const paths = svg.querySelectorAll('path[data-fill]');
    paths.forEach(function (shapePath) {
      const gradRef = shapePath.getAttribute('data-fill');
      shapePath.style.fill = 'url(#' + uid + '-' + gradRef + ')';
    });

    svg.style.width = '100%';
    svg.style.height = '100%';
  }

  function applyPetalPalette(svg, paletteIndex) {
    const palette = PETAL_PALETTES[paletteIndex] || PETAL_PALETTES[0];
    const gradients = svg.querySelectorAll('.g');

    gradients.forEach(function (gradient) {
      const colorKeys = PETAL_GRADIENT_RULES[gradient.getAttribute('data-id')];
      if (!colorKeys) {
        return;
      }

      const stops = gradient.querySelectorAll('stop');
      if (stops[0]) {
        stops[0].style.stopColor = palette[colorKeys[0]];
      }
      if (stops[1]) {
        stops[1].style.stopColor = palette[colorKeys[1]];
      }
    });
  }

  function applyStemShape(svg, stemIndex) {
    const stem = svg.querySelector('.rose-stem');
    const stemAnimation = stem ? stem.querySelector('.rose-anim') : null;
    const stemShape = STEM_SHAPES[stemIndex] || STEM_SHAPES[0];

    if (!stem || !stemAnimation) {
      return;
    }

    stem.setAttribute('d', stemShape.from);
    stemAnimation.setAttribute('to', stemShape.to);
  }

  function applyPetalVisibility(svg, hiddenPetals, dimmedPetals) {
    const hiddenSet = new Set(hiddenPetals || []);
    const dimmedSet = new Set(dimmedPetals || []);

    svg.querySelectorAll('.rose-petal-optional').forEach(function (petal, index) {
      if (hiddenSet.has(index)) {
        petal.style.opacity = '0';
        return;
      }

      if (dimmedSet.has(index)) {
        petal.style.opacity = '0.82';
        return;
      }

      petal.style.opacity = '';
    });
  }

  function forceBloomedState(svg) {
    svg.querySelectorAll('.rose-anim').forEach(function (anim) {
      const targetValue = anim.getAttribute('to');
      if (targetValue) {
        anim.parentNode.setAttribute('d', targetValue);
      }
    });
  }

  function createRoseContainer(left, top, size, animate) {
    const container = document.createElement('div');
    container.className = 'rose-container';
    container.style.left = left + 'px';
    container.style.top = top + 'px';
    container.style.width = size + 'px';
    container.style.height = size + 'px';

    if (!animate) {
      container.style.animation = 'none';
      container.style.opacity = '1';
      container.style.transform = 'scale(1)';
    }

    return container;
  }

  function triggerAnimations(container) {
    container.querySelectorAll('.rose-anim').forEach(function (anim) {
      anim.beginElement();
    });
  }

  function getFlowerLayout(flower) {
    const size = flower.size;
    const minX = size * 0.26;
    const maxX = W - size * 0.26;
    const minTop = Math.max(8, H * 0.02);
    const maxTop = Math.max(minTop + 1, H - size * 0.94);
    const centerX = Math.min(maxX, Math.max(minX, W * flower.x_ratio));
    const top = Math.min(maxTop, Math.max(minTop, H * flower.y_ratio));

    return {
      left: centerX - size / 2,
      top: top,
      size: size
    };
  }

  function updateRenderedFlowerPosition(entry) {
    const layout = getFlowerLayout(entry.flower);
    entry.backContainer.style.left = layout.left + 'px';
    entry.backContainer.style.top = layout.top + 'px';
    entry.backContainer.style.width = layout.size + 'px';
    entry.backContainer.style.height = layout.size + 'px';
    entry.frontContainer.style.left = layout.left + 'px';
    entry.frontContainer.style.top = layout.top + 'px';
    entry.frontContainer.style.width = layout.size + 'px';
    entry.frontContainer.style.height = layout.size + 'px';
  }

  function renderFlower(flower, options) {
    if (renderedFlowers.has(flower.id)) {
      return;
    }

    const animate = !!(options && options.animate);
    const layout = getFlowerLayout(flower);
    const uid = 'r' + flower.id;

    const backClone = roseTemplate.content.cloneNode(true);
    const frontClone = roseTemplate.content.cloneNode(true);
    const backSvg = backClone.querySelector('.rose-svg');
    const frontSvg = frontClone.querySelector('.rose-svg');

    backSvg.querySelectorAll('.rose-petal').forEach(function (petal) {
      petal.remove();
    });
    frontSvg.querySelectorAll('.rose-stem, .rose-leaf').forEach(function (part) {
      part.remove();
    });

    prepareSvg(backSvg, uid + '-back');
    prepareSvg(frontSvg, uid + '-front');
    applyStemShape(backSvg, flower.stem_index);
    applyPetalPalette(frontSvg, flower.palette_index);
    applyPetalVisibility(frontSvg, flower.hidden_petals, flower.dimmed_petals);
    applySway(backSvg, flower.flip, flower);
    applySway(frontSvg, flower.flip, flower);

    if (!animate) {
      forceBloomedState(backSvg);
      forceBloomedState(frontSvg);
    }

    const backContainer = createRoseContainer(layout.left, layout.top, layout.size, animate);
    const frontContainer = createRoseContainer(layout.left, layout.top, layout.size, animate);

    backContainer.appendChild(backSvg);
    frontContainer.appendChild(frontSvg);
    roseBackLayer.appendChild(backContainer);
    roseFrontLayer.appendChild(frontContainer);

    if (animate) {
      setTimeout(function () {
        triggerAnimations(backContainer);
        triggerAnimations(frontContainer);
      }, BLOOM_TRIGGER_DELAY_MS);
    }

    renderedFlowers.set(flower.id, {
      flower: flower,
      backContainer: backContainer,
      frontContainer: frontContainer
    });
  }

  function renderFlowers(flowers, options) {
    flowers.forEach(function (flower) {
      renderFlower(flower, options);
      latestFlowerId = Math.max(latestFlowerId, flower.id);
    });
  }

  function createRipple(x, y) {
    const ripple = document.createElement('div');
    ripple.className = 'ripple';
    ripple.style.left = (x - 60) + 'px';
    ripple.style.top = (y - 60) + 'px';
    document.body.appendChild(ripple);
    setTimeout(function () {
      ripple.remove();
    }, 800);
  }

  function requestJson(url, options) {
    const nextOptions = options || {};
    const headers = Object.assign({}, nextOptions.headers || {});

    if (vidPlanAccessToken) {
      headers.Authorization = 'Bearer ' + vidPlanAccessToken;
    }
    if (visitorIdentity.clientId) {
      headers['X-Client-Id'] = visitorIdentity.clientId;
    }
    if (visitorIdentity.fingerprintHash) {
      headers['X-Fingerprint-Hash'] = visitorIdentity.fingerprintHash;
      headers['X-Fingerprint-Version'] = visitorIdentity.fingerprintVersion;
    }

    return fetch(url, Object.assign({}, nextOptions, {
      headers: headers
    })).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          const message = data && data.message ? data.message : '请求失败';
          throw new Error(message);
        }
        return data;
      });
    });
  }

  function applyGardenSnapshot(payload, options) {
    setCounter(payload.count || 0);
    renderFlowers(payload.flowers || [], options);
    latestFlowerId = Math.max(latestFlowerId, payload.latest_id || 0);
    syncViewerState(payload.viewer, options);
  }

  function fetchGarden(afterId, options) {
    const url = afterId > 0 ? API_GARDEN_URL + '?after_id=' + afterId : API_GARDEN_URL;
    return requestJson(url, { credentials: 'same-origin' }).then(function (payload) {
      applyGardenSnapshot(payload, options);
      return payload;
    });
  }

  function plantFlower(clickX, clickY) {
    if (!canPlant || isSubmitting) {
      if (!canPlant) {
        showTransientHint(PLANTED_HINT_TEXT, SUCCESS_HINT_HOLD_MS);
      }
      return;
    }

    isSubmitting = true;
    const xRatio = W ? clickX / W : 0.5;
    const yRatio = H ? clickY / H : 0.5;
    const idempotencyKey = window.crypto && window.crypto.randomUUID
      ? window.crypto.randomUUID()
      : 'plant-' + Date.now() + '-' + Math.random().toString(16).slice(2);

    requestJson(API_PLANT_URL, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Idempotency-Key': idempotencyKey
      },
      body: JSON.stringify({
        x_ratio: xRatio,
        y_ratio: yRatio
      })
    }).then(function (payload) {
      const justCreated = payload.status === 'created';
      if (payload.flower) {
        renderFlower(payload.flower, { animate: !renderedFlowers.has(payload.flower.id) });
        latestFlowerId = Math.max(latestFlowerId, payload.flower.id);
      }
      setCounter(payload.count || flowerCount);
      syncViewerState(payload.viewer, { justPlanted: justCreated });
      if (justCreated) {
        hasPlantedThisSession = true;
        playPlantingMusic();
      }
    }).catch(function () {
      showErrorHint();
    }).finally(function () {
      isSubmitting = false;
    });
  }

  function pollGarden() {
    fetchGarden(latestFlowerId, { animate: true }).catch(function () {
      // 轮询失败时保持静默，避免频繁打扰用户。
    });
  }

  function startPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
    }
    pollTimer = setInterval(pollGarden, GARDEN_POLL_INTERVAL_MS);
  }

  function handlePlantEvent(clientX, clientY) {
    createRipple(clientX, clientY);
    plantFlower(clientX, clientY);
  }

  function syncAllFlowerLayouts() {
    renderedFlowers.forEach(function (entry) {
      updateRenderedFlowerPosition(entry);
    });
  }

  function bootstrapGarden() {
    fetchGarden(0, { animate: false }).then(function () {
      initialized = true;
      startPolling();
    }).catch(function () {
      showErrorHint();
    });
  }

  window.addEventListener('resize', function () {
    W = window.innerWidth;
    H = window.innerHeight;
    if (initialized) {
      syncAllFlowerLayouts();
    }
  });

  garden.addEventListener('click', function (e) {
    handlePlantEvent(e.clientX, e.clientY);
  });

  garden.addEventListener('touchstart', function (e) {
    e.preventDefault();
    const touch = e.touches[0];
    handlePlantEvent(touch.clientX, touch.clientY);
  }, { passive: false });

  function generateClientId() {
    if (window.crypto && window.crypto.randomUUID) {
      return window.crypto.randomUUID();
    }
    return 'client-' + Date.now() + '-' + Math.random().toString(16).slice(2);
  }

  function openIdentityDb() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) {
        resolve(null);
        return;
      }

      const request = window.indexedDB.open(IDB_NAME, 1);
      request.onupgradeneeded = function () {
        const db = request.result;
        if (!db.objectStoreNames.contains(IDB_STORE)) {
          db.createObjectStore(IDB_STORE);
        }
      };
      request.onsuccess = function () {
        resolve(request.result);
      };
      request.onerror = function () {
        reject(request.error);
      };
    });
  }

  function readClientIdFromDb() {
    return openIdentityDb().then(function (db) {
      if (!db) {
        return '';
      }
      return new Promise(function (resolve, reject) {
        const tx = db.transaction(IDB_STORE, 'readonly');
        const store = tx.objectStore(IDB_STORE);
        const request = store.get(CLIENT_ID_STORAGE_KEY);
        request.onsuccess = function () {
          resolve(request.result || '');
        };
        request.onerror = function () {
          reject(request.error);
        };
      });
    }).catch(function () {
      return '';
    });
  }

  function writeClientIdToDb(clientId) {
    return openIdentityDb().then(function (db) {
      if (!db) {
        return;
      }
      return new Promise(function (resolve, reject) {
        const tx = db.transaction(IDB_STORE, 'readwrite');
        tx.objectStore(IDB_STORE).put(clientId, CLIENT_ID_STORAGE_KEY);
        tx.oncomplete = function () {
          resolve();
        };
        tx.onerror = function () {
          reject(tx.error);
        };
      });
    }).catch(function () {
      return undefined;
    });
  }

  function readClientIdFromStorage() {
    try {
      return window.localStorage.getItem(CLIENT_ID_STORAGE_KEY) || '';
    } catch (error) {
      return '';
    }
  }

  function writeClientIdToStorage(clientId) {
    try {
      window.localStorage.setItem(CLIENT_ID_STORAGE_KEY, clientId);
    } catch (error) {
      // 本地存储不可用时忽略，后续仍可依赖 Cookie 与指纹。
    }
  }

  function getWebGlFingerprint() {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) {
        return 'no-webgl';
      }
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (!debugInfo) {
        return 'webgl';
      }
      const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || '';
      const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || '';
      return vendor + '|' + renderer;
    } catch (error) {
      return 'webgl-error';
    }
  }

  function hashString(value) {
    if (window.crypto && window.crypto.subtle && window.TextEncoder) {
      const encoder = new window.TextEncoder();
      return window.crypto.subtle.digest('SHA-256', encoder.encode(value)).then(function (buffer) {
        const bytes = Array.from(new Uint8Array(buffer));
        return bytes.map(function (byte) {
          return byte.toString(16).padStart(2, '0');
        }).join('');
      });
    }

    let hash = 0;
    for (let i = 0; i < value.length; i += 1) {
      hash = ((hash << 5) - hash) + value.charCodeAt(i);
      hash |= 0;
    }
    return Promise.resolve('fallback-' + Math.abs(hash));
  }

  function buildFingerprintSource() {
    const timezone = (window.Intl && window.Intl.DateTimeFormat)
      ? window.Intl.DateTimeFormat().resolvedOptions().timeZone
      : '';
    const parts = [
      navigator.userAgent || '',
      navigator.language || '',
      Array.isArray(navigator.languages) ? navigator.languages.join(',') : '',
      navigator.platform || '',
      String(screen.width || 0),
      String(screen.height || 0),
      String(screen.colorDepth || 0),
      String(window.devicePixelRatio || 1),
      String(navigator.hardwareConcurrency || 0),
      String(navigator.deviceMemory || 0),
      String(navigator.maxTouchPoints || 0),
      timezone || '',
      String(!!navigator.webdriver),
      getWebGlFingerprint()
    ];

    return parts.join('||');
  }

  function ensureVisitorIdentity() {
    const storageClientId = readClientIdFromStorage();

    return Promise.resolve(storageClientId).then(function (clientId) {
      if (clientId) {
        return clientId;
      }
      return readClientIdFromDb();
    }).then(function (clientId) {
      const finalClientId = clientId || generateClientId();
      writeClientIdToStorage(finalClientId);
      return writeClientIdToDb(finalClientId).then(function () {
        return finalClientId;
      });
    }).then(function (clientId) {
      return hashString(buildFingerprintSource()).then(function (fingerprintHash) {
        visitorIdentity = {
          clientId: clientId,
          fingerprintHash: fingerprintHash,
          fingerprintVersion: FINGERPRINT_VERSION
        };
      });
    });
  }

  function waitForVidPlanAuth() {
    if (window.parent === window) {
      return Promise.resolve();
    }

    try {
      window.parent.postMessage({ type: 'bower-ready' }, '*');
    } catch (error) {
      // 嵌入环境不可通信时,稍后按匿名访客模式启动。
    }

    return new Promise(function (resolve) {
      if (vidPlanAccessToken) {
        resolve();
        return;
      }

      authReadyResolver = resolve;
      setTimeout(function () {
        if (authReadyResolver) {
          authReadyResolver = null;
          resolve();
        }
      }, AUTH_READY_TIMEOUT_MS);
    });
  }

  window.addEventListener('message', function (event) {
    const data = event.data || {};
    if (!data || data.type !== 'vidplan-auth') {
      return;
    }

    vidPlanAccessToken = data.accessToken || '';
    if (authReadyResolver) {
      const resolve = authReadyResolver;
      authReadyResolver = null;
      resolve();
    }
  });

  waitForVidPlanAuth().then(function () {
    return ensureVisitorIdentity();
  }).then(function () {
    bootstrapGarden();
  }).catch(function () {
    bootstrapGarden();
  });
})();
