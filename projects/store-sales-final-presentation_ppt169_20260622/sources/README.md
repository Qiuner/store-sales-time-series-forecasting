# Store Sales - Time Series Forecasting

这个仓库记录了我在 Kaggle `Store Sales - Time Series Forecasting` 比赛中的多版建模尝试。

## Models Overview

当前仓库一共出现了 `5` 种预测方案，其中真正的模型类型有 `4` 种，另有 `1` 种纯统计基线。

| 版本 | 使用的预测方案 / 模型 |
| --- | --- |
| `version1` | `LinearRegression` |
| `version2` | 分层移动平均基线 |
| `version3` | 分层移动平均基线 + 岭回归校准 |
| `version4` | `LightGBM` |
| `version5` | `LightGBM`（无泄漏递推预测） |
| `version6` | `Darts + LightGBMModel + XGBModel` 多序列集成 |
| `version6.1` | `Darts + LightGBMModel + XGBModel` 多序列加权融合 |
| `version6.2` | `Darts + LightGBMModel + XGBModel` 多序列加权融合 |
| `version6.3` | `Darts + LightGBMModel + XGBModel` 多序列加权融合 |
| `version6.4` | `Darts + LightGBMModel + XGBModel` 多序列加权融合 |
| `version6.5` | `Darts + LightGBMModel + XGBModel` 多序列加权融合 |
| `version7.1` | `Darts + LightGBMModel + XGBModel` 多序列加权融合（移除 `lag=730` 分支） |
| `version7.2` | `Darts + LightGBMModel + XGBModel` 多序列加权融合（移除 `lag=365` 分支） |
| `version7.3` | `Darts + LightGBMModel + XGBModel` 多序列加权融合（只保留核心节假日） |
| `version7.4` | `Darts + LightGBMModel + XGBModel` 多序列加权融合（移除 `transactions`） |

按独立模型类型看，当前仓库用到的是：

- `LinearRegression`
- 岭回归 `Ridge`
- `LightGBM`
- `XGBoost`
- 分层移动平均基线（非机器学习模型）

## Data Cleaning Overview

当前各版本都做了一定程度的数据清洗，但强度差异很大。越往后的主线版本，清洗和缺失处理越完整。

| 版本 | 是否做数据清洗 | 主要清洗内容 |
| --- | --- | --- |
| `version1` | 少量 | `date` 转时间格式，`family` 转分类编码，没有专门缺失值处理 |
| `version2` | 少量 | `date` 转时间格式，补 `dayofweek`，主要依赖分层均值 `fillna` 兜底 |
| `version3` | 中等 | 油价 `ffill/bfill`，节假日映射到 `store-date` 粒度，节假日缺失补 `0`，油价平滑特征补齐 |
| `version4` | 中等 | 训练测试拼接成统一面板，构造 `lag/rolling` 后对数值缺失统一填 `-1` |
| `version5` | 中等 | 时间字段标准化，递推特征缺失统一填 `-1`，按 `store-family` 排序维护历史缓存 |
| `version6` | 较强 | 补齐训练面板缺失日期与组合，`sales/onpromotion` 缺失补 `0`，油价全日期插值，`transactions` 按门店插值，清洗节假日文本并去掉 transferred 假日，合并后节假日缺失补 `0` |
| `version6.1` ~ `version7.4` | 与 `version6` 一致 | 这些版本都复用 `version6/darts_ensemble.py` 的同一套清洗流程，只改单因子实验项 |

如果只看当前主线方案，那么实际生效的数据清洗主要集中在 [version6/darts_ensemble.py](D:/Code/store-sales-time-series-forecasting/version6/darts_ensemble.py) 里的这几步：

- `preprocess_train`: 补齐缺失日期和 `store_nbr + family` 面板，`sales/onpromotion` 缺失补 `0`
- `preprocess_oil`: 补齐油价日期并做线性插值
- `preprocess_transactions`: 合并销量辅助补齐交易量，再按门店插值
- `process_holidays`: 清洗节假日描述、去掉 transferred 假日、筛选保留节日
- `merge_all_data`: 合并全表后补节假日缺失，构造时间索引和类别标签

## Versions

| 版本 | 核心方案 | Kaggle public score | 是否推荐继续 |
| --- | --- | --- | --- |
| `version1` | 线性回归基线 | 未提交 | 否 |
| `version2` | 分层移动平均 | `0.47815` | 否 |
| `version3` | 移动平均 + 节假日/油价/岭回归校准 | `0.44476` | 否 |
| `version4` | `LightGBM + lag/rolling` | 线上失真 | 否 |
| `version5` | 无泄漏递推 `LightGBM` | 未作为主线提交 | 否 |
| `version6` | `Darts + LightGBM/XGBoost` 多序列集成 | `0.38022` | 是 |
| `version6.1` | `version6` 的 `0.6 / 0.4` 加权融合 | `0.38041` | 否 |
| `version6.2` | `version6` 的 `0.45 / 0.55` 加权融合 | `0.38017` | 是 |
| `version6.3` | `version6.2` 的 `0.40 / 0.60` 单因子实验 | `0.38015` | 是 |
| `version6.4` | `version6.3` 的 `0.35 / 0.65` 单因子实验 | `0.38016` | 否 |
| `version6.5` | `version6.3` 的 `0.42 / 0.58` 收尾微调实验 | `0.38016` | 否 |
| `version7.1` | 去掉 `730` 超长滞后的单因子实验 | `0.38138` | 否 |
| `version7.2` | 去掉 `365` 年周期滞后的单因子实验 | `0.38074` | 否 |
| `version7.3` | 只保留核心节假日的单因子实验 | `0.38005` | 是 |
| `version7.4` | 去掉 `transactions` 过去协变量的单因子实验 | `0.38110` | 否 |

### `version1`

- 核心方案: `LinearRegression`
- 主要做法: 使用 `year/month/day/dayofweek + store_nbr + family_code + onpromotion` 直接回归 `sales`
- 目的: 建一个最基础、最容易跑通的线性基线
- 特点: 实现简单、运行很快，但对时间序列的季节性和长尾销量建模能力弱

### `version2`

- 核心方案: 分层移动平均基线
- 主要做法: 按 `store_nbr + family + dayofweek` 统计最近 `14/28/56` 天均值，并用 `onpromotion` 做轻量修正
- 目的: 用纯 `pandas`/`numpy` 做一个不依赖复杂模型的强基线
- Kaggle public score: `0.47815`
- 特点: 很稳、很快、可解释性强

### `version3`

- 核心方案: `version2 + 节假日/油价/岭回归校准`
- 主要做法: 在移动平均基线之上加入 `holidays_events`、`oil` 和门店区域映射，再用轻量岭回归做校准
- 目的: 验证外部协变量是否能直接带来收益
- Kaggle public score: `0.44476`
- 特点: 比纯移动平均更强，但外部特征处理较粗，提升有限

### `version4`

- 核心方案: `LightGBM + lag/rolling` 特征
- 主要做法: 构造 `lag_7/14/28`、滚动均值/标准差、日期特征和促销特征，在 `log1p(sales)` 上训练 `LightGBM`
- 目的: 从统计基线升级到表格树模型
- 已知问题: 验证方式存在多步预测泄漏，线下结果过于乐观，线上提交失真

### `version5`

- 核心方案: 无泄漏递推版 `LightGBM`
- 主要做法: 改成未来 16 天逐日滚动预测，每一步只使用历史和前一步预测值生成特征
- 目的: 修复 `version4` 的验证和提交不一致问题
- 特点: 逻辑更正确，但当前效果不如 `version6` 路线

### `version6`

- 核心方案: `Darts` 多序列集成
- 主要做法:
  - 参考 [storesales-1.ipynb](D:/Code/store-sales-time-series-forecasting/storesales-1.ipynb)
  - 按 `family` 拆成多条门店时间序列
  - 使用静态协变量、过去协变量、未来协变量
  - 引入 `transactions`、`oil`、`onpromotion`、节假日和时间索引
  - 使用 4 组不同 `lags` 的 `LightGBMModel`
  - 使用 4 组不同 `lags` 的 `XGBModel`
  - 再对两轮预测结果做平均融合
- 目的: 复刻接近高分 notebook 的重型方案
- Kaggle public score: `0.38022`
- 特点: 当前主线高分方案，但训练和预测耗时明显更长

### `version6.1`

- 核心方案: `version6 + 加权融合`
- 主要做法: 保持 `version6` 所有数据处理和模型配置不变，只把最终 `LightGBM/XGBoost` 融合从 `1:1` 平均改成 `0.6 / 0.4`
- 目的: 单独测试最终融合权重是否影响线上分数
- Kaggle public score: `0.38041`
- 结论: 这组权重比 `version6` 更差，说明简单偏向 `LightGBM` 不是正确方向

### `version6.2`

- 核心方案: `version6 + 更偏向 XGBoost 的加权融合`
- 主要做法: 保持 `version6.1` 的全部流程不变，只把最终融合权重改成 `0.45 / 0.55`
- 目的: 单独检验“更偏向 `XGBoost`”是否能继续降分
- Kaggle public score: `0.38017`
- 结论: 目前是当前最佳结果，说明最终融合权重是一个有效优化因子

### `version6.3`

- 核心方案: `version6.2` 的单因子延伸实验
- 主要做法: 保持 `version6.2` 的数据处理、模型配置和集成流程完全不变，只把最终融合权重改成 `0.40 / 0.60`
- 目的: 继续验证“增加 `XGBoost` 权重”是否稳定降低分数
- Kaggle public score: `0.38015`
- 结论: 在当前实验链条里，最终融合继续偏向 `XGBoost` 仍然带来了小幅提升

### `version6.4`

- 核心方案: `version6.3` 的单因子延伸实验
- 主要做法: 保持 `version6.3` 的数据处理、模型配置和集成流程完全不变，只把最终融合权重改成 `0.35 / 0.65`
- 目的: 继续验证“增加 `XGBoost` 权重”是否仍然稳定降低分数
- Kaggle public score: `0.38016`
- 结论: 比 `version6.3` 略差，说明最优权重区间大概率已经在 `0.40 / 0.60` 附近

### `version6.5`

- 核心方案: `version6.3` 的收尾微调实验
- 主要做法: 保持 `version6.3` 的全部数据处理、模型配置和集成流程不变，只把最终融合权重改成 `0.42 / 0.58`
- 目的: 在当前最优区间附近做最后一次小步微调，确认 `0.40 / 0.60` 是否已经接近局部最优
- Kaggle public score: `0.38016`
- 结论: 没有超过 `version6.3`，进一步说明当前局部最优点就在 `0.40 / 0.60` 附近

### `version7.1`

- 核心方案: `version6.3` 的结构单因子实验
- 主要做法: 保持 `version6.3` 的全部数据处理、协变量、模型参数和最终融合权重 `0.40 / 0.60` 不变，只移除 `730` 这组超长滞后配置
- 目的: 验证 `730` 这组长周期信息到底是在提供长期季节性，还是在引入额外噪声与训练开销
- Kaggle public score: `0.38138`
- 结论: 去掉 `730` 后分数明显变差，说明这组超长滞后提供了有效的长周期信息，应当保留

### `version7.2`

- 核心方案: `version6.3` 的结构单因子实验
- 主要做法: 保持 `version6.3` 的全部数据处理、协变量、模型参数和最终融合权重 `0.40 / 0.60` 不变，只移除 `365` 这组年周期滞后配置
- 目的: 验证 `365` 这组一年周期信息是否也在稳定提供有效信号
- Kaggle public score: `0.38074`
- 结论: 去掉 `365` 后分数明显变差，说明这组一年周期信息同样有效，应继续保留

### `version7.3`

- 核心方案: `version6.3` 的节假日单因子实验
- 主要做法: 保持 `version6.3` 的全部数据处理、协变量、模型参数、`lags` 结构和最终融合权重 `0.40 / 0.60` 不变，只把节假日集合从 `7` 个候选缩减为 `4` 个核心节日：`nat_navidad`、`nat_dia trabajo`、`nat_futbol`、`nat_dia difuntos`
- 目的: 验证当前节假日集合里是否存在噪声特征，核心节日子集是否能进一步降分
- Kaggle public score: `0.38005`
- 结论: 相比 `version6.3` 的 `0.38015` 进一步提升，说明节假日集合里确实存在噪声，保留核心节日是有效优化方向

### `version7.4`

- 核心方案: `version7.3` 的 past covariate 单因子实验
- 主要做法: 保持 `version7.3` 的全部数据处理、核心节日集合、模型参数、`lags` 结构和最终融合权重 `0.40 / 0.60` 不变，只移除过去协变量中的 `transactions`
- 目的: 验证交易量时间序列是否真的提供了有效信息，还是只是增加了复杂度
- Kaggle public score: `0.38110`
- 结论: 去掉 `transactions` 后分数明显变差，说明交易量序列当前仍然是有效的过去协变量，应继续保留

## Files

- [data_dictionary.md](D:/Code/store-sales-time-series-forecasting/data_dictionary.md): 数据表和字段说明
- [storesales-1.ipynb](D:/Code/store-sales-time-series-forecasting/storesales-1.ipynb): 参考 notebook

## Latest Scores

- `version7.3`: `0.38005`
  - 说明: 当前最佳公开分数，只保留 `4` 个核心节日后进一步提升
- `version7.4`: `0.38110`
  - 说明: 在 `version7.3` 基础上移除 `transactions` 后退化，说明 `transactions` 仍应保留

## Notes

- 比赛原始 CSV 数据较大，不纳入 git。
- 关键版本的提交结果 CSV 已随版本目录保留，便于回溯 leaderboard 分数。
