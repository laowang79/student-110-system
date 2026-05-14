from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator') # 'admin' 或 'operator'
    department = db.Column(db.String(100)) # 关联的处警单位（部门），管理员可为空

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SchoolRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), unique=True, nullable=False)
    standard_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<SchoolRule {self.keyword} -> {self.standard_name}>'

class EventRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_no = db.Column(db.String(100), unique=True, nullable=True, index=True) # 事件单编号
    report_time = db.Column(db.String(50)) # 接警时间
    school_name = db.Column(db.String(100)) # 学校名称
    department = db.Column(db.String(100)) # 处警单位 (用于二级用户权限过滤)
    full_data = db.Column(db.Text) # 完整原始数据 JSON

    def __repr__(self):
        return f'<EventRecord {self.event_no}>'
