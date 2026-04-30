<template>
  <div class="rose-backdrop" aria-hidden="true">
    <span
      v-for="rose in roses"
      :key="rose.id"
      class="rose-container"
      :style="{
        left: rose.left,
        top: rose.top,
        width: rose.size + 'px',
        height: rose.size + 'px',
        opacity: String(rose.opacity),
        '--flip': rose.flip ? 'scaleX(-1)' : 'scaleX(1)',
        '--rotate': rose.rotate + 'deg',
        '--sway': rose.sway + 'deg',
        '--duration': rose.duration + 's',
        '--delay': rose.delay + 's',
      }"
    >
      <svg class="rose-svg" viewBox="0 0 188 264" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient :id="`petal-main-${rose.id}`" cx="64" cy="44" r="92" gradientUnits="userSpaceOnUse">
            <stop offset="0" :stop-color="rose.palette.light" />
            <stop offset="0.45" :stop-color="rose.palette.mid" />
            <stop offset="1" :stop-color="rose.palette.shadow" />
          </radialGradient>
          <radialGradient :id="`petal-core-${rose.id}`" cx="88" cy="88" r="58" gradientUnits="userSpaceOnUse">
            <stop offset="0" :stop-color="rose.palette.core" />
            <stop offset="1" :stop-color="rose.palette.mid" />
          </radialGradient>
          <linearGradient :id="`stem-${rose.id}`" x1="78" y1="148" x2="90" y2="264" gradientUnits="userSpaceOnUse">
            <stop offset="0" stop-color="#bada55" />
            <stop offset="1" stop-color="#3b480e" />
          </linearGradient>
          <radialGradient :id="`leaf-${rose.id}`" cx="42" cy="156" r="48" gradientUnits="userSpaceOnUse">
            <stop offset="0" stop-color="#6f8126" />
            <stop offset="1" stop-color="#aeba76" />
          </radialGradient>
        </defs>

        <g class="rose-stem-group">
          <path
            :d="rose.stem"
            :fill="`url(#stem-${rose.id})`"
            stroke="transparent"
          />
          <path
            d="M 46.953 119.95 C 45.235 117.533 42.584 112.794 41.114 110.103 C 40.46 108.906 40.478 108.549 40.039 108.114 C 35.996 104.1 26.687 103.38 26.687 103.38 C 26.687 103.38 34.854 97.115 39.086 97.698 C 44.858 98.492 50.547 103.452 55.298 110.008 C 62.512 119.962 72.703 149.303 72.703 149.303 C 72.703 149.303 55.029 131.31 46.953 119.95 Z"
            :fill="`url(#leaf-${rose.id})`"
          />
          <path
            d="M 125.945 180.107 L 109.454 169.372 C 106.365 165.002 109.271 159.533 100.933 155.899 C 94.395 153.05 66.464 149.933 78.394 155.058 C 93.119 161.382 82.057 170.1 125.945 180.107 Z"
            :fill="`url(#leaf-${rose.id})`"
          />
        </g>

        <g class="rose-petal-group">
          <path
            d="M 39.237 122.683 C 46.749 118.213 62.759 115.009 61.295 123.063 C 61.295 123.063 66.241 120.779 68.9 120.401 C 73.55 119.739 78.314 120.546 82.971 121.162 C 91.45 122.284 99.617 125.191 108.071 126.486 C 110.714 126.891 116.057 127.246 116.057 127.246 C 116.057 127.246 120.185 127.658 122.142 128.767 C 123.524 129.55 124.424 132.951 124.424 132.951 C 124.424 132.951 121.753 137.349 119.86 139.035 C 114.6 143.72 107.654 146.072 101.606 149.684 C 99.31 151.055 97.21 152.793 94.761 153.867 C 91.38 155.35 87.793 156.625 84.112 156.909 C 81.055 157.145 77.91 156.69 74.985 155.769 C 70.063 154.22 65.03 152.103 61.295 148.543 C 58.95 146.308 58.664 142.444 56.351 140.176 C 53.96 137.831 50.7 136.511 47.604 135.233 C 42.743 133.227 32.392 131.049 32.392 131.049 C 32.392 131.049 31.189 128.709 31.631 127.627 C 32.774 124.828 36.639 124.229 39.237 122.683 Z"
            :fill="`url(#petal-main-${rose.id})`"
          />
          <path
            d="M 44.942 120.781 C 41.293 117.204 34.996 117.021 31.631 113.175 C 28.748 109.88 28.911 104.778 26.688 101.006 C 24.536 97.356 20.866 94.76 18.701 91.118 C 15.826 86.281 12.931 81.109 12.236 75.526 C 11.587 70.314 12.3 64.695 14.518 59.934 C 18.386 51.632 24.959 44.177 32.772 39.398 C 35.788 37.553 39.364 37.623 43.04 36.736 C 44.401 36.407 43.421 32.553 43.421 32.553 C 43.421 32.553 44.315 31.034 47.984 32.172 C 47.984 32.172 51.048 22.903 54.829 20.383 C 58.872 17.689 64.775 16.663 69.281 18.482 C 78.148 22.061 87.155 40.919 87.155 40.919 C 129.95 85.497 103.042 177.736 44.942 120.781 Z"
            :fill="`url(#petal-main-${rose.id})`"
            opacity="0.95"
          />
          <path
            d="M 73.464 53.849 L 87.535 41.68 C 87.535 41.68 105.977 36.949 113.775 40.919 C 116.376 42.243 118.719 48.145 118.719 48.145 C 118.719 48.145 125.275 48.072 128.227 49.286 C 134.91 52.035 141.618 56.401 145.34 62.596 C 151.436 72.743 153.533 85.935 151.425 97.583 C 149.908 105.969 143.531 112.765 138.495 119.64 C 134.358 125.288 124.424 135.233 124.424 135.233 C 79.951 183.412 45.768 83.853 73.464 53.849 Z"
            :fill="`url(#petal-main-${rose.id})`"
            opacity="0.92"
          />
          <path
            d="M 112.254 128.767 C 132.537 99.358 127.585 45.893 100.845 62.596 C 72.14 80.525 55.462 179.114 112.254 128.767 Z"
            :fill="`url(#petal-core-${rose.id})`"
            opacity="0.8"
          />
          <path
            d="M 47.239 119.453 L 46.478 100.819 C 33.928 66.212 37.351 54.17 56.746 64.691 C 78.482 76.482 88.877 98.92 87.93 132.003 C 87.522 146.276 73.958 142.092 47.239 119.453 Z"
            :fill="`url(#petal-core-${rose.id})`"
            opacity="0.78"
          />
          <path
            d="M 108.832 77.808 C 97.54 33.77 37.151 58.943 46.083 93.78 C 73.235 179.557 125.789 131.376 108.832 77.808 Z"
            :fill="`url(#petal-core-${rose.id})`"
            opacity="0.86"
          />
          <path
            d="M 55.21 105.95 C 57.733 114.529 114.801 99.399 112.254 90.738 C 123.536 115.964 118.212 136.627 97.042 142.078 C 80.803 146.259 65.338 131.428 55.21 105.95 Z"
            :fill="`url(#petal-main-${rose.id})`"
          />
        </g>
      </svg>
    </span>
  </div>
</template>

<script setup lang="ts">
interface RoseSpec {
  id: number
  left: string
  top: string
  size: number
  rotate: number
  opacity: number
  sway: number
  duration: number
  delay: number
  flip: boolean
  palette: RosePalette
  stem: string
}

interface RosePalette {
  light: string
  mid: string
  shadow: string
  core: string
}

const ROSE_COUNT = 55 + Math.floor(Math.random() * 18)
const PALETTES: RosePalette[] = [
  { light: '#ffe3ea', mid: '#f26c8f', shadow: '#bf3b60', core: '#8f1d3b' },
  { light: '#fffef9', mid: '#f5efe2', shadow: '#d8d0c0', core: '#b7ae9f' },
  { light: '#fdf0f4', mid: '#f7d4de', shadow: '#e7a6b6', core: '#cb8799' },
  { light: '#fff1ea', mid: '#f8d8cd', shadow: '#e8b1a3', core: '#cb8f83' },
  { light: '#fdf0f7', mid: '#f4d4e3', shadow: '#e2a8bf', core: '#c687a0' },
  { light: '#fff4ed', mid: '#f7dccd', shadow: '#e4b49e', core: '#c9947d' },
]

const STEMS = [
  'M 77.412 165.402 C 76.838 193.746 77.692 226.143 80.04 260.956 C 80.223 263.67 83.56 264.17 83.94 261.489 C 88.758 227.089 91.033 194.79 90.918 166.349 C 90.88 156.688 79.848 155.096 77.412 165.402 Z',
  'M 78.782 165.164 C 70.951 191.015 65.787 223.381 68.587 257.011 L 76.978 257.011 C 84.987 225.667 88.888 195.432 88.273 165.811 C 88.103 157.56 81.013 155.514 78.782 165.164 Z',
  'M 77.986 165.164 C 81.915 193.818 87.633 224.147 95.719 256.857 L 104.133 256.857 C 101.188 224.301 95.818 194.09 86.801 165.631 C 84.383 158.002 80.197 155.956 77.986 165.164 Z',
]

function seeded(index: number, salt: number) {
  const value = Math.sin(index * 12.9898 + salt * 78.233 + Math.random()) * 43758.5453
  return value - Math.floor(value)
}

function makeRose(index: number): RoseSpec {
  return {
    id: index,
    left: `${Number((4 + seeded(index, 1) * 92).toFixed(2))}%`,
    top: `${Number((1 + seeded(index, 2) * 92).toFixed(2))}%`,
    size: Math.round(104 + seeded(index, 3) * 28),
    rotate: Math.round(-14 + seeded(index, 4) * 28),
    opacity: Number((0.4 + seeded(index, 5) * 0.34).toFixed(2)),
    sway: Number((1.8 + seeded(index, 6) * 1.8).toFixed(1)),
    duration: Number((5 + seeded(index, 7) * 2.1).toFixed(1)),
    delay: Number((-1 * seeded(index, 8) * 4).toFixed(1)),
    flip: seeded(index, 9) > 0.5,
    palette: PALETTES[Math.floor(seeded(index, 10) * PALETTES.length)] || PALETTES[0],
    stem: STEMS[Math.floor(seeded(index, 11) * STEMS.length)] || STEMS[0],
  }
}

const roses = Array.from({ length: ROSE_COUNT }, (_, index) => makeRose(index))
</script>

<style scoped>
.rose-backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
  background: #FFF8F0;
}

.rose-container {
  position: absolute;
  transform: translate(-50%, 0) rotate(var(--rotate));
  transform-origin: bottom center;
  animation: roseAppear 1.8s cubic-bezier(0.22, 1, 0.36, 1) both;
  z-index: 1;
}

.rose-svg {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: 50% 100%;
  animation: roseSway var(--duration) ease-in-out var(--delay) infinite alternate;
  filter: drop-shadow(0 8px 12px rgba(141, 41, 54, 0.08));
}

.rose-stem-group,
.rose-petal-group {
  transform-origin: 50% 100%;
  transform: var(--flip);
}

@keyframes roseAppear {
  0% {
    opacity: 0;
    transform: translate(-50%, 0) scale(0.1) rotate(var(--rotate));
  }

  100% {
    opacity: 1;
    transform: translate(-50%, 0) scale(1) rotate(var(--rotate));
  }
}

@keyframes roseSway {
  0% {
    transform: rotate(calc(var(--sway) * -1)) translateY(0);
  }

  50% {
    transform: rotate(calc(var(--sway) * 0.25)) translateY(-1px);
  }

  100% {
    transform: rotate(var(--sway)) translateY(-2px);
  }
}

@media (max-width: 720px) {
  .rose-container {
    opacity: 0.58 !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rose-container,
  .rose-svg {
    animation: none;
  }
}
</style>
