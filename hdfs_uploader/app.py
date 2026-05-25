import os
import io
import logging
import requests
import pandas as pd
import pymysql
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SCRIPT_FOLDER'] = 'scripts'

HDFS_HOST = '192.168.139.160'
HDFS_PORT = 9870
HDFS_USER = 'hdfs'
HDFS_BASE_PATH = '/user/data'

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 改成你的
    'database': 'amazon_analysis',
    'charset': 'utf8mb4'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'txt', 'tsv', 'parquet'}
SCRIPT_EXTENSIONS = {'sql', 'hql'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_script(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in SCRIPT_EXTENSIONS


def get_mysql_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def clean_data(df):
    report = {
        'original_rows': len(df),
        'original_cols': len(df.columns),
        'steps': []
    }
    before = len(df)
    df = df.drop_duplicates()
    report['steps'].append({'action': '删除重复行', 'removed': before - len(df)})
    before_rows = len(df)
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')
    report['steps'].append({'action': '删除全空行/列', 'removed': before_rows - len(df)})
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({'nan': None, 'None': None, '': None})
    report['steps'].append({'action': '字符串列去空白 & 标准化空值', 'cols': list(str_cols)})
    num_cols = df.select_dtypes(include='number').columns
    filled = {}
    for col in num_cols:
        null_count = df[col].isna().sum()
        if null_count > 0:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            filled[col] = {'filled': int(null_count), 'with': round(float(median_val), 4)}
    if filled:
        report['steps'].append({'action': '数值列空值填充（中位数）', 'detail': filled})
    original_cols = df.columns.tolist()
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r'[\s\-/\\]+', '_', regex=True)
                  .str.replace(r'[^\w]', '', regex=True)
    )
    renamed = {o: n for o, n in zip(original_cols, df.columns) if o != n}
    if renamed:
        report['steps'].append({'action': '列名标准化', 'renamed': renamed})
    report['cleaned_rows'] = len(df)
    report['cleaned_cols'] = len(df.columns)
    return df, report


def read_file(filepath, ext):
    if ext == 'csv':
        try:
            df = pd.read_excel(filepath)
            logger.info('检测到文件实为 Excel 格式，已用 Excel 方式读取')
            return df
        except Exception:
            pass
        for enc in ('utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin1'):
            try:
                return pd.read_csv(filepath, encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(filepath, encoding='latin1')
    elif ext in ('xlsx', 'xls'):
        return pd.read_excel(filepath)
    elif ext == 'json':
        return pd.read_json(filepath)
    elif ext == 'tsv':
        for enc in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'latin1'):
            try:
                return pd.read_csv(filepath, sep='\t', encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(filepath, sep='\t', encoding='latin1')
    elif ext == 'parquet':
        return pd.read_parquet(filepath)
    elif ext == 'txt':
        for enc in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'latin1'):
            try:
                return pd.read_csv(filepath, sep=None, engine='python', encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(filepath, sep=None, engine='python', encoding='latin1')
    raise ValueError(f'不支持的文件类型: {ext}')


def hdfs_mkdirs(hdfs_path):
    url = f'http://{HDFS_HOST}:{HDFS_PORT}/webhdfs/v1{hdfs_path}'
    resp = requests.put(url, params={'op': 'MKDIRS', 'user.name': HDFS_USER}, timeout=30)
    resp.raise_for_status()


def hdfs_upload(local_bytes, hdfs_path):
    url = f'http://{HDFS_HOST}:{HDFS_PORT}/webhdfs/v1{hdfs_path}'
    params = {'op': 'CREATE', 'user.name': HDFS_USER, 'overwrite': 'true', 'noredirect': 'true'}
    resp = requests.put(url, params=params, timeout=30)
    resp.raise_for_status()
    data_url = resp.json().get('Location', None)
    if not data_url:
        params.pop('noredirect')
        resp2 = requests.put(url, params=params, data=local_bytes,
                             allow_redirects=True, timeout=120)
        resp2.raise_for_status()
    else:
        resp2 = requests.put(data_url, data=local_bytes,
                             headers={'Content-Type': 'application/octet-stream'},
                             timeout=120)
        resp2.raise_for_status()


@app.route('/')
def index():
    return render_template('index.html',
                           hdfs_host=HDFS_HOST,
                           hdfs_port=HDFS_PORT,
                           hdfs_base=HDFS_BASE_PATH)


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/product_details')
def api_product_details():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page
        
        conn = get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM product_details")
        total = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT shop_id, brand, title, comment_star, avg_price, 
                   shop_rank, five_proportion, one_proportion 
            FROM product_details 
            LIMIT {per_page} OFFSET {offset}
        """)
        data = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'data': [{
                'shop_id': r[0],
                'brand': r[1],
                'title': r[2],
                'rating': float(r[3]) if r[3] else 0,
                'price': float(r[4]) if r[4] else 0,
                'rank': r[5],
                'good_rate': float(r[6]) if r[6] else 0,
                'bad_rate': float(r[7]) if r[7] else 0
            } for r in data]
        })
    except Exception as e:
        logger.exception('获取商品详情失败')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/price_distribution')
def api_price_distribution():
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT price_range, count, avg_rating FROM price_distribution")
        data = cursor.fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'data': [{'range': r[0], 'count': r[1], 'avg_rating': float(r[2])} for r in data]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/rating_distribution')
def api_rating_distribution():
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT rating_level, count FROM rating_distribution WHERE rating_level <= 10 ORDER BY rating_level")
        data = cursor.fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'data': [{'level': r[0], 'count': r[1]} for r in data]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/review_sentiment')
def api_review_sentiment():
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT star_type, avg_percentage FROM review_sentiment")
        data = cursor.fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'data': [{'type': r[0], 'percentage': float(r[1])} for r in data]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/brand_stats')
def api_brand_stats():
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT brand, product_count, avg_price, avg_rating FROM brand_stats LIMIT 10")
        data = cursor.fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'data': [{'brand': r[0], 'count': r[1], 'price': float(r[2]), 'rating': float(r[3])} for r in data]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/upload_script', methods=['POST'])
def upload_script():
    if 'script' not in request.files:
        return jsonify({'success': False, 'error': '没有找到脚本文件'}), 400
    
    file = request.files['script']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400
    
    if not allowed_script(file.filename):
        return jsonify({'success': False, 'error': '只支持 .sql 和 .hql 文件'}), 400
    
    filename = secure_filename(file.filename)
    script_path = os.path.join(app.config['SCRIPT_FOLDER'], filename)
    file.save(script_path)
    
    try:
        # 执行 Hive 脚本
        result = subprocess.run(
            ['hive', '-f', script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '脚本执行成功',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': '脚本执行失败',
                'output': result.stderr
            }), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '脚本执行超时（5分钟）'}), 500
    except Exception as e:
        logger.exception('脚本执行失败')
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有找到上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400
    if not allowed_file(file.filename):
        return jsonify({'success': False,
                        'error': f'不支持的文件类型，允许: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(local_path)
    logger.info(f'文件已保存到本地: {local_path}')
    try:
        df = read_file(local_path, ext)
        logger.info(f'读取完成，shape={df.shape}')
        df_clean, report = clean_data(df)
        logger.info(f'清洗完成，shape={df_clean.shape}')
        buf = io.BytesIO()
        df_clean.to_csv(buf, index=False, encoding='utf-8-sig')
        csv_bytes = buf.getvalue()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = filename.rsplit('.', 1)[0]
        custom_path = request.form.get('hdfs_path', '').strip() or HDFS_BASE_PATH
        hdfs_dir = f'{custom_path}/{datetime.now().strftime("%Y%m%d")}'
        hdfs_filename = f'{stem}_cleaned_{timestamp}.csv'
        hdfs_full_path = f'{hdfs_dir}/{hdfs_filename}'
        hdfs_mkdirs(hdfs_dir)
        hdfs_upload(csv_bytes, hdfs_full_path)
        logger.info(f'已上传到 HDFS: {hdfs_full_path}')
        return jsonify({
            'success': True,
            'filename': filename,
            'hdfs_path': hdfs_full_path,
            'hdfs_url': f'http://{HDFS_HOST}:{HDFS_PORT}/webhdfs/v1{hdfs_full_path}?op=OPEN',
            'clean_report': report
        })
    except Exception as e:
        logger.exception('处理失败')
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


@app.route('/hdfs/status', methods=['GET'])
def hdfs_status():
    try:
        url = f'http://{HDFS_HOST}:{HDFS_PORT}/webhdfs/v1/?op=LISTSTATUS&user.name={HDFS_USER}'
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            return jsonify({'online': True, 'host': HDFS_HOST, 'port': HDFS_PORT})
        return jsonify({'online': False, 'code': resp.status_code})
    except Exception as e:
        return jsonify({'online': False, 'error': str(e)})


@app.route('/hdfs/list', methods=['GET'])
def hdfs_list():
    path = request.args.get('path', HDFS_BASE_PATH)
    try:
        url = f'http://{HDFS_HOST}:{HDFS_PORT}/webhdfs/v1{path}'
        resp = requests.get(url, params={'op': 'LISTSTATUS', 'user.name': HDFS_USER}, timeout=15)
        if resp.status_code == 200:
            files = resp.json().get('FileStatuses', {}).get('FileStatus', [])
            return jsonify({'success': True, 'path': path, 'files': files})
        return jsonify({'success': False, 'error': resp.text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SCRIPT_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
