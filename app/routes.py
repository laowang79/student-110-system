import os
import uuid
import json
import pandas as pd
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, send_file, session, flash
from werkzeug.utils import secure_filename
from .models import SchoolRule, EventRecord, User, db

bp = Blueprint('main', __name__)
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 权限校验装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('您没有管理员权限执行此操作', 'danger')
            return redirect(url_for('main.query_data'))
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'success': False, 'message': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.context_processor
def inject_user():
    return dict(current_user=session)

# ----------------- 认证与页面路由 -----------------

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['department'] = user.department
            
            # 管理员去工作台，普通用户去查询页面
            if user.role == 'admin':
                return redirect(url_for('main.index'))
            else:
                return redirect(url_for('main.query_data'))
        else:
            flash('账号或密码错误', 'danger')
            
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('index.html')

@bp.route('/rules', methods=['GET'])
@login_required
@admin_required
def manage_rules():
    rules = SchoolRule.query.all()
    return render_template('dict_manage.html', rules=rules)

@bp.route('/users', methods=['GET'])
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@bp.route('/query', methods=['GET'])
@login_required
def query_data():
    if session.get('role') == 'admin':
        total_records = EventRecord.query.count()
        school_records = EventRecord.query.filter(EventRecord.school_name != '').count()
    else:
        dept = session.get('department', '')
        total_records = EventRecord.query.filter_by(department=dept).count()
        school_records = EventRecord.query.filter(EventRecord.school_name != '', EventRecord.department == dept).count()
        
    return render_template('query.html', total=total_records, school_count=school_records)

# ----------------- API 路由 -----------------

@bp.route('/api/users', methods=['POST'])
@api_admin_required
def add_user():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'operator')
    department = data.get('department', '').strip()
    
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '账号已存在'})
        
    user = User(username=username, role=role, department=department)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/users/<int:id>', methods=['DELETE'])
@api_admin_required
def delete_user(id):
    if id == session.get('user_id'):
        return jsonify({'success': False, 'message': '不能删除自己'})
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/records', methods=['GET'])
@login_required
def get_all_records():
    if session.get('role') == 'admin':
        records = EventRecord.query.all()
    else:
        records = EventRecord.query.filter_by(department=session.get('department', '')).all()
        
    data = []
    
    for r in records:
        if r.full_data:
            row_dict = json.loads(r.full_data)
            # 删除原有的序号（如果有的话）
            if '序号' in row_dict:
                del row_dict['序号']
            data.append(row_dict)
            
    # 按接警时间倒序排序
    data.sort(key=lambda x: str(x.get('接警时间', '')), reverse=True)
    
    ordered_cols = ['序号']
    for idx, row in enumerate(data):
        row['序号'] = idx + 1
        for k in row.keys():
            if k not in ordered_cols and k != '_is_modified':
                ordered_cols.append(k)
                
    return jsonify({'data': data, 'columns': ordered_cols})

@bp.route('/api/records/update', methods=['POST'])
@login_required
def update_record():
    data = request.json
    event_no = data.get('事件单编号')
    if event_no:
        record = EventRecord.query.filter_by(event_no=event_no).first()
        if record:
            # 权限检查：如果是操作员，只能修改本部门的数据
            if session.get('role') != 'admin' and record.department != session.get('department'):
                return jsonify({'success': False, 'message': '无权修改其他部门的数据'})
                
            record.school_name = data.get('学校名称', record.school_name)
            
            if session.get('role') == 'admin':
                record.department = data.get('处警单位', record.department)
                data['_is_modified'] = True
                record.full_data = json.dumps(data, ensure_ascii=False)
            else:
                # 核心安全逻辑：二级操作员只能修改特定的补充信息字段
                old_data = json.loads(record.full_data) if record.full_data else {}
                allowed_prefixes = ["报警人基本信息", "学校名称", "学校阶段", "原因类型", "校内外", "发案地点类型", "处置结果", "是否重复报警", "是否闭环", "下一步拟采取措施"]
                for k, v in data.items():
                    if any(prefix in k for prefix in allowed_prefixes):
                        old_data[k] = v
                old_data['_is_modified'] = True
                record.full_data = json.dumps(old_data, ensure_ascii=False)
                
            db.session.commit()
            return jsonify({'success': True})
    return jsonify({'success': False, 'message': '未找到对应记录'})

@bp.route('/api/records/delete/<string:event_no>', methods=['DELETE'])
@api_admin_required
def delete_record(event_no):
    record = EventRecord.query.filter_by(event_no=event_no).first()
    if record:
        db.session.delete(record)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '记录不存在'})

@bp.route('/upload', methods=['POST'])
@api_admin_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        result = process_excel(filepath)
        return jsonify({'success': True, 'data': result, 'columns': result['columns'], 'filename': unique_filename})
    return jsonify({'success': False, 'message': '不支持的文件格式'})

def process_excel(filepath):
    # 读取数据，强制所有列读取为字符串
    df = pd.read_excel(filepath, dtype=str)
    
    # 填补NaN为空字符串
    df = df.fillna('')
    
    # 全局清洗：去除回车、换行，以及头尾空格
    df = df.replace(to_replace=r'[\r\n]+', value='', regex=True)
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # 获取学校规则字典
    rules = SchoolRule.query.all()
    rule_dict = {rule.keyword: rule.standard_name for rule in rules}
    
    if '学校名称' not in df.columns:
        df['学校名称'] = ''
        
    if '序号' in df.columns:
        df = df.drop(columns=['序号'])
        
    original_columns = ['序号'] + df.columns.tolist()
    total_count = len(df)
    imported_count = duplicate_count = completed_school_count = 0
    records_to_return = []

    for index, row in df.iterrows():
        event_no = str(row.get('事件单编号', '')).strip()
        dept = str(row.get('处警单位', '')).strip()
        
        if event_no:
            existing = EventRecord.query.filter_by(event_no=event_no).first()
            if existing:
                duplicate_count += 1
                continue
                
        text_to_search = str(row.get('处理结果', '')) + " " + str(row.get('事件详情', ''))
        extracted_school = row.get('学校名称', '')
        if not extracted_school:
            for keyword, std_name in rule_dict.items():
                if keyword in text_to_search:
                    extracted_school = std_name
                    completed_school_count += 1
                    break
            df.at[index, '学校名称'] = extracted_school

        row_dict = df.iloc[index].to_dict()
        records_to_return.append(row_dict)
        
        new_record = EventRecord(
            event_no=event_no or f"TEMP_{uuid.uuid4().hex[:8]}",
            report_time=str(row.get('接警时间', '')),
            school_name=extracted_school,
            department=dept,
            full_data=json.dumps(row_dict, ensure_ascii=False)
        )
        db.session.add(new_record)
        imported_count += 1
        
    db.session.commit()
    return {
        'records': records_to_return,
        'columns': original_columns,
        'stats': {'total': total_count, 'imported': imported_count, 'duplicates': duplicate_count, 'completed_schools': completed_school_count}
    }

@bp.route('/export', methods=['POST'])
@login_required
def export_data():
    data = request.json.get('data')
    columns = request.json.get('columns')
    
    if not data:
        return jsonify({'success': False, 'message': '没有提供数据'})
        
    df = pd.DataFrame(data)
    
    # 彻底从导出数据中移除前端辅助状态标识
    if '_is_modified' in df.columns:
        df = df.drop(columns=['_is_modified'])
        
    if columns:
        export_cols = [col for col in columns if col in df.columns]
        export_cols.extend([col for col in df.columns if col not in export_cols])
        df = df[export_cols]
        
    export_filename = f"exported_{uuid.uuid4().hex}.xlsx"
    export_path = os.path.join(current_app.config['UPLOAD_FOLDER'], export_filename)
    
    with pd.ExcelWriter(export_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    return jsonify({'success': True, 'download_url': url_for('main.download_file', filename=export_filename)})

@bp.route('/download/<filename>')
@login_required
def download_file(filename):
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    return send_file(filepath, as_attachment=True)

# 保留之前编写的关于规则导入删除等API，稍微修饰...
@bp.route('/api/rules', methods=['POST'])
@api_admin_required
def add_rule():
    data = request.json
    keyword = data.get('keyword', '').strip()
    standard_name = data.get('standard_name', '').strip()
    if not keyword or not standard_name: return jsonify({'success': False, 'message': '不能为空'})
    if SchoolRule.query.filter_by(keyword=keyword).first(): return jsonify({'success': False, 'message': '已存在'})
    rule = SchoolRule(keyword=keyword, standard_name=standard_name)
    db.session.add(rule)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/rules/<int:id>', methods=['DELETE'])
@api_admin_required
def delete_rule(id):
    rule = SchoolRule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/rules/import', methods=['POST'])
@api_admin_required
def import_rules():
    file = request.files.get('file')
    if not file or not allowed_file(file.filename): return jsonify({'success': False})
    try:
        df = pd.read_excel(file, dtype=str).fillna('')
        added = 0
        for index, row in df.iterrows():
            k, s = str(row.iloc[0]).strip(), str(row.iloc[1]).strip()
            if k and s and not SchoolRule.query.filter_by(keyword=k).first():
                db.session.add(SchoolRule(keyword=k, standard_name=s))
                added += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'导入了 {added} 条'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
