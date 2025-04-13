# models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from configuration import Config

conf = Config()
# 创建一个基础类
Base = declarative_base()


# 定义 User 模型，包含 id, 微信ID, 积分, 是否被拉黑字段
class User(Base):
    __tablename__ = 'users'  # 定义表名

    id = Column(Integer, primary_key=True, autoincrement=True)  # id, 主键，自增
    wechat_id = Column(String(255), unique=True, nullable=False)  # 微信ID, 唯一，不可为空
    points = Column(Integer, default=0)  # 积分，默认为0
    is_blacklisted = Column(Boolean, default=False)  # 是否被拉黑，默认为否（False）
    is_super_admin = Column(Boolean, default=False)  # 是否为超级管理员，默认为否（False）


# # 数据库连接配置
# DATABASE_URL = conf.URL
#
# # 创建数据库引擎
# engine = create_engine(DATABASE_URL, echo=True)
#
# # 创建所有表
# Base.metadata.create_all(engine)
