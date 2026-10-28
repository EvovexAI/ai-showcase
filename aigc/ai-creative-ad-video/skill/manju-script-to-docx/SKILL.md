---
name: manju-script-to-docx  
description: 把已定稿的漫剧/短剧剧本正文（Markdown，格式为「## 第N集（浪M…）」＋「场景：」＋「出场人物：」＋「\*\*角色\*\*（动作）："台词"」＋「△动作」＋「——N——集完」）一键转成排版美化、可交付的 Word（.docx）。当主编说「转成word」「出个word版」「剧本转文档」，或任何需要把剧本 md 变成 .docx 交付件时使用。走 tencent-docx 插件 beautify_only（S2→S3）链路，含门禁避坑与保真校验。ALSO use for 蓝图类内容转 Word 表格 requests（「大纲人物小传细纲 做成 word 表格」「蓝图做成表格」「带表格的 word 给我看」）——见 §七b：体例映射表、SI-01/TQ-03 两个必踩门禁的规避法（章节标题改用 p 元素承载）、交付前保真校验三条与其假红陷阱。  
agent_created: true  
version: "1.1.0"  
---

# 剧本 Markdown → Word 交付（漫剧主编专用）

## 何时用

主编已定稿剧本正文（如 `06-正文全本-E1-60.md`），要一份能发给合作方/平台看的 **.docx**。  
**铁律：内容已定稿 ⇒ 只做版式美化，绝不改写/增删一个字。**

## 一、路由（不得跳过）

1. 先加载 skill **`tencent-docs-routing`** 定路由 → 结论固定为：  
   **`tencent-docx` 插件，入口 `beautify_only`（S2 → S3）**  
   （有现成内容文档 + 无创作动词 = 美化，不是 full_pipeline）
2. 再加载 skill **`tencent-docx`** → 其 **强制**要求下一步 Read：  
   `<plugin_root>/skills/tdoc-orchestrator/SKILL.md`（`<plugin_root>` 见下）  
   ❌ 禁止跳过 orchestrator 直接调 MCP / 直接用 python-docx。

`<plugin_root>` = `/Users/xiguang/.workbuddy/plugins/cache/workbuddy-builtin/tencent-docx/<版本号>/`  
（版本号会变，用 `ls` 取最新的那一个）

## 二、Stage 0（编排层）

```bash
WS="<项目根>"
RID=$(python3 -c "import uuid;print(uuid.uuid4())")
mkdir -p "$WS/output/$RID"/{stage1,stage2/intermediate,stage3,working,trace}
python3 "$P/scripts/wb/local/resolve_output_docx_path.py" \
  --workspace "$WS" --request-id "$RID" --filename "<剧名>-E1-60.docx"
```

把返回的 `output_docx_path` / `output_docx_user_specified` 写进  
`output/<RID>/pipeline-state.yaml`（`entry_type: beautify_only`，`stage_chain: [2,3]`，`stage_1: skipped`，  
`current_stage: 2`）。  
**`stage2/intermediate/` 必须预建**，否则 S2 直接失败。

## 三、Stage 2（doc-formatter，角色切换执行）

声明 `[角色切换] 现在以 doc-formatter 身份执行 Stage 2` → 读 `<plugin_root>/agents/doc-formatter.md`。

- **genre**：剧本**不命中**任何垂类模板（合同/论文/公文/研报/纪要/年报）→ 按 §4.1 兜底  
  **`general`（主题 modern-minimal）**，走 **`html-template`**（`templates/base.html` + `prompts/base.md`）。
- **内容不手写**：60 集 900+ 句对白必须用脚本确定性生成 HTML。现成脚本模板见本 skill  
  `assets/build_html_template.py`（入参：`<输出html> <输出tokens.json>`，只改顶部 `SRC_MD` 路径即可复用）。
- 解析规则（格式固定，先 `assert` 总数）：  
  `## ` 集标题｜`场景：`｜`出场人物：`｜`**角色**（动作）："台词"`｜`△动作`｜`——（转场）——`｜`——N——集完`  
  台词引号是 **ASCII `"`（U+0022）**，分隔符是 **全角 `：`（U+FF1A）**。
- **★体例适配清单（实战：外来稿常不按上面这套写，脚本必须改这几处再跑；改完全部 6 处即可复用）**
  | #                                                                        | 改哪里         | 怎么改                                                                                                                                               |
  | ------------------------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
  | 1                                                                        | `SRC_MD`    | 指向实际正文 md                                                                                                                                         |
  | 2                                                                        | `DLG_RE`    | **三体例兼容**：`^\*{0,2}([^：:△（*]{1,12})\*{0,2}\s*(?:（([^）]*)）)?\s*[：:](.*)$`——本稿是 `角色（动作）：台词`（**无粗体、无引号**），旧版只认 `**角色**（动作）："台词"` ⇒ 会印出「对白 0 句」**假绿** |
  | 3                                                                        | `assert` 集数 | 改成实际集数（如 120）                                                                                                                                     |
  | 4                                                                        | 题头          | 多行 `> ` 要**拼成一行**（外来稿常两行 `>`）                                                                                                                     |
  | 5                                                                        | 封面文案        | 题材/副题/meta 按剧改写；meta 用 `%d` 统计                                                                                                                    |
  | 6                                                                        | `dlg` 分支    | 补**无括注**分支：`<p class="dlg"><span class="who">X</span>：台词</p>`                                                                                     |
  | **★自证**：改完先看脚本打印的 `dlg` 计数是否与 `audit.py`「对白 N 句」吻合（两条独立路径互证）；不吻合＝正则还没改对。 |             |                                                                                                                                                   |
- 产物：`stage2/formatted-<主题>.html` ＋ `stage2/design_tokens.json`（design-token 静态查表：`tokens/compiled/general.json`）

### ★ 门禁避坑（被 `html-review/scripts/review_html.py` 卡过的坑）

| 坑                              | 规避做法                                                                                                                                                                                                  |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SI-02/07/08（table 结构/badge/嵌套） | **剧本正文**不用 `<table>`（正文没有表格语义，键值信息用 `<p>` 行）；**但"表格类内容"〔大纲表/人物表/细纲字段〕必须用 `<table>`** —— 实测可行、能落成 Word 原生表格，见 §七b。规范：`<thead>` 内必须用 `<th>`（不能全 `<td>`）、`<caption>` 若用须为表格第一个子元素、**严禁表内嵌表**（内层表拿不到边框样式） |
| TQ-08（封面块必须显式 text-align）      | 封面**每个** `<h1>/<p>` 内联写 `style="text-align: center;"`；且**不要**用 `.cover`/`.cover-page` 类名                                                                                                              |
| TQ-03（标题间无正文）                  | **别插 `<h3>` 当"浪标"**（h3→h2 必罚）→ 用 `<p class="wave-title">`                                                                                                                                             |
| DT-01～04（裸值）                   | 所有 `font-size`/`margin*`/`padding*`/`font-family`/颜色 **一律 `var(--*)`**；`border: 1px solid var(--color-border)` 这种可以（只查上述几类属性 + 全属性查裸色值）                                                               |
| DT-05                          | `:root{}` 里必须有 `--fs-body`、`--color-text`、`--ff-body`                                                                                                                                                 |
| DU-04                          | divider 不连续出现                                                                                                                                                                                         |

- **跑门禁**：`python3 <plugin_root>/skills/html-review/scripts/review_html.py --html <html> --genre general`  
  → 需 `passed=true`；不通过就把 issues 回给生成脚本改**一次**，不复检（不循环）。
- 用 yaml 记 `stage_2`（`route: html` / `html_sub: template` / `output_path` 写**实际文件名**），  
  然后声明 `[Stage 2 完成]`。
- ⚠️ **S2 的 html 禁止 `present_files` / 贴正文**。

## 四、Stage 3（doc-converter，角色切换执行）

声明 `[角色切换] 现在以 doc-converter 身份执行 Stage 3` → 读 `<plugin_root>/agents/doc-converter.md`  
→ 加载 `<plugin_root>/skills/html-to-docx/SKILL.md`。

```bash
bash "$P/scripts/wb/local/setup-html-to-docx.sh"      # 幂等，已就绪秒退（首次需外网）
PY="${HTML_TO_DOCX_VENV:-$HOME/.venv-html-to-docx}/bin/python"
cd "$P/skills/html-to-docx/scripts"
"$PY" -m html_to_docx convert "<html>" -o "<output_docx_path>" \
  --page-size A4 --orientation portrait \
  --margin-top 2.54 --margin-bottom 2.54 --margin-left 3.17 --margin-right 3.17
```

`success:true` → **🔒 立即 `present_files` 打开 .docx**（硬约束，无例外）  
→ 再写 `stage_3`（`executor: doc-converter` / `skill_used: ["html-to-docx"]` /  
`present_files_opened: true` / `status: completed`）→ 写 `consistency_check` → 声明 `[Stage 3 转换完成]`。  
**S3 即链路终点**，本 skill 调用结束；后续编辑属**下一轮**（回 `tencent-docs-routing`）。

## 五、交付前保真校验（必做）

```python
x = zipfile.ZipFile(docx).read('word/document.xml').decode('utf-8')
txt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x))
# 源每条内容行（剥掉 ** 与 △）都应 in txt；只允许 "## 集标题" 因其带 # 未命中
```

docx 汉字数 ≈ 源汉字数 + 封面元信息字数；对不上就是掉内容，必须回查。

## 六、注意

- `present_files` 只呈现 **.docx**（唯一最终交付）；md/html 是中间态。
- 只新增 `output/<RID>/` 目录，**不要**在项目根另起副本（主编对目录零漂移零容忍）。

## 七、轻量「阅读版」HTML（**即时过目用**，非交付件）

```bash
python3 assets/render_script_html.py <正文.md> <输出.html>
```

把正文体例（`## 第N集（浪M·标题）`／`场景：`↔`出场人物：`／`**角色**（动作）："台词"`／`△…`／`**【本集卡点】**`／`——第N集完——`）  
渲染成**浅／深色自适应**的 HTML。**HTML 会在预览面板自动打开**（docx 只会落成卡片）  
⇒ 主编说「**剧本呢**」「我看下改完的」这类**即时阅读**请求，用它；说「**转成 word**」才走本 skill 的 docx 主链路。

**★三个已踩的坑**：

1. **对白引号两种都要吃**（`["“]…["”]`）——正文里混入全角弯引号的行，否则会**掉成普通段落**。  
   （实测《女猎户》E5／E6 各 1 行；同族：`dlgcheck.DQ` 只认直角 ⇒ 核销表**少抽 2 句**，`langcheck.DLG_IN` 已容忍两式。）
2. **★标记要放进 `<h2>` 内部**，否则 `margin-left:auto` 无法右浮，标签会掉到下一行。
3. **元信息行要剥掉 Markdown**（`**`／反引号），否则页面上直接露出星号。

**渲染后必自检**：`grep -c 'class="dlg"' <html>` 应**等于 ① 门禁的对白数**；`class="other"` 应为 **0**  
（**非 0 ⇒ 有行没被识别**，先查参数化体例再交付）。

## 七b、★蓝图类内容 → 表格化 Word（大纲 / 人物小传 / 细纲 · 2026-09-17 实战补）

> **触发**：主编说「**把大纲 人物小传 细纲 这些都做到有个 word 表格上**」「蓝图做成表格」「出个带表格的 word 给我看」。  
> **入口**：`beautify_only`（S2→S3）。**内容源 = 蓝图合订本 md**（`build_heben.py` 的产物，如  
> `10-蓝皮书合订本-大纲·小传·细纲E1-120.md`）⇒ 一份就够，别去拼 `03/04/05-08` 单个源件。  
> **不是** `full_pipeline`：无创作动词，只是"要个新形态"，属抽象排版 ⇒ **零改写，只做体例映射**。

**体例映射表**（md 蓝图 → HTML）：

| md 源                                        | HTML 产物                                                | 说明                                      |
| ------------------------------------------- | ------------------------------------------------------ | --------------------------------------- |
| 管道表 `\| a \| b \|`                          | `<table><thead><tr><th>` + `<tbody><tr><td>`           | 第 2 行 `\|---\|` 是分隔行，**丢弃**；表头行用 `<th>` |
| 每集字段块（集头行 `**E0NN** ｜…` ＋ 若干 `- **字段**：内容`） | `<p class="ep-head">` ＋ **每集一张两列表**（项 | 内容）            | 字段的 2 空格缩进**续行**要并入上一字段内容               |
| `#` / `##` / `###` / `####`                 | `<p class="h2">` / `<p class="h3">` / `<p class="h4">` | **★不要用 hN，见下面两个坑**                      |
| `> 引用`                                      | `<p class="note">`（逐行独立成段）                             | **不要用 callout**：DU-01 上限 5 个            |
| `---`                                       | `<div data-component="divider">`                       | 连续 divider 必须**后处理去重**（DU-04），首尾也去掉     |
| `- ` / `1. `                                | `<ul><li>` / `<ol><li>`                                | SI-03：ul 内只能有 li                        |

**★两个必踩的门禁（源文档结构决定的，不是偶然）**：

1. **SI-01 标题跳级** —— 蓝图里普遍存在 `# 第一部分` 直连 `### 一、`（跳到 h3）。
2. **TQ-03 相邻标题无正文** —— 蓝图里普遍存在"部分标题紧跟子标题"（`# 第二部分` → `### 表一`）、  
   以及自证区 `### 05 · …` → `### 本册自证` 这类 **h3→h3 无正文**。  
   实测《女猎户》：跳级 **5 处**、相邻标题 **11 处** ⇒ TQ 罚分直接把 `passed` 打到 false。

⇒ **统一解法（零改写、不增一个字）**：**章节标题一律用 `<p class="h2|h3|h4">` 承载，不用 `hN`**；  
真 heading 只留 **封面 `<h1>` ×1** ＋ **部分级 `<h2>` ×N（N ≤ 10，避免 TQ-05）**。  
`<p>` 属于 `CONTENT_TAGS` ⇒ 既能"当过标题"，又让 `seen_content` 恒为 True，两条门禁同时不触发。  
代价＝Word 导航窗格只有那 N 个 h2（通读场景可接受）。

**★交付前保真校验（三条，缺一不可）**：

1. **结构**：解 docx 的 `word/document.xml`，`<w:tbl>` 个数 **必须等于** 源表格数 ＋ 集数。
2. **逐条比对**：源**每条**内容（表格单元格 / 集字段名 / 集字段内容 / 普通行）去空白后应 `in` docx 全文本 ⇒ **未命中 0**。
3. **字数闭环**：`HTML 正文汉字数 == docx 汉字数`；再 `− 新增部分（封面 ＋ 每张集表的表头「项/内容」）` ⇒ **必须等于源汉字数，差 0**。  
   （只报"总数差不多"＝假绿；必须能算到 0。）

**★校验器自身的两个假红（先证伪自己的比对器，再怀疑产物）**：

- 忘了剥 **md 行首标记**（`#` / `>` / `- ` / `##`）⇒ 源行当然"找不到"（实测误报 1,496 条）。
- 忘了**解码 XML 实体**（`&amp;` / `&gt;`）、忘了**集字段在 docx 里是两个单元格** ⇒ 又误报 1,122 条。  
  ⇒ 口诀：**"未命中 N 条"先查我的比对器，别急着改正文。**

**★另注（`html_to_docx` 的空白注入 · 2026-09-17 实测结论）**：转换器内部调用 `text_splitter.split_cjk_latin`  
（**中英混排规范**，硬编码、无开关）⇒ 会在两处**插入空格**：  
① **inline 元素边界**（`<strong>`／`<b>`／`<span>` 前后，如 `；<strong>枪托` ⇒ `； 枪托`）；  
② **全角引号前后**（纯文本里 `“铁山”` ⇒ `“ 铁山 ”`）。  
**实测：换标签躲不掉**（strong／b／span 三种都一样）；`_cell_richtext.py` 的"保留 strong 且不加空格"路径  
**只服务 data_card／callout**，普通 `<td>` 不吃它。**结论：属转换器既定行为、不是内容错误，不要去改共享库。**  
⇒ **对下游的两条影响**：① 保真比对**必须先去空白再比**，否则满屏假红；  
② 交付说明里如实列出，不当成缺陷隐藏。

**参考实现**：`实战/52-…/output/<RID>/working/build_blueprint_html.py`（确定性脚本，非手写 DOM；  
含块解析状态机、divider 去重、集字段续行合并、末尾自检）。**复用前先把硬编码的 SRC/OUT 参数化。**
