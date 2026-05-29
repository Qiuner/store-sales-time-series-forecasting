# Store Sales - Time Series Forecasting

这个仓库记录了我在 Kaggle `Store Sales - Time Series Forecasting` 比赛中的多版建模尝试。

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
| `version6.5` | `version6.3` 的 `0.42 / 0.58` 收尾微调实验 | 待提交 | 待定 |

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
- 状态: 待运行/待记录线上分数

## Files

- [data_dictionary.md](D:/Code/store-sales-time-series-forecasting/data_dictionary.md): 数据表和字段说明
- [storesales-1.ipynb](D:/Code/store-sales-time-series-forecasting/storesales-1.ipynb): 参考 notebook

## Notes

- 比赛原始 CSV 数据较大，不纳入 git。
- 各版本生成的提交结果 CSV 默认不纳入 git。
