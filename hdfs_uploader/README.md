# DataPipe · 数据清洗 & HDFS 上传平台

Flask Web 服务，支持上传数据文件 → 自动清洗 → 上传到 HDFS。

## 目录结构

```
hdfs_uploader/
├── app.py              # Flask 主程序
├── templates/
│   └── index.html      # 前端页面
├── requirements.txt    # Python 依赖
├── start.sh            # 一键启动脚本
└── uploads/            # 临时上传目录（自动创建，处理后清除）
```

## 快速启动

```bash
# 方式 1：使用启动脚本（自动建虚拟环境）
chmod +x start.sh && ./start.sh

# 方式 2：手动
pip install -r requirements.txt
python app.py
```

访问 http://localhost:5000

## 配置说明

编辑 `app.py` 顶部：

```python
HDFS_HOST      = '192.168.139.160'   # HDFS NameNode IP
HDFS_PORT      = 9870                # WebHDFS 端口
HDFS_USER      = 'hdfs'              # HDFS 用户名
HDFS_BASE_PATH = '/user/data'        # 默认上传目录
```

## 支持的文件类型

| 格式 | 说明 |
|------|------|
| CSV / TSV | 逗号/Tab 分隔文本 |
| XLSX / XLS | Excel 表格 |
| JSON | JSON 数组或对象 |
| Parquet | 列式存储格式 |
| TXT | 自动检测分隔符 |

## 数据清洗步骤

1. **删除重复行** — 完全相同的记录只保留一条
2. **删除全空行/列** — 所有值均为空的行/列直接删除
3. **字符串标准化** — 去除首尾空白，统一空值表示（`nan`/`None`/`""` → NULL）
4. **数值填充** — 数值列的空值用该列**中位数**填充
5. **列名标准化** — 列名转小写、空格/特殊字符替换为下划线

## HDFS WebHDFS 要求

确保 HDFS 开启 WebHDFS（`hdfs-site.xml`）：

```xml
<property>
  <name>dfs.webhdfs.enabled</name>
  <value>true</value>
</property>
```

NameNode 防火墙需放行 **9870（WebHDFS）** 和 **9864（DataNode）** 端口。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 主页面 |
| POST | `/upload` | 上传并处理文件 |
| GET | `/hdfs/status` | 检查 HDFS 连通性 |
| GET | `/hdfs/list?path=...` | 列出 HDFS 目录文件 |
