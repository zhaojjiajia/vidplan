<template>
  <div
    class="aig"
    :class="{ 'is-dragging': dragOver }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragEnter"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @paste="onPaste"
    tabindex="0"
  >
    <div v-if="!modelValue.length && !uploading.length" class="aig-empty">
      <el-icon class="aig-empty-icon"><Picture /></el-icon>
      <p>还没有上传任何图</p>
      <p class="hint">把图拖进来 / Cmd+V 粘贴 / 选文件,或者直接让 AI 帮你生成</p>
      <div class="aig-empty-actions">
        <label class="aig-pick-btn">
          <el-icon><Plus /></el-icon> 选文件
          <input
            ref="fileInputRef"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            class="aig-file-input"
            @change="onFileSelect"
          />
        </label>
        <button
          type="button"
          class="aig-pick-btn aig-pick-btn--ai"
          :disabled="aiGenerating"
          @click="onAIClick"
        >
          <el-icon v-if="aiGenerating" class="is-loading"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon>
          {{ aiGenerating ? 'AI 生成中…' : 'AI 生成' }}
        </button>
      </div>
    </div>

    <div v-else class="aig-grid">
      <article
        v-for="(img, idx) in modelValue"
        :key="img.url"
        class="aig-tile"
      >
        <button class="aig-tile-image" type="button" @click="openLightbox(idx)">
          <img :src="img.thumb_url || img.url" :alt="img.label || `图 ${idx + 1}`" />
        </button>
        <button class="aig-tile-remove" type="button" :title="`删除`" @click.stop="removeAt(idx)">
          <el-icon><Close /></el-icon>
        </button>
        <select
          class="aig-tile-label"
          :value="img.label || ''"
          @change="onLabelChange(idx, ($event.target as HTMLSelectElement).value)"
          @click.stop
        >
          <option value="">未分类</option>
          <option v-for="opt in labels" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </article>

      <article v-for="(item, idx) in uploading" :key="item.tempId" class="aig-tile is-uploading">
        <div class="aig-tile-image">
          <div class="aig-tile-progress">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>{{ item.percent }}%</span>
          </div>
        </div>
      </article>

      <label class="aig-add">
        <el-icon><Plus /></el-icon>
        <span>上传</span>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          class="aig-file-input"
          @change="onFileSelect"
        />
      </label>

      <button
        type="button"
        class="aig-add aig-add--ai"
        :disabled="aiGenerating"
        @click="onAIClick"
      >
        <el-icon v-if="aiGenerating" class="is-loading"><Loading /></el-icon>
        <el-icon v-else><MagicStick /></el-icon>
        <span>{{ aiGenerating ? '生成中…' : 'AI 生成' }}</span>
      </button>
    </div>

    <div v-if="errors.length" class="aig-errors">
      <p v-for="(err, i) in errors" :key="i">⚠ {{ err }}</p>
    </div>

    <!-- AI Generation dialog -->
    <el-dialog
      v-model="aiDialogOpen"
      title="AI 生成参考图"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item label="描述(中英文均可)">
          <el-input
            v-model="aiPrompt"
            type="textarea"
            :autosize="{ minRows: 4 }"
            :placeholder="aiPromptHint"
          />
          <p class="aig-hint">
            提示越具体效果越好。比如:&quot;19岁亚洲女生,齐刘海黑色长直发,白衬衫,上半身正面,工作室白底,柔光,写实风格&quot;
          </p>
        </el-form-item>
        <el-form-item label="比例">
          <el-radio-group v-model="aiSize">
            <el-radio-button label="1024x1024">方形</el-radio-button>
            <el-radio-button label="1792x1024">横版</el-radio-button>
            <el-radio-button label="1024x1792">竖版</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="aiDialogOpen = false" :disabled="aiGenerating">取消</el-button>
        <el-button type="primary" :loading="aiGenerating" @click="runAIGenerate">生成</el-button>
      </template>
    </el-dialog>

    <!-- Lightbox -->
    <Teleport to="body">
      <div v-if="lightboxIdx !== null" class="aig-lightbox" @click.self="closeLightbox">
        <button class="aig-lb-close" type="button" @click="closeLightbox">
          <el-icon><Close /></el-icon>
        </button>
        <button v-if="modelValue.length > 1" class="aig-lb-nav prev" type="button" @click="lightboxPrev">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <img :src="modelValue[lightboxIdx]?.url" :alt="modelValue[lightboxIdx]?.label || ''" />
        <button v-if="modelValue.length > 1" class="aig-lb-nav next" type="button" @click="lightboxNext">
          <el-icon><ArrowRight /></el-icon>
        </button>
        <div class="aig-lb-meta">
          <strong>{{ modelValue[lightboxIdx]?.label || '未分类' }}</strong>
          <span>{{ lightboxIdx + 1 }} / {{ modelValue.length }}</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, ArrowRight, Close, Loading, MagicStick, Picture, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { assetsApi } from '@/api/assets'
import type { AssetImage } from '@/types/api'

const props = defineProps<{
  modelValue: AssetImage[]
  /** Allowed labels for the per-image dropdown (e.g. ['正面', '侧面', '其他']). */
  labels: string[]
  /**
   * Provider that returns a prompt synthesised from surrounding asset state
   * (name + payload + traits). When supplied, the AI 生成 button bypasses
   * the prompt-input dialog and just fires immediately — UX requested:
   * "用户不需要输入描述,直接根据资产卡内容生成". When absent we fall back
   * to the manual-prompt dialog.
   */
  aiPromptProvider?: () => string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: AssetImage[]): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const errors = ref<string[]>([])
const lightboxIdx = ref<number | null>(null)

const aiDialogOpen = ref(false)
const aiPrompt = ref('')
const aiSize = ref<'1024x1024' | '1792x1024' | '1024x1792'>('1024x1024')
const aiGenerating = ref(false)
const aiPromptHint = '描述你想要的图片(主体、构图、光线、风格)'

/**
 * Click handler for the ✨ AI 生成 button.
 * Two modes: with promptProvider → fire-and-forget (no dialog).
 * Without → open manual prompt dialog (legacy, kept for flexibility).
 */
async function onAIClick() {
  if (props.aiPromptProvider) {
    const prompt = props.aiPromptProvider().trim()
    if (!prompt) {
      ElMessage.warning('请先填写资产名称和基本信息,AI 才能据此生成')
      return
    }
    await runDirectGenerate(prompt)
    return
  }
  // Fallback path: keep manual dialog for when no provider is wired up.
  aiPrompt.value = ''
  aiSize.value = '1024x1024'
  aiDialogOpen.value = true
}

async function runDirectGenerate(prompt: string) {
  aiGenerating.value = true
  try {
    // Default to landscape 16:9 — matches the gallery tile aspect-ratio so
    // the image fills the tile without letterboxing, and reference images
    // for video work read as landscape by convention.
    const result = await assetsApi.generateImage({ prompt, size: '1792x1024' })
    emitUpdate([...props.modelValue, result])
    ElMessage.success('AI 已生成')
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || 'AI 生成失败'
    ElMessage.error(String(detail))
  } finally {
    aiGenerating.value = false
  }
}

async function runAIGenerate() {
  const prompt = aiPrompt.value.trim()
  if (!prompt) {
    ElMessage.warning('请填写描述')
    return
  }
  aiGenerating.value = true
  try {
    const result = await assetsApi.generateImage({ prompt, size: aiSize.value })
    emitUpdate([...props.modelValue, result])
    aiDialogOpen.value = false
    ElMessage.success('AI 已生成')
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || 'AI 生成失败'
    ElMessage.error(String(detail))
  } finally {
    aiGenerating.value = false
  }
}

interface UploadingItem {
  tempId: number
  percent: number
}
let uploadCounter = 0
const uploading = reactive<UploadingItem[]>([])

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const MAX_BYTES = 5 * 1024 * 1024

function emitUpdate(next: AssetImage[]) {
  emit('update:modelValue', next)
}

function onDragEnter() {
  dragOver.value = true
}
function onDragLeave(e: DragEvent) {
  // Only clear when leaving the gallery root, not just hovering child elements.
  if (e.currentTarget === e.target) dragOver.value = false
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const files = e.dataTransfer?.files
  if (files?.length) handleFiles(Array.from(files))
}

function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const files: File[] = []
  for (const item of items) {
    if (item.kind === 'file') {
      const file = item.getAsFile()
      if (file) files.push(file)
    }
  }
  if (files.length) {
    e.preventDefault()
    handleFiles(files)
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) handleFiles(Array.from(input.files))
  input.value = ''
}

async function handleFiles(files: File[]) {
  errors.value = []
  for (const file of files) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      errors.value.push(`${file.name}: 仅支持 JPG / PNG / WebP`)
      continue
    }
    if (file.size > MAX_BYTES) {
      errors.value.push(`${file.name}: 超过 5 MB`)
      continue
    }
    void uploadOne(file)
  }
}

async function uploadOne(file: File) {
  const item: UploadingItem = { tempId: ++uploadCounter, percent: 10 }
  uploading.push(item)
  // Fake a smooth progress climb (real backend doesn't stream progress for
  // a single small image; the visible bar is just so the user sees motion).
  const tick = window.setInterval(() => {
    item.percent = Math.min(item.percent + 10, 88)
  }, 120)
  try {
    const result = await assetsApi.uploadImage(file)
    emitUpdate([...props.modelValue, result])
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '上传失败'
    errors.value.push(`${file.name}: ${detail}`)
    ElMessage.error(`上传失败: ${detail}`)
  } finally {
    window.clearInterval(tick)
    const idx = uploading.findIndex((u) => u.tempId === item.tempId)
    if (idx >= 0) uploading.splice(idx, 1)
  }
}

function removeAt(idx: number) {
  const next = [...props.modelValue]
  next.splice(idx, 1)
  emitUpdate(next)
}

function onLabelChange(idx: number, value: string) {
  const next = [...props.modelValue]
  next[idx] = { ...next[idx], label: value }
  emitUpdate(next)
}

function openLightbox(idx: number) {
  lightboxIdx.value = idx
}
function closeLightbox() {
  lightboxIdx.value = null
}
function lightboxPrev() {
  if (lightboxIdx.value === null) return
  lightboxIdx.value = (lightboxIdx.value - 1 + props.modelValue.length) % props.modelValue.length
}
function lightboxNext() {
  if (lightboxIdx.value === null) return
  lightboxIdx.value = (lightboxIdx.value + 1) % props.modelValue.length
}

function onKey(e: KeyboardEvent) {
  if (lightboxIdx.value === null) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') lightboxPrev()
  if (e.key === 'ArrowRight') lightboxNext()
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.aig {
  position: relative;
  border-radius: 10px;
  outline: none;
  transition: background .15s ease;
}
.aig.is-dragging {
  background: var(--vp-primary-soft, #eef2ff);
  outline: 2px dashed var(--vp-primary, #4f46e5);
  outline-offset: 4px;
}

.aig-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 16px;
  border: 1px dashed var(--vp-border, #d1d5db);
  border-radius: 10px;
  color: var(--vp-text-3, #6b7280);
}
.aig-empty-icon { font-size: 36px; color: var(--vp-text-4, #9ca3af); }
.aig-empty p { margin: 0; font-size: 14px; }
.aig-empty .hint { font-size: 12.5px; color: var(--vp-text-3, #9ca3af); }
.aig-empty .aig-pick-btn { margin-top: 6px; }

.aig-empty-actions {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}
.aig-pick-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: 6px;
  background: var(--vp-primary, #4f46e5);
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  border: none;
  font-family: inherit;
}
.aig-pick-btn:hover { background: var(--vp-primary-hover, #4338ca); }
.aig-pick-btn--ai {
  background: transparent;
  color: var(--vp-primary, #4f46e5);
  border: 1px solid var(--vp-primary, #4f46e5);
}
.aig-pick-btn--ai:hover {
  background: var(--vp-primary-soft, #eef2ff);
}
.aig-file-input { display: none; }

/* Flex+wrap with a deterministic tile width is more reliable across the
   various dialog widths than CSS Grid's auto-fill — auto-fill kept
   collapsing to one column when the parent container reported a slightly
   narrower content box. Each tile + add-button is exactly 130px wide. */
.aig-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.aig-tile,
.aig-add {
  width: 130px;
  flex-shrink: 0;
}

.aig-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--vp-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
  background: var(--vp-surface, #fff);
  transition: border-color .12s, box-shadow .12s;
}
.aig-tile:hover { border-color: var(--vp-primary, #4f46e5); }

/* Landscape (4:3) tiles instead of square. User asked for "横着" — wider
   than tall fits typical reference photos better and avoids the page
   feeling like a column of stacked portraits. */
.aig-tile-image {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  border: none;
  padding: 0;
  background: var(--vp-surface-alt, #f9fafb);
  cursor: zoom-in;
}
.aig-tile-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.aig-tile-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity .12s, background .12s;
}
.aig-tile:hover .aig-tile-remove { opacity: 1; }
.aig-tile-remove:hover { background: #ef4444; }
.aig-tile-remove :deep(.el-icon) { font-size: 12px; }

.aig-tile-label {
  border: none;
  border-top: 1px solid var(--vp-border, #f3f4f6);
  padding: 5px 8px;
  font-size: 12px;
  color: var(--vp-text-2, #4b5563);
  background: transparent;
  outline: none;
  cursor: pointer;
}

.aig-tile.is-uploading .aig-tile-image {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
}
.aig-tile-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--vp-text-3, #9ca3af);
}
.aig-tile-progress .is-loading {
  font-size: 22px;
  animation: aig-spin 1.2s linear infinite;
}
@keyframes aig-spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

.aig-add {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 4px;
  border: 1px dashed var(--vp-border, #d1d5db);
  border-radius: 8px;
  aspect-ratio: 4 / 3;
  cursor: pointer;
  color: var(--vp-text-3, #9ca3af);
  font-size: 12.5px;
  transition: border-color .12s, color .12s, background .12s;
  background: transparent;
  font-family: inherit;
}
.aig-add:disabled { cursor: wait; opacity: .7; }
.aig-add .is-loading {
  animation: aig-spin 1.2s linear infinite;
}
.aig-add:hover {
  border-color: var(--vp-primary, #4f46e5);
  color: var(--vp-primary, #4f46e5);
  background: var(--vp-primary-soft, #eef2ff);
}
.aig-add :deep(.el-icon) { font-size: 18px; }

/* AI 生成 tile distinguishes itself with primary-tinted border so users
   notice the "magic" path next to plain upload. */
.aig-add--ai {
  border-color: var(--vp-primary, #4f46e5);
  color: var(--vp-primary, #4f46e5);
  background: linear-gradient(135deg, rgba(79, 70, 229, .04), rgba(79, 70, 229, .12));
}
.aig-add--ai:hover {
  background: linear-gradient(135deg, rgba(79, 70, 229, .12), rgba(79, 70, 229, .22));
}

.aig-hint {
  margin: 6px 0 0;
  font-size: 11.5px;
  color: var(--vp-text-3, #9ca3af);
  line-height: 1.5;
}

.aig-errors {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fef2f2;
  border-radius: 6px;
  font-size: 12.5px;
  color: #b91c1c;
}
.aig-errors p { margin: 2px 0; }

/* Lightbox */
.aig-lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .82);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.aig-lightbox img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
}
.aig-lb-close, .aig-lb-nav {
  position: absolute;
  border: none;
  background: rgba(0, 0, 0, .4);
  color: #fff;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.aig-lb-close { top: 16px; right: 16px; }
.aig-lb-close:hover, .aig-lb-nav:hover { background: rgba(0, 0, 0, .7); }
.aig-lb-nav.prev { left: 16px; top: 50%; transform: translateY(-50%); }
.aig-lb-nav.next { right: 16px; top: 50%; transform: translateY(-50%); }
.aig-lb-meta {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  color: #fff;
  font-size: 13px;
  background: rgba(0, 0, 0, .5);
  padding: 6px 16px;
  border-radius: 999px;
}
.aig-lb-meta strong { font-weight: 600; }
.aig-lb-meta span { font-size: 11.5px; opacity: .7; }
</style>
