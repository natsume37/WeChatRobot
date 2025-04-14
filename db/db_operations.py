# db_operations.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import User, conf  # 导入 User 模型和数据库引擎

# 创建 Session 类
Session = sessionmaker(bind=create_engine(conf.URL))


# 示例：添加用户
def add_user(wechat_id, points=10, is_blacklisted=False, is_super_admin=False):
    """
    添加一个新用户
    :param wechat_id: 用户的微信ID
    :param points: 用户的初始积分，默认为 10
    :param is_blacklisted: 是否被拉黑，默认为 False
    :param is_super_admin: 是否为超级管理员，默认为 False
    :return: 新创建的 User 对象
    """
    session = Session()  # 创建 session

    # 检查用户是否已经存在
    existing_user = session.query(User).filter(User.wechat_id == wechat_id).first()

    if existing_user:
        session.close()
        return existing_user  # 用户已存在，返回现有用户

    # 用户不存在，创建新用户
    new_user = User(
        wechat_id=wechat_id,
        points=points,
        is_blacklisted=is_blacklisted,
        is_super_admin=is_super_admin
    )
    session.add(new_user)  # 将新用户添加到会话
    session.commit()  # 提交事务
    session.close()  # 关闭 session
    return new_user  # 返回新创建的用户


# 示例：查询用户，如果没有则创建新用户
def get_or_create_user_by_wechat_id(wechat_id, points=0, is_blacklisted=False, is_super_admin=False):
    """
    根据微信 ID 查询用户，如果不存在则创建一个新用户
    :param wechat_id: 用户的微信ID
    :param points: 初始积分，默认为0
    :param is_blacklisted: 是否被拉黑，默认为 False
    :param is_super_admin: 是否为超级管理员，默认为 False
    :return: 用户对象（查询到的或新创建的）
    """
    session = Session()  # 创建 session

    # 查询用户是否存在
    user = session.query(User).filter(User.wechat_id == wechat_id).first()

    if user:
        session.close()
        return user  # 用户已存在，返回该用户

    # 用户不存在，创建新用户
    new_user = User(
        wechat_id=wechat_id,
        points=points,
        is_blacklisted=is_blacklisted,
        is_super_admin=is_super_admin
    )
    session.add(new_user)  # 添加到会话
    session.commit()  # 提交事务
    session.close()  # 关闭 session
    return new_user  # 返回新创建的用户


# 示例：更新用户积分
def update_user_points(wechat_id, change_points):
    """
    根据微信ID更新用户积分
    :param wechat_id: 用户的微信ID
    :param change_points: 要更改的积分，正数表示加积分，负数表示减积分
    :return: 返回更新后的用户对象，或者 None（如果用户不存在）
    """
    session = Session()  # 创建 session

    # 查询用户是否存在
    user = session.query(User).filter(User.wechat_id == wechat_id).first()

    if user:
        # 用户存在，更新积分
        user.points += change_points  # 根据传入的积分值加或减
        session.commit()  # 提交事务
        session.close()  # 关闭 session
        return user  # 返回更新后的用户对象
    else:
        # 用户不存在，返回 None
        session.close()  # 关闭 session
        return None


def get_points(wechat_id):
    user = get_or_create_user_by_wechat_id(wechat_id)
    if user:
        return user.points
