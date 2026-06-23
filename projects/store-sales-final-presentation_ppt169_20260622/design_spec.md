# store-sales-final-presentation - Design Spec

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | store-sales-final-presentation |
| **Canvas Format** | PPT 16:9 (1280×720) |
| **Page Count** | 14 |
| **Design Style** | instructional + data-journalism |
| **Target Audience** | 课程老师与同学 |
| **Use Case** | 期末大作业答辩汇报 |
| **Content Strategy** | balanced default |
| **Created Date** | 2026-06-22 |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280×720 |
| **viewBox** | `0 0 1280 720` |
| **Margins** | left/right 52px, top 42px, bottom 36px |
| **Content Area** | 1176×642 |

---

## III. Visual Theme

### Theme Style

- **Mode**: instructional
- **Visual style**: data-journalism
- **Theme**: Light theme
- **Tone**: 冷静、克制、数据导向、课程答辩风格

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#F7F8FA` | Page background |
| **Secondary bg** | `#FFFFFF` | Card background |
| **Primary** | `#163B66` | Titles, rules, key structure |
| **Accent** | `#2F80ED` | Highlights, metrics, key data |
| **Secondary accent** | `#27AE60` | Positive comparison, supporting emphasis |
| **Body text** | `#1F2937` | Main body text |
| **Secondary text** | `#6B7280` | Captions, annotations |
| **Tertiary text** | `#9CA3AF` | Footnotes, page numbers |
| **Border/divider** | `#D9E1EA` | Card borders and separators |
| **Success** | `#219653` | Positive indicators |
| **Warning** | `#D64545` | Risks / regression marks |
| **Surface** | `#EEF2F7` | Lifted panels |
| **Grid** | `#E6ECF2` | Hairline guides and chart grid |

### Gradient Scheme

```xml
<linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">
  <stop offset="0%" stop-color="#163B66"/>
  <stop offset="100%" stop-color="#2F80ED"/>
</linearGradient>
```

---

## IV. Typography System

### Font Plan

**Typography direction**: serif headline + CJK sans body + monospace-flavored numeric annotations

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | `"Microsoft YaHei"` | `Georgia` | `serif` |
| **Body** | `"Microsoft YaHei"` | `Arial` | `sans-serif` |
| **Emphasis** | `"Microsoft YaHei"` | `Georgia` | `serif` |
| **Code** | — | `Consolas, "Courier New"` | `monospace` |

- Title: `Georgia, "Microsoft YaHei", serif`
- Body: `"Microsoft YaHei", Arial, sans-serif`
- Emphasis: `Georgia, "Microsoft YaHei", serif`
- Code: `Consolas, "Courier New", monospace`

### Font Size Hierarchy

**Baseline**: Body font size = 20px

| Purpose | Ratio to body | Example @ body=20 | Weight |
| ------- | ------------- | ----------------- | ------ |
| Cover title | 2.8-4x | 56-80px | Bold |
| Chapter / section opener | 2-2.5x | 40-50px | Bold |
| Page title | 1.5-1.9x | 30-38px | Bold |
| Hero number | 2-3x | 40-60px | Bold |
| Subtitle | 1.2-1.5x | 24-30px | SemiBold |
| **Body content** | **1x** | **20px** | Regular |
| Annotation / caption | 0.7-0.8x | 14-16px | Regular |
| Page number / footnote | 0.55-0.65x | 11-13px | Regular |

---

## V. Layout Principles

### Page Structure

- **Header area**: 80-100px, contains title and one editorial rule
- **Content area**: 520-560px, accommodates charts, cards, explanatory blocks
- **Footer area**: 28-36px, page number and source line

### Layout Pattern Library

| Pattern | Suitable Scenarios |
| ------- | ----------------- |
| **Single column centered** | Cover, result page, closing page |
| **Asymmetric split (3:7 / 2:8)** | Visual-led architecture and narrative explainer pages |
| **Top-bottom split** | Architecture or process pages with top summary and bottom detail |
| **Three/four column cards** | Dataset and experiment summary |
| **Matrix grid (2×2)** | Core findings and parallel conclusions |
| **Z-pattern / waterfall** | Version evolution page |
| **Negative-space-driven** | Best score and closing takeaway |

### Spacing Specification

| Element | Recommended Range | Current Project |
| ------- | ---------------- | --------------- |
| Safe margin from canvas edge | 40-60px | 52px |
| Content block gap | 24-40px | 28px |
| Icon-text gap | 8-16px | 12px |
| Card gap | 20-32px | 24px |
| Card padding | 20-32px | 22px |
| Card border radius | 8-16px | 12px |

---

## VI. Icon Usage Specification

### Source

- **Built-in icon library**: `tabler-outline`
- **Usage method**: SVG placeholder `<use data-icon="tabler-outline/name" .../>`

### Recommended Icon List

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| 项目总览 | `tabler-outline/presentation-analytics` | P01 |
| 数据表征 | `tabler-outline/database` | P02 |
| 分数/结果 | `tabler-outline/chart-bar` | P11 |
| 时间演进 | `tabler-outline/timeline` | P04 |
| 目标/指标 | `tabler-outline/target` | P01, P11 |
| 思路/启发 | `tabler-outline/bulb` | P08, P10, P13 |
| 版本分叉 | `tabler-outline/git-branch` | P04 |
| 集成结构 | `tabler-outline/stack-2` | P05, P07 |
| 编程语言与实现 | `tabler-outline/code` | P07, P09 |
| 算力与训练 | `tabler-outline/cpu` | P07 |
| 工程环境 | `tabler-outline/device-laptop` | P09 |
| 数据结构与关系 | `tabler-outline/schema` | P09 |
| 解决策略 | `tabler-outline/settings-2` | P10 |

---

## VII. Visualization Reference List

Catalog read: 71 templates

| Page | Template | Path | Summary-quote (verbatim from `charts_index.json`) | Usage |
| ---- | -------- | ---- | ------------------------------------------------- | ----- |
| P04 | timeline | `templates/charts/timeline.svg` | "Pick for 3-8 milestone events on a horizontal time axis (no duration). Skip for tasks with start/end ranges (use gantt_chart) or vertical layout (use roadmap_vertical)." | 展示版本从 version1 到 version7.4 的建模演进主线 |
| P05 | module_composition | `templates/charts/module_composition.svg` | "Pick for one parent container wrapping 3-N child module cards, each = title + 2-3 bullets — fits 'Feature X contains 3 parts, each with its own description'. Skip if source has only labels without descriptions (use numbered_steps or icon_grid)." | 展示主线方案由 target series、covariates 与 ensemble 三层组成 |
| P07 | labeled_card | `templates/charts/labeled_card.svg` | "Pick for 3-4 parallel aspects of one subject with per-aspect titles + short body (self-introduction, four-pillar overview, capability quadrant). Skip for plain feature lists (use icon_grid), sequential steps (use numbered_steps), or strategic quadrants (use quadrant_text_bullets / matrix_2x2)." | 总结 4 个最关键实验结论 |

**Runners-up considered**

- `vertical_list` | rejected for P07: 四个结论彼此平行且需要并列对比，卡片式比单列更直观
- `agenda_list` | rejected for P04: 版本演进是时间轴，不是目录条目
- `layered_architecture` | rejected for P05: 当前内容强调总框架包含多个子模块，而非严格分层堆栈

---

## VIII. Image Resource List

本 deck 不使用外部图片与 AI 生成图片，全部页面以原生 SVG、图标、图表和排版构成。

---

## IX. Content Outline

### Part 1: 项目建立背景

#### Slide 01 - 封面

- **Cover impact**: 用 `0.38005` 这个最佳分数作为钩子，配合“从基线到集成”的标题关系，形成数据驱动的期末答辩封面
- **Layout**: 单列居中 + 顶部细规则线 + 中央大数字 + 下方项目信息
- **Title**: Store Sales - Time Series Forecasting
- **Subtitle**: 从统计基线到多模型时间序列集成的课程项目迭代
- **Info**: Kaggle 时间序列预测期末大作业 / 2026-06-22

#### Slide 02 - 项目任务与数据

- **Layout**: 左侧任务说明，右侧数据概况卡片
- **Title**: 项目任务与数据输入
- **Core message**: 这是一个以 `date + store_nbr + family` 为粒度、目标明确且协变量丰富的销量预测任务。
- **Content**:
  - 任务目标是结合销量、促销、交易量、油价和节假日，预测未来 16 天销量，并以 RMSLE 作为评价指标。
  - 训练与测试主表之外，项目还引入了 stores、transactions、oil、holidays_events 四类辅助数据。
  - 关键字段包括 `sales`、`onpromotion`、`transactions`、`family` 和 `store_nbr`。

### Part 2: 建模路线

#### Slide 03 - 整体建模思路

- **Layout**: 上方五段式流程带 + 下方解释块
- **Title**: 整体建模路线
- **Core message**: 项目采用“先建立基线，再逐步修正问题并做单因子验证”的迭代策略，而不是一次性追求复杂模型。
- **Content**:
  - 先从可快速跑通的线性回归和移动平均基线起步，建立比较基准。
  - 再引入时间特征、节假日、油价等外部信息，并修复验证与预测不一致导致的信息泄漏。
  - 最终转向 Darts 多序列集成，并通过单因子实验确认哪些因子真的带来提升。

#### Slide 04 - 版本演进路径

- **Layout**: 水平时间轴 + 版本节点标注
- **Title**: 版本演进路径
- **Core message**: 仓库中的版本不是简单堆叠，而是围绕“模型复杂度提升”和“实验问题定位”两条线推进。
- **Visualization**: timeline
- **Content**:
  - `version1-3`：建立基线并验证外部协变量价值。
  - `version4-5`：从树模型出发，修复多步预测泄漏问题。
  - `version6-7.4`：进入 Darts + LightGBM + XGBoost 主线，并围绕单因子持续优化。

### Part 3: 主线方案

#### Slide 05 - 主线模型结构

- **Layout**: 模块总览 + 底部三组说明卡
- **Title**: 主线模型结构
- **Core message**: 最终高分方案的核心不是单一模型，而是由多序列目标、协变量体系和多分支集成共同构成。
- **Visualization**: module_composition
- **Content**:
  - 顶层任务是按 `family` 拆分后的销量时间序列预测。
  - 中间层由 static covariates、past covariates 和 future covariates 共同支撑。
  - 底层建模由 4 组 LightGBMModel、4 组 XGBModel、两轮平均和最终加权融合组成。

#### Slide 06 - 数据预处理与特征工程

- **Layout**: 左侧预处理步骤，右侧特征类型
- **Title**: 数据预处理与特征工程
- **Core message**: 主线方案之所以稳定，关键在于先把训练面板补齐，再对油价、交易量和节假日做统一清洗与对齐。
- **Content**:
  - 训练面板补齐缺失日期与 `store-family` 组合，`sales` 和 `onpromotion` 缺失补零。
  - 油价按全日期插值，交易量按门店序列插值，节假日剔除 transferred 并筛选有效项。
  - 最终构造了时间索引、周内位置、年内位置、促销、交易量和核心节假日等特征。

### Part 4: 技术说明

#### Slide 07 - 项目中的主流技术栈

- **Layout**: 四卡技术总览 + 底部补充说明
- **Title**: 项目中的主流技术栈
- **Core message**: 这个项目虽然是课程作业，但技术选型并不是“学生版简化方案”，而是与主流时间序列建模实践一致的一整套 Python 数据科学技术栈。
- **Content**:
  - Python：作为整体实验与建模语言，负责把数据处理、训练、验证、预测和提交整合在一个可迭代环境里。
  - pandas / numpy：负责多表清洗、时间字段转换、缺失值处理、插值与数值运算，是整个项目的数据底座。
  - LightGBM / XGBoost：作为主力树模型，承担多组 lag 分支训练与最终融合，是成绩提升的核心建模工具。
  - Darts / scikit-learn：负责统一时间序列接口、协变量组织与预处理流程，让主线方案具备结构化表达能力。

#### Slide 08 - 为什么选择这些技术

- **Layout**: 左侧技术选择原则，右侧技术对应理由
- **Title**: 为什么选择这些技术
- **Core message**: 这些技术的选择逻辑，不是“哪个名字更高级”，而是“哪个技术最适合这个任务的数据结构、验证方式和实验目标”。
- **Content**:
  - 选择 Python 和 pandas / numpy，是因为这个项目本质上是多表融合问题，先要把数据整明白，才能谈模型。
  - 选择 LightGBM / XGBoost，是因为这类树模型对表格特征、类别信息和 lag 设计都很友好，适合做强基线和主力分支。
  - 选择 Darts，是因为主线方案已经不只是“喂一张表给模型”，而是需要显式管理 target series、past covariates 和 future covariates。
  - 选择 scikit-learn 相关组件，是因为它能稳定承担编码、缩放和流水线这些通用环节，让实验更加规范。

#### Slide 09 - 这些技术在项目里的具体用法

- **Layout**: 上方代码模块映射，下方按技术分工展开
- **Title**: 这些技术在项目里的具体用法
- **Core message**: 技术栈在这个项目里不是抽象名词，而是可以直接对应到代码文件、函数职责和实验环节上的。
- **Content**:
  - pandas / numpy：在 `preprocess_train`、`preprocess_oil`、`preprocess_transactions` 和 `merge_all_data` 中负责清洗、补齐和合并。
  - LightGBM：在 `version5/lgbm_recursive.py` 中承担无泄漏递推预测，在 `version6+` 中作为 Darts 的 LightGBMModel 分支。
  - XGBoost：在 `version6+` 中承担与 LightGBM 并行的另一组分支，并参与最终加权融合。
  - Darts：在 `get_target_series`、`get_covariates` 和 `Trainer` 中统一管理多序列、协变量和集成预测流程。

#### Slide 10 - 项目难点与解决策略

- **Layout**: 左侧难点，右侧对应解决策略
- **Title**: 项目难点与解决策略
- **Core message**: 这个项目真正难的地方，不是“把模型跑起来”，而是把时间序列任务里最容易出错的几个环节处理正确。
- **Content**:
  - 难点一：多表、多粒度、多时间字段对齐复杂。解决策略是先补齐统一面板，再逐步合并 oil、transactions 和 holidays。
  - 难点二：树模型线下验证容易与真实预测流程不一致。解决策略是通过递推预测和时间切分，修复多步预测泄漏问题。
  - 难点三：特征很多，但并不是越多越好。解决策略是坚持单因子实验，逐个验证 lag、节假日和 transactions 的边际贡献。
  - 难点四：主线方案已经进入多模型、多序列阶段。解决策略是用 Darts 统一接口，再用版本化脚本保持实验可追踪。

### Part 5: 实验结论

#### Slide 11 - 关键实验结论

- **Layout**: 2×2 结论卡片
- **Title**: 关键实验结论
- **Core message**: 最终成绩提升来自少数被验证有效的关键因子，而不是盲目增加特征。
- **Visualization**: labeled_card
- **Content**:
  - 融合权重：`0.40 / 0.60` 附近优于更偏向 LightGBM 的配置。
  - 长周期信息：`lag 730` 与 `lag 365` 删除后均明显退化。
  - 节假日筛选：保留 4 个核心节日优于保留更大集合。
  - 交易量协变量：移除 `transactions` 会使成绩退步。

#### Slide 12 - 最终结果

- **Layout**: 单焦点大数字 + 两侧短说明
- **Title**: 最终结果与最佳版本
- **Core message**: 当前仓库最优公开成绩来自 `version7.3`，说明节假日去噪与集成结构稳定结合后取得了最好的效果。
- **Content**:
  - 最佳版本是 `version7.3`，方案为 `Darts + LightGBMModel + XGBModel` 多序列加权融合。
  - 最佳 Kaggle Public Score 为 `0.38005`。
  - `version7.4` 去掉 `transactions` 后回退到 `0.38110`，进一步验证了过去协变量的重要性。

### Part 6: 总结与展望

#### Slide 13 - 项目收获与反思

- **Layout**: 三列并行总结
- **Title**: 项目收获与反思
- **Core message**: 这次作业的价值不仅是分数本身，更在于形成了一个相对规范的实验方法。
- **Content**:
  - 基线先行：简单模型能快速验证方向是否正确。
  - 过程一致：时间序列任务必须保证验证方式与真实预测流程一致。
  - 实验纪律：每次只改一个因子，才能真正知道提升来自哪里。

#### Slide 14 - 后续工作

- **Closing impact**: 用“从课程作业走向可复现实验框架”作为最后一句，配合留白式收束布局，强调这个项目后续还能继续深化
- **Layout**: 左上标题 + 中部四点展望 + 右下收束句
- **Title**: 后续工作
- **Core message**: 当前结果已经说明主线可行，但后续提升空间主要在实验精化和工程整理，而不是重复试错。
- **Content**:
  - 继续筛选最优节假日最小子集。
  - 测试其他协变量与 `lags` 分支的边际贡献。
  - 微调 LightGBM 与 XGBoost 参数。
  - 将脚本式实验整理成更规范、可复现的项目结构。

---

## X. Speaker Notes Requirements

- **Filename**: match SVG name, such as `01_封面.md`
- **Content**: 每页 2-5 句自然讲稿，包含过渡，不写舞台提示

---

## XI. Technical Constraints Reminder

### SVG Generation Must Follow:

1. viewBox: `0 0 1280 720`
2. Background uses `<rect>` elements
3. Text wrapping uses `<tspan>`
4. Transparency uses `fill-opacity` / `stroke-opacity`
5. Forbidden: `mask`, `<style>`, `class`, `<foreignObject>`
6. Forbidden: `textPath`, `animate*`, `script`
7. Use raw Unicode text and XML-safe escaping
8. Use top-level semantic `<g id="...">` groups for editable structure

### PPT Compatibility Rules:

- No `<g opacity>`
- Icons use `<use data-icon="tabler-outline/name"...>`
- Colors remain inside the locked palette
- Export follows `total_md_split.py` → `finalize_svg.py` → `svg_to_pptx.py`
