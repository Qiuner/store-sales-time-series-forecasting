# 导入 numpy，用于数值计算
import numpy as np

# 导入 pandas，用于数据处理
import pandas as pd

# 导入线性回归模型
from sklearn.linear_model import LinearRegression


# Kaggle 数据集路径
BASE = '/kaggle/input/competitions/store-sales-time-series-forecasting/'


# 读取训练集
train = pd.read_csv(BASE + 'train.csv')

# 读取测试集
test = pd.read_csv(BASE + 'test.csv')

# 读取官方提交模板
sample = pd.read_csv(BASE + 'sample_submission.csv')


# 特征工程函数
def make_features(df):

    # 复制一份数据，避免修改原始数据
    df = df.copy()

    # 将 date 列转成 datetime 时间格式
    df['date'] = pd.to_datetime(df['date'])

    # 提取年份
    df['year'] = df['date'].dt.year

    # 提取月份
    df['month'] = df['date'].dt.month

    # 提取日期（几号）
    df['day'] = df['date'].dt.day

    # 提取星期几
    # Monday=0, Sunday=6
    df['dayofweek'] = df['date'].dt.dayofweek

    # 店铺编号转整数
    df['store_nbr'] = df['store_nbr'].astype(int)

    # 商品类别 family 转成分类编码
    # 比如：
    # AUTOMOTIVE -> 0
    # BABY CARE -> 1
    df['family_code'] = df['family'].astype('category').cat.codes

    # 返回最终特征列
    return df[
        [
            'year',
            'month',
            'day',
            'dayofweek',
            'store_nbr',
            'family_code',
            'onpromotion'
        ]
    ]


# 构建训练特征
X_train = make_features(train)

# 训练目标值（销量）
y_train = train['sales']

# 构建测试特征
X_test = make_features(test)


# 创建线性回归模型
model = LinearRegression()

# 训练模型
model.fit(X_train, y_train)


# 预测测试集销量
preds = model.predict(X_test)

# clip(0) 表示把负数截断成 0
# 因为销量不可能是负数
preds = preds.clip(0)

# 复制提交模板
submission = sample.copy()

# 把预测结果填入 sales 列
submission['sales'] = preds

# 导出 CSV 文件
submission.to_csv('submission.csv', index=False)


# 打印完成提示
print("完成！")

# 查看前几行结果
print(submission.head())