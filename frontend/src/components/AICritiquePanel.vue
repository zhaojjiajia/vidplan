<template>
  <el-card class="critique-card" :class="`tone-${tone}`">
    <template #header>
      <div class="critique-head">
        <div class="critique-head-left">
          <span class="badge">AI 审稿</span>
          <span class="score-chip" :data-tone="tone">
            <strong>{{ clampedScore }}</strong><span class="score-chip-unit">分</span>
          </span>
          <span class="head-line">{{ headline }}</span>
          <span v-if="severityCounts.total" class="head-issue-counts">
            <span v-if="severityCounts.critical" class="sev-mini sev-critical">{{ severityCounts.critical }}</span>
            <span v-if="severityCounts.major" class="sev-mini sev-major">{{ severityCounts.major }}</span>
            <span v-if="severityCounts.minor" class="sev-mini sev-minor">{{ severityCounts.minor }}</span>
          </span>
        </div>
        <el-button text size="small" @click="collapsed = !collapsed">
          {{ collapsed ? '查看详情' : '收起' }}
        </el-button>
      </div>
    </template>

    <div v-show="!collapsed" class="critique-body">
      <div class="critique-top">
        <div class="score-ring">
          <el-progress
            type="dashboard"
            :percentage="clampedScore"
            :stroke-width="9"
            :width="110"
            :color="ringColor"
          >
            <template #default>
              <div class="score-inner">
                <span class="score-num">{{ clampedScore }}</span>
                <span class="score-label">总分</span>
              </div>
            </template>
          </el-progress>
        </div>

        <div class="critique-summary">
          <p v-if="critique.summary">{{ critique.summary }}</p>
          <p v-else class="muted">无总评</p>
          <div class="severity-counts" v-if="severityCounts.total > 0">
            <span class="sev-pill sev-critical" v-if="severityCounts.critical">
              严重 {{ severityCounts.critical }}
            </span>
            <span class="sev-pill sev-major" v-if="severityCounts.major">
              主要 {{ severityCounts.major }}
            </span>
            <span class="sev-pill sev-minor" v-if="severityCounts.minor">
              一般 {{ severityCounts.minor }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="critique.axes && critique.axes.length" class="critique-axes">
        <div v-for="axis in critique.axes" :key="axis.name" class="axis">
          <div class="axis-head">
            <span class="axis-name">{{ axis.name }}</span>
            <span class="axis-score" :data-tone="axisTone(axis.score)">{{ axis.score }}</span>
          </div>
          <div class="axis-bar">
            <div
              class="axis-bar-fill"
              :style="{ width: clampPercent(axis.score) + '%' }"
              :data-tone="axisTone(axis.score)"
            />
          </div>
          <p v-if="axis.comment" class="axis-comment">{{ axis.comment }}</p>
        </div>
      </div>

      <div v-if="critique.issues && critique.issues.length" class="critique-issues">
        <h4>需关注的问题</h4>
        <ul>
          <li
            v-for="(issue, i) in critique.issues"
            :key="i"
            :class="[`sev-${issue.severity}`, { 'is-handled': !!issueDone[i] }]"
          >
            <div class="issue-meta">
              <span class="issue-sev">{{ severityLabel(issue.severity) }}</span>
              <span v-if="issue.field" class="issue-field" :title="issue.field">
                {{ humanizePath(issue.field) }}
              </span>
              <span v-if="issueDone[i] === 'fixed'" class="issue-resolved-tag">已去修复</span>
              <span v-else-if="issueDone[i] === 'skipped'" class="issue-skipped-tag">已跳过</span>
            </div>
            <p class="issue-text">{{ issue.comment }}</p>
            <div v-if="issue.field && !issueDone[i]" class="issue-actions">
              <el-button
                text
                type="primary"
                size="small"
                @click="onFix(i, issue)"
              >
                去修复
              </el-button>
              <el-button text size="small" @click="onSkip(i)">跳过</el-button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import type { AICritique, AICritiqueIssue } from '@/types/api'
import { humanizePath } from '@/utils/critiquePath'

const props = withDefaults(defineProps<{
  critique: AICritique
  /**
   * Default open state. When the panel is rendered inside the right drawer,
   * the parent passes `false` so it shows fully expanded — there's no need
   * to collapse a panel the user opened on purpose.
   */
  defaultCollapsed?: boolean
  /**
   * Per-issue handled state. Lives in the parent (PlanEditor) so it survives
   * dialog open/close cycles — the modal uses destroy-on-close, which would
   * otherwise drop a panel-local Map every time the user reopens the dialog.
   * Keys are the issue array index; values are 'fixed' or 'skipped'.
   */
  issueDone?: Record<number, 'fixed' | 'skipped' | undefined>
}>(), {
  defaultCollapsed: true,
  issueDone: () => ({}),
})

const emit = defineEmits<{
  /**
   * Emitted when the user clicks "去修复". The parent opens the inline
   * rewrite popover for the field, with `comment` pre-filled as the hint.
   * The user explicitly chose this design over auto-running the LLM —
   * generation only fires when they click "生成候选" inside the popover.
   */
  (e: 'fix', path: string, hint: string): void
  /** Mark an issue as handled. Parent owns the issueDone map. */
  (e: 'mark-done', idx: number, state: 'fixed' | 'skipped'): void
}>()

const issueDone = computed(() => props.issueDone)

function onFix(idx: number, issue: AICritiqueIssue) {
  if (!issue.field) return
  emit('fix', issue.field, issue.comment)
  emit('mark-done', idx, 'fixed')
}

function onSkip(idx: number) {
  emit('mark-done', idx, 'skipped')
}

// Default-collapsed so the editor's first paint isn't dominated by the panel.
// The header still shows score + headline + issue counts so users can decide
// whether to expand without first reading the full rubric.
const collapsed = ref(props.defaultCollapsed)

const clampedScore = computed(() => Math.max(0, Math.min(100, props.critique.score || 0)))

const tone = computed(() => {
  if (clampedScore.value >= 85) return 'good'
  if (clampedScore.value >= 70) return 'ok'
  if (clampedScore.value >= 50) return 'warn'
  return 'bad'
})

const headline = computed(() => {
  switch (tone.value) {
    case 'good': return '方案质量优秀'
    case 'ok': return '方案可用,可继续打磨'
    case 'warn': return '存在明显问题,建议优化'
    default: return '方案需要重做关键部分'
  }
})

const ringColor = computed(() => {
  switch (tone.value) {
    case 'good': return '#34d399'
    case 'ok': return '#60a5fa'
    case 'warn': return '#f59e0b'
    default: return '#ef4444'
  }
})

const severityCounts = computed(() => {
  const counts = { critical: 0, major: 0, minor: 0, total: 0 }
  for (const issue of props.critique.issues || []) {
    const key = (issue.severity || 'minor').toLowerCase()
    if (key === 'critical' || key === 'major' || key === 'minor') {
      counts[key]++
      counts.total++
    } else {
      counts.minor++
      counts.total++
    }
  }
  return counts
})

function clampPercent(score: number): number {
  return Math.max(0, Math.min(100, score || 0))
}

function axisTone(score: number): 'good' | 'ok' | 'warn' | 'bad' {
  const s = clampPercent(score)
  if (s >= 85) return 'good'
  if (s >= 70) return 'ok'
  if (s >= 50) return 'warn'
  return 'bad'
}

function severityLabel(severity: string): string {
  switch ((severity || '').toLowerCase()) {
    case 'critical': return '严重'
    case 'major': return '主要'
    case 'minor': return '一般'
    default: return severity || '一般'
  }
}
</script>

<style scoped>
.critique-card {
  border-left: 4px solid var(--vp-border);
}
.critique-card.tone-good { border-left-color: #34d399; }
.critique-card.tone-ok { border-left-color: #60a5fa; }
.critique-card.tone-warn { border-left-color: #f59e0b; }
.critique-card.tone-bad { border-left-color: #ef4444; }

.critique-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.critique-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--vp-primary-soft, #eef2ff);
  color: var(--vp-primary, #4338ca);
  font-weight: 600;
  letter-spacing: .04em;
}

.score-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 600;
  background: #f3f4f6;
  color: #374151;
  white-space: nowrap;
  flex-shrink: 0;
}
.score-chip[data-tone="good"] { background: #d1fae5; color: #065f46; }
.score-chip[data-tone="ok"] { background: #dbeafe; color: #1e40af; }
.score-chip[data-tone="warn"] { background: #fef3c7; color: #92400e; }
.score-chip[data-tone="bad"] { background: #fee2e2; color: #991b1b; }
.score-chip strong { font-size: 14px; line-height: 1; }
.score-chip-unit { font-size: 11px; opacity: .75; }

.head-line {
  font-size: 13px;
  color: var(--vp-text-2, #4b5563);
  font-weight: 500;
}

.head-issue-counts {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.sev-mini {
  display: inline-block;
  min-width: 18px;
  height: 18px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  font-weight: 600;
  padding: 0 4px;
}
.sev-mini.sev-critical { background: #fee2e2; color: #991b1b; }
.sev-mini.sev-major { background: #fed7aa; color: #9a3412; }
.sev-mini.sev-minor { background: #dbeafe; color: #1e40af; }

.critique-body { display: flex; flex-direction: column; gap: 18px; }
.critique-top {
  display: flex;
  align-items: center;
  gap: 20px;
}
.score-ring { flex-shrink: 0; }
.score-inner {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.score-num { font-size: 26px; font-weight: 700; color: var(--vp-text-1); }
.score-label { font-size: 12px; color: var(--vp-text-3); }

.critique-summary { flex: 1; min-width: 0; }
.critique-summary p {
  margin: 0;
  line-height: 1.5;
  color: var(--vp-text-1);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.critique-summary .muted { color: var(--vp-text-3); }
.severity-counts { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.sev-pill {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.sev-pill.sev-critical { background: #fef2f2; color: #b91c1c; }
.sev-pill.sev-major { background: #fff7ed; color: #b45309; }
.sev-pill.sev-minor { background: #f0f9ff; color: #1d4ed8; }

.critique-axes { display: flex; flex-direction: column; gap: 10px; }
.axis { display: flex; flex-direction: column; gap: 4px; }
.axis-head { display: flex; justify-content: space-between; align-items: center; }
.axis-name { font-size: 13px; font-weight: 500; color: var(--vp-text-1); }
.axis-score { font-size: 13px; font-weight: 600; }
.axis-score[data-tone="good"] { color: #059669; }
.axis-score[data-tone="ok"] { color: #2563eb; }
.axis-score[data-tone="warn"] { color: #d97706; }
.axis-score[data-tone="bad"] { color: #dc2626; }

.axis-bar {
  width: 100%; height: 6px; background: var(--vp-surface-alt, #f3f4f6);
  border-radius: 3px; overflow: hidden;
}
.axis-bar-fill { height: 100%; transition: width .3s ease; }
.axis-bar-fill[data-tone="good"] { background: #34d399; }
.axis-bar-fill[data-tone="ok"] { background: #60a5fa; }
.axis-bar-fill[data-tone="warn"] { background: #f59e0b; }
.axis-bar-fill[data-tone="bad"] { background: #ef4444; }

.axis-comment {
  margin: 0;
  font-size: 12.5px;
  color: var(--vp-text-3);
  line-height: 1.4;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.critique-issues h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--vp-text-2);
}
.critique-issues ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
/*
 * Issue items stack vertically so long Chinese comments get the full width
 * to wrap into. Earlier we had everything on one flex row, but inside a
 * 380-460px drawer the comment ended up sandwiched between the severity
 * pill, field path chip, and "去修复" button — leaving only ~30px for the
 * comment, which forced one Chinese character per line.
 */
.critique-issues li {
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--vp-surface-alt, #f9fafb);
  border-left: 3px solid var(--vp-border);
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  line-height: 1.5;
}
.critique-issues li.sev-critical { border-left-color: #ef4444; }
.critique-issues li.sev-major { border-left-color: #f59e0b; }
.critique-issues li.sev-minor { border-left-color: #60a5fa; }

/* Top row: severity pill + field path chip + "去修复" pushed to the right. */
.issue-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.issue-sev {
  font-size: 11.5px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--vp-surface, #fff);
  color: var(--vp-text-2);
  flex-shrink: 0;
  white-space: nowrap;
}
/* Field is now a humanized Chinese label (e.g. "镜头 5 · 台词 / 旁白"),
   not a raw code path. The raw path lives in the title tooltip for power
   users / debugging. */
.issue-field {
  font-size: 12.5px;
  font-weight: 500;
  background: var(--vp-surface, #fff);
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--vp-text-2);
  flex: 1 1 auto;
  min-width: 0;
  word-break: break-word;
}

.issue-resolved-tag {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #d1fae5;
  color: #065f46;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}
.issue-skipped-tag {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #6b7280;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}
.critique-issues li.is-handled {
  opacity: .55;
}
.critique-issues li.is-handled .issue-text {
  text-decoration: line-through;
  text-decoration-color: rgba(107, 114, 128, .4);
}

.issue-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
  margin-top: 2px;
}
.issue-actions :deep(.el-button) {
  font-size: 12px !important;
  padding: 2px 8px !important;
  height: auto !important;
  margin-left: 0 !important;
}

/* Comment row: full width of the li, wraps naturally. */
.issue-text {
  margin: 0;
  color: var(--vp-text-1);
  word-break: break-word;
  overflow-wrap: anywhere;
}
</style>
