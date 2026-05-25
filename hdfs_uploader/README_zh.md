# DataPipe · 数据清洗 & HDFS 上传平台

> A modern Flask-based data cleaning and HDFS upload platform with analytics dashboard

## 📦 Features

✅ **多格式数据上传**  
支持 CSV、Excel、JSON、Parquet、TSV、TXT 等多种格式，自动编码识别

✅ **智能数据清洗**  
5步数据清洗流程：去重、删除空值、字符串标准化、数值补填、列名规范化

✅ **HDFS集成**  
WebHDFS API 直接上传，支持目录浏览和连接状态监控

✅ **数据可视化**  
基于 ECharts 的实时数据分析看板，支持多维度数据展示

✅ **Hive脚本执行**  
上传并执行 Hive/Spark SQL 脚本，实时查看执行日志

✅ **安全可靠**  
完整的错误处理、输入验证、日志记录和超时保护

## 🚀 快速开始

### 方式1：自动启动（推荐）

```bash
chmod +x start.sh && ./start.sh
```

### 方式2：手动启动

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 创建目录
mkdir -p uploads scripts

# 配置环境
cp .env.example .env
# 编辑 .env 文件配置参数

# 启动应用
python3 app.py
```

访问地址：**http://localhost:5000**

## ⚙️ 配置说明

### 环境变量配置

编辑 `.env` 文件：

```env
# HDFS 配置
HDFS_HOST=192.168.139.160
HDFS_PORT=9870
HDFS_USER=hdfs
HDFS_BASE_PATH=/user/data

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=amazon_analysis

# Flask 配置
FLASK_ENV=development
MAX_CONTENT_LENGTH=524288000
```

## 📊 支持的文件类型

| 格式 | 说明 | 编码 |
|------|------|------|
| CSV | 逗号分隔文本 | 自动识别 (UTF-8, GBK, Latin-1 等) |
| TSV | 制表符分隔文本 | 自动识别 |
| XLSX | Excel 2007+ 格式 | 二进制 |
| XLS | Excel 97-2003 格式 | 二进制 |
| JSON | JSON 数组或对象 | UTF-8 |
| Parquet | 列式存储格式 | 二进制 |
| TXT | 纯文本 (自动检测分隔符) | 自动识别 |

## 🔄 数据清洗流程

### 1. **删除重复行**
- 移除完全相同的行
- 保留第一次出现的记录

### 2. **删除空值行/列**
- 删除所有字段都为空的行
- 删除所有值都为空的列
- 减少数据体积，提高质量

### 3. **字符串标准化**
- 去除前后空白
- 规范化空值表示：`nan`、`None`、`""` → `NULL`
- 保证字符串格式统一

### 4. **数值补填**
- 用**列中位数**填充缺失值
- 中位数比平均值更稳健，适合有偏分布
- 保留原始数据分布特性

### 5. **列名规范化**
- 转小写：`ProductName` → `productname`
- 空格/连字符替换为下划线：`Product Name` → `product_name`
- 移除特殊字符：`Product@Name#` → `productname`
- 生成数据库友好的列名

## 🔗 HDFS 配置要求

### WebHDFS 启用

确保 `hdfs-site.xml` 配置：

```xml
<property>
  <name>dfs.webhdfs.enabled</name>
  <value>true</value>
</property>
```

### 防火墙规则

需要开放以下端口：
- **9870**: WebHDFS 端口（NameNode）
- **9864**: DataNode HTTP 端口

### HDFS 用户权限

```bash
# 创建数据目录
hdfs dfs -mkdir -p /user/data
hdfs dfs -chown hdfs:hdfs /user/data
hdfs dfs -chmod 755 /user/data
```

## 📡 API 接口

### 文件上传接口

```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@data.csv" \
  -F "hdfs_path=/user/data"
```

**响应示例**：
```json
{
  "success": true,
  "filename": "data.csv",
  "hdfs_path": "/user/data/20240115/data_cleaned_20240115_143022.csv",
  "clean_report": {
    "original_rows": 1000,
    "original_cols": 15,
    "cleaned_rows": 950,
    "cleaned_cols": 15,
    "steps": [
      {"action": "删除重复行", "removed": 10},
      {"action": "删除全空行/列", "removed": 40},
      ...
    ]
  }
}
```

### HDFS 状态接口

```bash
GET /hdfs/status
```

### 文件浏览接口

```bash
GET /hdfs/list?path=/user/data
```

### 数据分析接口

| 接口 | 说明 |
|------|------|
| `/api/product_details` | 商品详情（支持分页） |
| `/api/price_distribution` | 价格区间分布 |
| `/api/rating_distribution` | 评分分布趋势 |
| `/api/review_sentiment` | 好评差评占比 |
| `/api/brand_stats` | 品牌统计 Top10 |

## 📁 项目结构

```
hdfs_uploader/
├── app.py              # Flask 主程序
├── config.py           # 配置管理模块
├── requirements.txt    # Python 依赖
├── .env.example        # 环境配置示例
├── start.sh            # 一键启动脚本
├── templates/
│   ├── index.html      # 上传和清洗界面
│   └── dashboard.html  # 数据分析看板
├── uploads/            # 临时上传目录（自动创建）
├── scripts/            # 临时脚本目录（自动创建）
└── README.md           # 本文件
```

## 🛡️ 安全特性

- ✅ **HDFS 路径验证**: 防止目录穿越攻击
- ✅ **文件类型白名单**: 仅处理允许的文件格式
- ✅ **文件名清理**: 使用 `secure_filename()` 进行安全处理
- ✅ **环境变量隔离**: 敏感信息存储在 `.env`
- ✅ **错误信息脱敏**: 通用错误响应，防止信息泄露
- ✅ **超时保护**: 脚本执行 5 分钟超时限制
- ✅ **完整日志**: 所有操作详细记录用于审计

## 🐛 常见问题

### HDFS 连接失败
```
错误: "HDFS is offline"
```
**解决**: 检查 HDFS NameNode 是否运行，9870 端口是否开放

### MySQL 连接失败
```
错误: "Database connection failed"
```
**解决**: 验证 `.env` 中的 MySQL 凭证，确保 MySQL 服务运行

### 文件编码错误
```
错误: "UnicodeDecodeError"
```
**解决**: 应用会自动检测编码。如仍失败，转换文件为 UTF-8：
```bash
iconv -f GBK -t UTF-8 input.csv > output.csv
```

### 脚本执行超时
```
错误: "Script execution timeout"
```
**解决**: 简化查询或在配置中增加超时时间

## 📈 性能优化建议

1. **批量上传**: 依次上传多个文件以获得更好的吞吐量
2. **文件大小**: 建议单文件不超过 500MB（可配置）
3. **网络连接**: 确保到 HDFS 集群的连接稳定
4. **编码格式**: UTF-8 CSV 文件处理最快
5. **缓冲区**: 根据服务器内存调整 pandas chunk size

## 📝 日志记录

应用会输出详细的操作日志，帮助诊断问题：

```
2024-01-15 14:30:22 INFO app.py: File saved locally: uploads/data.csv
2024-01-15 14:30:23 INFO app.py: File read successfully, shape=(1000, 15)
2024-01-15 14:30:24 INFO app.py: Data cleaned, shape=(950, 15)
2024-01-15 14:30:25 INFO app.py: Uploaded to HDFS: /user/data/20240115/...
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Developed with ❤️ for data engineers**
