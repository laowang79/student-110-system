import os
from app import create_app
from app.models import User, db
from pypinyin import pinyin, Style

app = create_app()

departments = [
    "山阳",
    "张堰",
    "朱泾",
    "金山卫",
    "蒙山",
    "吕巷",
    "象州",
    "亭林",
    "朱行",
    "交警三大队",
    "兴塔"
]

def generate_username(dept_name):
    # 将中文转换为拼音，不带声调，全小写，拼接在一起
    pinyin_list = pinyin(dept_name, style=Style.NORMAL)
    username = ''.join([item[0] for item in pinyin_list]).lower()
    return username

with app.app_context():
    added_count = 0
    for dept in departments:
        username = generate_username(dept)
        
        # 检查是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            new_user = User(username=username, role='operator', department=dept)
            new_user.set_password('123456')
            db.session.add(new_user)
            added_count += 1
            print(f"创建用户成功: 账号={username}, 密码=123456, 部门={dept}")
        else:
            print(f"用户已存在跳过: 账号={username}, 部门={dept}")
            
    db.session.commit()
    print(f"\n批量生成完成！共新增 {added_count} 个用户。")
