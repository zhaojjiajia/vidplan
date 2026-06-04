<template>
  <div class="editor-page" v-loading="loading && !form.title">
    <!-- Sticky toolbar -->
    <header class="doc-toolbar">
      <div class="dt-left">
        <el-button text :icon="ArrowLeft" @click="backFromToolbar">返回</el-button>
        <span class="dt-divider" />
        <span class="dt-status" :data-tone="seriesStatusTone">{{ seriesStatusLabel(form.status) }}</span>
      </div>
    </header>

    <el-alert v-if="taskMessage && !generatingEpisode" type="info" show-icon :closable="false" class="task-alert">
      <template #title>
        <div class="task-title">
          <span>{{ taskMessage }}</span>
        </div>
      </template>
    </el-alert>

    <section v-if="isRelationshipPage" class="studio-wrap relationship-wrap">
      <section class="series-brief">
        <button type="button" class="series-brief-title" @click="openPanel('series')">
          {{ form.title || '未命名系列' }}
        </button>
        <p>{{ form.summary || positioning.core_concept || '暂无简介' }}</p>
      </section>

      <section class="pinboard-shell">
        <div
          ref="boardRef"
          class="pinboard-viewport"
          :data-tool="boardTool"
          @wheel.prevent="onPinboardWheel"
        >
          <div class="canvas-floating-tools">
            <button
              type="button"
              :class="['canvas-tool', { active: boardTool === 'select' }]"
              title="查看"
              @click="setBoardTool('select')"
            >
              <el-icon><Pointer /></el-icon>
            </button>
            <button
              type="button"
              :class="['canvas-tool', { active: boardTool === 'move' }]"
              title="拖动"
              @click="setBoardTool('move')"
            >
              <el-icon><Mouse /></el-icon>
            </button>
            <button
              type="button"
              :class="['canvas-tool', { active: canvasImageOnlyMode }]"
              :title="canvasImageOnlyMode ? '显示资产卡片和关系连线' : '只显示资产图片'"
              :aria-label="canvasImageOnlyMode ? '显示资产卡片和关系连线' : '只显示资产图片'"
              :aria-pressed="canvasImageOnlyMode"
              @click="toggleCanvasImageOnlyMode"
            >
              <el-icon><component :is="canvasImageOnlyMode ? Hide : View" /></el-icon>
            </button>
            <button
              type="button"
              class="canvas-tool"
              title="编辑资产关系"
              aria-label="编辑资产关系"
              @click="openRelationshipDialog"
            >
              <el-icon><Connection /></el-icon>
            </button>
            <el-dropdown trigger="click" placement="bottom-end" @command="openCanvasAsset">
              <button
                type="button"
                class="canvas-tool"
                title="增加资产卡"
                aria-label="增加资产卡"
                @click.stop
              >
                <el-icon><Plus /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="characters">人物</el-dropdown-item>
                  <el-dropdown-item command="worldviews">环境</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div
            class="pinboard-stage"
            :style="{
              width: `${Math.round(pinboardSize.width * boardScale)}px`,
              height: `${Math.round(pinboardSize.height * boardScale)}px`,
            }"
          >
            <div
              :class="['pinboard-canvas', { 'is-image-only': canvasImageOnlyMode }]"
              :style="pinboardCanvasStyle"
            >
              <svg
                v-if="!canvasImageOnlyMode"
                class="pin-lines"
                :width="pinboardSize.width"
                :height="pinboardSize.height"
              >
                <g
                  v-for="line in pinLines"
                  :key="line.id"
                  class="pin-line-group"
                >
	                  <path
	                    :d="linePath(line)"
	                    :class="[
	                      'pin-line',
	                      `pin-line--${line.kind}`,
	                      `pin-line--${relationTone(line)}`,
	                      { 'is-editing': activeRelationId === line.relation.id },
	                    ]"
	                  />
		                  <path
		                    v-if="boardTool === 'select'"
		                    :d="linePath(line)"
		                    class="pin-line-hit"
		                    @click.stop="openRelationEditor(line)"
	                  />
                  <text
                    v-if="line.relation.label && activeRelationId !== line.relation.id"
	                    :class="['pin-line-label', { 'is-editing': activeRelationId === line.relation.id }]"
	                    :x="lineLabelPosition(line).x"
	                    :y="lineLabelPosition(line).y"
	                    text-anchor="middle"
	                    dominant-baseline="middle"
	                    @click.stop="openRelationEditor(line)"
	                  >
	                    {{ line.relation.label }}
	                  </text>
	                </g>
	                <path
	                  v-if="relationPreviewPath"
	                  :d="relationPreviewPath"
	                  class="pin-line-preview"
	                />
	              </svg>

		              <button
		                v-for="line in actionableRelationLines"
		                v-show="boardTool === 'select' && !canvasImageOnlyMode"
		                :key="`relation-hotspot-${line.id}`"
		                type="button"
	                :class="['pin-relation-hotspot', { 'is-editing': activeRelationId === line.relation.id }]"
	                :style="relationEditorStyle(line)"
	                aria-label="编辑关系"
	                @click.stop="openRelationEditor(line)"
	                @pointerdown.stop
	              />

	              <div
	                v-if="activeRelationLine && !canvasImageOnlyMode"
	                class="pin-relation-editor"
	                :style="relationEditorStyle(activeRelationLine)"
	                @click.stop
	                @pointerdown.stop
	              >
		                <input
		                  ref="relationInputRef"
		                  v-model="relationDraft"
		                  placeholder="关系"
		                  @keydown.enter.prevent="commitRelationEditor"
		                  @keydown.esc.prevent="closeRelationEditor"
		                  @blur="commitRelationEditor"
		                />
		                <button
		                  type="button"
		                  class="pin-relation-delete"
		                  title="删除关系"
		                  aria-label="删除关系"
		                  @pointerdown.prevent.stop="deleteActiveRelation"
		                >
		                  <el-icon><Delete /></el-icon>
		                </button>
		              </div>

              <button
                type="button"
                class="big-environment-title"
                title="编辑大环境"
                @click.stop="openBigEnvironmentDialog"
                @pointerdown.stop
              >
                {{ bigEnvironment.name || '系列大环境' }}
              </button>

		              <article
                v-for="node in pinNodes"
                :key="node.id"
                :class="[
                  'pin-card',
                  `pin-card--${node.kind}`,
                  node.assetType ? `pin-card--${node.assetType}` : '',
                  {
                    'is-dragging': draggingNodeId === node.id,
                    'is-connect-start': relationStartNodeId === node.id,
                  },
                ]"
                :style="nodeStyle(node)"
                role="button"
                tabindex="0"
                @click="openPinNode(node)"
                @keydown.enter.space.prevent="openPinNode(node)"
                @pointerdown="maybeStartNodeDrag($event, node)"
              >
                <header class="pin-card-head">
                  <span class="pin-kicker">
                    <el-icon><component :is="nodeIcon(node)" /></el-icon>
                    {{ node.kicker }}
                  </span>
                </header>

                <div v-if="node.images.length" class="pin-images">
                  <img
                    v-for="image in node.images"
                    :key="image.url"
                    :src="image.thumb_url || image.url"
                    :alt="node.title"
                  />
                </div>
                <div v-else-if="node.kind === 'asset'" class="pin-images pin-images--empty">
                  <el-icon><component :is="nodePlaceholderIcon(node)" /></el-icon>
                </div>

                <h3>{{ node.title }}</h3>
                <p>{{ node.subtitle }}</p>

                <div v-if="node.tags.length" class="pin-tags">
                  <span v-for="tag in node.tags" :key="tag">{{ tag }}</span>
                </div>

	                <footer class="pin-card-foot">
	                  <span>{{ nodeActionLabel(node) }}</span>
	                  <el-icon><EditPen /></el-icon>
	                </footer>
	                <div class="pin-connect-handles">
	                  <button
	                    v-for="side in connectSides"
	                    :key="side"
	                    type="button"
	                    :class="['pin-connect-handle', `pin-connect-handle--${side}`]"
	                    :data-node-id="node.id"
	                    title="新建连线"
	                    aria-label="新建连线"
	                    tabindex="-1"
	                    v-show="boardTool === 'select' && !canvasImageOnlyMode"
	                    @click.stop.prevent
	                    @pointerdown.stop="startRelationDrag($event, node, side)"
	                  />
	                </div>
	              </article>
            </div>
          </div>
        </div>
      </section>
    </section>

    <section v-else-if="!isNew" class="series-ai-wrap">
      <section class="series-brief series-brief--editor">
        <button type="button" class="series-brief-title" @click="openPanel('series')">
          {{ form.title || '未命名系列' }}
        </button>
        <p>{{ form.summary || positioning.core_concept || '暂无简介' }}</p>
      </section>

      <section class="series-console">
        <div class="episode-rail-head">
          <div class="episode-rail-title">
            <span>单集时间轴</span>
            <strong>{{ episodeProgressText }}</strong>
            <button type="button" class="ghost-tool episode-relation-tool" @click="goRelationshipPage">
              <el-icon><View /></el-icon>
              资产关系
            </button>
          </div>
        </div>

        <div class="episode-timeline">
          <button
            type="button"
            class="timeline-add"
            :disabled="isNew || planPickerLoading"
            @click="openPlanPicker"
            title="添加我的方案"
          >
            <el-icon><Plus /></el-icon>
          </button>
          <article
            v-for="(ep, idx) in episodes"
            :key="ep.id"
            :class="[
              'timeline-episode',
              {
                'is-dragging': draggingEpisodeId === ep.id,
                'is-drop-before': dragOverEpisodeId === ep.id && dragOverSide === 'before',
                'is-drop-after': dragOverEpisodeId === ep.id && dragOverSide === 'after',
                'is-deleting': deletingEpisodeId === ep.id,
              },
            ]"
            :data-status="ep.status"
            :draggable="!episodeReordering && !deletingEpisodeId"
            role="button"
            tabindex="0"
            @click="router.push(`/app/plan/${ep.id}`)"
            @keydown.enter.space.prevent="router.push(`/app/plan/${ep.id}`)"
            @dragstart.stop="onEpisodeDragStart($event, ep.id)"
            @dragover.prevent.stop="onEpisodeDragOver($event, ep.id)"
            @dragleave.stop="onEpisodeDragLeave(ep.id)"
            @drop.prevent.stop="onEpisodeDrop($event, ep.id)"
            @dragend="onEpisodeDragEnd"
          >
            <div class="timeline-episode-controls" @click.stop @keydown.stop>
              <button
                type="button"
                class="timeline-icon-btn timeline-delete-btn"
                :disabled="episodeReordering || deletingEpisodeId === ep.id"
                title="删除单集"
                aria-label="删除单集"
                @click.stop="deleteEpisode(ep)"
              >
                <el-icon><Delete /></el-icon>
              </button>
            </div>
            <span class="timeline-index">E{{ idx + 1 }}</span>
            <strong>{{ ep.title || '未命名单集' }}</strong>
            <small>{{ episodeStatusLabel(ep.status) }} · {{ ep.duration_seconds }}s</small>
          </article>
          <article v-if="!episodes.length" class="timeline-empty">
            <strong>暂无单集</strong>
            <small>点击 + 从我的方案中添加。</small>
          </article>
        </div>
      </section>

      <section class="series-chat">
        <div v-if="seriesChatMessages.length" class="series-chat-stream">
          <div
            v-for="message in seriesChatMessages"
            :key="message.key"
            :class="[
              'series-chat-bubble',
              `series-chat-bubble--${message.role}`,
              { 'series-chat-bubble--thinking': message.key === 'generating' },
            ]"
          >
            {{ message.text }}
          </div>
        </div>

        <div class="series-composer" :class="{ generating: generatingEpisode }">
          <textarea
            v-model="episodeIdea"
            :disabled="isNew || generatingEpisode"
            rows="4"
            placeholder="输入下一集想法..."
            @keydown.meta.enter.prevent="submitEpisodeComposer"
            @keydown.ctrl.enter.prevent="submitEpisodeComposer"
          />
          <div class="series-composer-bar">
            <span>{{ seriesMemoryText }}</span>
            <button
              type="button"
              class="series-send"
              :disabled="isNew || generatingEpisode || !episodeIdea.trim()"
              title="生成单集"
              @click="submitEpisodeComposer"
            >
              <el-icon v-if="!generatingEpisode"><MagicStick /></el-icon>
              <span v-else class="series-send-loading" />
            </button>
          </div>
        </div>
      </section>
    </section>

    <div v-else class="doc-wrap">
      <article class="doc doc--new-series">
        <div class="doc-form-head">
          <h2>新建系列</h2>
          <el-button type="primary" :loading="saving" @click="save">保存系列</el-button>
        </div>

        <div class="doc-head">
          <input
            v-model="form.title"
            class="doc-title"
            placeholder="给系列起个标题"
          />
          <el-input
            v-model="form.summary"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="一句话简介,这个系列在做什么"
            class="doc-summary"
          />
        </div>

        <div class="pin-edit-body pin-edit-body--plain">
          <table class="aed-table">
            <tbody>
              <tr>
                <th>方向</th>
                <td>
                  <el-select v-model="form.direction" clearable filterable placeholder="未选方向" style="width:100%">
                    <el-option-group v-for="group in directionGroups" :key="group.label" :label="group.label">
                      <el-option v-for="item in group.options" :key="item.key" :label="item.label" :value="item.key" />
                    </el-option-group>
                  </el-select>
                </td>
              </tr>
              <tr>
                <th>状态</th>
                <td>
                  <el-select v-model="form.status" placeholder="选择状态" style="width:100%">
                    <el-option
                      v-for="item in seriesStatusOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </td>
              </tr>
              <tr v-for="row in positioningRows" :key="row.key">
                <th>{{ row.label }}</th>
                <td>
                  <el-input
                    v-model="positioning[row.key]"
                    type="textarea"
                    :autosize="{ minRows: 1 }"
                    :placeholder="row.placeholder"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="panelDialogOpen"
      :title="activePanelTitle"
      width="780px"
      :close-on-click-modal="false"
      class="pin-edit-dialog"
      @close="autoSaveSeries"
    >
      <div v-if="activePanel === 'series'" class="pin-edit-body pin-edit-body--plain">
        <table class="aed-table">
          <tbody>
            <tr>
              <th>标题</th>
              <td><el-input v-model="form.title" placeholder="给系列起个标题" /></td>
            </tr>
            <tr>
              <th>简介</th>
              <td>
                <el-input
                  v-model="form.summary"
                  type="textarea"
                  :autosize="{ minRows: 2 }"
                  placeholder="一句话简介,这个系列在做什么"
                />
              </td>
            </tr>
            <tr>
              <th>方向</th>
              <td>
                <el-select v-model="form.direction" clearable filterable placeholder="未选方向" style="width:100%">
                  <el-option-group v-for="group in directionGroups" :key="group.label" :label="group.label">
                    <el-option v-for="item in group.options" :key="item.key" :label="item.label" :value="item.key" />
                  </el-option-group>
                </el-select>
              </td>
            </tr>
            <tr>
              <th>状态</th>
              <td>
                <el-select v-model="form.status" placeholder="选择状态" style="width:100%">
                  <el-option
                    v-for="item in seriesStatusOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </td>
            </tr>
            <tr v-for="row in positioningRows" :key="row.key">
              <th>{{ row.label }}</th>
              <td>
                <el-input
                  v-model="positioning[row.key]"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  :placeholder="row.placeholder"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="activePanel === 'positioning'" class="pin-edit-body pin-edit-body--plain">
        <table class="aed-table">
          <tbody>
            <tr v-for="row in positioningRows" :key="row.key">
              <th>{{ row.label }}</th>
              <td>
                <el-input
                  v-model="positioning[row.key]"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  :placeholder="row.placeholder"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="activePanel === 'template'" class="pin-edit-body">
        <div class="pin-edit-actions">
          <el-button text size="small" :icon="Plus" @click="addSection">添加章节</el-button>
        </div>
        <div v-if="episodeTemplate.sections.length === 0" class="empty-state">
          <p>暂无章节,点击"添加章节"开始搭建单集结构</p>
        </div>
        <table v-else class="aed-table">
          <thead>
            <tr>
              <th class="aed-th-narrow">章节</th>
              <th class="aed-th-narrow">时长</th>
              <th>目标 / 要达成的效果</th>
              <th class="aed-th-action"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(section, idx) in episodeTemplate.sections" :key="idx">
              <td><el-input v-model="section.name" placeholder="开场钩子" /></td>
              <td><el-input v-model="section.duration" placeholder="0-3s" /></td>
              <td><el-input v-model="section.goal" placeholder="3 秒抓住观众" /></td>
              <td class="aed-th-action">
                <div class="row-order-actions">
                  <el-button
                    text
                    :icon="ArrowUp"
                    size="small"
                    :disabled="idx === 0"
                    title="上移"
                    @click="moveSection(idx, -1)"
                  />
                  <el-button
                    text
                    :icon="ArrowDown"
                    size="small"
                    :disabled="idx === episodeTemplate.sections.length - 1"
                    title="下移"
                    @click="moveSection(idx, 1)"
                  />
                  <el-button text type="danger" :icon="Delete" size="small" title="删除" @click="removeSection(idx)" />
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="must-have-block">
          <div class="must-have-label">必备元素 (每行一条)</div>
          <el-input
            v-model="mustHaveText"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="每集结尾留悬念&#10;主角必须出现在前 3 秒"
          />
        </div>
      </div>

      <div v-else-if="activePanel === 'style'" class="pin-edit-body">
        <div class="style-block">
          <div class="style-block-title">视觉风格</div>
          <table class="aed-table">
            <tbody>
              <tr>
                <th>调性</th>
                <td><el-input v-model="visualStyleDraft.tone" type="textarea" :autosize="{ minRows: 1 }" placeholder="治愈 / 悬疑 / 反差 / 浮夸" /></td>
              </tr>
              <tr>
                <th>色彩</th>
                <td><el-input v-model="visualStyleDraft.color" type="textarea" :autosize="{ minRows: 1 }" placeholder="暖色系 / 冷蓝高饱和 / 黑白对比" /></td>
              </tr>
              <tr>
                <th>光线</th>
                <td><el-input v-model="visualStyleDraft.lighting" type="textarea" :autosize="{ minRows: 1 }" placeholder="柔光 / 高对比 / 自然窗光 / 霓虹光" /></td>
              </tr>
              <tr>
                <th>镜头语言</th>
                <td><el-input v-model="visualStyleDraft.camera" type="textarea" :autosize="{ minRows: 1 }" placeholder="慢推 + 定格;手持 + 近景;固定中景" /></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="style-block mt">
          <div class="style-block-title">标题风格</div>
          <table class="aed-table">
            <tbody>
              <tr>
                <th>套路</th>
                <td><el-input v-model="titleStyleDraft.pattern" type="textarea" :autosize="{ minRows: 1 }" placeholder="数字 + 痛点 + 反转;一句话承诺;反常识断言" /></td>
              </tr>
              <tr>
                <th>示例</th>
                <td><el-input v-model="titleStyleDraft.examples" type="textarea" :autosize="{ minRows: 2 }" placeholder="一行一个示例标题" /></td>
              </tr>
              <tr>
                <th>字数</th>
                <td><el-input v-model="titleStyleDraft.length" placeholder="例如:8-15 字" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="activePanel === 'assets'" class="pin-edit-body">
        <div
          v-for="group in assetGroups"
          :key="group.type"
          class="asset-group"
        >
          <div class="asset-group-head">
            <strong>{{ group.label }}</strong>
            <span class="muted">{{ selectedAssetsMap[group.type].length }} 个已关联</span>
            <el-button text type="primary" size="small" :icon="Plus" @click="openQuickAsset(group.type)">
              新建并关联
            </el-button>
          </div>

          <div v-if="selectedAssetsMap[group.type].length" class="asset-mini-grid">
            <article
              v-for="item in selectedAssetsMap[group.type]"
              :key="item.id"
              class="asset-mini"
            >
              <div v-if="coverOf(item)" class="asset-mini-cover">
                <img :src="coverOf(item)?.thumb_url || coverOf(item)?.url" :alt="item.name" />
              </div>
              <div v-else class="asset-mini-cover asset-mini-cover--empty">
                <el-icon><Picture /></el-icon>
              </div>
              <div class="asset-mini-name">{{ item.name }}</div>
              <button
                type="button"
                class="asset-mini-remove"
                title="移除关联"
                @click="toggleAsset(group.type, item.id)"
              >
                <el-icon><Close /></el-icon>
              </button>
            </article>
          </div>

          <el-select
            v-model="form[group.type]"
            multiple
            filterable
            collapse-tags
            :placeholder="`从${group.label}库挑选...`"
            style="width:100%"
            class="asset-multi"
          >
            <el-option v-for="item in assets[group.type]" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </div>
      </div>

      <div v-else-if="activePanel === 'topics'" class="pin-edit-body">
        <el-input
          v-model="initialTopicsText"
          type="textarea"
          :autosize="{ minRows: 8 }"
          placeholder="一行一个选题,可以先列 5-20 条"
        />
      </div>

      <template #footer>
        <el-button @click="panelDialogOpen = false">关闭</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="planPickerOpen"
      title="添加我的方案"
      width="720px"
      :close-on-click-modal="false"
      class="plan-picker-dialog"
    >
      <div class="plan-picker">
        <el-input
          v-model="planPickerSearch"
          clearable
          :prefix-icon="Search"
          placeholder="搜索方案标题、简介"
        />

        <div v-loading="planPickerLoading" class="plan-picker-list">
          <div v-if="!planPickerLoading && filteredAttachablePlans.length === 0" class="empty-state">
            <p>{{ planPickerSearch ? '没有匹配的可添加方案' : '我的方案中暂无可添加方案' }}</p>
          </div>

          <article
            v-for="item in filteredAttachablePlans"
            :key="item.id"
            class="plan-picker-item"
          >
            <div class="plan-picker-main">
              <strong>{{ item.title || '未命名方案' }}</strong>
              <p>{{ item.summary || '暂无简介' }}</p>
              <span>
                {{ findDirectionLabel(item.direction) || '未选方向' }}
                · {{ episodeStatusLabel(item.status) }}
                · {{ item.duration_seconds }}s
              </span>
            </div>
            <el-button
              type="primary"
              size="small"
              :disabled="!!attachingPlanId && attachingPlanId !== item.id"
              :loading="attachingPlanId === item.id"
              @click="attachPlanToSeries(item)"
            >
              添加
            </el-button>
          </article>
        </div>
      </div>
      <template #footer>
        <el-button @click="planPickerOpen = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="relationshipDialogOpen"
      title="资产关系"
      width="760px"
      :close-on-click-modal="false"
      class="relationship-edit-dialog"
    >
      <div class="relationship-dialog-body">
        <div v-if="relationshipAssetOptions.length < 2" class="empty-state">
          <p>至少关联两个资产后,才能编辑资产关系。</p>
        </div>
        <template v-else>
          <div
            v-for="(row, idx) in relationshipDraftRows"
            :key="`relationship-draft-${idx}`"
            class="relationship-edit-row"
          >
            <el-select v-model="row.from_asset_id" filterable placeholder="资产 A">
              <el-option
                v-for="item in relationshipAssetOptions"
                :key="item.id"
                :label="relationshipAssetOptionLabel(item)"
                :value="item.id"
              />
            </el-select>
            <el-select v-model="row.to_asset_id" filterable placeholder="资产 B">
              <el-option
                v-for="item in relationshipTargetOptions(row)"
                :key="item.id"
                :label="relationshipAssetOptionLabel(item)"
                :value="item.id"
              />
            </el-select>
            <el-input v-model="row.label" placeholder="关系,如朋友 / 居住 / 工作 / 冲突" />
            <el-button
              text
              type="danger"
              :icon="Delete"
              title="删除关系"
              @click="removeRelationshipDraft(idx)"
            />
          </div>
          <el-button
            text
            size="small"
            :icon="Plus"
            :disabled="relationshipAssetOptions.length < 2"
            @click="addRelationshipDraft"
          >
            添加关系
          </el-button>
        </template>
      </div>
      <template #footer>
        <el-button @click="relationshipDialogOpen = false">取消</el-button>
        <el-button type="primary" @click="applyRelationshipDialog">应用到画布</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="bigEnvironmentDialogOpen"
      title="大环境"
      width="720px"
      :close-on-click-modal="false"
      class="asset-edit-dialog"
      @close="autoSaveSeries"
    >
      <el-form label-position="top">
        <el-form-item class="aed-gallery-item">
          <AssetImageGallery
            v-model="bigEnvironment.images"
            :labels="bigEnvironmentImageLabels"
            :ai-prompt-provider="buildBigEnvironmentPrompt"
          />
        </el-form-item>
        <table class="aed-table">
          <tbody>
            <tr>
              <th>名称</th>
              <td><el-input v-model="bigEnvironment.name" placeholder="例如: 海边小镇 / 未来校园" /></td>
            </tr>
            <tr>
              <th>描述</th>
              <td>
                <el-input
                  v-model="bigEnvironment.description"
                  type="textarea"
                  :autosize="{ minRows: 2 }"
                  placeholder="所有角色共同所处的总体环境"
                />
              </td>
            </tr>
            <tr>
              <th>影调与色彩</th>
              <td><el-input v-model="bigEnvironment.tone_color" placeholder="例如: 低饱和暖光、浅雾感" /></td>
            </tr>
            <tr>
              <th>固定规则</th>
              <td>
                <el-input
                  v-model="bigEnvironmentRulesText"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  placeholder="每行一条"
                />
              </td>
            </tr>
            <tr>
              <th>代表地点</th>
              <td>
                <el-input
                  v-model="bigEnvironmentLocationsText"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  placeholder="每行一条"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </el-form>
      <template #footer>
        <el-button @click="bigEnvironmentDialogOpen = false">关闭</el-button>
        <el-button type="primary" @click="bigEnvironmentDialogOpen = false">完成</el-button>
      </template>
    </el-dialog>

    <!-- AI 生成单集弹窗保留给内部生成流程。 -->
    <el-dialog v-model="episodeDialogOpen" title="AI 生成单集" width="560px" :close-on-click-modal="false">
      <el-form :model="episodeForm" label-position="top">
        <el-form-item label="本集主题">
          <el-input v-model="episodeForm.topic" placeholder="例如:第 1 集 转校生收到匿名纸条" />
        </el-form-item>
        <el-form-item label="本集目标">
          <el-input v-model="episodeForm.episode_goal" type="textarea" :rows="2" placeholder="例如:建立主角形象,埋下悬念" />
        </el-form-item>
        <el-form-item label="额外要求">
          <el-input v-model="episodeForm.extra_requirements" type="textarea" :rows="3" placeholder="例如:结尾必须反转,主角不能改变发色" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="episodeDialogOpen = false" :disabled="generatingEpisode">取消</el-button>
        <el-button type="primary" :loading="generatingEpisode" @click="onGenerateEpisode">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="assetSuggestionDialogOpen"
      title="发现新资产"
      width="640px"
      :close-on-click-modal="!assetSuggestionSaving"
    >
      <div class="asset-suggestion-dialog">
        <p class="asset-suggestion-copy">
          AI 在本集里发现了新的角色、小环境或资产关系，确认后会同步到当前系列。
        </p>
        <div v-for="group in assetSuggestionGroups" :key="group.type" class="asset-suggestion-group">
          <div class="asset-suggestion-group-title">
            <el-icon><component :is="group.icon" /></el-icon>
            <span>{{ group.label }}</span>
          </div>
          <label v-for="item in group.items" :key="item.key" class="asset-suggestion-item">
            <el-checkbox v-model="assetSuggestionSelection[item.key]" :disabled="assetSuggestionSaving" />
            <div>
              <strong>{{ item.name }}</strong>
              <p>{{ assetSuggestionSummary(item) }}</p>
            </div>
          </label>
        </div>
        <div v-if="pendingRelationshipSuggestions.length" class="asset-suggestion-group">
          <div class="asset-suggestion-group-title">
            <el-icon><Connection /></el-icon>
            <span>资产关系</span>
          </div>
          <label v-for="item in pendingRelationshipSuggestions" :key="relationshipDisplayKey(item)" class="asset-suggestion-item">
            <el-checkbox :model-value="true" disabled />
            <div>
              <strong>{{ relationshipDisplayText(item) }}</strong>
              <p>确认后会映射到关系画布</p>
            </div>
          </label>
        </div>
      </div>
      <template #footer>
        <el-button @click="dismissAssetSuggestions" :disabled="assetSuggestionSaving">跳过</el-button>
        <el-button
          type="primary"
          :loading="assetSuggestionSaving"
          :disabled="!selectedAssetSuggestions.length && !pendingRelationshipSuggestions.length"
          @click="confirmAssetSuggestions"
        >
          同步到系列
        </el-button>
      </template>
    </el-dialog>

    <!-- 一致性检查 modal -->
    <el-dialog v-model="reportDialogOpen" title="一致性检查报告" width="640px">
      <div v-if="report" class="report">
        <div class="report-head">
          <div class="score-block">
            <div class="score" :class="scoreClass">{{ report.score }}</div>
            <div class="muted">总分</div>
          </div>
          <div class="muted">共发现 {{ report.issues.length }} 项问题</div>
        </div>
        <div v-if="report.issues.length === 0" class="empty">系列与单集设定一致,未发现冲突。</div>
        <div v-for="(issue, idx) in report.issues" :key="idx" class="issue-row">
          <div class="issue-head">
            <el-tag :type="levelTag(issue.level)" size="small">{{ issue.level }}</el-tag>
            <span v-if="issue.asset_type" class="muted">{{ issue.asset_type }}{{ issue.field ? ` / ${issue.field}` : '' }}</span>
          </div>
          <div class="issue-msg">{{ issue.message }}</div>
          <div v-if="issue.suggestion" class="issue-fix muted">建议: {{ issue.suggestion }}</div>
        </div>
      </div>
    </el-dialog>

    <!-- 资产快建 dialog (kept) -->
    <el-dialog
      v-model="assetDialogOpen"
      :title="assetEditingId ? `编辑${activeAssetSchema.title}` : `新建${activeAssetSchema.title}`"
      width="720px"
      :close-on-click-modal="false"
      class="asset-edit-dialog"
    >
      <el-form label-position="top">
        <el-form-item class="aed-gallery-item">
          <AssetImageGallery
            v-model="assetImages"
            :labels="activeAssetSchema.imageLabels"
            :ai-prompt-provider="buildQuickAssetPrompt"
          />
        </el-form-item>

        <table class="aed-table">
          <tbody>
            <tr>
              <th>名称</th>
              <td>
                <el-input v-model="assetForm.name" :placeholder="`例如: ${activeAssetSchema.title}`" />
              </td>
            </tr>
            <tr v-for="field in activeAssetSchema.fields" :key="field.key">
              <th>{{ field.label }}</th>
              <td>
                <el-input
                  v-if="field.kind === 'text'"
                  v-model="assetTextValues[field.key]"
                  :placeholder="field.placeholder"
                />
                <el-input
                  v-else
                  v-model="assetTextValues[field.key]"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  :placeholder="field.placeholder"
                />
              </td>
            </tr>
            <tr>
              <th>固定特征</th>
              <td>
                <el-input
                  v-model="assetFixedTraitsText"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  placeholder="每行一条"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </el-form>
      <template #footer>
        <div class="asset-dialog-footer">
          <el-button
            v-if="assetEditingId"
            type="danger"
            text
            :icon="Delete"
            :loading="assetDeleting"
            :disabled="assetSaving"
            @click="deleteActiveAsset"
          >
            删除
          </el-button>
          <span v-else />
          <div class="asset-dialog-actions">
            <el-button @click="assetDialogOpen = false" :disabled="assetSaving || assetDeleting">取消</el-button>
            <el-button type="primary" :loading="assetSaving" :disabled="assetDeleting" @click="saveQuickAsset">
              {{ assetEditingId ? '保存' : '保存并关联' }}
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Brush,
  Close,
  Delete,
  DocumentChecked,
  EditPen,
  Hide,
  House,
  MagicStick,
  MapLocation,
  Mouse,
  Notebook,
  Picture,
  Pointer,
  Plus,
  RefreshLeft,
  Search,
  Setting,
  User,
  UserFilled,
  View,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { isAITaskResponse } from '@/api/aiTasks'
import { assetsApi } from '@/api/assets'
import { plansApi } from '@/api/plans'
import { seriesApi, type ConsistencyReport, type SeriesPayload } from '@/api/series'
import AssetImageGallery from '@/components/AssetImageGallery.vue'
import { ASSET_SCHEMAS } from '@/data/assetSchemas'
import { CATEGORIES, DIRECTIONS, findDirectionLabel } from '@/data/directions'
import type {
  AITask,
  AssetBase,
  AssetImage,
  AssetSuggestion,
  AssetType,
  EpisodeAssetSuggestions,
  EpisodeSummary,
  VideoPlan,
} from '@/types/api'
import {
  type ActiveAITask,
  findActiveAITask,
  removeActiveAITask,
  saveActiveAITask,
  waitForAITask,
} from '@/utils/aiTaskRecovery'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'series-new')
const isRelationshipPage = computed(() => route.name === 'series-relationships')
const loading = ref(false)
const saving = ref(false)

const directionGroups = CATEGORIES.map((cat) => ({
  label: cat.label,
  options: DIRECTIONS[cat.key],
}))

const seriesStatusOptions: { label: string; value: SeriesPayload['status'] }[] = [
  { label: '草稿', value: 'draft' },
  { label: '连载中', value: 'ongoing' },
  { label: '已暂停', value: 'paused' },
  { label: '已完成', value: 'completed' },
]

const form = reactive<SeriesPayload>(defaultPayload())

const assetGroups: { type: AssetType; label: string }[] = [
  { type: 'characters', label: '人物' },
  { type: 'worldviews', label: '环境' },
]

interface Positioning {
  core_concept: string
  target_user: string
  promise: string
}

interface EpisodeSection {
  name: string
  duration: string
  goal: string
}

interface EpisodeTemplate {
  sections: EpisodeSection[]
  must_have: string[]
}

const positioning = reactive<Positioning>({
  core_concept: '',
  target_user: '',
  promise: '',
})

const episodeTemplate = reactive<EpisodeTemplate>({
  sections: [],
  must_have: [],
})

const initialTopicsList = ref<string[]>([])

/**
 * Visual + title style — was previously raw JSON textareas. We now expose
 * named fields so users don't need to author JSON. The form still saves as
 * a generic `{}` dict so any extra keys preserved by the AI generator pass
 * through untouched.
 */
const visualStyleDraft = reactive({
  tone: '',
  color: '',
  lighting: '',
  camera: '',
})
const titleStyleDraft = reactive({
  pattern: '',
  examples: '',
  length: '',
})

// Document-section collapse state. Default: only 单集列表 expanded for
// returning users (their main reason to open SeriesEditor again is to add
// or check episodes). 系列定位 also opens for first-time / new-series users
// since the series doesn't exist yet.
const sections = reactive({
  positioning: true,
  template: false,
  style: false,
  assets: false,
  topics: false,
  episodes: true,
})

type PinPanel = 'series' | 'positioning' | 'template' | 'style' | 'assets' | 'topics'
type PinKind = 'asset'
type PinLineKind = 'relationship'
type RelationshipAssetType = 'characters' | 'worldviews'
type BoardTool = 'select' | 'move'
type ConnectSide = 'top' | 'right' | 'bottom' | 'left'

interface PinRelation {
  id: string
  fromId: string
  toId: string
  label: string
  deleted?: boolean
}

interface SeriesRelationship {
  from: string
  to: string
  label: string
  description: string
  from_asset_id?: string
  to_asset_id?: string
  from_asset_type?: RelationshipAssetType
  to_asset_type?: RelationshipAssetType
  from_asset_name?: string
  to_asset_name?: string
}

interface RelationshipEditDraft {
  from_asset_id: string
  to_asset_id: string
  label: string
}

interface RelationshipAssetOption {
  id: string
  type: RelationshipAssetType
  name: string
}

interface BigEnvironment {
  name: string
  description: string
  tone_color: string
  rules: string[]
  locations: string[]
  images: AssetImage[]
}

type EpisodeSuggestionAssetType = 'characters' | 'worldviews'

interface PendingAssetSuggestion extends AssetSuggestion {
  key: string
  asset_type: EpisodeSuggestionAssetType
}

interface PinNode {
  id: string
  kind: PinKind
  panel?: PinPanel
  targetId?: string
  assetType?: AssetType
  kicker: string
  title: string
  subtitle: string
  tags: string[]
  images: AssetImage[]
  x: number
  y: number
  w: number
  h: number
}

interface PinLine {
  id: string
  from: PinNode
  to: PinNode
  kind: PinLineKind
  relation: PinRelation
}

interface Point {
  x: number
  y: number
}

interface RelationDrag {
  fromId: string
  side: ConnectSide
  start: Point
  end: Point
}

const connectSides: ConnectSide[] = ['top', 'right', 'bottom', 'left']
const boardRef = ref<HTMLElement | null>(null)
const pinboardViewportSize = reactive({ width: 0, height: 0 })
const boardLayout = reactive<Record<string, { x: number; y: number }>>({})
const imageOnlyBoardLayout = reactive<Record<string, { x: number; y: number }>>({})
const boardScale = ref(0.92)
const boardTool = ref<BoardTool>('select')
const draggingNodeId = ref('')
const canvasImageOnlyMode = ref(false)
const activeRelationId = ref('')
const relationDraft = ref('')
const relationInputRef = ref<HTMLInputElement | null>(null)
const relationStartNodeId = ref('')
const relationDrag = ref<RelationDrag | null>(null)
const suppressPinClick = ref(false)
const panelDialogOpen = ref(false)
const activePanel = ref<PinPanel>('series')
const relationshipDialogOpen = ref(false)
const bigEnvironmentDialogOpen = ref(false)
const relationEdges = ref<PinRelation[]>([])
const aiRelationshipRows = ref<SeriesRelationship[]>([])
const relationshipDraftRows = ref<RelationshipEditDraft[]>([])
const bigEnvironment = reactive<BigEnvironment>({
  name: '',
  description: '',
  tone_color: '',
  rules: [],
  locations: [],
  images: [],
})
const bigEnvironmentImageLabels = ['背景', '色彩', '地标', '氛围', '其他']

const pinLayoutKey = computed(() => `vp.series.relationship-canvas.${route.params.id || 'new'}`)
const imageOnlyPinLayoutKey = computed(() => `vp.series.image-canvas.${route.params.id || 'new'}`)
const relationStorageKey = computed(() => `vp.series.relationships.${route.params.id || 'new'}`)

let pinboardResizeObserver: ResizeObserver | null = null

function assetNodeFrame(index: number) {
  const characterCount = selectedAssetsMap.value.characters.length
  const isEnvironment = index >= characterCount
  const localIndex = isEnvironment ? index - characterCount : index
  if (canvasImageOnlyMode.value) {
    const col = localIndex % 3
    const row = Math.floor(localIndex / 3)
    const groupX = 86 + col * 390
    const groupY = 106 + row * 270
    return isEnvironment
      ? {
          x: groupX + 136,
          y: groupY + 26,
          w: 244,
          h: 178,
        }
      : {
          x: groupX,
          y: groupY + 74,
          w: 128,
          h: 148,
        }
  }
  const col = localIndex % 3
  const row = Math.floor(localIndex / 3)
  return {
    x: isEnvironment ? 790 + col * 250 : 70 + col * 250,
    y: 80 + row * 180,
    w: 220,
    h: 148,
  }
}

const basePinboardSize = computed(() => {
  const assetCount = Math.max(totalSelectedAssets.value, 1)
  if (canvasImageOnlyMode.value) {
    const pairs = Math.max(selectedAssetsMap.value.characters.length, selectedAssetsMap.value.worldviews.length, 1)
    const rows = Math.ceil(pairs / 3)
    return {
      width: Math.max(1420, 170 + Math.min(pairs, 3) * 390),
      height: Math.max(760, 180 + rows * 270),
    }
  }
  const rows = Math.max(
    Math.ceil(selectedAssetsMap.value.characters.length / 3),
    Math.ceil(selectedAssetsMap.value.worldviews.length / 3),
    1,
  )
  return {
    width: Math.max(1420, 860 + Math.min(Math.max(assetCount, 1), 3) * 250),
    height: Math.max(760, 180 + rows * 180),
  }
})

const pinboardSize = computed(() => {
  const base = basePinboardSize.value
  const layout = canvasImageOnlyMode.value ? imageOnlyBoardLayout : boardLayout
  let width = Math.max(base.width, Math.ceil(pinboardViewportSize.width / boardScale.value) + 48)
  let height = Math.max(base.height, Math.ceil(pinboardViewportSize.height / boardScale.value) + 48)

  for (const node of pinNodes.value) {
    const pos = layout[node.id] || { x: node.x, y: node.y }
    width = Math.max(width, Math.ceil(pos.x + node.w + 220))
    height = Math.max(height, Math.ceil(pos.y + node.h + 180))
  }

  return { width, height }
})

const bigEnvironmentCover = computed(() => bigEnvironment.images.find((image) => image.url || image.thumb_url))
const pinboardCanvasStyle = computed(() => {
  const style: Record<string, string> = {
    width: `${pinboardSize.value.width}px`,
    height: `${pinboardSize.value.height}px`,
    transform: `scale(${boardScale.value})`,
  }
  const imageUrl = bigEnvironmentCover.value?.url || bigEnvironmentCover.value?.thumb_url || ''
  if (imageUrl) {
    const safeUrl = imageUrl.replace(/"/g, '%22')
    style.backgroundImage = `linear-gradient(rgba(255,255,255,.78), rgba(255,255,255,.84)), url("${safeUrl}")`
    style.backgroundSize = 'cover'
    style.backgroundPosition = 'center'
  }
  return style
})

const pinNodes = computed<PinNode[]>(() => {
  const nodes: PinNode[] = []

  let assetIndex = 0
  for (const group of assetGroups) {
    for (const item of selectedAssetsMap.value[group.type]) {
      const cover = coverOf(item)
      const frame = assetNodeFrame(assetIndex)
      nodes.push({
        id: `asset-${group.type}-${item.id}`,
        kind: 'asset',
        panel: 'assets',
        targetId: item.id,
        assetType: group.type,
        kicker: group.label,
        title: item.name || '未命名资产',
        subtitle: assetSummary(item),
        tags: assetTags(item),
        images: cover ? [cover] : [],
        ...frame,
      })
      assetIndex += 1
    }
  }

  return nodes
})

const pinLines = computed<PinLine[]>(() => {
  const byId = new Map(pinNodes.value.map((node) => [node.id, node]))
  const lines: PinLine[] = []
  for (const relation of relationEdges.value) {
    if (relation.deleted) continue
    if (!relation.label.trim() && activeRelationId.value !== relation.id) continue
    const from = byId.get(relation.fromId)
    const to = byId.get(relation.toId)
    if (!from || !to) continue
    lines.push({ id: relation.id, from, to, kind: 'relationship', relation })
  }
  return lines
})

const activeRelationLine = computed(() =>
  pinLines.value.find((line) => line.relation.id === activeRelationId.value),
)
const actionableRelationLines = computed(() =>
  pinLines.value,
)
const relationshipDisplayRows = computed<SeriesRelationship[]>(() => {
  const rows: SeriesRelationship[] = []
  const seenRelations = new Set<string>()
  const seenEndpoints = new Set<string>()
  const deleted = new Set(relationEdges.value.filter((relation) => relation.deleted).map((relation) => relation.id))

  for (const line of pinLines.value) {
    if (isEnvironmentRelation(line)) continue
    const label = line.relation.label.trim()
    if (!label) continue
    const row = relationshipFromLine(line)
    seenRelations.add(line.relation.id)
    const endpointKey = relationshipEndpointKey(row)
    if (endpointKey) seenEndpoints.add(endpointKey)
    rows.push(row)
  }

  for (const row of aiRelationshipRows.value) {
    const relationKey = relationshipRelationId(row)
    if (relationKey && deleted.has(relationKey)) continue
    const endpointKey = relationshipEndpointKey(row)
    if (relationKey && seenRelations.has(relationKey)) continue
    if (endpointKey && seenEndpoints.has(endpointKey)) continue
    if (relationshipDisplayText(row)) {
      if (relationKey) seenRelations.add(relationKey)
      if (endpointKey) seenEndpoints.add(endpointKey)
      rows.push(row)
    }
  }

  return rows
})
const relationPreviewPath = computed(() =>
  relationDrag.value ? pointCurvePath(relationDrag.value.start, relationDrag.value.end) : '',
)

const activePanelTitle = computed(() => ({
  series: '系列详情',
  positioning: '系列定位',
  template: '单集章节模板',
  style: '视听风格',
  assets: '资产引用',
  topics: '选题池',
})[activePanel.value])

const positioningRows: Array<{ key: keyof Positioning; label: string; placeholder: string }> = [
  { key: 'core_concept', label: '核心概念', placeholder: '一句话说清这个系列做什么、解决什么' },
  { key: 'target_user', label: '目标用户', placeholder: '是谁、有什么诉求' },
  { key: 'promise', label: '观众承诺', placeholder: '看完这个系列他们能得到什么' },
]

const assets = reactive<Record<AssetType, AssetBase[]>>({
  characters: [],
  styles: [],
  worldviews: [],
  columns: [],
})

const episodes = ref<EpisodeSummary[]>([])

const planPickerOpen = ref(false)
const planPickerLoading = ref(false)
const planPickerSearch = ref('')
const attachablePlans = ref<VideoPlan[]>([])
const attachingPlanId = ref('')
const episodeReordering = ref(false)
const draggingEpisodeId = ref('')
const dragOverEpisodeId = ref('')
const dragOverSide = ref<'before' | 'after'>('before')
const deletingEpisodeId = ref('')

const episodeDialogOpen = ref(false)
const generatingEpisode = ref(false)
const episodeForm = reactive({ topic: '', episode_goal: '', extra_requirements: '' })
const episodeIdea = ref('')
const episodeConversationMessages = ref<Array<{ key: string; role: 'user' | 'ai'; text: string }>>([])
const assetSuggestionDialogOpen = ref(false)
const assetSuggestionSaving = ref(false)
const pendingAssetSuggestions = ref<PendingAssetSuggestion[]>([])
const pendingRelationshipSuggestions = ref<SeriesRelationship[]>([])
const assetSuggestionSelection = reactive<Record<string, boolean>>({})
const selectedAssetSuggestions = computed(() =>
  pendingAssetSuggestions.value.filter((item) => assetSuggestionSelection[item.key]),
)
const assetSuggestionGroups = computed(() => [
  {
    type: 'characters' as const,
    label: '新人物',
    icon: User,
    items: pendingAssetSuggestions.value.filter((item) => item.asset_type === 'characters'),
  },
  {
    type: 'worldviews' as const,
    label: '新环境',
    icon: House,
    items: pendingAssetSuggestions.value.filter((item) => item.asset_type === 'worldviews'),
  },
].filter((group) => group.items.length))

const reportDialogOpen = ref(false)
const checking = ref(false)
const report = ref<ConsistencyReport | null>(null)
const taskMessage = ref('')
const taskProgress = ref(0)
let taskAbortController: AbortController | null = null
const assetDialogOpen = ref(false)
const assetSaving = ref(false)
const assetDeleting = ref(false)
const assetEditingId = ref<string | null>(null)
const activeAssetType = ref<AssetType>('characters')
const activeAssetSchema = computed(() => ASSET_SCHEMAS[activeAssetType.value])
const assetForm = reactive({ name: '' })
const assetTextValues = reactive<Record<string, string>>({})
const assetFixedTraitsList = ref<string[]>([])
const assetImages = ref<AssetImage[]>([])
const scoreClass = computed(() => {
  if (!report.value) return ''
  if (report.value.score >= 90) return 'score-good'
  if (report.value.score >= 70) return 'score-warn'
  return 'score-bad'
})

const mustHaveText = computed({
  get: () => episodeTemplate.must_have.join('\n'),
  set: (v) => {
    episodeTemplate.must_have = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const initialTopicsText = computed({
  get: () => initialTopicsList.value.join('\n'),
  set: (v) => {
    initialTopicsList.value = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const assetFixedTraitsText = computed({
  get: () => assetFixedTraitsList.value.join('\n'),
  set: (v) => {
    assetFixedTraitsList.value = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const bigEnvironmentRulesText = computed({
  get: () => bigEnvironment.rules.join('\n'),
  set: (v) => {
    bigEnvironment.rules = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const bigEnvironmentLocationsText = computed({
  get: () => bigEnvironment.locations.join('\n'),
  set: (v) => {
    bigEnvironment.locations = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const selectedAssetsMap = computed<Record<AssetType, AssetBase[]>>(() => {
  const out = {} as Record<AssetType, AssetBase[]>
  for (const group of assetGroups) {
    const selected = new Set(form[group.type])
    out[group.type] = assets[group.type].filter((item) => selected.has(item.id))
  }
  return out
})

const relationshipAssetOptions = computed<RelationshipAssetOption[]>(() => [
  ...selectedAssetsMap.value.characters.map((item) => ({ id: item.id, type: 'characters' as const, name: item.name })),
  ...selectedAssetsMap.value.worldviews.map((item) => ({ id: item.id, type: 'worldviews' as const, name: item.name })),
])

const overviewStats = computed(() => [
  { label: '方向', value: findDirectionLabel(form.direction) },
  { label: '状态', value: seriesStatusLabel(form.status) },
  { label: '单集进度', value: `${episodes.value.length}/${form.planned_episodes || 0}` },
  { label: '单集时长', value: `${form.episode_duration_seconds || 0}s` },
  { label: '关联资产', value: String(assetGroups.reduce((sum, group) => sum + form[group.type].length, 0)) },
])

const positioningOverview = computed(() => [
  { label: '核心概念', value: positioning.core_concept },
  { label: '目标用户', value: positioning.target_user },
  { label: '观众承诺', value: positioning.promise },
])

const recentEpisodes = computed(() => episodes.value.slice(0, 5))

onMounted(async () => {
  loading.value = true
  try {
    await loadAssets()
    if (!isNew.value) {
      const data = await seriesApi.get(route.params.id as string)
      hydrateFromServer(data)
      resumeSeriesTasks(data.id)
    } else {
      syncStyleDrafts()
    }
    loadPinLayout()
    loadImageOnlyPinLayout()
    loadRelations()
    await nextTick()
    setupPinboardViewportObserver()
  } finally {
    loading.value = false
  }
})

async function loadAssets() {
  const types: AssetType[] = assetGroups.map((group) => group.type)
  const results = await Promise.all(types.map((type) => assetsApi.list(type)))
  types.forEach((type, index) => {
    assets[type] = results[index].results
  })
}

function hydrateFromServer(data: import('@/types/api').SeriesPlan) {
  Object.assign(form, {
    title: data.title,
    direction: data.direction,
    summary: data.summary,
    target_platform: data.target_platform,
    target_audience: data.target_audience,
    update_frequency: data.update_frequency,
    episode_duration_seconds: data.episode_duration_seconds,
    planned_episodes: data.planned_episodes,
    positioning: data.positioning,
    episode_template: data.episode_template,
    visual_style: data.visual_style,
    title_style: data.title_style,
    initial_topics: data.initial_topics,
    characters: data.characters,
    styles: data.styles,
    worldviews: data.worldviews,
    columns: data.columns,
    status: data.status,
  })

  const p = (data.positioning as Partial<Positioning>) || {}
  positioning.core_concept = p.core_concept || ''
  positioning.target_user = p.target_user || ''
  positioning.promise = p.promise || ''
  hydrateBigEnvironment((data.positioning as Record<string, unknown> | null | undefined)?.big_environment)
  aiRelationshipRows.value = normalizeRelationshipRows(
    (data.positioning as Record<string, unknown> | null | undefined)?.relationships,
  )

  const tpl = (data.episode_template as Partial<EpisodeTemplate>) || {}
  episodeTemplate.sections = Array.isArray(tpl.sections)
    ? tpl.sections.map((s) => ({
        name: s?.name || '',
        duration: s?.duration ? String(s.duration) : '',
        goal: s?.goal || '',
      }))
    : []
  episodeTemplate.must_have = Array.isArray(tpl.must_have)
    ? tpl.must_have.map((x) => String(x)).filter(Boolean)
    : []

  initialTopicsList.value = Array.isArray(data.initial_topics)
    ? data.initial_topics.map((x) => (typeof x === 'string' ? x : JSON.stringify(x)))
    : []

  episodes.value = sortEpisodes(Array.isArray(data.episodes) ? data.episodes : [])
  syncStyleDrafts()
}

/** Pull structured fields out of the dict-shaped visual_style/title_style
 * the backend stores. Unknown keys are ignored — they survive on the form
 * object and get written back via buildPayload's spread. */
function syncStyleDrafts() {
  const vs = (form.visual_style || {}) as Record<string, unknown>
  visualStyleDraft.tone = pickStr(vs.tone)
  visualStyleDraft.color = pickStr(vs.color)
  visualStyleDraft.lighting = pickStr(vs.lighting)
  visualStyleDraft.camera = pickStr(vs.camera)

  const ts = (form.title_style || {}) as Record<string, unknown>
  titleStyleDraft.pattern = pickStr(ts.pattern)
  titleStyleDraft.examples = Array.isArray(ts.examples)
    ? ts.examples.map((x) => String(x)).join('\n')
    : pickStr(ts.examples)
  titleStyleDraft.length = pickStr(ts.length)
}

function pickStr(v: unknown): string {
  if (typeof v === 'string') return v
  if (Array.isArray(v)) return v.map((x) => String(x)).join('\n')
  if (v == null) return ''
  return String(v)
}

function listFromUnknown(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean)
  if (typeof value === 'string') return value.split(/\n|[;；、,，]/).map((item) => item.trim()).filter(Boolean)
  return []
}

function hydrateBigEnvironment(value: unknown) {
  const raw = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  bigEnvironment.name = pickStr(raw.name || raw.title) || '系列大环境'
  bigEnvironment.description = pickStr(raw.description || raw.background || raw.summary)
  bigEnvironment.tone_color = pickStr(raw.tone_color || raw.tone || raw.color)
  bigEnvironment.rules = listFromUnknown(raw.rules)
  bigEnvironment.locations = listFromUnknown(raw.locations)
  bigEnvironment.images = Array.isArray(raw.images) ? raw.images as AssetImage[] : []
}

function buildBigEnvironmentPayload(): BigEnvironment {
  return {
    name: bigEnvironment.name.trim() || '系列大环境',
    description: bigEnvironment.description.trim(),
    tone_color: bigEnvironment.tone_color.trim(),
    rules: [...bigEnvironment.rules],
    locations: [...bigEnvironment.locations],
    images: [...bigEnvironment.images],
  }
}

function openBigEnvironmentDialog() {
  if (!bigEnvironment.name.trim()) bigEnvironment.name = '系列大环境'
  bigEnvironmentDialogOpen.value = true
}

function buildBigEnvironmentPrompt(): string {
  const lines: string[] = []
  const name = bigEnvironment.name.trim() || form.title.trim() || '系列大环境'
  lines.push(`场景:${name}`)
  if (bigEnvironment.description.trim()) lines.push(`总体环境:${bigEnvironment.description.trim()}`)
  else if (form.summary.trim()) lines.push(`系列简介:${form.summary.trim()}`)
  if (bigEnvironment.tone_color.trim()) lines.push(`影调与色彩:${bigEnvironment.tone_color.trim()}`)
  if (bigEnvironment.rules.length) lines.push(`环境规则:${bigEnvironment.rules.join(' / ')}`)
  if (bigEnvironment.locations.length) lines.push(`代表地点:${bigEnvironment.locations.join(' / ')}`)
  lines.push('生成一张适合作为视频系列关系画布背景的横版环境图,浅色、低饱和、干净、有空间纵深,不要文字,不要人物特写,主体不要过暗。')
  return lines.join('\n')
}

function addSection() {
  episodeTemplate.sections.push({ name: '', duration: '', goal: '' })
}
function removeSection(idx: number) {
  episodeTemplate.sections.splice(idx, 1)
}
function moveSection(idx: number, delta: -1 | 1) {
  const target = idx + delta
  if (target < 0 || target >= episodeTemplate.sections.length) return
  const [item] = episodeTemplate.sections.splice(idx, 1)
  if (!item) return
  episodeTemplate.sections.splice(target, 0, item)
}

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写系列标题')
    return
  }
  const payload = buildPayload()
  if (!payload) return

  saving.value = true
  try {
    if (isNew.value) {
      const created = await seriesApi.create(payload)
      ElMessage.success('已创建系列')
      router.replace(`/app/series/${created.id}`)
    } else {
      const updated = await seriesApi.patch(route.params.id as string, payload)
      ElMessage.success('已保存')
      hydrateFromServer(updated)
    }
  } finally {
    saving.value = false
  }
}

async function autoSaveSeries() {
  if (isNew.value || !route.params.id || !form.title.trim()) return
  const payload = buildPayload()
  if (!payload) return

  saving.value = true
  try {
    await seriesApi.patch(route.params.id as string, payload)
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '自动保存失败'
    ElMessage.error(String(detail))
  } finally {
    saving.value = false
  }
}

function buildPayload(): SeriesPayload | null {
  // Merge the structured drafts back over whatever was already in form.*_style
  // so unknown keys (e.g. fields the AI added that aren't in our schema) are
  // preserved. Empty values get omitted so the dict stays clean.
  const visualStyle: Record<string, unknown> = { ...(form.visual_style || {}) }
  for (const [k, v] of Object.entries(visualStyleDraft)) {
    const trimmed = (v || '').trim()
    if (trimmed) visualStyle[k] = trimmed
    else delete visualStyle[k]
  }

  const titleStyle: Record<string, unknown> = { ...(form.title_style || {}) }
  if (titleStyleDraft.pattern.trim()) titleStyle.pattern = titleStyleDraft.pattern.trim()
  else delete titleStyle.pattern
  if (titleStyleDraft.examples.trim()) {
    titleStyle.examples = titleStyleDraft.examples
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
  } else {
    delete titleStyle.examples
  }
  if (titleStyleDraft.length.trim()) titleStyle.length = titleStyleDraft.length.trim()
  else delete titleStyle.length

  return {
    ...form,
    positioning: {
      ...positioning,
      big_environment: buildBigEnvironmentPayload(),
      relationships: dedupeRelationshipRows(relationshipDisplayRows.value),
    },
    episode_template: {
      sections: episodeTemplate.sections
        .filter((s) => s.name.trim() || s.goal.trim() || s.duration.trim())
        .map((s) => ({ name: s.name, duration: s.duration, goal: s.goal })),
      must_have: [...episodeTemplate.must_have],
    },
    visual_style: visualStyle,
    title_style: titleStyle,
    initial_topics: [...initialTopicsList.value],
  }
}

function openQuickAsset(type: AssetType) {
  activeAssetType.value = type
  assetEditingId.value = null
  assetForm.name = ''
  assetFixedTraitsList.value = []
  assetImages.value = []
  resetAssetTextValues()
  assetDialogOpen.value = true
}

function openCanvasAsset(command: string) {
  if (command === 'characters' || command === 'worldviews') {
    openQuickAsset(command)
  }
}

function openAssetEditor(node: PinNode) {
  if (!node.assetType || !node.targetId) return
  const item = assets[node.assetType].find((asset) => asset.id === node.targetId)
  if (!item) return
  openAssetEditorForItem(node.assetType, item)
}

function openAssetEditorForItem(type: AssetType, item: AssetBase) {
  activeAssetType.value = type
  assetEditingId.value = item.id
  assetForm.name = item.name || ''
  assetFixedTraitsList.value = Array.isArray(item.fixed_traits)
    ? item.fixed_traits.map((trait) => String(trait))
    : []
  assetImages.value = Array.isArray(item.images) ? [...item.images] : []
  resetAssetTextValues(item.payload || {})
  assetDialogOpen.value = true
}

function resetAssetTextValues(payload: Record<string, unknown> = {}) {
  for (const key of Object.keys(assetTextValues)) delete assetTextValues[key]
  for (const field of activeAssetSchema.value.fields) {
    assetTextValues[field.key] = fieldFromPayload(field, payload[field.key])
  }
}

function fieldFromPayload(field: { kind: string }, value: unknown): string {
  if (field.kind === 'lines') {
    if (Array.isArray(value)) return value.map((item) => String(item)).join('\n')
    if (typeof value === 'string') return value.split(/\n|[;；]/).map((item) => item.trim()).filter(Boolean).join('\n')
    return ''
  }
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map((item) => String(item)).join('\n')
  if (value == null) return ''
  return JSON.stringify(value)
}

function buildAssetPayloadFromFields(): Record<string, unknown> {
  const payload: Record<string, unknown> = {}
  for (const field of activeAssetSchema.value.fields) {
    const raw = assetTextValues[field.key] ?? ''
    payload[field.key] = field.kind === 'lines'
      ? raw.split('\n').map((s) => s.trim()).filter(Boolean)
      : raw
  }
  return payload
}

function buildQuickAssetPrompt(): string {
  const lines: string[] = []
  if (assetForm.name.trim()) lines.push(`资产名称:${assetForm.name.trim()}`)
  lines.push(`资产类型:${activeAssetSchema.value.title}`)
  for (const field of activeAssetSchema.value.fields) {
    const raw = (assetTextValues[field.key] || '').trim()
    if (raw) lines.push(`${field.label}:${raw}`)
  }
  if (assetFixedTraitsList.value.length) {
    lines.push(`固定特征:${assetFixedTraitsList.value.join(' / ')}`)
  }
  lines.push('请基于以上设定生成一张高质量参考图,主体清晰,白色或浅色背景,工作室柔光。')
  return lines.join('\n')
}

async function saveQuickAsset() {
  if (!assetForm.name.trim()) {
    ElMessage.warning('请填写资产名称')
    return
  }
  assetSaving.value = true
  try {
    const type = activeAssetType.value
    const payload = {
      name: assetForm.name.trim(),
      payload: buildAssetPayloadFromFields(),
      fixed_traits: [...assetFixedTraitsList.value],
      images: [...assetImages.value],
    }
    const saved = assetEditingId.value
      ? await assetsApi.patch(type, assetEditingId.value, payload)
      : await assetsApi.create(type, payload)
    assets[type] = [saved, ...assets[type].filter((item) => item.id !== saved.id)]
    if (!form[type].includes(saved.id)) {
      form[type] = [...form[type], saved.id]
    }
    await autoSaveSeries()
    assetDialogOpen.value = false
    ElMessage.success(assetEditingId.value ? '已保存资产' : '已创建并关联资产')
  } finally {
    assetSaving.value = false
  }
}

async function deleteActiveAsset() {
  const id = assetEditingId.value
  if (!id || assetSaving.value || assetDeleting.value) return
  const type = activeAssetType.value
  const assetName = assetForm.name.trim() || assets[type].find((item) => item.id === id)?.name || '未命名资产'
  try {
    await ElMessageBox.confirm(
      `确认删除「${assetName}」? 删除后会从当前系列和画布中移除。`,
      '删除资产',
      { type: 'warning' },
    )
  } catch {
    return
  }

  assetDeleting.value = true
  try {
    await assetsApi.remove(type, id)
    assets[type] = assets[type].filter((item) => item.id !== id)
    form[type] = form[type].filter((itemId) => itemId !== id)

    const nodeId = `asset-${type}-${id}`
    delete boardLayout[nodeId]
    delete imageOnlyBoardLayout[nodeId]
    persistPinLayout()
    persistImageOnlyPinLayout()
    relationEdges.value = relationEdges.value.filter((relation) =>
      relation.fromId !== nodeId && relation.toId !== nodeId,
    )
    if (type === 'characters') {
      aiRelationshipRows.value = aiRelationshipRows.value.filter((row) => !relationshipHasAssetId(row, id))
      relationshipDraftRows.value = relationshipDraftRows.value.filter((row) =>
        row.from_asset_id !== id && row.to_asset_id !== id,
      )
    }
    persistRelations()
    closeRelationEditor()
    await autoSaveSeries()

    assetDialogOpen.value = false
    assetEditingId.value = null
    ElMessage.success('已删除资产')
  } finally {
    assetDeleting.value = false
  }
}

function defaultPayload(): SeriesPayload {
  return {
    title: '',
    direction: '',
    summary: '',
    target_platform: '',
    target_audience: '',
    update_frequency: '',
    episode_duration_seconds: 60,
    planned_episodes: 0,
    positioning: {},
    episode_template: {},
    visual_style: {},
    title_style: {},
    initial_topics: [],
    characters: [],
    styles: [],
    worldviews: [],
    columns: [],
    status: 'draft',
  }
}

function seriesStatusLabel(s: SeriesPayload['status']) {
  return { draft: '草稿', ongoing: '连载中', paused: '已暂停', completed: '已完成' }[s] || s
}

function episodeStatusLabel(s: VideoPlan['status']) {
  return { draft: '草稿', optimizing: '优化中', confirmed: '已确认', completed: '已完成' }[s] || s
}
function episodeTagType(s: VideoPlan['status']): 'info' | 'warning' | 'success' {
  if (s === 'optimizing') return 'warning'
  if (s === 'confirmed' || s === 'completed') return 'success'
  return 'info'
}
function formatTime(iso: string) {
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function compactJson(value: Record<string, unknown>) {
  if (!value || Object.keys(value).length === 0) return '未填写'
  return JSON.stringify(value, null, 2)
}

// --- New helpers for the document-mode UI ---------------------------------

function hasText(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function firstFilled(values: unknown[]): string {
  const found = values.find(hasText)
  return found ? found.trim() : ''
}

function assetSummary(item: AssetBase): string {
  const payload = item.payload || {}
  const candidates = [
    payload.description,
    payload.personality,
    payload.visual_style,
    payload.world_rules,
    payload.structure,
    payload.role,
  ]
  const picked = firstFilled(candidates)
  if (picked) return picked
  if (Array.isArray(item.fixed_traits) && item.fixed_traits.length) {
    return item.fixed_traits.slice(0, 3).map((trait) => String(trait)).join(' / ')
  }
  return '点击管理这个系列引用的资产'
}

function assetTags(item: AssetBase): string[] {
  const tags: string[] = []
  if (Array.isArray(item.fixed_traits) && item.fixed_traits.length) tags.push(`固定 ${item.fixed_traits.length}`)
  if (Array.isArray(item.images) && item.images.length) tags.push(`${item.images.length} 图`)
  return tags
}

function nodeIcon(node: PinNode) {
  if (node.kind === 'asset') {
    if (node.assetType === 'characters') return User
    if (node.assetType === 'worldviews') return MapLocation
    return Picture
  }
  return Setting
}

function nodePlaceholderIcon(node: PinNode) {
  if (node.assetType === 'characters') return UserFilled
  if (node.assetType === 'worldviews') return House
  return Picture
}

function nodeActionLabel(node: PinNode): string {
  return node.assetType === 'characters' ? '查看人物' : '查看环境'
}

function openPanel(panel: PinPanel) {
  activePanel.value = panel
  panelDialogOpen.value = true
}

function openPinNode(node: PinNode) {
  if (boardTool.value === 'move' || draggingNodeId.value || suppressPinClick.value) return
  if (node.kind === 'asset') {
    openAssetEditor(node)
    return
  }
  openPanel(node.panel || 'series')
}

function nodePosition(node: PinNode): { x: number; y: number } {
  const layout = canvasImageOnlyMode.value ? imageOnlyBoardLayout : boardLayout
  return layout[node.id] || { x: node.x, y: node.y }
}

function nodeStyle(node: PinNode) {
  const pos = nodePosition(node)
  const tilt = canvasImageOnlyMode.value || draggingNodeId.value === node.id ? 0 : nodeTilt(node)
  return {
    width: `${node.w}px`,
    minHeight: `${node.h}px`,
    height: canvasImageOnlyMode.value ? `${node.h}px` : undefined,
    transform: `translate(${pos.x}px, ${pos.y}px) rotate(${tilt}deg)`,
  }
}

function nodeTilt(node: PinNode): number {
  const seed = Array.from(node.id).reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return ((seed % 7) - 3) * 0.42
}

function nodeCenter(node: PinNode): Point {
  const pos = nodePosition(node)
  return {
    x: pos.x + node.w / 2,
    y: pos.y + node.h / 2,
  }
}

function linePath(line: PinLine): string {
  return pointCurvePath(nodeCenter(line.from), nodeCenter(line.to))
}

function pointCurvePath(from: Point, to: Point): string {
  const dx = Math.max(80, Math.abs(to.x - from.x) * 0.45)
  const c1x = from.x + (to.x >= from.x ? dx : -dx)
  const c2x = to.x - (to.x >= from.x ? dx : -dx)
  return `M ${from.x} ${from.y} C ${c1x} ${from.y}, ${c2x} ${to.y}, ${to.x} ${to.y}`
}

function lineLabelPosition(line: PinLine): Point {
  const from = nodeCenter(line.from)
  const to = nodeCenter(line.to)
  return {
    x: (from.x + to.x) / 2,
    y: (from.y + to.y) / 2 - 10,
  }
}

function relationTone(line: PinLine): 'good' | 'bad' | 'environment' | 'neutral' {
  if (isEnvironmentRelation(line)) return 'environment'
  const label = line.relation.label.trim()
  if (/朋友|友|家人|亲人|亲属|伙伴|同伴|盟友|队友|兄弟|姐妹|父|母|子|女/.test(label)) return 'good'
  if (/敌|仇|坏|冲突|对手|反派|敌人|敌对|不和|关系不好|讨厌|背叛/.test(label)) return 'bad'
  return 'neutral'
}

function isEnvironmentRelation(line: PinLine): boolean {
  return line.from.assetType === 'worldviews' || line.to.assetType === 'worldviews'
}

function isEditableRelation(line: PinLine): boolean {
  return boardTool.value === 'select'
}

function openRelationEditor(line: PinLine) {
  if (boardTool.value !== 'select' || canvasImageOnlyMode.value) return
  activeRelationId.value = line.relation.id
  relationDraft.value = line.relation.label || ''
  if (isEditableRelation(line)) {
    void nextTick(() => relationInputRef.value?.select())
  }
}

function relationEditorStyle(line: PinLine) {
  const position = lineLabelPosition(line)
  return {
    left: `${position.x}px`,
    top: `${position.y}px`,
  }
}

function commitRelationEditor() {
  if (!activeRelationId.value) return
  const label = relationDraft.value.trim()
  relationEdges.value = relationEdges.value.map((relation) =>
    relation.id === activeRelationId.value ? { ...relation, label, deleted: !label } : relation,
  )
  persistRelations()
  closeRelationEditor()
  void autoSaveSeries()
}

function deleteActiveRelation() {
  if (!activeRelationId.value) return
  relationEdges.value = relationEdges.value.map((relation) =>
    relation.id === activeRelationId.value ? { ...relation, deleted: true } : relation,
  )
  persistRelations()
  closeRelationEditor()
  void autoSaveSeries()
}

function closeRelationEditor() {
  activeRelationId.value = ''
  relationDraft.value = ''
}

function canConnectNodes(from: PinNode, to: PinNode): boolean {
  if (from.id === to.id) return false
  const fromType = from.assetType
  const toType = to.assetType
  return (fromType === 'characters' || fromType === 'worldviews') &&
    (toType === 'characters' || toType === 'worldviews')
}

function upsertRelation(from: PinNode, to: PinNode): PinRelation {
  const id = relationId(from.id, to.id)
  const existing = relationEdges.value.find((relation) => relation.id === id)
  if (existing) {
    const revived = { ...existing, fromId: existing.fromId || from.id, toId: existing.toId || to.id, deleted: false }
    relationEdges.value = relationEdges.value.map((relation) => relation.id === id ? revived : relation)
    return revived
  }
  const created = { id, fromId: from.id, toId: to.id, label: '' }
  relationEdges.value = [...relationEdges.value, created]
  return created
}

function nodeHandlePosition(node: PinNode, side: ConnectSide): Point {
  const pos = nodePosition(node)
  if (side === 'top') return { x: pos.x + node.w / 2, y: pos.y }
  if (side === 'right') return { x: pos.x + node.w, y: pos.y + node.h / 2 }
  if (side === 'bottom') return { x: pos.x + node.w / 2, y: pos.y + node.h }
  return { x: pos.x, y: pos.y + node.h / 2 }
}

function canvasPointFromClient(clientX: number, clientY: number): Point {
  const board = boardRef.value
  if (!board) return { x: 0, y: 0 }
  const rect = board.getBoundingClientRect()
  return {
    x: (board.scrollLeft + clientX - rect.left) / boardScale.value,
    y: (board.scrollTop + clientY - rect.top) / boardScale.value,
  }
}

function startRelationDrag(event: PointerEvent, node: PinNode, side: ConnectSide) {
  if (boardTool.value !== 'select' || canvasImageOnlyMode.value || event.button !== 0) return
  event.preventDefault()
  closeRelationEditor()
  const start = nodeHandlePosition(node, side)
  relationStartNodeId.value = node.id
  relationDrag.value = {
    fromId: node.id,
    side,
    start,
    end: canvasPointFromClient(event.clientX, event.clientY),
  }
  window.addEventListener('pointermove', onRelationDrag)
  window.addEventListener('pointerup', stopRelationDrag)
}

function onRelationDrag(event: PointerEvent) {
  if (!relationDrag.value) return
  relationDrag.value = {
    ...relationDrag.value,
    end: canvasPointFromClient(event.clientX, event.clientY),
  }
}

function stopRelationDrag(event?: PointerEvent) {
  const drag = relationDrag.value
  if (!drag) return
  window.removeEventListener('pointermove', onRelationDrag)
  window.removeEventListener('pointerup', stopRelationDrag)
  relationDrag.value = null
  relationStartNodeId.value = ''
  if (!event) return

  const target = document.elementFromPoint(event.clientX, event.clientY)
  const handle = target instanceof Element
    ? (target.closest('.pin-connect-handle') as HTMLElement | null)
    : null
  const targetNodeId = handle?.dataset.nodeId || ''
  const from = pinNodes.value.find((node) => node.id === drag.fromId)
  const to = pinNodes.value.find((node) => node.id === targetNodeId)
  if (!from || !to || !canConnectNodes(from, to)) return

  const relation = upsertRelation(from, to)
  persistRelations()
  activeRelationId.value = relation.id
  relationDraft.value = relation.label || ''
  void nextTick(() => relationInputRef.value?.select())
}

let dragState: {
  id: string
  imageOnly: boolean
  startX: number
  startY: number
  offsetX: number
  offsetY: number
  w: number
  h: number
} | null = null

function maybeStartNodeDrag(event: PointerEvent, node: PinNode) {
  if (event.button !== 0) return
  if (!canvasImageOnlyMode.value && boardTool.value !== 'move') return
  event.preventDefault()
  startNodeDrag(event, node)
}

function startNodeDrag(event: PointerEvent, node: PinNode) {
  const pos = nodePosition(node)
  const point = canvasPointFromClient(event.clientX, event.clientY)
  dragState = {
    id: node.id,
    imageOnly: canvasImageOnlyMode.value,
    startX: event.clientX,
    startY: event.clientY,
    offsetX: point.x - pos.x,
    offsetY: point.y - pos.y,
    w: node.w,
    h: node.h,
  }
  draggingNodeId.value = node.id
  window.addEventListener('pointermove', onNodeDrag)
  window.addEventListener('pointerup', stopNodeDrag)
}

function onNodeDrag(event: PointerEvent) {
  if (!dragState) return
  event.preventDefault()
  if (Math.abs(event.clientX - dragState.startX) > 3 || Math.abs(event.clientY - dragState.startY) > 3) {
    suppressPinClick.value = true
  }
  autoScrollPinboardDuringDrag(event)
  const point = canvasPointFromClient(event.clientX, event.clientY)
  const maxX = Math.max(16, pinboardSize.value.width - dragState.w - 24)
  const maxY = Math.max(16, pinboardSize.value.height - dragState.h - 24)
  const layout = dragState.imageOnly ? imageOnlyBoardLayout : boardLayout
  layout[dragState.id] = {
    x: clamp(point.x - dragState.offsetX, 16, maxX),
    y: clamp(point.y - dragState.offsetY, 16, maxY),
  }
}

function stopNodeDrag() {
  if (dragState) {
    if (dragState.imageOnly) persistImageOnlyPinLayout()
    else persistPinLayout()
  }
  dragState = null
  draggingNodeId.value = ''
  window.removeEventListener('pointermove', onNodeDrag)
  window.removeEventListener('pointerup', stopNodeDrag)
  window.setTimeout(() => {
    suppressPinClick.value = false
  }, 0)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function autoScrollPinboardDuringDrag(event: PointerEvent) {
  const board = boardRef.value
  if (!board) return
  const rect = board.getBoundingClientRect()
  const edge = 56
  const maxStep = 18
  let dx = 0
  let dy = 0

  if (event.clientX < rect.left + edge) {
    dx = -Math.ceil(((rect.left + edge - event.clientX) / edge) * maxStep)
  } else if (event.clientX > rect.right - edge) {
    dx = Math.ceil(((event.clientX - (rect.right - edge)) / edge) * maxStep)
  }

  if (event.clientY < rect.top + edge) {
    dy = -Math.ceil(((rect.top + edge - event.clientY) / edge) * maxStep)
  } else if (event.clientY > rect.bottom - edge) {
    dy = Math.ceil(((event.clientY - (rect.bottom - edge)) / edge) * maxStep)
  }

  if (dx) board.scrollLeft += dx
  if (dy) board.scrollTop += dy
}

function updatePinboardViewportSize() {
  const board = boardRef.value
  if (!board) return
  pinboardViewportSize.width = board.clientWidth
  pinboardViewportSize.height = board.clientHeight
}

function setupPinboardViewportObserver() {
  updatePinboardViewportSize()
  const board = boardRef.value
  if (!board || typeof ResizeObserver === 'undefined') return
  pinboardResizeObserver?.disconnect()
  pinboardResizeObserver = new ResizeObserver(updatePinboardViewportSize)
  pinboardResizeObserver.observe(board)
}

function loadPinLayout() {
  loadLayoutFromStorage(boardLayout, pinLayoutKey.value)
}

function loadImageOnlyPinLayout() {
  loadLayoutFromStorage(imageOnlyBoardLayout, imageOnlyPinLayoutKey.value)
}

function loadLayoutFromStorage(target: Record<string, { x: number; y: number }>, key: string) {
  for (const layoutKey of Object.keys(target)) delete target[layoutKey]
  if (typeof window === 'undefined') return
  const raw = window.localStorage.getItem(key)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw) as Record<string, { x: number; y: number }>
    for (const [layoutKey, value] of Object.entries(parsed)) {
      if (typeof value?.x === 'number' && typeof value?.y === 'number') {
        target[layoutKey] = value
      }
    }
  } catch {
    window.localStorage.removeItem(key)
  }
}

function onPinboardWheel(event: WheelEvent) {
  const direction = event.deltaY > 0 ? -1 : 1
  zoomPinboard(direction * 0.08, event)
}

function zoomPinboard(delta: number, event?: WheelEvent) {
  const board = boardRef.value
  const oldScale = boardScale.value
  const nextScale = Math.round(clamp(oldScale + delta, 0.5, 1.6) * 100) / 100
  if (nextScale === oldScale) return

  if (!board || !event) {
    boardScale.value = nextScale
    return
  }

  const rect = board.getBoundingClientRect()
  const offsetX = event.clientX - rect.left
  const offsetY = event.clientY - rect.top
  const canvasX = (board.scrollLeft + offsetX) / oldScale
  const canvasY = (board.scrollTop + offsetY) / oldScale
  boardScale.value = nextScale
  window.requestAnimationFrame(() => {
    board.scrollLeft = canvasX * nextScale - offsetX
    board.scrollTop = canvasY * nextScale - offsetY
  })
}

function persistPinLayout() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(pinLayoutKey.value, JSON.stringify(boardLayout))
}

function persistImageOnlyPinLayout() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(imageOnlyPinLayoutKey.value, JSON.stringify(imageOnlyBoardLayout))
}

function resetPinLayout() {
  const layout = canvasImageOnlyMode.value ? imageOnlyBoardLayout : boardLayout
  const key = canvasImageOnlyMode.value ? imageOnlyPinLayoutKey.value : pinLayoutKey.value
  for (const layoutKey of Object.keys(layout)) delete layout[layoutKey]
  if (typeof window !== 'undefined') window.localStorage.removeItem(key)
  ElMessage.success('已按当前模式自动排布')
}

function setBoardTool(tool: BoardTool) {
  boardTool.value = tool
  closeRelationEditor()
  stopRelationDrag()
}

function toggleCanvasImageOnlyMode() {
  canvasImageOnlyMode.value = !canvasImageOnlyMode.value
  closeRelationEditor()
  stopRelationDrag()
  if (canvasImageOnlyMode.value) {
    boardTool.value = 'select'
  }
}

function relationId(a: string, b: string): string {
  return [a, b].sort().join('__')
}

function textValue(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (value == null) return ''
  return String(value).trim()
}

function nameKey(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, '')
}

function normalizeRelationshipAssetType(value: unknown): RelationshipAssetType | undefined {
  const raw = textValue(value).toLowerCase()
  if (['characters', 'character', '人物', '角色'].includes(raw)) return 'characters'
  if (['worldviews', 'worldview', 'environment', 'environments', '环境', '小环境', '场景', '地点'].includes(raw)) return 'worldviews'
  return undefined
}

function relationshipAssetTypeLabel(type: RelationshipAssetType): string {
  return type === 'characters' ? '人物' : '环境'
}

function relationshipAssetOptionLabel(item: RelationshipAssetOption): string {
  return `${relationshipAssetTypeLabel(item.type)} · ${item.name}`
}

function normalizeRelationshipRows(value: unknown): SeriesRelationship[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => {
    if (typeof item === 'string') {
      return { from: '', to: '', label: '', description: item.trim() }
    }
    if (!item || typeof item !== 'object') {
      return { from: '', to: '', label: '', description: '' }
    }
    const raw = item as Record<string, unknown>
    const from = textValue(raw.from ?? raw.from_ ?? raw.source ?? raw.from_name ?? raw.from_asset_name)
    const to = textValue(raw.to ?? raw.target ?? raw.to_name ?? raw.to_asset_name)
    const label = textValue(raw.label ?? raw.relation ?? raw.relationship ?? raw.type)
    const description = textValue(raw.description ?? raw.note ?? raw.summary)
    const fromType = normalizeRelationshipAssetType(raw.from_asset_type ?? raw.from_type ?? raw.source_type)
    const toType = normalizeRelationshipAssetType(raw.to_asset_type ?? raw.to_type ?? raw.target_type)
    return {
      from,
      to,
      label,
      description,
      from_asset_id: textValue(raw.from_asset_id) || undefined,
      to_asset_id: textValue(raw.to_asset_id) || undefined,
      from_asset_type: fromType,
      to_asset_type: toType,
      from_asset_name: textValue(raw.from_asset_name) || from || undefined,
      to_asset_name: textValue(raw.to_asset_name) || to || undefined,
    }
  }).filter((row) => relationshipDisplayText(row))
}

function relationshipAssetById(id: string): RelationshipAssetOption | undefined {
  return relationshipAssetOptions.value.find((item) => item.id === id)
}

function findRelationshipAssetByName(name: string, preferredType?: RelationshipAssetType): RelationshipAssetOption | undefined {
  const key = nameKey(name)
  if (!key) return undefined
  const candidates = preferredType
    ? relationshipAssetOptions.value.filter((item) => item.type === preferredType)
    : relationshipAssetOptions.value
  return candidates.find((item) => nameKey(item.name) === key) ||
    candidates.find((item) => {
      const itemKey = nameKey(item.name)
      return itemKey.includes(key) || key.includes(itemKey)
    })
}

function relationshipAssetId(row: SeriesRelationship, side: 'from' | 'to'): string {
  const explicit = side === 'from' ? row.from_asset_id : row.to_asset_id
  if (explicit) return explicit
  const preferredType = side === 'from' ? row.from_asset_type : row.to_asset_type
  const name = side === 'from'
    ? row.from || row.from_asset_name || ''
    : row.to || row.to_asset_name || ''
  return findRelationshipAssetByName(name, preferredType)?.id || ''
}

function relationshipAssetType(row: SeriesRelationship, side: 'from' | 'to'): RelationshipAssetType | undefined {
  const explicit = side === 'from' ? row.from_asset_type : row.to_asset_type
  if (explicit) return explicit
  const id = relationshipAssetId(row, side)
  return relationshipAssetById(id)?.type
}

function relationshipRelationId(row: SeriesRelationship): string {
  const fromId = relationshipAssetId(row, 'from')
  const toId = relationshipAssetId(row, 'to')
  if (!fromId || !toId) return ''
  const fromNode = pinNodes.value.find((node) => node.targetId === fromId || node.id.endsWith(`-${fromId}`))
  const toNode = pinNodes.value.find((node) => node.targetId === toId || node.id.endsWith(`-${toId}`))
  if (!fromNode || !toNode) return ''
  return relationId(fromNode.id, toNode.id)
}

function dedupeRelationshipRows(rows: SeriesRelationship[]): SeriesRelationship[] {
  const seen = new Set<string>()
  const out: SeriesRelationship[] = []
  for (const row of rows) {
    if (!relationshipDisplayText(row)) continue
    const key = relationshipEndpointKey(row) || relationshipDisplayKey(row)
    if (seen.has(key)) continue
    seen.add(key)
    out.push(row)
  }
  return out
}

function relationshipDisplayKey(row: SeriesRelationship): string {
  const left = row.from_asset_id || `${row.from_asset_type || ''}:${row.from || row.from_asset_name || ''}`
  const right = row.to_asset_id || `${row.to_asset_type || ''}:${row.to || row.to_asset_name || ''}`
  const endpoints = [nameKey(left), nameKey(right)].sort()
  return [endpoints[0], endpoints[1], nameKey(row.label || row.description)].join('__')
}

function relationshipDisplayText(row: SeriesRelationship): string {
  const from = row.from || row.from_asset_name || ''
  const to = row.to || row.to_asset_name || ''
  const label = row.label || row.description || ''
  if (from && to && label) return `${from} 与 ${to}: ${label}`
  if (from && to) return `${from} 与 ${to}`
  return label
}

function relationshipFromLine(line: PinLine): SeriesRelationship {
  return {
    from: line.from.title,
    to: line.to.title,
    label: line.relation.label,
    description: '',
    from_asset_id: line.from.targetId,
    to_asset_id: line.to.targetId,
    from_asset_type: line.from.assetType === 'characters' || line.from.assetType === 'worldviews' ? line.from.assetType : undefined,
    to_asset_type: line.to.assetType === 'characters' || line.to.assetType === 'worldviews' ? line.to.assetType : undefined,
    from_asset_name: line.from.title,
    to_asset_name: line.to.title,
  }
}

function relationshipEndpointKey(row: SeriesRelationship): string {
  const fromId = relationshipAssetId(row, 'from')
  const toId = relationshipAssetId(row, 'to')
  const from = fromId || row.from_asset_name || row.from || ''
  const to = toId || row.to_asset_name || row.to || ''
  if (!from || !to) return ''
  return [nameKey(from), nameKey(to)].sort().join('__')
}

function assetPairKey(a: string, b: string): string {
  return [a, b].sort().join('__')
}

function selectedRelationshipAssetById(id: string): RelationshipAssetOption | undefined {
  return relationshipAssetById(id)
}

function relationshipEditDraftFromRow(row: SeriesRelationship): RelationshipEditDraft | null {
  const fromId = relationshipAssetId(row, 'from')
  const toId = relationshipAssetId(row, 'to')
  if (!fromId || !toId || fromId === toId) return null
  if (!selectedRelationshipAssetById(fromId) || !selectedRelationshipAssetById(toId)) return null
  return {
    from_asset_id: fromId,
    to_asset_id: toId,
    label: row.label || row.description || '',
  }
}

function usedRelationshipPairs(current?: RelationshipEditDraft): Set<string> {
  const used = new Set<string>()
  for (const draft of relationshipDraftRows.value) {
    if (draft === current) continue
    if (!draft.from_asset_id || !draft.to_asset_id || draft.from_asset_id === draft.to_asset_id) continue
    used.add(assetPairKey(draft.from_asset_id, draft.to_asset_id))
  }
  return used
}

function firstAvailableRelationshipDraft(): RelationshipEditDraft | null {
  const options = relationshipAssetOptions.value
  const used = usedRelationshipPairs()
  for (let i = 0; i < options.length; i += 1) {
    for (let j = i + 1; j < options.length; j += 1) {
      const from = options[i]
      const to = options[j]
      if (!from || !to) continue
      if (!used.has(assetPairKey(from.id, to.id))) {
        return {
          from_asset_id: from.id,
          to_asset_id: to.id,
          label: '',
        }
      }
    }
  }
  return null
}

function openRelationshipDialog() {
  const rows = relationshipDisplayRows.value
    .map((row) => relationshipEditDraftFromRow(row))
    .filter((row): row is RelationshipEditDraft => !!row)
  const seen = new Set<string>()
  relationshipDraftRows.value = rows.filter((row) => {
    const key = assetPairKey(row.from_asset_id, row.to_asset_id)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  if (!relationshipDraftRows.value.length) {
    const first = firstAvailableRelationshipDraft()
    if (first) relationshipDraftRows.value = [first]
  }
  relationshipDialogOpen.value = true
}

function relationshipTargetOptions(row: RelationshipEditDraft): RelationshipAssetOption[] {
  const used = usedRelationshipPairs(row)
  return relationshipAssetOptions.value.filter((item) => {
    if (item.id === row.from_asset_id) return false
    if (!row.from_asset_id) return true
    const key = assetPairKey(row.from_asset_id, item.id)
    return item.id === row.to_asset_id || !used.has(key)
  })
}

function addRelationshipDraft() {
  const draft = firstAvailableRelationshipDraft()
  if (!draft) {
    ElMessage.info('可用的人物组合都已添加')
    return
  }
  relationshipDraftRows.value.push(draft)
}

function removeRelationshipDraft(index: number) {
  relationshipDraftRows.value.splice(index, 1)
}

function relationshipRowsFromDialogDrafts(): SeriesRelationship[] {
  const rows: SeriesRelationship[] = []
  const seen = new Set<string>()
  for (const draft of relationshipDraftRows.value) {
    const from = selectedRelationshipAssetById(draft.from_asset_id)
    const to = selectedRelationshipAssetById(draft.to_asset_id)
    if (!from || !to || from.id === to.id) continue
    const label = draft.label.trim()
    if (!label) continue
    const key = assetPairKey(from.id, to.id)
    if (seen.has(key)) continue
    seen.add(key)
    rows.push({
      from: from.name,
      to: to.name,
      label,
      description: '',
      from_asset_id: from.id,
      to_asset_id: to.id,
      from_asset_type: from.type,
      to_asset_type: to.type,
      from_asset_name: from.name,
      to_asset_name: to.name,
    })
  }
  return rows
}

function relationshipHasAssetId(row: SeriesRelationship, assetId: string): boolean {
  return row.from_asset_id === assetId ||
    row.to_asset_id === assetId ||
    relationshipAssetId(row, 'from') === assetId ||
    relationshipAssetId(row, 'to') === assetId
}

async function applyRelationshipDialog() {
  const rows = relationshipRowsFromDialogDrafts()
  aiRelationshipRows.value = rows

  relationEdges.value = relationEdges.value.map((relation) =>
    ({ ...relation, label: '', deleted: true }),
  )

  for (const row of rows) {
    const from = findRelationshipNode(row, 'from')
    const to = findRelationshipNode(row, 'to')
    if (!from || !to || from.assetType !== 'characters' || to.assetType !== 'characters' || !canConnectNodes(from, to)) continue
    const next = upsertRelation(from, to)
    relationEdges.value = relationEdges.value.map((relation) =>
      relation.id === next.id
        ? { ...relation, label: row.label || '', deleted: false }
        : relation,
    )
  }

  persistRelations()
  closeRelationEditor()
  await autoSaveSeries()
  relationshipDialogOpen.value = false
  ElMessage.success('资产关系已更新')
}

function findRelationshipNode(row: SeriesRelationship, side: 'from' | 'to'): PinNode | undefined {
  const assetId = side === 'from' ? row.from_asset_id : row.to_asset_id
  if (assetId) {
    const byId = pinNodes.value.find((node) => node.targetId === assetId || node.id.endsWith(`-${assetId}`))
    if (byId) return byId
  }

  const name = side === 'from'
    ? row.from || row.from_asset_name || ''
    : row.to || row.to_asset_name || ''
  const key = nameKey(name)
  if (!key) return undefined

  const preferredType = relationshipAssetType(row, side)
  const candidates = preferredType
    ? pinNodes.value.filter((node) => node.assetType === preferredType)
    : pinNodes.value
  const exact = candidates.find((node) => nameKey(node.title) === key)
  if (exact) return exact
  return candidates.find((node) => {
    const nodeKey = nameKey(node.title)
    return nodeKey.includes(key) || key.includes(nodeKey)
  })
}

function defaultRelations(): PinRelation[] {
  const out = new Map<string, PinRelation>()

  for (const row of aiRelationshipRows.value) {
    const from = findRelationshipNode(row, 'from')
    const to = findRelationshipNode(row, 'to')
    if (!from || !to || !canConnectNodes(from, to)) continue
    const label = row.label || row.description || ''
    if (!label.trim()) continue
    const idKey = relationId(from.id, to.id)
    out.set(idKey, { id: idKey, fromId: from.id, toId: to.id, label })
  }

  return Array.from(out.values())
}

function mergeRelations(stored: PinRelation[]): PinRelation[] {
  const nodeIds = new Set(pinNodes.value.map((node) => node.id))
  const merged = new Map(defaultRelations().map((relation) => [relation.id, relation]))
  for (const relation of stored) {
    if (!nodeIds.has(relation.fromId) || !nodeIds.has(relation.toId)) continue
    const fallback = merged.get(relation.id)
    merged.set(relation.id, {
      id: relation.id,
      fromId: relation.fromId,
      toId: relation.toId,
      label: relation.label || fallback?.label || '',
      deleted: relation.deleted === true,
    })
  }
  return Array.from(merged.values())
}

function loadRelations() {
  if (typeof window === 'undefined') {
    relationEdges.value = defaultRelations()
    return
  }
  const raw = window.localStorage.getItem(relationStorageKey.value)
  if (!raw) {
    relationEdges.value = defaultRelations()
    persistRelations()
    return
  }
  try {
    const parsed = JSON.parse(raw) as PinRelation[]
    relationEdges.value = Array.isArray(parsed)
      ? mergeRelations(parsed.filter((relation) =>
          typeof relation?.id === 'string' &&
          typeof relation?.fromId === 'string' &&
          typeof relation?.toId === 'string',
        ).map((relation) => ({ ...relation, label: relation.label || '' })))
      : mergeRelations([])
    persistRelations()
  } catch {
    window.localStorage.removeItem(relationStorageKey.value)
    relationEdges.value = defaultRelations()
    persistRelations()
  }
}

function persistRelations() {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(relationStorageKey.value, JSON.stringify(relationEdges.value))
}

function coverOf(item: AssetBase): AssetImage | undefined {
  return Array.isArray(item.images) && item.images.length ? item.images[0] : undefined
}

function toggleAsset(type: AssetType, id: string) {
  const list = form[type]
  if (list.includes(id)) {
    form[type] = list.filter((x) => x !== id)
  } else {
    form[type] = [...list, id]
  }
}

function formatTimeShort(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const that = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((today.getTime() - that.getTime()) / 86400000)
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays} 天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const totalSelectedAssets = computed(() =>
  assetGroups.reduce((sum, group) => sum + form[group.type].length, 0),
)

const beatBoardSubtitle = computed(() => {
  if (!episodes.value.length) return '暂无单集'
  const total = episodes.value.length
  const planned = form.planned_episodes || 0
  const confirmed = episodes.value.filter((e) => e.status === 'confirmed' || e.status === 'completed').length
  if (planned > 0) return `进度 ${total} / ${planned} · 已确认 ${confirmed}`
  return `共 ${total} 集 · 已确认 ${confirmed}`
})

const episodeProgressText = computed(() => {
  const total = episodes.value.length
  const planned = form.planned_episodes || 0
  return planned > 0 ? `${total}/${planned}` : `${total} 集`
})

const filteredAttachablePlans = computed(() => {
  const existingIds = new Set(episodes.value.map((episode) => episode.id))
  const keyword = planPickerSearch.value.trim().toLowerCase()
  return attachablePlans.value
    .filter((item) => !item.series && !existingIds.has(item.id))
    .filter((item) => {
      if (!keyword) return true
      const haystack = [
        item.title,
        item.summary,
        findDirectionLabel(item.direction),
      ].join(' ').toLowerCase()
      return haystack.includes(keyword)
    })
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
})

const seriesMemoryText = computed(() => {
  const count = episodes.value.length
  if (isNew.value) return '先保存系列后再生成单集'
  if (!count) return '将使用系列设定、人物和环境资产'
  return `将参考前 ${Math.min(count, 5)} 集、系列设定、人物和环境资产`
})

const seriesChatMessages = computed(() => {
  const messages = [...episodeConversationMessages.value]
  if (generatingEpisode.value) {
    messages.push({
      key: 'generating',
      role: 'ai',
      text: taskMessage.value || 'AI 正在基于系列上下文生成下一集...',
    })
  }
  return messages
})

const seriesStatusTone = computed(() => {
  switch (form.status) {
    case 'ongoing': return 'primary'
    case 'completed': return 'success'
    case 'paused': return 'warning'
    default: return 'info'
  }
})

function backFromToolbar() {
  if (isRelationshipPage.value && route.params.id) {
    router.push(`/app/series/${route.params.id}`)
    return
  }
  router.push('/app/me/series')
}

function goRelationshipPage() {
  if (isNew.value || !route.params.id) {
    ElMessage.info('先保存系列后再进入资产关系')
    return
  }
  router.push(`/app/series/${route.params.id}/relationships`)
}

async function openPlanPicker() {
  if (isNew.value || !route.params.id) {
    ElMessage.info('先保存系列后再添加方案')
    return
  }
  planPickerOpen.value = true
  await loadAttachablePlans()
}

async function loadAttachablePlans() {
  planPickerLoading.value = true
  try {
    const data = await plansApi.list()
    attachablePlans.value = data.results
  } finally {
    planPickerLoading.value = false
  }
}

function nextEpisodeOrder() {
  const maxOrder = episodes.value.reduce((max, episode) => Math.max(max, Number(episode.episode_order) || 0), 0)
  return maxOrder + 1
}

function sortEpisodes(list: EpisodeSummary[]) {
  return [...list].sort((a, b) => {
    const orderA = Number(a.episode_order) || Number.MAX_SAFE_INTEGER
    const orderB = Number(b.episode_order) || Number.MAX_SAFE_INTEGER
    if (orderA !== orderB) return orderA - orderB
    return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
  })
}

async function attachPlanToSeries(item: VideoPlan) {
  if (!route.params.id || attachingPlanId.value) return
  attachingPlanId.value = item.id
  try {
    const updated = await plansApi.patch(item.id, {
      series: route.params.id as string,
      episode_order: nextEpisodeOrder(),
    })
    addEpisodeToList(updated)
    attachablePlans.value = attachablePlans.value.filter((plan) => plan.id !== item.id)
    ElMessage.success('已添加到系列')
  } finally {
    attachingPlanId.value = ''
  }
}

function normalizeEpisodeOrders(list: EpisodeSummary[]) {
  return list.map((episode, index) => ({ ...episode, episode_order: index + 1 }))
}

async function persistEpisodeOrder(nextList: EpisodeSummary[], before: EpisodeSummary[]) {
  episodes.value = normalizeEpisodeOrders(nextList)
  episodeReordering.value = true
  try {
    await Promise.all(
      episodes.value.map((episode) =>
        plansApi.patch(episode.id, { episode_order: episode.episode_order }),
      ),
    )
    ElMessage.success('单集顺序已更新')
  } catch (err) {
    episodes.value = before
    ElMessage.error(err instanceof Error ? err.message : '调整单集顺序失败')
  } finally {
    episodeReordering.value = false
  }
}

async function moveEpisode(idx: number, delta: -1 | 1) {
  const target = idx + delta
  if (episodeReordering.value || target < 0 || target >= episodes.value.length) return
  const before = episodes.value.map((episode) => ({ ...episode }))
  const next = episodes.value.map((episode) => ({ ...episode }))
  const [item] = next.splice(idx, 1)
  if (!item) return
  next.splice(target, 0, item)
  await persistEpisodeOrder(next, before)
}

function onEpisodeDragStart(event: DragEvent, episodeId: string) {
  if (episodeReordering.value || deletingEpisodeId.value) {
    event.preventDefault()
    return
  }
  draggingEpisodeId.value = episodeId
  dragOverEpisodeId.value = ''
  event.dataTransfer?.setData('text/plain', episodeId)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function onEpisodeDragOver(event: DragEvent, episodeId: string) {
  const sourceId = draggingEpisodeId.value
  if (!sourceId || sourceId === episodeId) {
    dragOverEpisodeId.value = ''
    return
  }
  const target = event.currentTarget as HTMLElement | null
  const rect = target?.getBoundingClientRect()
  dragOverEpisodeId.value = episodeId
  dragOverSide.value = rect && event.clientX > rect.left + rect.width / 2 ? 'after' : 'before'
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}

function onEpisodeDragLeave(episodeId: string) {
  if (dragOverEpisodeId.value === episodeId) dragOverEpisodeId.value = ''
}

async function onEpisodeDrop(event: DragEvent, targetId: string) {
  const sourceId = event.dataTransfer?.getData('text/plain') || draggingEpisodeId.value
  const before = episodes.value.map((episode) => ({ ...episode }))
  const source = before.find((episode) => episode.id === sourceId)
  if (!source || sourceId === targetId || episodeReordering.value) {
    onEpisodeDragEnd()
    return
  }

  const next = before.filter((episode) => episode.id !== sourceId)
  const targetIndex = next.findIndex((episode) => episode.id === targetId)
  if (targetIndex < 0) {
    onEpisodeDragEnd()
    return
  }
  const insertIndex = dragOverSide.value === 'after' ? targetIndex + 1 : targetIndex
  next.splice(insertIndex, 0, source)
  onEpisodeDragEnd()
  await persistEpisodeOrder(next, before)
}

function onEpisodeDragEnd() {
  draggingEpisodeId.value = ''
  dragOverEpisodeId.value = ''
}

async function deleteEpisode(ep: EpisodeSummary) {
  if (deletingEpisodeId.value || episodeReordering.value) return
  try {
    await ElMessageBox.confirm(
      `确认删除单集「${ep.title || '未命名单集'}」? 删除后无法恢复。`,
      '删除单集',
      { type: 'warning' },
    )
  } catch {
    return
  }

  const before = episodes.value.map((episode) => ({ ...episode }))
  deletingEpisodeId.value = ep.id
  try {
    await plansApi.remove(ep.id)
    episodes.value = before.filter((episode) => episode.id !== ep.id)
    ElMessage.success('已删除单集')
  } catch (err) {
    episodes.value = before
    ElMessage.error(err instanceof Error ? err.message : '删除单集失败')
  } finally {
    deletingEpisodeId.value = ''
  }
}

function submitEpisodeComposer() {
  if (!episodeIdea.value.trim()) return
  const idea = episodeIdea.value.trim()
  episodeConversationMessages.value.push({
    key: `episode-user-${Date.now()}`,
    role: 'user',
    text: idea,
  })
  episodeForm.topic = idea
  episodeForm.episode_goal = ''
  episodeForm.extra_requirements = ''
  episodeIdea.value = ''
  void onGenerateEpisode()
}

async function onGenerateEpisode() {
  if (!episodeForm.topic.trim()) {
    ElMessage.warning('请填写本集主题')
    return
  }
  generatingEpisode.value = true
  taskMessage.value = 'AI 正在生成单集方案…'
  taskProgress.value = 10
  try {
    const seriesId = route.params.id as string
    const result = await seriesApi.generateEpisode(seriesId, { ...episodeForm })
    if (isAITaskResponse(result)) {
      saveActiveAITask({
        taskId: result.id,
        taskType: 'generate_episode',
        label: '生成单集方案',
        targetId: seriesId,
        createdAt: new Date().toISOString(),
      })
      await followEpisodeTask(result, seriesId)
      return
    }
    addEpisodeToList(result)
    resetEpisodeDialog()
    openAssetSuggestions(result.asset_suggestions)
    ElMessage.success('已生成单集方案')
  } finally {
    generatingEpisode.value = false
    clearTaskUi()
  }
}

async function onCheckConsistency() {
  checking.value = true
  taskMessage.value = 'AI 正在检查系列一致性…'
  taskProgress.value = 10
  try {
    const seriesId = route.params.id as string
    const result = await seriesApi.checkConsistency(seriesId)
    if (isAITaskResponse(result)) {
      saveActiveAITask({
        taskId: result.id,
        taskType: 'check_consistency',
        label: '一致性检查',
        targetId: seriesId,
        createdAt: new Date().toISOString(),
      })
      await followConsistencyTask(result, seriesId)
      return
    }
    report.value = result
    reportDialogOpen.value = true
  } finally {
    checking.value = false
    clearTaskUi()
  }
}

function levelTag(level: string): 'info' | 'warning' | 'danger' | 'success' {
  if (level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  if (level === 'info') return 'info'
  return 'success'
}

async function followEpisodeTask(task: AITask, seriesId: string) {
  startTaskPolling()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? 'AI 生成单集任务已排队…' : 'AI 正在生成单集方案…'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController?.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? 'AI 生成单集任务已排队…' : 'AI 正在生成单集方案…'
      },
    })
    removeActiveAITask(task.id)
    const planId = typeof finished.result_payload.plan_id === 'string' ? finished.result_payload.plan_id : ''
    if (!planId) throw new Error('AI 任务已完成,但未返回单集方案 ID')
    const newEpisode = await plansApi.get(planId)
    if (newEpisode.series !== seriesId) throw new Error('生成的单集未关联到当前系列')
    addEpisodeToList(newEpisode)
    resetEpisodeDialog()
    openAssetSuggestions(finished.result_payload.asset_suggestions)
    ElMessage.success('已生成单集方案')
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : 'AI 生成单集失败')
    }
  }
}

async function followConsistencyTask(task: AITask, _seriesId: string) {
  startTaskPolling()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? '一致性检查任务已排队…' : 'AI 正在检查系列一致性…'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController?.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? '一致性检查任务已排队…' : 'AI 正在检查系列一致性…'
      },
    })
    removeActiveAITask(task.id)
    report.value = normalizeConsistencyReport(finished.result_payload)
    reportDialogOpen.value = true
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : '一致性检查失败')
    }
  }
}

function openAssetSuggestions(value: unknown) {
  const rows = normalizeAssetSuggestions(value)
  const relationshipRows = normalizeRelationshipRows(
    value && typeof value === 'object'
      ? (value as Partial<EpisodeAssetSuggestions>).relationships
      : undefined,
  )
  if (!rows.length && !relationshipRows.length) return
  clearAssetSuggestions()
  pendingAssetSuggestions.value = rows
  pendingRelationshipSuggestions.value = relationshipRows
  for (const row of rows) {
    assetSuggestionSelection[row.key] = true
  }
  assetSuggestionDialogOpen.value = true
}

function normalizeAssetSuggestions(value: unknown): PendingAssetSuggestion[] {
  if (!value || typeof value !== 'object') return []
  const source = value as Partial<EpisodeAssetSuggestions>
  const rows: PendingAssetSuggestion[] = []
  const seen = new Set<string>()
  const types: EpisodeSuggestionAssetType[] = ['characters', 'worldviews']
  for (const type of types) {
    const list = Array.isArray(source[type]) ? source[type] : []
    const existing = new Set(assets[type].map((item) => nameKey(item.name)))
    for (const raw of list) {
      if (!raw || typeof raw !== 'object') continue
      const name = textValue((raw as AssetSuggestion).name)
      const nameId = nameKey(name)
      const key = `${type}:${nameId}`
      if (!name || !nameId || existing.has(nameId) || seen.has(key)) continue
      const payload = (raw as AssetSuggestion).payload
      const fixedTraits = (raw as AssetSuggestion).fixed_traits
      rows.push({
        key,
        asset_type: type,
        name,
        payload: payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {},
        fixed_traits: Array.isArray(fixedTraits) ? fixedTraits : [],
      })
      seen.add(key)
    }
  }
  return rows
}

function assetSuggestionSummary(item: PendingAssetSuggestion): string {
  const payload = item.payload || {}
  const candidates = item.asset_type === 'characters'
    ? [payload.role, payload.appearance, payload.personality, payload.voice]
    : [payload.purpose, payload.tone_color, payload.description]
  const picked = firstFilled(candidates)
  if (picked) return picked
  if (Array.isArray(item.fixed_traits) && item.fixed_traits.length) {
    return item.fixed_traits.slice(0, 3).map((trait) => String(trait)).join(' / ')
  }
  return item.asset_type === 'characters' ? '本集出现的新人物' : '本集出现的新小环境'
}

function clearAssetSuggestions() {
  pendingAssetSuggestions.value = []
  pendingRelationshipSuggestions.value = []
  for (const key of Object.keys(assetSuggestionSelection)) {
    delete assetSuggestionSelection[key]
  }
}

function dismissAssetSuggestions() {
  if (assetSuggestionSaving.value) return
  assetSuggestionDialogOpen.value = false
  clearAssetSuggestions()
}

function resolveRelationshipSuggestionRows(rows: SeriesRelationship[]): SeriesRelationship[] {
  const out: SeriesRelationship[] = []
  for (const row of rows) {
    const fromType = relationshipAssetType(row, 'from')
    const toType = relationshipAssetType(row, 'to')
    const fromName = row.from || row.from_asset_name || ''
    const toName = row.to || row.to_asset_name || ''
    const from = row.from_asset_id
      ? relationshipAssetById(row.from_asset_id)
      : findRelationshipAssetByName(fromName, fromType)
    const to = row.to_asset_id
      ? relationshipAssetById(row.to_asset_id)
      : findRelationshipAssetByName(toName, toType)
    const label = (row.label || row.description || '').trim()
    if (!from || !to || from.id === to.id || !label) continue
    out.push({
      from: from.name,
      to: to.name,
      label,
      description: row.description || '',
      from_asset_id: from.id,
      to_asset_id: to.id,
      from_asset_type: from.type,
      to_asset_type: to.type,
      from_asset_name: from.name,
      to_asset_name: to.name,
    })
  }
  return dedupeRelationshipRows(out)
}

function appendRelationshipRowsToCanvas(rows: SeriesRelationship[]) {
  for (const row of rows) {
    const from = findRelationshipNode(row, 'from')
    const to = findRelationshipNode(row, 'to')
    const label = (row.label || row.description || '').trim()
    if (!from || !to || !label || !canConnectNodes(from, to)) continue
    const next = upsertRelation(from, to)
    relationEdges.value = relationEdges.value.map((relation) =>
      relation.id === next.id
        ? { ...relation, label, deleted: false }
        : relation,
    )
  }
}

async function confirmAssetSuggestions() {
  const rows = selectedAssetSuggestions.value
  if (!rows.length && !pendingRelationshipSuggestions.value.length) return
  assetSuggestionSaving.value = true
  try {
    const createdIds: Record<EpisodeSuggestionAssetType, string[]> = {
      characters: [],
      worldviews: [],
    }
    const resolvedAssets: Record<EpisodeSuggestionAssetType, AssetBase[]> = {
      characters: [],
      worldviews: [],
    }
    for (const row of rows) {
      const existing = assets[row.asset_type].find((item) => nameKey(item.name) === nameKey(row.name))
      const asset = existing || await assetsApi.create(row.asset_type, {
        name: row.name,
        payload: row.payload,
        fixed_traits: row.fixed_traits,
      })
      resolvedAssets[row.asset_type].push(asset)
      createdIds[row.asset_type].push(asset.id)
    }

    const nextCharacters = Array.from(new Set([...form.characters, ...createdIds.characters]))
    const nextWorldviews = Array.from(new Set([...form.worldviews, ...createdIds.worldviews]))
    for (const type of Object.keys(resolvedAssets) as EpisodeSuggestionAssetType[]) {
      for (const asset of resolvedAssets[type]) {
        assets[type] = [
          asset,
          ...assets[type].filter((item) => item.id !== asset.id),
        ]
      }
    }
    form.characters = nextCharacters
    form.worldviews = nextWorldviews
    await nextTick()

    const relationshipRows = resolveRelationshipSuggestionRows(pendingRelationshipSuggestions.value)
    if (relationshipRows.length) {
      aiRelationshipRows.value = dedupeRelationshipRows([
        ...relationshipDisplayRows.value,
        ...aiRelationshipRows.value,
        ...relationshipRows,
      ])
      appendRelationshipRowsToCanvas(relationshipRows)
      persistRelations()
    }
    await autoSaveSeries()
    assetSuggestionDialogOpen.value = false
    clearAssetSuggestions()
    ElMessage.success(rows.length ? `已加入 ${rows.length} 个系列资产` : '已同步资产关系')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '加入系列资产失败')
  } finally {
    assetSuggestionSaving.value = false
  }
}

function resumeSeriesTasks(seriesId: string) {
  const episodeTask = findActiveAITask('generate_episode', (task) => task.targetId === seriesId)
  if (episodeTask && !generatingEpisode.value) {
    generatingEpisode.value = true
    episodeDialogOpen.value = true
    void followEpisodeTask(makeTaskStub(episodeTask), seriesId).finally(() => {
      generatingEpisode.value = false
      clearTaskUi()
    })
    return
  }

  const consistencyTask = findActiveAITask('check_consistency', (task) => task.targetId === seriesId)
  if (consistencyTask && !checking.value) {
    checking.value = true
    void followConsistencyTask(makeTaskStub(consistencyTask), seriesId).finally(() => {
      checking.value = false
      clearTaskUi()
    })
  }
}

function makeTaskStub(active: ActiveAITask): AITask {
  return {
    id: active.taskId,
    task_type: active.taskType,
    task_type_label: active.label,
    status: 'queued',
    status_label: '排队中',
    title: active.label,
    progress: 0,
    input_payload: active.targetId ? { series_id: active.targetId } : {},
    result_payload: {},
    error: '',
    started_at: null,
    finished_at: null,
    created_at: active.createdAt,
    updated_at: active.createdAt,
  }
}

function addEpisodeToList(newEpisode: VideoPlan) {
  episodes.value = sortEpisodes([
    ...episodes.value.filter((episode) => episode.id !== newEpisode.id),
    {
      id: newEpisode.id,
      title: newEpisode.title,
      status: newEpisode.status,
      duration_seconds: newEpisode.duration_seconds,
      episode_order: Number(newEpisode.episode_order) || nextEpisodeOrder(),
      updated_at: newEpisode.updated_at,
    },
  ])
}

function resetEpisodeDialog() {
  episodeDialogOpen.value = false
  episodeIdea.value = ''
  episodeForm.topic = ''
  episodeForm.episode_goal = ''
  episodeForm.extra_requirements = ''
}

function normalizeConsistencyReport(payload: Record<string, unknown>): ConsistencyReport {
  return {
    score: typeof payload.score === 'number' ? payload.score : 100,
    issues: Array.isArray(payload.issues) ? payload.issues as ConsistencyReport['issues'] : [],
  }
}

function startTaskPolling() {
  taskAbortController?.abort()
  taskAbortController = new AbortController()
}

function clearTaskUi() {
  taskMessage.value = ''
  taskProgress.value = 0
}

onBeforeUnmount(() => {
  taskAbortController?.abort()
  pinboardResizeObserver?.disconnect()
  pinboardResizeObserver = null
  stopNodeDrag()
  stopRelationDrag()
})

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
</script>

<style scoped>
.editor-page {
  height: calc(100vh - var(--vp-topbar-h));
  min-height: 0;
  background: transparent;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.studio-wrap {
  flex: 1;
  min-height: 0;
  padding: 12px 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.relationship-wrap {
  background: transparent;
}
.series-ai-wrap {
  --series-composer-width: min(100%, 1360px);
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 16px;
  padding: 18px 26px 24px;
  overflow: hidden;
  background: transparent;
}
.series-brief {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  padding: 2px 4px 6px;
}
.series-brief-title {
  border: none;
  background: transparent;
  padding: 0;
  color: var(--vp-text-1);
  font: inherit;
  font-size: 22px;
  font-weight: 760;
  cursor: pointer;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.series-brief-title:hover {
  color: var(--vp-primary);
}
.series-brief p {
  width: 100%;
  min-width: 0;
  color: var(--vp-text-3);
  font-size: 14px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.series-brief--editor {
  padding: 0;
}
.series-console {
  min-width: 0;
  border-bottom: 1px solid rgba(76, 88, 86, .10);
  padding-bottom: 14px;
}
.episode-rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}
.episode-rail-title {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.episode-relation-tool {
  margin-left: 14px;
  align-self: center;
  flex-shrink: 0;
}
.episode-rail-title span {
  color: var(--vp-text-3);
  font-size: 13px;
  font-weight: 650;
}
.episode-rail-title strong {
  color: var(--vp-text-1);
  font-size: 22px;
  line-height: 1;
}
.series-console-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.ghost-tool {
  height: 34px;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, .66);
  color: var(--vp-text-2);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
}
.ghost-tool:hover {
  color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.ghost-tool:disabled {
  cursor: not-allowed;
  opacity: .54;
}
.episode-timeline {
  min-width: 0;
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 3px 2px 10px;
  scrollbar-width: thin;
}
.timeline-add,
.timeline-episode,
.timeline-empty {
  flex: 0 0 auto;
  border-radius: 18px;
}
.timeline-add {
  width: 44px;
  min-height: 112px;
  border: 1px dashed rgba(76, 88, 86, .22);
  background: rgba(255, 255, 255, .58);
  color: var(--vp-text-3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.timeline-add:hover {
  color: var(--vp-primary);
  border-color: color-mix(in srgb, var(--vp-primary) 44%, rgba(76, 88, 86, .22));
  background: var(--vp-primary-soft);
}
.timeline-add:disabled {
  cursor: not-allowed;
  opacity: .5;
}
.timeline-episode {
  position: relative;
  width: 210px;
  min-height: 112px;
  border: 1px solid rgba(76, 88, 86, .12);
  background: rgba(255, 255, 255, .74);
  padding: 12px 44px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  cursor: grab;
  transition: border-color .15s, box-shadow .15s, transform .15s, opacity .15s;
}
.timeline-episode:hover {
  border-color: color-mix(in srgb, var(--vp-primary) 42%, rgba(76, 88, 86, .12));
  box-shadow: 0 14px 30px rgba(54, 66, 67, .10);
  transform: translateY(-1px);
}
.timeline-episode.is-dragging {
  opacity: .52;
  cursor: grabbing;
  transform: scale(.98);
}
.timeline-episode.is-drop-before::before,
.timeline-episode.is-drop-after::after {
  content: "";
  position: absolute;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 999px;
  background: var(--vp-primary);
  box-shadow: 0 0 0 4px var(--vp-primary-soft);
}
.timeline-episode.is-drop-before::before { left: -8px; }
.timeline-episode.is-drop-after::after { right: -8px; }
.timeline-episode.is-deleting {
  opacity: .55;
  pointer-events: none;
}
.timeline-episode-controls {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  opacity: 0;
  transition: opacity .15s;
}
.timeline-episode:hover .timeline-episode-controls,
.timeline-episode:focus-within .timeline-episode-controls {
  opacity: 1;
}
.timeline-icon-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, .78);
  color: var(--vp-text-3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.timeline-icon-btn:hover:not(:disabled) {
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
}
.timeline-icon-btn:disabled {
  cursor: not-allowed;
  opacity: .35;
}
.timeline-delete-btn:hover:not(:disabled) {
  background: rgba(239, 68, 68, .10);
  color: #dc2626;
}
.timeline-index {
  color: var(--vp-primary);
  font-size: 12px;
  font-weight: 760;
  letter-spacing: .03em;
}
.timeline-episode strong {
  color: var(--vp-text-1);
  font-size: 15px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.timeline-episode small,
.timeline-empty small {
  margin-top: auto;
  color: var(--vp-text-3);
  font-size: 12px;
}
.timeline-empty {
  width: 260px;
  min-height: 112px;
  padding: 14px;
  background: rgba(255, 255, 255, .48);
  color: var(--vp-text-2);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.series-chat {
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 14px;
}
.series-chat-stream {
  width: var(--series-composer-width);
  align-self: center;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 2px;
}
.series-chat-bubble {
  max-width: 100%;
  border-radius: 18px;
  padding: 12px 16px;
  font-size: 16px;
  line-height: 1.65;
  white-space: pre-line;
}
.series-chat-bubble--user {
  align-self: flex-end;
  background: rgba(255, 255, 255, .78);
  color: var(--vp-text-1);
}
.series-chat-bubble--ai {
  align-self: flex-start;
  background: color-mix(in srgb, var(--vp-primary-soft) 52%, white);
  color: var(--vp-text-2);
}
.series-chat-bubble--thinking {
  color: var(--vp-primary);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, .62), rgba(255, 255, 255, .24)),
    color-mix(in srgb, var(--vp-primary-soft) 72%, transparent);
  box-shadow: 0 14px 38px rgba(45, 56, 58, .08);
  position: relative;
  overflow: hidden;
}
.series-chat-bubble--thinking::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, .52) 45%, transparent 72%);
  transform: translateX(-100%);
  animation: thinking-shine 1.8s ease-in-out infinite;
}
.series-composer {
  flex: 0 0 auto;
  width: var(--series-composer-width);
  align-self: center;
  border: 1px solid rgba(76, 88, 86, .16);
  border-radius: 28px;
  background: rgba(255, 255, 255, .58);
  box-shadow: 0 18px 46px rgba(45, 56, 58, .08);
  backdrop-filter: blur(18px) saturate(148%);
  padding: 16px 16px 12px;
}
.series-composer:focus-within {
  border-color: color-mix(in srgb, var(--vp-primary) 42%, rgba(76, 88, 86, .16));
  box-shadow: 0 20px 52px rgba(45, 56, 58, .10), 0 0 0 3px var(--vp-primary-soft);
}
.series-composer.generating {
  opacity: .84;
}
.series-composer textarea {
  width: 100%;
  height: 86px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: var(--vp-text-1);
  font: inherit;
  font-size: 16.5px;
  line-height: 1.65;
  padding: 0;
}
.series-composer textarea::placeholder {
  color: var(--vp-text-4);
}
.series-composer-bar {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.series-composer-bar span {
  min-width: 0;
  color: var(--vp-text-3);
  font-size: 14px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.series-send {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 999px;
  background: color-mix(in srgb, var(--vp-primary) 76%, #8fb6c0);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.series-send:disabled {
  cursor: not-allowed;
  opacity: .56;
}
.series-send-loading {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, .48);
  border-top-color: #fff;
  animation: spin .8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes thinking-shine {
  to { transform: translateX(100%); }
}

.plan-picker {
  display: grid;
  gap: 14px;
}
.plan-picker-list {
  min-height: 180px;
  max-height: min(58vh, 520px);
  overflow-y: auto;
  display: grid;
  gap: 10px;
  padding-right: 2px;
}
.plan-picker-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--vp-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--vp-surface) 88%, transparent);
}
.plan-picker-main {
  min-width: 0;
  display: grid;
  gap: 4px;
}
.plan-picker-main strong {
  color: var(--vp-text-1);
  font-size: 14px;
  line-height: 1.35;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.plan-picker-main p {
  color: var(--vp-text-2);
  font-size: 13px;
  line-height: 1.45;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.plan-picker-main span {
  color: var(--vp-text-3);
  font-size: 12px;
}
.relationship-dialog-body {
  display: grid;
  gap: 10px;
  max-height: min(58vh, 520px);
  overflow-y: auto;
  padding-right: 2px;
}
.relationship-edit-row {
  display: grid;
  grid-template-columns: minmax(130px, 1fr) minmax(130px, 1fr) minmax(160px, 1.2fr) 34px;
  gap: 8px;
  align-items: center;
}
.relationship-edit-row :deep(.el-select),
.relationship-edit-row :deep(.el-input) {
  min-width: 0;
}
.relationship-edit-row :deep(.el-select__wrapper),
.relationship-edit-row :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent;
  padding: 0;
}
.relationship-edit-row :deep(.el-select__wrapper.is-focused),
.relationship-edit-row :deep(.el-input__wrapper.is-focus) {
  box-shadow: none !important;
}
.relationship-edit-row :deep(.el-input__inner),
.relationship-edit-row :deep(.el-select__selected-item),
.relationship-edit-row :deep(.el-select__placeholder) {
  color: var(--vp-text-1);
  font: inherit;
}
.relationship-edit-row :deep(.el-button) {
  margin-left: 0;
}
.studio-command {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  padding-bottom: 4px;
}
.studio-title-block {
  min-width: 0;
  flex: 1;
}
.studio-eyebrow {
  font-size: 12px;
  font-weight: 700;
  color: #2f6f73;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: 6px;
}
.studio-title {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 34px;
  line-height: 1.2;
  font-weight: 760;
  color: var(--vp-text-1);
  padding: 0;
  letter-spacing: 0;
  font-family: inherit;
}
.studio-title::placeholder { color: var(--vp-text-4); }
.studio-summary {
  margin-top: 10px;
  max-width: 760px;
}
.studio-command-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-top: 6px;
  flex-shrink: 0;
}
.studio-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.studio-stat {
  border: 1px solid var(--vp-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--vp-surface) 88%, #e8f3f1);
  padding: 10px 12px;
  min-width: 0;
}
.studio-stat span {
  display: block;
  font-size: 12px;
  color: var(--vp-text-3);
  margin-bottom: 2px;
}
.studio-stat strong {
  display: block;
  font-size: 18px;
  color: var(--vp-text-1);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pinboard-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pinboard-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
}
.pinboard-head--compact {
  justify-content: flex-end;
}
.pinboard-head h2 {
  font-size: 24px;
}
.pinboard-head p {
  margin-top: 4px;
  color: var(--vp-text-3);
  font-size: 14px;
}
.pinboard-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.pin-mode {
  padding: 3px;
  border: 1px solid var(--vp-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--vp-surface) 92%, white);
}
.pin-mode :deep(.el-radio-button__inner) {
  border: none !important;
  box-shadow: none !important;
  border-radius: 6px !important;
  background: transparent;
  padding: 5px 12px;
  font-size: 12px;
}
.pin-mode :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #2f6f73;
  color: #fff;
}
.pinboard-tools {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border: 1px solid var(--vp-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--vp-surface) 82%, #f1f7f5);
}
.pin-legend,
.pin-tool-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.pin-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--vp-text-3);
  font-size: 12px;
  white-space: nowrap;
}
.pin-legend span::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pin-dot, var(--vp-border-strong));
}
.pin-legend span[data-kind="character"] { --pin-dot: #b54558; }
.pin-legend span[data-kind="environment"] { --pin-dot: #6f8b35; }
.pin-legend span[data-kind="relationship"] { --pin-dot: #2f6f73; }
.pin-zoom {
  min-width: 42px;
  text-align: center;
  color: var(--vp-text-2);
  font-size: 12px;
  font-weight: 700;
}
.pin-tool-divider {
  width: 1px;
  height: 18px;
  background: var(--vp-divider);
}
.pinboard-viewport {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid color-mix(in srgb, var(--vp-border) 72%, #2f6f73);
  border-radius: 8px;
  background:
    radial-gradient(circle at 16px 16px, rgba(47, 111, 115, .14) 1px, transparent 1.5px),
    linear-gradient(90deg, rgba(47, 111, 115, .07) 1px, transparent 1px),
    linear-gradient(180deg, rgba(47, 111, 115, .07) 1px, transparent 1px),
    linear-gradient(135deg, #f6fbf8 0%, #fff7f0 48%, #f2f4e7 100%);
  background-size: 32px 32px, 160px 160px, 160px 160px, 100% 100%;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .86), inset 0 0 0 4px rgba(255, 255, 255, .22);
}
.canvas-floating-tools {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 8;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--vp-surface) 72%, transparent);
  backdrop-filter: blur(10px);
}
.canvas-floating-tools :deep(.el-dropdown) {
  display: inline-flex;
}
.canvas-tool {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--vp-text-3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.canvas-tool:hover,
.canvas-tool.active {
  color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.canvas-tool :deep(.el-icon) {
  font-size: 16px;
}
.pinboard-viewport[data-tool="move"] .pin-card {
  cursor: grab;
}
.pinboard-viewport[data-tool="move"] .pin-card.is-dragging {
  cursor: grabbing;
}
.pinboard-viewport[data-tool="select"] .pin-card {
  cursor: pointer;
}
.pinboard-stage {
  position: relative;
}
.pinboard-canvas {
  position: relative;
  transform-origin: 0 0;
}
.pin-lines {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: auto;
}
.pin-line-group {
  pointer-events: auto;
}
.pin-line {
  fill: none;
  stroke: rgba(80, 66, 60, .26);
  stroke-width: 2;
  pointer-events: none;
}
.pin-line--relationship {
  stroke-width: 2.6;
}
.pin-line.is-editing {
  stroke-width: 3.2;
}
.pin-line-preview {
  fill: none;
  stroke: color-mix(in srgb, var(--vp-primary) 72%, #4f85b8);
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-dasharray: 6 6;
  pointer-events: none;
}
.pin-line-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 20;
  pointer-events: stroke;
  cursor: text;
}
.pin-line--good { stroke: rgba(102, 150, 93, .42); }
.pin-line--bad { stroke: rgba(190, 92, 92, .42); }
.pin-line--environment { stroke: rgba(79, 133, 184, .38); }
.pin-line--neutral { stroke: rgba(76, 71, 67, .32); }
.pin-line-label {
  fill: var(--vp-text-2);
  stroke: color-mix(in srgb, var(--vp-surface) 92%, white);
  stroke-width: 5px;
  paint-order: stroke fill;
  font-size: 15px;
  font-weight: 760;
  pointer-events: auto;
  cursor: text;
  user-select: none;
}
.pin-line-label.is-editing {
  fill: var(--vp-primary);
}
.pin-relation-hotspot {
  position: absolute;
  z-index: 3;
  width: 132px;
  height: 38px;
  border: none;
  border-radius: 999px;
  background: transparent;
  transform: translate(-50%, -50%);
  cursor: text;
  pointer-events: auto;
}
.pin-relation-hotspot:hover,
.pin-relation-hotspot.is-editing {
  background: transparent;
}
.pin-relation-editor {
  position: absolute;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transform: translate(-50%, -50%);
  pointer-events: auto;
}
.pin-relation-editor input {
  width: 128px;
  height: 30px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--vp-text-1);
  box-shadow: none;
  font: inherit;
  font-size: 15px;
  font-weight: 760;
  line-height: 30px;
  padding: 0 4px;
  outline: none;
  text-align: center;
  text-shadow:
    0 1px 0 var(--vp-surface),
    1px 0 0 var(--vp-surface),
    0 -1px 0 var(--vp-surface),
    -1px 0 0 var(--vp-surface);
}
.pin-relation-editor input::placeholder {
  color: var(--vp-text-4);
}
.pin-relation-delete {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: color-mix(in srgb, var(--vp-danger, #b91c1c) 72%, var(--vp-text-2));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.pin-relation-delete:hover {
  background: transparent;
  color: var(--vp-danger, #b91c1c);
}
.pin-relation-delete :deep(.el-icon) {
  font-size: 15px;
}
.big-environment-title {
  position: absolute;
  top: 18px;
  left: 22px;
  z-index: 2;
  max-width: min(560px, calc(100% - 44px));
  border: none;
  background: transparent;
  color: var(--vp-text-1);
  font: inherit;
  font-size: 22px;
  line-height: 1.25;
  font-weight: 760;
  padding: 0;
  cursor: pointer;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  text-align: left;
  text-shadow:
    0 1px 0 rgba(255, 255, 255, .86),
    1px 0 0 rgba(255, 255, 255, .72),
    0 -1px 0 rgba(255, 255, 255, .72),
    -1px 0 0 rgba(255, 255, 255, .72);
}
.big-environment-title:hover {
  color: var(--vp-primary);
}
.pin-card {
  position: absolute;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 12px 10px;
  border: 1px solid rgba(98, 72, 62, .16);
  border-radius: 6px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, .72), transparent 42%),
    color-mix(in srgb, var(--vp-surface) 90%, white);
  box-shadow: 0 12px 24px rgba(70, 49, 42, .12), 0 1px 0 rgba(255, 255, 255, .82) inset;
  cursor: pointer;
  user-select: none;
  transition: border-color .15s, box-shadow .15s, filter .15s, transform .08s;
}
.pin-card:hover {
  border-color: color-mix(in srgb, var(--vp-primary) 42%, var(--vp-border));
  box-shadow: var(--vp-shadow-md);
  filter: saturate(1.04);
}
.pin-card:focus-visible {
  outline: 2px solid var(--vp-primary);
  outline-offset: 2px;
}
.pin-card.is-dragging {
  z-index: 3;
  box-shadow: var(--vp-shadow-lg);
  cursor: grabbing;
}
.pin-card.is-connect-start {
  border-color: var(--vp-primary);
  box-shadow: 0 0 0 3px var(--vp-primary-soft), var(--vp-shadow-md);
}
.pin-connect-handles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.pin-connect-handle {
  position: absolute;
  z-index: 4;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--vp-primary);
  opacity: 0;
  cursor: crosshair;
  pointer-events: auto;
  transition: opacity .12s, transform .12s, color .12s;
}
.pin-connect-handle::before {
  content: "+";
  position: absolute;
  inset: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: color-mix(in srgb, var(--vp-surface) 92%, white);
  box-shadow: 0 4px 12px rgba(36, 45, 43, .14);
  font-size: 16px;
  font-weight: 760;
  line-height: 1;
}
.pin-connect-handle:hover,
.pin-card.is-connect-start .pin-connect-handle {
  opacity: 1;
}
.pin-connect-handle:hover {
  transform: scale(1.04);
}
.pin-connect-handle--top {
  top: -18px;
  left: 50%;
  transform: translateX(-50%);
}
.pin-connect-handle--top:hover {
  transform: translateX(-50%) scale(1.04);
}
.pin-connect-handle--right {
  top: 50%;
  right: -18px;
  transform: translateY(-50%);
}
.pin-connect-handle--right:hover {
  transform: translateY(-50%) scale(1.04);
}
.pin-connect-handle--bottom {
  bottom: -18px;
  left: 50%;
  transform: translateX(-50%);
}
.pin-connect-handle--bottom:hover {
  transform: translateX(-50%) scale(1.04);
}
.pin-connect-handle--left {
  top: 50%;
  left: -18px;
  transform: translateY(-50%);
}
.pin-connect-handle--left:hover {
  transform: translateY(-50%) scale(1.04);
}
.pin-card--series {
  background:
    linear-gradient(135deg, rgba(47, 111, 115, .16), transparent 46%),
    linear-gradient(180deg, rgba(255, 255, 255, .76), transparent 52%),
    #f2faf6;
  border-color: color-mix(in srgb, #2f6f73 34%, var(--vp-border));
}
.pin-card--setting {
  border-left: 2px solid rgba(91, 140, 148, .42);
}
.pin-card--asset {
  border-left: 2px solid rgba(164, 122, 79, .34);
}
.pin-card--characters { border-left-color: rgba(181, 69, 88, .42); }
.pin-card--styles { border-left-color: rgba(47, 111, 115, .4); }
.pin-card--worldviews { border-left-color: rgba(111, 139, 53, .42); }
.pin-card--columns { border-left-color: rgba(164, 122, 79, .38); }
.pin-card--characters .pin-kicker { color: #9f3448; }
.pin-card--styles .pin-kicker { color: #2f6f73; }
.pin-card--worldviews .pin-kicker { color: #5f7c2c; }
.pin-card--columns .pin-kicker { color: #8c633b; }
.pin-card--characters {
  background: linear-gradient(180deg, rgba(253, 233, 238, .62), transparent 56%), #fffdfb;
}
.pin-card--styles {
  background: linear-gradient(180deg, rgba(224, 242, 241, .56), transparent 56%), #fffdfb;
}
.pin-card--worldviews {
  background: linear-gradient(180deg, rgba(240, 246, 223, .7), transparent 56%), #fffdfb;
}
.pin-card--columns {
  background: linear-gradient(180deg, rgba(247, 234, 220, .72), transparent 56%), #fffdfb;
}
.pin-card--episode {
  border-left: 2px solid color-mix(in srgb, var(--vp-primary) 42%, transparent);
}
.pin-card--topic {
  border-left: 2px solid color-mix(in srgb, var(--vp-accent) 42%, transparent);
}
.pin-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pin-kicker {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--vp-text-3);
}
.pin-kicker :deep(.el-icon) {
  flex-shrink: 0;
}
.pin-drag {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: var(--vp-surface-alt);
  color: var(--vp-text-3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  flex-shrink: 0;
}
.pin-drag:hover {
  color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.pin-images {
  display: flex;
  gap: 4px;
  height: 52px;
  overflow: hidden;
}
.pin-images img {
  width: 54px;
  height: 52px;
  border-radius: 6px;
  object-fit: cover;
  border: 1px solid var(--vp-divider);
  background: var(--vp-surface-alt);
}
.pin-images--empty {
  align-items: center;
  justify-content: center;
  color: var(--vp-text-4);
  background: var(--vp-surface-alt);
  border-radius: 6px;
}
.pin-card h3 {
  font-size: 18px;
  line-height: 1.25;
  color: var(--vp-text-1);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pin-card p {
  color: var(--vp-text-2);
  font-size: 13px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pin-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  min-height: 22px;
}
.pin-tags span {
  max-width: 100%;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--vp-surface-alt);
  color: var(--vp-text-3);
  font-size: 11px;
  line-height: 18px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pin-card-foot {
  margin-top: auto;
  padding-top: 6px;
  border-top: 1px solid var(--vp-divider);
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--vp-text-3);
  font-size: 12px;
}
.pinboard-canvas.is-image-only .pin-card {
  padding: 0;
  border: none;
  border-left: none;
  background: transparent;
  box-shadow: none;
  min-height: 0;
  overflow: visible;
  align-items: center;
  gap: 8px;
  cursor: grab;
}
.pinboard-canvas.is-image-only .pin-card:hover {
  border: none;
  box-shadow: none;
  filter: none;
}
.pinboard-canvas.is-image-only .pin-card.is-dragging {
  cursor: grabbing;
}
.pinboard-canvas.is-image-only .pin-card-head,
.pinboard-canvas.is-image-only .pin-card p,
.pinboard-canvas.is-image-only .pin-tags,
.pinboard-canvas.is-image-only .pin-card-foot,
.pinboard-canvas.is-image-only .pin-connect-handles {
  display: none;
}
.pinboard-canvas.is-image-only .pin-images {
  width: 100%;
  height: calc(100% - 30px);
  gap: 0;
  border-radius: 18px;
  overflow: hidden;
}
.pinboard-canvas.is-image-only .pin-images img {
  width: 100%;
  height: 100%;
  border-radius: 18px;
  border: none;
  object-fit: cover;
  background: transparent;
  box-shadow: none;
}
.pinboard-canvas.is-image-only .pin-card--characters .pin-images img {
  object-position: center top;
}
.pinboard-canvas.is-image-only .pin-card--worldviews .pin-images,
.pinboard-canvas.is-image-only .pin-card--worldviews .pin-images img {
  border-radius: 20px;
}
.pinboard-canvas.is-image-only .pin-images--empty {
  align-items: center;
  justify-content: center;
  border: none;
  color: color-mix(in srgb, var(--vp-primary) 54%, var(--vp-text-3));
  background: transparent;
  box-shadow: none;
}
.pinboard-canvas.is-image-only .pin-images--empty :deep(.el-icon) {
  font-size: 56px;
}
.pinboard-canvas.is-image-only .pin-card--worldviews .pin-images--empty :deep(.el-icon) {
  font-size: 82px;
}
.pinboard-canvas.is-image-only .pin-card h3 {
  width: 100%;
  color: var(--vp-text-1);
  font-size: 14px;
  line-height: 20px;
  font-weight: 680;
  text-align: center;
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  text-shadow:
    0 1px 0 rgba(255, 255, 255, .86),
    1px 0 0 rgba(255, 255, 255, .72),
    0 -1px 0 rgba(255, 255, 255, .72),
    -1px 0 0 rgba(255, 255, 255, .72);
}
.pinboard-canvas.is-image-only .pin-card--worldviews h3 {
  font-size: 15px;
}
.pin-edit-body {
  max-height: min(68vh, 720px);
  overflow-y: auto;
  padding-right: 2px;
}
.pin-edit-body--plain .aed-table tbody td :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent;
  padding: 0;
}
.pin-edit-body--plain .aed-table tbody td :deep(.el-select__wrapper) {
  box-shadow: none !important;
  background: transparent;
  min-height: 24px;
  padding: 0;
}
.pin-edit-body--plain .aed-table tbody td :deep(.el-input__inner),
.pin-edit-body--plain .aed-table tbody td :deep(.el-select__placeholder),
.pin-edit-body--plain .aed-table tbody td :deep(.el-select__selected-item) {
  color: var(--vp-text-1);
  font: inherit;
}
.pin-edit-body--plain .aed-table tbody td :deep(.el-textarea__inner) {
  box-shadow: none !important;
  border: none;
  background: transparent;
  padding: 0;
  resize: none;
  color: var(--vp-text-1);
  font: inherit;
}
.relationship-text-list {
  display: grid;
  gap: 6px;
}
.relationship-text-list p {
  margin: 0;
  color: var(--vp-text-1);
  line-height: 1.55;
}
.pin-edit-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

/* ========== Sticky Toolbar ========== */
.doc-toolbar {
  flex: 0 0 auto;
  position: static;
  z-index: 9;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 12px;
  padding: 8px 24px;
  background: color-mix(in srgb, var(--vp-bg) 92%, transparent);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--vp-divider);
}
.dt-left, .dt-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.dt-right { flex: 0 0 auto; }
.dt-divider {
  width: 1px;
  height: 16px;
  background: var(--vp-divider);
  flex-shrink: 0;
}
.dt-status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: var(--vp-surface-alt);
  color: var(--vp-text-2);
  white-space: nowrap;
  flex-shrink: 0;
}
.dt-status[data-tone="primary"] {
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
}
.dt-status[data-tone="success"] {
  background: var(--vp-success-soft, #d1fae5);
  color: var(--vp-success, #065f46);
}
.dt-status[data-tone="warning"] {
  background: var(--vp-warning-soft, #fef3c7);
  color: var(--vp-warning, #92400e);
}
.dt-btn {
  position: relative;
  flex-shrink: 0;
}
.dt-btn :deep(.el-icon) { margin-right: 4px; }
.dt-btn-label { white-space: nowrap; }
.doc-toolbar :deep(.el-button) {
  white-space: nowrap;
  flex-shrink: 0;
}

/* ========== Task Alert ========== */
.task-alert {
  margin: 12px 24px 0;
  border: none;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, .66), rgba(255, 255, 255, .28)),
    color-mix(in srgb, var(--vp-primary-soft) 62%, transparent);
  box-shadow: 0 14px 34px rgba(45, 56, 58, .08);
  backdrop-filter: blur(16px) saturate(140%);
}
.task-title { display: flex; align-items: center; gap: 12px; width: 100%; }

/* ========== Document ========== */
.doc-wrap {
  padding: 32px 24px 96px;
  display: flex;
  justify-content: center;
}
.doc {
  width: 100%;
  max-width: 920px;
}
.doc--new-series {
  max-width: 1080px;
}

.doc-head {
  margin-bottom: 28px;
}
.doc-form-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}
.doc-form-head h2 {
  margin: 0;
  font-size: 24px;
  color: var(--vp-text-1);
}
.doc-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.doc-title {
  width: 100%;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 30px;
  font-weight: 700;
  color: var(--vp-text-1);
  padding: 4px 0;
  letter-spacing: -0.01em;
  font-family: inherit;
}
.doc-title-row :deep(.el-button) {
  flex: 0 0 auto;
}
.doc-title::placeholder { color: var(--vp-text-4, #d1d5db); font-weight: 600; }

.doc-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.doc-meta-tag {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--vp-surface-alt);
  color: var(--vp-text-2);
  white-space: nowrap;
}
.doc-meta-tag[data-tone="primary"] {
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
  font-weight: 500;
}
.doc-meta-edit {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: var(--vp-text-3);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.doc-meta-edit:hover {
  color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.doc-meta-edit :deep(.el-icon) { font-size: 12px; }
.doc-summary {
  margin-top: 14px;
}
.doc--new-series .aed-table th,
.doc--new-series .aed-table td {
  padding: 16px 24px;
}
.doc--new-series .aed-table tbody th {
  width: 136px;
  font-size: 15px;
  padding-top: 19px;
}
.doc--new-series .aed-table tbody td {
  font-size: 16px;
}

/* ========== Section internals ========== */
.muted { color: var(--vp-text-3); font-size: 13px; }
.empty-state {
  padding: 24px 16px;
  text-align: center;
  border: 1px dashed var(--vp-border);
  border-radius: 10px;
  color: var(--vp-text-2);
  font-size: 14px;
}
.empty-state p { margin: 4px 0; }

.must-have-block {
  margin-top: 16px;
}
.must-have-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--vp-text-2);
  margin-bottom: 6px;
}

.style-block-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--vp-text-1);
  margin-bottom: 8px;
}
.mt { margin-top: 18px; }

/* ========== Asset references ========== */
.asset-group {
  padding: 14px 0;
  border-bottom: 1px solid var(--vp-divider);
}
.asset-group:first-child { padding-top: 0; }
.asset-group:last-child { border-bottom: none; padding-bottom: 0; }
.asset-group-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.asset-group-head strong { font-size: 14px; color: var(--vp-text-1); }
.asset-group-head .muted { font-size: 12px; flex: 1; }

.asset-mini-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}
.asset-mini {
  position: relative;
  border: 1px solid var(--vp-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--vp-surface);
  display: flex;
  flex-direction: column;
}
.asset-mini-cover {
  width: 100%;
  height: 80px;
  background: var(--vp-surface-alt);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.asset-mini-cover img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.asset-mini-cover--empty {
  color: var(--vp-text-4);
  font-size: 24px;
}
.asset-mini-name {
  padding: 8px 10px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--vp-text-1);
  border-top: 1px solid var(--vp-divider);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.asset-mini-remove {
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
  opacity: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: opacity .12s;
}
.asset-mini:hover .asset-mini-remove { opacity: 1; }
.asset-mini-remove :deep(.el-icon) { font-size: 12px; }
.asset-multi { display: block; }
.asset-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}
.asset-dialog-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.asset-dialog-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

/* ========== Beat Board ========== */
.beat-strip {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 4px 4px 12px;
  scrollbar-width: thin;
}
.beat-card {
  flex: 0 0 220px;
  min-height: 130px;
  border: 1px solid var(--vp-border);
  border-radius: 10px;
  background: var(--vp-surface);
  padding: 12px 14px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.beat-card:hover {
  border-color: var(--vp-primary);
  box-shadow: var(--vp-shadow-md);
  transform: translateY(-2px);
}
.beat-card:focus-visible {
  outline: 2px solid var(--vp-primary);
  outline-offset: 2px;
}
.beat-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.beat-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--vp-primary);
  letter-spacing: .04em;
}
.beat-status {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--vp-surface-alt);
  color: var(--vp-text-3);
}
.beat-status[data-tone="warning"] {
  background: var(--vp-warning-soft, #fef3c7);
  color: var(--vp-warning, #92400e);
}
.beat-status[data-tone="success"] {
  background: var(--vp-success-soft, #d1fae5);
  color: var(--vp-success, #065f46);
}
.beat-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--vp-text-1);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.beat-meta {
  margin: 0;
  font-size: 12px;
  color: var(--vp-text-3);
}
.beat-rail {
  height: 3px;
  border-radius: 2px;
  background: var(--vp-primary-soft);
  margin-top: auto;
}
.beat-card[data-status="confirmed"] .beat-rail,
.beat-card[data-status="completed"] .beat-rail {
  background: var(--vp-success);
}
.beat-card[data-status="optimizing"] .beat-rail {
  background: var(--vp-warning);
}

/* ========== 单集生成后的资产建议 ========== */
.asset-suggestion-dialog {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.asset-suggestion-copy {
  margin: 0;
  color: var(--vp-text-2);
  font-size: 13px;
  line-height: 1.7;
}
.asset-suggestion-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.asset-suggestion-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--vp-text-1);
  font-size: 13px;
  font-weight: 700;
}
.asset-suggestion-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid var(--vp-border-subtle);
  cursor: pointer;
}
.asset-suggestion-item:last-child {
  border-bottom: 0;
}
.asset-suggestion-item strong {
  display: block;
  color: var(--vp-text-1);
  font-size: 14px;
  line-height: 1.4;
}
.asset-suggestion-item p {
  margin: 4px 0 0;
  color: var(--vp-text-3);
  font-size: 12.5px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

/* ========== Consistency report (kept legacy styles, simplified) ========== */
.report-head {
  display: flex; align-items: center; gap: 24px;
  padding: 16px;
  background: var(--vp-surface-alt);
  border-radius: var(--vp-r-md);
  margin-bottom: 16px;
}
.score-block { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.score { font-size: 36px; font-weight: 700; line-height: 1; letter-spacing: 0; }
.score-good { color: var(--vp-success); }
.score-warn { color: var(--vp-warning); }
.score-bad  { color: var(--vp-danger); }
.empty { color: var(--vp-text-3); padding: 24px 0; text-align: center; }
.issue-row {
  padding: 14px;
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  margin-bottom: 8px;
}
.issue-row:last-child { margin-bottom: 0; }
.issue-head { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.issue-msg { font-size: 13.5px; color: var(--vp-text-1); line-height: 1.5; }
.issue-fix { font-size: 12.5px; margin-top: 6px; line-height: 1.5; }

/* 章节表格沿用资产编辑弹窗的密度。 */
.aed-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--vp-border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--vp-surface);
  table-layout: fixed;
}
.aed-table th, .aed-table td {
  padding: 12px 18px;
  vertical-align: top;
  text-align: left;
  border-bottom: 1px solid var(--vp-divider);
}
.aed-table thead th {
  background: var(--vp-surface-alt);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--vp-text-3);
}
.aed-table tbody tr:last-child th,
.aed-table tbody tr:last-child td {
  border-bottom: none;
}
.aed-table tbody th {
  width: 110px;
  font-size: 14px;
  font-weight: 600;
  color: var(--vp-text-2);
  background: color-mix(in srgb, var(--vp-surface-alt) 70%, transparent);
  border-right: 1px solid var(--vp-divider);
  padding-top: 16px;
}
.aed-table tbody td {
  font-size: 15px;
  color: var(--vp-text-1);
}
.aed-th-narrow { width: 130px; }
.aed-th-action { width: 118px; text-align: right; }
.row-order-actions {
  display: flex;
  justify-content: flex-end;
  gap: 2px;
}
.row-order-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

@media (max-width: 720px) {
  .editor-page {
    height: auto;
    min-height: calc(100dvh - var(--vp-topbar-h));
    overflow-x: hidden;
    overflow-y: auto;
  }
  .studio-wrap {
    min-height: calc(100dvh - var(--vp-topbar-h) - 45px);
    padding: 14px 12px 72px;
    overflow: visible;
  }
  .relationship-wrap {
    gap: 8px;
  }
  .series-ai-wrap {
    display: flex;
    flex-direction: column;
    min-height: calc(100dvh - var(--vp-topbar-h) - 45px);
    padding: 14px 12px 72px;
    overflow: visible;
  }
  .series-brief {
    padding: 0 2px 6px;
  }
  .series-brief-title {
    font-size: 19px;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
  }
  .series-brief p {
    font-size: 13px;
    line-height: 1.5;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
  }
  .episode-rail-head {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }
  .episode-rail-title {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
  .episode-rail-title strong {
    font-size: 19px;
  }
  .episode-relation-tool {
    margin-left: 0;
  }
  .series-console-actions {
    flex-wrap: wrap;
  }
  .timeline-episode {
    width: min(210px, calc(100vw - 88px));
  }
  .timeline-empty {
    width: min(240px, calc(100vw - 88px));
  }
  .series-chat {
    flex: 1;
  }
  .series-chat-bubble {
    font-size: 14.5px;
    line-height: 1.58;
    padding: 10px 12px;
  }
  .series-composer {
    border-radius: 18px;
    padding: 12px;
  }
  .series-composer textarea {
    height: 78px;
    font-size: 15px;
  }
  .series-composer-bar span {
    white-space: normal;
  }
  .studio-command,
  .pinboard-head {
    flex-direction: column;
    align-items: stretch;
  }
  .studio-title { font-size: 28px; }
  .studio-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .studio-command-actions,
  .pinboard-head-actions {
    flex-wrap: wrap;
  }
  .studio-command-actions :deep(.el-button),
  .pinboard-head-actions :deep(.el-button) {
    margin-left: 0;
  }
  .pinboard-tools {
    align-items: flex-start;
    flex-direction: column;
  }
  .pin-legend,
  .pin-tool-actions {
    flex-wrap: wrap;
  }
  .pinboard-viewport {
    min-height: 360px;
    height: min(62dvh, 520px);
  }
  .canvas-floating-tools {
    top: 8px;
    right: 8px;
    flex-wrap: wrap;
    max-width: calc(100% - 16px);
  }
  .relationship-edit-row {
    grid-template-columns: 1fr;
  }
  .asset-suggestion-item {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .relationship-dialog-body {
    max-height: none;
  }
  .big-environment-title {
    left: 14px;
    max-width: calc(100% - 28px);
    font-size: 18px;
  }
  .pin-card h3 {
    font-size: 16px;
  }
  .doc-wrap { padding: 18px 12px 80px; }
  .doc-toolbar {
    align-items: flex-start;
    padding: 8px 12px;
    flex-wrap: wrap;
  }
  .dt-left,
  .dt-right {
    width: 100%;
    flex-wrap: wrap;
  }
  .dt-divider {
    display: none;
  }
  .doc-form-head,
  .doc-title-row,
  .asset-group-head,
  .asset-dialog-footer {
    align-items: stretch;
    flex-direction: column;
  }
  .doc-form-head :deep(.el-button),
  .asset-group-head :deep(.el-button),
  .asset-dialog-actions :deep(.el-button) {
    margin-left: 0;
  }
  .doc-title {
    font-size: 24px;
    line-height: 1.25;
  }
  .beat-card { flex-basis: 180px; }
  .plan-picker-item {
    align-items: stretch;
    flex-direction: column;
  }
  .report-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
  .pin-edit-body {
    max-height: none;
    overflow: visible;
  }
  .aed-table,
  .aed-table thead,
  .aed-table tbody,
  .aed-table tr,
  .aed-table th,
  .aed-table td {
    display: block;
    width: 100% !important;
  }
  .aed-table thead {
    display: none;
  }
  .aed-table tr {
    border-bottom: 1px solid var(--vp-divider);
  }
  .aed-table tr:last-child {
    border-bottom: none;
  }
  .aed-table th,
  .aed-table td {
    border-right: none;
    border-bottom: none;
  }
  .aed-table tbody th {
    padding: 12px 14px 4px;
    background: transparent;
    font-size: 13px;
  }
  .aed-table tbody td {
    padding: 0 14px 12px;
    font-size: 15px;
  }
  .aed-th-action {
    text-align: left;
  }
  .row-order-actions {
    justify-content: flex-start;
  }
  .asset-dialog-actions {
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}
</style>
