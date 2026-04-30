<template>
  <div ref="homeRef" class="home">
    <header class="topbar">
      <div class="topbar-inner">
        <router-link to="/" class="brand" aria-label="VidPlan">
          <span class="brand-name">VidPlan</span>
        </router-link>
        <nav class="top-links">
          <a href="#features" @click.prevent="scrollToSection('features')">功能</a>
          <a href="#how" @click.prevent="scrollToSection('how')">如何工作</a>
        </nav>
        <div class="actions">
          <template v-if="!auth.isLoggedIn">
            <el-button text @click="$router.push('/login')">登录</el-button>
            <el-button type="primary" @click="$router.push('/register')">免费试用</el-button>
          </template>
          <el-button v-else type="primary" @click="$router.push('/app/me/plans')">进入工作台</el-button>
        </div>
      </div>
    </header>

    <section class="hero" data-home-snap>
      <h1 class="hero-title">把你的想法<br/>变成可执行的短视频方案</h1>
      <p class="hero-sub">
        从方向选择、脚本分镜、人设沉淀,到系列内容规划。<br/>
        VidPlan 帮你完成创作前所有的核心准备。
      </p>
    </section>

    <section id="features" class="features" data-home-snap>
      <div class="section-head">
        <h2>专注创作前的关键工作</h2>
        <p>不取代创作者,而是让结构化的事情快十倍。</p>
      </div>
      <div class="feature-grid">
        <article v-for="f in features" :key="f.title" class="feature">
          <div class="feature-icon">
            <component :is="f.icon" />
          </div>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </article>
      </div>
    </section>

    <section id="how" class="how" data-home-snap>
      <div class="section-head">
        <h2>三步从灵感到完整方案</h2>
        <p>每一步都可以独立修改、迭代,直到你满意为止。</p>
      </div>
      <ol class="steps">
        <li v-for="(s, i) in steps" :key="s.title">
          <div class="step-num">{{ String(i + 1).padStart(2, '0') }}</div>
          <h4>{{ s.title }}</h4>
          <p>{{ s.desc }}</p>
        </li>
      </ol>
    </section>

    <footer class="foot" data-home-snap>
      <span>© {{ year }} VidPlan</span>
      <span class="foot-meta">为短视频创作者打造</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  Connection,
  Edit,
  MagicStick,
  TrendCharts,
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const homeRef = ref<HTMLElement | null>(null)

const year = computed(() => new Date().getFullYear())

let activeSnapIndex = 0
let isSnapping = false
let snapTimer: number | undefined
let snapUnlockTimer: number | undefined
let snapMedia: MediaQueryList | undefined
let reduceMotionMedia: MediaQueryList | undefined

const features = [
  { icon: MagicStick,    title: '一句话生成方案', desc: '描述想法,AI 直接产出标题、定位、脚本、分镜、剪辑建议。' },
  { icon: Edit,          title: '所见即所得编辑', desc: '结构化字段实时编辑,自动保存。AI 优化按 scope 精准更新。' },
  { icon: Connection,    title: '系列与资产复用', desc: '人设、风格、栏目长期沉淀,系列每集都自动一致。' },
  { icon: TrendCharts,   title: '一致性自动审核', desc: 'AI 检查每一集与系列设定的偏差,给出修复建议。' },
]

const steps = [
  { title: '选方向 · 写想法', desc: '从大类与具体方向入手,再用一两句话描述创作意图。' },
  { title: 'AI 生成首版方案', desc: '10-30 秒拿到完整结构化方案,包含分镜与提示词。' },
  { title: '编辑确认 · 导出',  desc: '逐字段微调,导出为 Markdown 或 Word,直接进入拍摄。' },
]

interface SnapTarget {
  id: string
  top: number
}

function shouldSnap(): boolean {
  return Boolean(snapMedia?.matches && !reduceMotionMedia?.matches)
}

function getTopbarHeight(): number {
  return homeRef.value?.querySelector<HTMLElement>('.topbar')?.offsetHeight ?? 0
}

function getSnapTargets(): SnapTarget[] {
  const root = homeRef.value
  if (!root) return []

  const topbarHeight = getTopbarHeight()
  const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
  const elements = Array.from(root.querySelectorAll<HTMLElement>('[data-home-snap]'))
  const targets = elements.map((el, index) => ({
    id: el.id,
    top: Math.min(maxScroll, Math.max(0, index === 0 ? 0 : el.offsetTop - topbarHeight)),
  }))

  return targets.filter((target, index) => index === 0 || Math.abs(target.top - targets[index - 1].top) > 4)
}

function getNearestSnapIndex(targets: SnapTarget[], top = window.scrollY): number {
  if (!targets.length) return 0
  return targets.reduce((nearest, target, index) => {
    const nearestDistance = Math.abs(targets[nearest].top - top)
    const targetDistance = Math.abs(target.top - top)
    return targetDistance < nearestDistance ? index : nearest
  }, 0)
}

function snapToIndex(index: number, behavior: ScrollBehavior = 'smooth') {
  const targets = getSnapTargets()
  if (!targets.length) return

  const targetIndex = Math.min(Math.max(index, 0), targets.length - 1)
  activeSnapIndex = targetIndex
  isSnapping = true
  window.clearTimeout(snapUnlockTimer)
  window.scrollTo({ top: targets[targetIndex].top, behavior })
  snapUnlockTimer = window.setTimeout(() => {
    isSnapping = false
  }, behavior === 'smooth' ? 620 : 0)
}

function snapAfterScroll() {
  if (!shouldSnap() || isSnapping) return

  const targets = getSnapTargets()
  if (targets.length < 2) return

  if (!targets[activeSnapIndex]) {
    activeSnapIndex = getNearestSnapIndex(targets)
  }

  const currentTop = targets[activeSnapIndex].top
  const delta = window.scrollY - currentTop
  const threshold = window.innerHeight * 0.5

  if (Math.abs(delta) > window.innerHeight * 1.25) {
    snapToIndex(getNearestSnapIndex(targets))
  } else if (delta > threshold && activeSnapIndex < targets.length - 1) {
    snapToIndex(activeSnapIndex + 1)
  } else if (delta < -threshold && activeSnapIndex > 0) {
    snapToIndex(activeSnapIndex - 1)
  } else {
    snapToIndex(activeSnapIndex)
  }
}

function scheduleSnap() {
  if (!shouldSnap() || isSnapping) return
  window.clearTimeout(snapTimer)
  snapTimer = window.setTimeout(snapAfterScroll, 120)
}

function handleResize() {
  const targets = getSnapTargets()
  activeSnapIndex = getNearestSnapIndex(targets)
  if (shouldSnap()) snapToIndex(activeSnapIndex, 'auto')
}

function scrollToSection(id: string) {
  const targets = getSnapTargets()
  const targetIndex = targets.findIndex((target) => target.id === id)
  if (targetIndex >= 0) {
    snapToIndex(targetIndex)
    window.history.replaceState(null, '', `#${id}`)
  }
}

onMounted(() => {
  snapMedia = window.matchMedia('(min-width: 900px)')
  reduceMotionMedia = window.matchMedia('(prefers-reduced-motion: reduce)')
  activeSnapIndex = getNearestSnapIndex(getSnapTargets())
  window.addEventListener('scroll', scheduleSnap, { passive: true })
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.clearTimeout(snapTimer)
  window.clearTimeout(snapUnlockTimer)
  window.removeEventListener('scroll', scheduleSnap)
  window.removeEventListener('resize', handleResize)
})

</script>

<style scoped>
.home {
  min-height: 100vh;
  background: transparent;
  color: var(--vp-text-1);
  font-size: 20px;
}

/* ----- Topbar ----- */
.topbar {
  padding: 14px 24px;
  position: sticky; top: 0; z-index: 10;
  backdrop-filter: saturate(180%) blur(12px);
  background: color-mix(in srgb, var(--vp-bg) 90%, transparent);
  border-bottom: 1px solid var(--vp-divider);
}
.topbar-inner {
  max-width: 1180px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.brand { display: flex; align-items: center; text-decoration: none; color: var(--vp-text-1); }
.brand-name { font-family: var(--vp-font-display); font-weight: 700; font-size: 26px; }
.top-links { display: flex; gap: 28px; }
.top-links a {
  color: var(--vp-text-2); text-decoration: none;
  font-size: 20px; font-weight: 500;
  transition: color .12s ease;
}
.top-links a:hover { color: var(--vp-text-1); }
.actions { display: flex; gap: 10px; }

/* ----- Hero ----- */
.hero {
  max-width: 1180px; margin: 0 auto;
  min-height: calc(100vh - 67px);
  padding: 90px 24px;
  text-align: center;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.hero-title {
  font-size: 74px; line-height: 1.08;
  font-family: var(--vp-font-display);
  font-weight: 760;
  letter-spacing: 0;
  margin-bottom: 58px;
  color: var(--vp-text-1);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.55);
  position: relative;
  top: -58px;
  animation: vp-fade-up .6s ease .05s both;
}
.hero-sub {
  font-size: 24px;
  color: var(--vp-text-2);
  line-height: 1.9;
  margin-bottom: 0;
  animation: vp-fade-up .6s ease .15s both;
}

/* ----- Sections ----- */
.section-head { text-align: center; max-width: 720px; margin: 0 auto 40px; }
.section-head h2 { font-size: 38px; letter-spacing: 0; margin-bottom: 8px; }
.section-head p  { color: var(--vp-text-3); font-size: 20px; }

.features { padding: 138px 24px 80px; max-width: 1180px; margin: 0 auto; }
.feature-grid {
  display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}
.feature {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  padding: 20px;
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.feature:hover {
  transform: translateY(-2px);
  box-shadow: var(--vp-shadow-md);
  border-color: var(--vp-border-strong);
}
.feature-icon {
  width: 36px; height: 36px;
  border-radius: var(--vp-r-md);
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
  display: inline-flex; align-items: center; justify-content: center;
  margin-bottom: 14px;
}
.feature-icon :deep(svg) { width: 18px; height: 18px; }
.feature h3 { font-size: 22px; margin-bottom: 6px; }
.feature p { font-size: 18px; color: var(--vp-text-3); line-height: 1.55; }

/* ----- How ----- */
.how { padding: 40px 24px 96px; max-width: 1180px; margin: 0 auto; }
.steps {
  list-style: none; padding: 0; margin: 0;
  display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.steps li {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  padding: 24px 22px;
}
.step-num {
  font-family: var(--vp-mono);
  font-size: 15px; font-weight: 600;
  color: var(--vp-primary);
  margin-bottom: 12px;
  letter-spacing: 0;
}
.steps h4 { font-size: 22px; margin-bottom: 6px; }
.steps p  { font-size: 18px; color: var(--vp-text-3); line-height: 1.55; }

/* ----- Foot ----- */
.foot {
  border-top: 1px solid var(--vp-divider);
  padding: 24px 40px;
  display: flex; justify-content: space-between;
  font-size: 16px; color: var(--vp-text-3);
}

@media (max-width: 720px) {
  .top-links { display: none; }
  .topbar { padding: 12px 16px; }
  .hero { min-height: calc(100vh - 61px); padding: 54px 20px; }
  .hero-title { font-size: 46px; line-height: 1.22; margin-bottom: 42px; top: -34px; }
  .hero-sub { font-size: 20px; line-height: 1.85; }
  .features { padding: 112px 20px 80px; }
  .how { padding-left: 20px; padding-right: 20px; }
  .foot { flex-direction: column; gap: 6px; padding: 22px 24px; }
}
</style>
