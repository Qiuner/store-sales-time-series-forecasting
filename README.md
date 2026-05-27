# Store Sales - Time Series Forecasting

这个仓库记录了我在 Kaggle `Store Sales - Time Series Forecasting` 比赛中的多版建模尝试。

## Versions

- `version1`: 最基础的线性回归基线。使用日期拆分特征、门店编号、商品大类编码和促销数量直接回归销量。
- `version2`: 基于 `store_nbr + family + dayofweek` 的分层移动平均基线。使用最近 14/28/56 天统计量并加入温和促销修正。
- `version3`: 在 `version2` 上加入节假日、油价和轻量岭回归校准，测试外部协变量是否带来提升。
- `version4`: `LightGBM + lag/rolling` 特征版。验证分数好，但后续确认存在多步预测泄漏问题。
- `version5`: 无泄漏递推版 `LightGBM`。按未来 16 天逐日滚动预测，修复 `version4` 的验证与提交不一致问题。
- `version6`: 参考 `storesales-1.ipynb` 的 `Darts` 多序列集成方案，复刻 `LightGBM/XGBoost` 多滞后集成与协变量流程。
  - 思路: `Darts` 多序列建模，`LightGBM/XGBoost` 多滞后集成，结合交易量、油价、促销和节假日协变量
  - Kaggle public score: `0.38022`

## Files

- [data_dictionary.md](D:/Code/store-sales-time-series-forecasting/data_dictionary.md): 数据表和字段说明
- [storesales-1.ipynb](D:/Code/store-sales-time-series-forecasting/storesales-1.ipynb): 参考 notebook

## Notes

- 比赛原始 CSV 数据较大，不纳入 git。
- 各版本生成的提交结果 CSV 默认不纳入 git。
