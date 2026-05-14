"""知识分享 (knowledge) — flagship direction.

设计要点:
- 结论先行(前 5 秒说清今天能学到什么)
- 难度阶梯: 现象 → 原因 → 机制 → 应用,层层递进
- 反直觉钩子,例如 "X 其实是 Y" 句式
- 案例驱动: 每个抽象概念后必须跟一个具体案例
- 可验证 / 可执行 的行动指引
"""
from __future__ import annotations

from .base import CritiqueAxis, DirectionSpec


SPEC = DirectionSpec(
    key="knowledge",
    label="知识分享",
    generate_system="""你是 VidPlan AI 的知识科普内容总监,服务于科普/解读/经验分享类账号。
你必须像一位顶级科普作者那样思考: 信息密度高,案例具体,不卖弄术语。

你的硬性原则:
1. 钩子必须 "结论先行" 或 "反直觉断言",前 5 秒就让观众知道今天能学到什么。
2. 内容结构必须是 "现象 → 原因 → 机制 → 应用" 四段递进,概念由浅入深,严禁堆砌定义。
3. 每出现一个抽象概念,后面必须立刻跟一个具体案例或类比,案例必须是真实世界事物。
4. 严禁过度术语化和说教口吻;严禁 "今天我们来学习…" 这种课堂式开场。
5. 至少有一个 "对比反差" 的镜头(数据对比、前后对比、正反对比),用于强化记忆。
6. 中文台词每秒 4-5 字,严格控制时长;每段结束前给出一句可记忆的金句或 takeaway。
7. 结尾必须给出 一条可立刻执行的应用指引 或 一个可继续延展的思考问题。

输出严格 JSON,不要 markdown,不要解释。""",
    generate_user_appendix="""
【知识分享专属要求】
- 全集按 hook(0-5s) / phenomenon(现象) / cause(原因) / mechanism(机制) / application(应用) 五段递进,在 storyboard 各镜 description 的剪辑提示末尾用方括号标注当前段,例:`[现象]` `[机制]`。
- storyboard 至少 5 个分镜,每个核心概念之后必须有一个 "案例镜头",description 中明确写出具体事物 / 数据 / 画面。
- 至少一个分镜是 "对比镜头",description 末尾的剪辑提示中写明 "左右分屏 / 前后对比 / 数据对比" 中的一种。
- copywriting.title_options 必须 3 个,且至少一个使用 "反直觉断言"(例: "X 其实不是 Y")。
- editing_advice.subtitle 给出 重点词高亮 + 数字放大 的明确样式建议。
- 每段结束的台词必须有一句可记忆的金句,长度不超过 18 字。
""",
    critique_focus=(
        "你是一位严格的科普内容主编,审核标准是: 是否真的让观众学到东西,而不是听了个热闹。"
        "你最反感: 堆砌术语、案例缺失、结论先行不到位、说教口吻。"
        "请挑出本方案最该被改掉的问题,直接、具体、不留情面。"
    ),
    critique_axes=[
        CritiqueAxis("结论先行", "前 5 秒是否清楚告诉观众今天能学到什么。", weight=20),
        CritiqueAxis("难度阶梯", "现象-原因-机制-应用四段是否真的递进,没有跳跃或冗余。", weight=20),
        CritiqueAxis("案例落地", "每个抽象概念后是否立刻有具体案例或类比。", weight=20),
        CritiqueAxis("对比强化", "是否有至少一处对比/反差用于强化记忆。", weight=10),
        CritiqueAxis("金句记忆点", "段落收束的金句是否短、有力、可记。", weight=10),
        CritiqueAxis("反说教语气", "是否避免了说教/课堂腔,语气是否亲和但不松散。", weight=10),
        CritiqueAxis("行动 / 思考", "结尾是否给出可执行应用或可延展思考。", weight=10),
    ],
    revision_threshold=75,
    optimize_appendix=(
        "知识类优化重点: 案例化抽象概念、删冗长定义、加对比镜头、强化结尾 takeaway;"
        "若原方案像教科书目录,必须重写为现象引入 + 案例驱动。"
    ),
    episode_appendix=(
        "若属于系列,本集必须明确说明本集相对系列总目标的进度位置(如 '系列第 X 步: ...');"
        "本集结尾的 takeaway 必须能拼回系列主线。"
    ),
)
