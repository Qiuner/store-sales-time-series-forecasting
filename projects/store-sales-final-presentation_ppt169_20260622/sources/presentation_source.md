# Store Sales - Time Series Forecasting 期末大作业介绍

## 1. 项目背景

- 项目名称：Store Sales - Time Series Forecasting
- 项目类型：Kaggle 时间序列预测竞赛课程大作业
- 任务目标：基于历史销量、促销、交易量、油价和节假日等信息，预测未来 16 天各门店各商品大类销量
- 预测粒度：date + store_nbr + family
- 评价指标：RMSLE

## 2. 数据概况

- 训练集：train.csv
- 测试集：test.csv
- 门店信息：stores.csv
- 交易量：transactions.csv
- 油价：oil.csv
- 节假日与事件：holidays_events.csv
- 提交模板：sample_submission.csv

核心字段说明：

- sales：目标变量，表示销量
- onpromotion：促销商品数量
- transactions：门店每日交易笔数
- family：商品大类
- store_nbr：门店编号

## 3. 项目整体思路

本项目不是单次建模，而是按版本不断迭代优化，整体路线如下：

1. 从简单基线模型开始，快速建立可运行方案
2. 逐步加入时间特征、促销信息、外部协变量
3. 修复验证与预测不一致导致的信息泄漏问题
4. 过渡到多模型、多序列集成方案
5. 通过单因子实验逐步确认哪些因子真正有效

## 4. 版本演进路径

### version1

- 模型：LinearRegression
- 作用：建立最基础回归基线
- 特点：简单、快速、可跑通

### version2

- 模型：分层移动平均
- 作用：构造强统计基线
- 公榜分数：0.47815

### version3

- 模型：移动平均 + 节假日/油价 + Ridge 校准
- 作用：验证外部协变量是否有效
- 公榜分数：0.44476

### version4

- 模型：LightGBM + lag/rolling 特征
- 作用：从统计方法升级到树模型
- 问题：存在多步预测泄漏，线下乐观、线上失真

### version5

- 模型：无泄漏递推版 LightGBM
- 作用：修复 version4 的验证问题
- 特点：逻辑更正确，但效果不是主线最优

### version6 - version7.4

- 模型：Darts + LightGBMModel + XGBModel 多序列集成
- 作用：构建主线高分方案
- 核心做法：按 family 拆分多序列，引入静态协变量、过去协变量、未来协变量，并做多组 lag 集成与模型融合

## 5. 数据预处理与特征工程

主线版本主要完成了以下处理：

- 补齐训练面板缺失日期与 store-family 组合
- sales 与 onpromotion 缺失值补零
- 油价按日期补齐并线性插值
- transactions 按门店插值补齐
- 节假日文本清洗、去除 transferred 假日
- 合并门店、油价、交易量、节假日等信息
- 构造 day、month、day_of_week、day_of_year、week_of_year、date_index 等时间特征

## 6. 主线模型设计

当前主线来自 version6 之后的 Darts 集成路线：

- target series：按 family 分组的门店销量时间序列
- static covariates：city、state、type、cluster
- past covariates：transactions
- future covariates：oil、onpromotion、日期因子、work_day、节假日
- 模型结构：
  - 4 组 LightGBMModel，不同 lags
  - 4 组 XGBModel，不同 lags
  - 每个模型内部做两轮预测平均
  - 最后跨模型加权融合

## 7. 关键实验结论

已经验证有效的核心因子包括：

- 最终融合权重会影响分数，最佳区间在 LightGBM/XGBoost = 0.40 / 0.60 附近
- lag 730 提供有效长周期信息，不能删除
- lag 365 提供有效年周期信息，不能删除
- 节假日特征存在噪声，只保留核心节日更有效
- transactions 是有效的过去协变量，移除后分数退化

## 8. 最终结果

- 当前最佳版本：version7.3
- 方案：Darts + LightGBMModel + XGBModel 多序列加权融合
- 关键优化：仅保留 4 个核心节假日
- 最佳 Kaggle Public Score：0.38005

## 9. 项目收获与反思

- 简单基线是必要的，可以帮助快速判断后续改进是否有效
- 时间序列任务中，验证方式必须与真实预测流程一致，避免信息泄漏
- 外部协变量并非越多越好，需要通过单因子实验识别噪声
- 多模型融合和多尺度 lag 设计能显著提升效果
- 实验记录、版本管理和结论沉淀，对课程项目与竞赛项目都很重要

## 10. 后续可优化方向

- 进一步筛选最优节假日最小子集
- 测试其他协变量组合
- 继续分析不同 lag 分支的边际贡献
- 微调 LightGBM 与 XGBoost 参数
- 将当前脚本式实验整理成更规范的可复现实验框架
