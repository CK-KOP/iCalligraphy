from ocr import ocr_recognize, parse_ocr_result
from flask import Flask, render_template, request, redirect, jsonify, send_from_directory, url_for, flash, abort, session, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy import func
import os, base64, re, subprocess, json
from single_char import search_character
from great_works import search_artworks
from your_api_code import main
from fonts_comparison import combined_similarity
import asyncio, threading, shutil, hashlib, cv2, time
from datetime import datetime  # 只导入 datetime 类
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from datetime import timedelta


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Kop_Date.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config["UPLOAD_FOLDER"] = "static/upload_imgs"
app.config["OCR_PAGES_FOLDER"] = "static/ocr_pages"
app.config["OCR_DATA_FOLDER"] = "static/ocr_data"
app.config["CUTTED_SINGLE_CHAR"] = "static/cutted_single_char"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 替换为你的实际信息
appid = "215b6f53"
api_secret = "M2U0NTJhZDc5OTg0OTlhZWVlNzI4NjI3"
api_key = "820decebec8b95259edd806a6640ed31"
imageunderstanding_url = "wss://spark-api.cn-huabei-1.xf-yun.com/v2.1/image"
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB，确保请求大小限制

app.config['SECRET_KEY'] = 'your-secret-key-here'
db = SQLAlchemy(app)

# 模型定义
class User(db.Model):
    __tablename__ = 'user'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)  # 用户id
    username = db.Column(db.String(30), nullable=False, unique=True)  # 用户名
    password_hash = db.Column(db.String(60), nullable=False)  # 密码哈希
    avatar_filepath = db.Column(db.String(255))  # 默认头像路径
    profile = db.Column(db.Text)  # 个人简介
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 注册时间
    user_likes = db.Column(db.Integer, nullable=False, default=0)  # 用户被点赞数

    def __init__(self, username, password, avatar_filepath = None, profile=None):
        self.username = username
        self.password_hash = self.hash_password(password)
        self.avatar_filepath = avatar_filepath
        self.profile = profile
        self.user_likes = 0

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest()  # 使用SHA-256对密码进行哈希

    @staticmethod
    def verify_password(input_password, stored_password_hash):
        return User.hash_password(input_password) == stored_password_hash

class RecognitionRecord(db.Model):
    __tablename__ = 'recognition_records'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    image_name = db.Column(db.String(255), nullable=False)
    original_image_name = db.Column(db.String(255), nullable=False)
    work_source = db.Column(db.String(255), nullable=True)
    work_author = db.Column(db.String(255), nullable=True)
    work_style = db.Column(db.String(255), nullable=True)
    work_layout = db.Column(db.String(255), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<RecognitionRecord {self.record_id} - {self.image_name}>"

class EvaluateCharacter(db.Model):
    __tablename__ = 'evaluate_character'
    
    evaluation_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)  # 评估记录id
    user_id = db.Column(db.Integer, nullable=False)  # 进行操作的用户id
    img_filepath = db.Column(db.String(255), nullable=False)  # 评估图片路径
    upload_date = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())  # 评估图片日期，自动填充当前时间
    evaluation_text = db.Column(db.Text)  # 评估文本
    
    def __init__(self, user_id, img_filepath, evaluation_text=None):
        self.user_id = user_id
        self.img_filepath = img_filepath
        self.evaluation_text = evaluation_text

class Character(db.Model):
    __tablename__ = 'characters'

    character_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)  # 汉字id
    character = db.Column(db.String(10), nullable=False)  # 汉字内容
    author_name = db.Column(db.String(20), nullable=True)  # 汉字作者
    style = db.Column(db.String(10), nullable=True)  # 汉字字体
    svg = db.Column(db.Text, nullable=True)  # 汉字矢量图格式
    image_data = db.Column(db.LargeBinary, nullable=True)  # 图片二进制数据
    image_type = db.Column(db.String(10), nullable=True)  # 图片MIME类型
    is_svg = db.Column(db.Boolean, nullable=False, default=True)  # 标识是否为SVG

    def __init__(self, character, author_name, style, svg=None, image_data=None, image_type=None):
        self.character = character
        self.author_name = author_name
        self.style = style
        self.svg = svg
        self.image_data = image_data
        self.image_type = image_type
        self.is_svg = svg is not None

class GreatWork(db.Model):
    __tablename__ = 'great_works'
    
    artwork_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)  # 书法作品id
    author_name = db.Column(db.String(20), nullable=False)  # 书法作品作家
    title = db.Column(db.String(50), nullable=False)  # 书法作品标题
    location = db.Column(db.String(50), nullable=False)  # 书法作品存储地
    img_filepath = db.Column(db.String(255), nullable=False)  # 书法作品图片路径
    description = db.Column(db.Text)  # 书法作品描述

    def __init__(self, author_name, title, location, img_filepath, description=None):
        self.author_name = author_name
        self.title = title
        self.location = location
        self.img_filepath = img_filepath
        self.description = description
    
class UserFavourite(db.Model):
    __tablename__ = 'user_favourites'
    
    favourite_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    character = db.Column(db.String(20), nullable=False)
    svg = db.Column(db.Text, nullable=True)  # 改为可空
    image_data = db.Column(db.LargeBinary, nullable=True)  # 新增图片数据字段
    image_type = db.Column(db.String(10), nullable=True)  # 新增图片类型字段
    is_svg = db.Column(db.Boolean, nullable=False, default=True)  # 新增标识字段

    def __init__(self, user_id, character, svg=None, image_data=None, image_type=None):
        self.user_id = user_id
        self.character = character
        self.svg = svg
        self.image_data = image_data
        self.image_type = image_type
        self.is_svg = svg is not None

class UserCopybook(db.Model):
    __tablename__ = 'user_copybook'
    
    copybook_id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)  # 创建字帖id
    user_id = db.Column(db.Integer, nullable=False)  # 创建用户id
    title = db.Column(db.String(50), nullable=False)  # 字帖标题
    creation_date = db.Column(db.DateTime, nullable=False)  # 创建日期
    img_filepath = db.Column(db.String(255))  # 保存字帖图片路径

    def __init__(self, user_id, title, creation_date, img_filepath=None):
        self.user_id = user_id
        self.title = title
        self.creation_date = creation_date
        self.img_filepath = img_filepath

class Post(db.Model):
    post_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    post_likes = db.Column(db.Integer, default=0)
    post_comments = db.Column(db.Integer, default=0)
    user_avatar = db.Column(db.String(255), nullable=False)
    image_paths = db.Column(JSON, nullable=True)  # 存储图片路径的列表

class UserClock(db.Model):
    __tablename__ = 'user_clock'
    clock_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    clock_char = db.Column(db.String(50), nullable=False)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    img_filepath = db.Column(db.String(255), nullable=False)

class UserCheckin(db.Model):
    __tablename__ = 'user_checkin'
    user_id = db.Column(db.Integer, primary_key=True)
    checkin_days = db.Column(db.Integer, default=0)

class UserLikes(db.Model):
    __tablename__ = 'user_likes'
    
    like_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    post_id = db.Column(db.Integer, nullable=False)
    like_time = db.Column(db.DateTime, default=datetime.utcnow)
    

class PostComment(db.Model):
    comment_id = db.Column(db.Integer, primary_key=True)               # 评论ID
    post_id = db.Column(db.Integer, db.ForeignKey('post.post_id'), nullable=False)  # 关联的帖子ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)  # 评论的用户ID
    content = db.Column(db.Text, nullable=False)                        # 评论内容
    creation_date = db.Column(db.DateTime, default=db.func.current_timestamp())  # 评论创建时间
    image_path = db.Column(db.String(255), nullable=True)                # 可选：评论的图片路径

    def __repr__(self):
        return f'<Comment {self.comment_id}>'
    
#------------------------------------------------------------------------------------
# 创建字帖页面
@app.route("/copybook_creation")
def copybook_creation():
    # 将集字数据传递到模板
    return render_template("copybook_creation.html")

# 获取书法字库数据
@app.route('/get_collection_images')
def get_collection_images():
    # 获取 query 参数
    library = request.args.get('library')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search_query = request.args.get('search', '', type=str)
    fontType = request.args.get('fontType', '', type=str)
    
    if fontType == 'kaishu':
        fontType = '楷书'
    elif fontType == 'xingshu':
        fontType = '行书'
    elif fontType == 'caoshu':
        fontType = '草书'
    elif fontType == 'lishu':
        fontType = '隶书'



    # 根据 library 参数从不同的表中获取数据
    if library == 'system':
        query = Character.query

        if search_query:
            query = query.filter(
                or_(
                    Character.author_name.ilike(f'%{search_query}%'),
                    Character.style.ilike(f'%{search_query}%'),
                    Character.character.ilike(f'%{search_query}%')
                )
            )
        if fontType != 'all':
                query = query.filter(Character.style.ilike(f'%{fontType}%'))

        paginated_characters = query.paginate(page=page, per_page=per_page)

        images = []
        for character in paginated_characters.items:
            image_data = {
                'id': character.character_id,
                'description': f'{character.author_name} {character.style} {character.character}',
                'is_svg': character.is_svg
            }

            if character.is_svg:
                image_data['svg'] = character.svg
            else:
                image_data['image_url'] = url_for('get_collection_image',
                                                  library='system',
                                                  image_id=character.character_id)

            images.append(image_data)

        return jsonify({
            'images': images,
            'total_pages': paginated_characters.pages,
            'current_page': page,
            'total_items': paginated_characters.total
        })

    elif library == 'personal':
        query = UserFavourite.query

        if search_query:
            query = query.filter(
                UserFavourite.character.ilike(f'%{search_query}%')
            )
            
        if fontType != 'all':
                query = query.filter(UserFavourite.character.ilike(f'%{fontType}%'))
        
        paginated_favourites = query.paginate(page=page, per_page=per_page)

        images = []
        for favourite in paginated_favourites.items:
            image_data = {
                'id': favourite.favourite_id,
                'description': favourite.character,
                'is_svg': favourite.is_svg
            }

            if favourite.is_svg:
                image_data['svg'] = favourite.svg
            else:
                image_data['image_url'] = url_for('get_collection_image',
                                                  library='personal',
                                                  image_id=favourite.favourite_id)

            images.append(image_data)

        return jsonify({
            'images': images,
            'total_pages': paginated_favourites.pages,
            'current_page': page,
            'total_items': paginated_favourites.total
        })

# 获取图片数据的路由
@app.route('/get_collection_image/<string:library>/<int:image_id>')
def get_collection_image(library, image_id):
    if library == 'system':
        # 检查系统字库
        character = Character.query.get(image_id)
        if character and not character.is_svg:
            response = make_response(character.image_data)
            response.headers.set('Content-Type', f'image/{character.image_type}')
            return response
    elif library == 'personal':
        # 检查个人字库
        favourite = UserFavourite.query.get(image_id)
        if favourite and not favourite.is_svg:
            response = make_response(favourite.image_data)
            response.headers.set('Content-Type', f'image/{favourite.image_type}')
            return response

    return "No image found", 404

# 个人上传集字收藏
@app.route('/add_collection', methods=['POST'])
def add_collection():
    try:
        file = request.files.get('image')
        character = request.form.get('character')
        
        if not character:
            return jsonify({'success': False, 'message': '请输入汉字'}), 400

        if file:
            # 处理上传的图片
            image_data = file.read()
            image_type = file.filename.split('.')[-1].lower()
            
            if image_type not in ['jpg', 'jpeg', 'png', 'gif']:
                return jsonify({'success': False, 'message': '不支持的图片格式'}), 400

            new_favourite = UserFavourite(
                user_id=session['user']['user_id'],
                character=character,
                image_data=image_data,
                image_type=image_type,
                svg=None
            )
        else:
            return jsonify({'success': False, 'message': '请上传图片'}), 400

        db.session.add(new_favourite)
        db.session.commit()

        return jsonify({'success': True, 'message': '添加成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# 保存字帖地址
COPYBOOK_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'copybook_uploads')  # 修改为 copybook_uploads
os.makedirs(COPYBOOK_UPLOAD_FOLDER, exist_ok=True)  # 确保文件夹存在
app.config['COPYBOOK_UPLOAD_FOLDER'] = COPYBOOK_UPLOAD_FOLDER

# 保存字帖
@app.route("/api/save_copybook", methods=["POST"])
def save_copybook():
    data = request.json
    user_id = session['user']['user_id']
    title = data.get('title')
    image_data = data.get('image')

    if not user_id or not title or not image_data:
        return jsonify({"message": "缺少必要参数"}), 400

    try:
        # 使用字帖标题的前几字符来生成文件名
        file_name_base = f"{title[:10]}_{user_id}_{int(datetime.now().timestamp())}"  # 取标题的前10个字符
        file_name = f"{file_name_base}.png"
        file_path = os.path.join(app.config['COPYBOOK_UPLOAD_FOLDER'], file_name)

        # 保存图片
        image_data = image_data.replace('data:image/png;base64,', '')
        with open(file_path, 'wb') as file:
            file.write(base64.b64decode(image_data))

        # 保存到数据库
        copybook = UserCopybook(user_id=user_id, title=title, img_filepath=file_path, creation_date=datetime.now())
        db.session.add(copybook)
        db.session.commit()

        # 返回下载链接
        download_url = f"/uploads/{file_name}"
        return jsonify({"message": "字帖保存成功", "downloadUrl": download_url}), 200

    except Exception as e:
        print(e)
        return jsonify({"message": "保存字帖失败"}), 500

# 下载字帖
@app.route('/uploads/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['COPYBOOK_UPLOAD_FOLDER'], filename)

#------------------------------------------------------------------------------------
# 书法搜索页面
@app.route("/calligraphy_search")
def calligraphy_search():
    # 将集字数据传递到模板
    return render_template("calligraphy_search.html")

# 判断是否为中文字符
def is_chinese_char(char):
    return re.match(r"[\u4e00-\u9fa5]", char) is not None

# 搜索功能
@app.route('/search', methods=['POST'])
async def search():
    max_cnt = 50
    # 接收前端传来的 JSON 数据
    data = request.get_json()
    search_type = data.get('type', '')
    query = data.get('query', '')
    fontType = data.get('fontType')
    
    if fontType == 'kaishu':
        fontType = '楷书'
    elif fontType == 'xingshu':
        fontType = '行书'
    elif fontType == 'caoshu':
        fontType = '草书'
    elif fontType == 'lishu':
        fontType = '隶书'

    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400

    # 毛笔字搜索逻辑
    if search_type == "calligraphy":
        # 检查输入是否包含中文字符
        first_char = query.strip()[0]  # 截取第一个字符
        if is_chinese_char(first_char):
            
            # 数据库查询
            query = db.session.query(Character).filter(Character.character == first_char)
            if fontType != 'all':
                query = query.filter(Character.style.ilike(f'%{fontType}%'))
            db_results = query.all()  # 获取查询结果
            if db_results:
                    # 如果数据库中存在该字
                results = [{
                    "svgContent": result.svg,  # 数据库没有 SVG 内容
                    "vectorId": str(result.character_id),
                    "info": f"{result.author_name or '作者不详'} {result.style or '字体不详'} {result.character}"
                } for result in db_results]
            else:
                # 如果数据库中不存在，调用自定义函数
                results = await search_character(first_char)

                # 毛笔字搜索逻辑中的存储部分
                insert_count = 0
                for result in results:
                    if insert_count >= max_cnt:  # 达到最大插入数，停止插入
                        break

                    info_parts = result.get('info', '').split()
                    
                    # 处理不同的 info 格式
                    if len(info_parts) == 3:  # 格式: 作家 style char
                        author_name = info_parts[0]
                        style = info_parts[1]
                        character = info_parts[2]
                    elif len(info_parts) == 1:  # 格式: 只有 char
                        author_name = None
                        style = None
                        character = info_parts[0]
                    else:
                        # 如果格式不符合预期，跳过此条记录
                        continue
                    
                    new_character = Character(
                        character=character,
                        svg=result['svgContent'],
                        author_name=author_name,
                        style=style
                    )
                    db.session.add(new_character)

                    insert_count += 1  # 更新插入计数
                # 提交数据库事务
                
                    db.session.commit()
                    db.session.rollback()

            return jsonify(results)
            
        else:
            return jsonify({"error": "查询内容必须包含一个中文字符"}), 400

    # 作品或书法家搜索逻辑
    elif search_type == "artwork":
        try:
            # 在数据库中模糊查找
            db_results = GreatWork.query.filter(
                (GreatWork.author_name.like(f'%{query}%')) | 
                (GreatWork.title.like(f'%{query}%'))
            ).all()
            if db_results:
                # 如果数据库中存在匹配结果
                results = [{
                    "artist": work.author_name,
                    "title": work.title,
                    "location": work.location,
                    "imageUrl": work.img_filepath,
                    "dynasty": work.description
                } for work in db_results]
            else:
                # 数据库中不存在，调用自定义搜索函数
                results = await search_artworks(query)

                # 将爬取的作品数据存储到数据库
                insert_count = 0
                for result in results:
                    if insert_count >= max_cnt:  # 达到最大插入数，停止插入
                            break
                    
                    new_work = GreatWork(
                        author_name=result['artist'],
                        title=result['title'],
                        location=result.get('location', ''),
                        img_filepath=result.get('imageUrl', ''),
                        description=result.get('dynasty', '')
                    )
                    db.session.add(new_work)

                    insert_count += 1  # 更新插入计数
                # 提交数据库事务
                try:
                    db.session.commit()
                except Exception as commit_error:
                    db.session.rollback()
                    return jsonify({"error": f"数据库存储失败: {str(commit_error)}"}), 500
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": f"搜索过程中发生错误: {str(e)}"}), 500

    # 未知搜索类型
    else:
        return jsonify({"error": "未知搜索类型"}), 400

# 展示书法字库与作品库
@app.route('/get_data', methods=['POST'])
def get_data():
    # 接收前端传来的 JSON 数据
    data = request.get_json()
    type = data.get('type')  # 获取前端传来的类型
    fontType = data.get('fontType')
    
    if fontType == 'kaishu':
        fontType = '楷书'
    elif fontType == 'xingshu':
        fontType = '行书'
    elif fontType == 'caoshu':
        fontType = '草书'
    elif fontType == 'lishu':
        fontType = '隶书'
    
    if type == 'calligraphy':
        # 查询书法字库的数据
        query = db.session.query(Character)
        
        if fontType != 'all':
            query = query.filter(Character.style.ilike(f'%{fontType}%'))
        
        db_results = query.all()  # 获取查询结果
        
        results = [{
            "svgContent": result.svg,  # 数据库没有 SVG 内容
            "vectorId": str(result.character_id),
            "info": f"{result.author_name or '作者不详'} {result.style or '字体不详'} {result.character}"
        } for result in db_results]
        return jsonify(results)
    
    else:
        # 查询作品库的数据
        db_results = db.session.query(GreatWork).all()
        
        results = [{
            "artist": work.author_name,
            "title": work.title,
            "location": work.location,
            "imageUrl": work.img_filepath,
            "dynasty": work.description
        } for work in db_results]
        return jsonify(results)


# 将字库中的字加入为收藏
@app.route('/add_favourite', methods=['POST'])
async def add_favourite():
    # 接收前端传来的 JSON 数据
    data = request.get_json()
    
    user_id = session['user'].get('user_id')
    
    # 获取字符和SVG内容
    character = data.get('info')
    svg_content = data.get('svgContent')
    
    # 参数验证
    if not character or not svg_content:
        return jsonify({"error": "字符和SVG内容不能为空"}), 400
    
    try:
        # 检查是否已经收藏过
        existing_favourite = UserFavourite.query.filter_by(
            user_id=user_id, 
            character=character,
            svg=svg_content
        ).first()
        
        if existing_favourite:
            return jsonify({"message": "该字已经收藏"}), 200
        
        # 创建新的收藏记录，只处理SVG内容
        new_favourite = UserFavourite(
            user_id=user_id,
            character=character,
            svg=svg_content,
        )
        
        # 添加到数据库
        db.session.add(new_favourite)
        db.session.commit()
        
        return jsonify({
            "message": "收藏成功", 
            "character": character
        }), 200
    
    except Exception as e:
        # 如果发生错误，回滚事务
        db.session.rollback()
        return jsonify({"error": f"收藏失败: {str(e)}"}), 500

#-------------------------------------------------------------------------------------
# 主页内容路由
@app.route('/main_page')
def main_page():
    return render_template('main_page.html')

# 登录页面路由
@app.route('/login')
def login():
    return render_template('login.html')

# 登录验证路由
@app.route('/check_login', methods=['POST'])
def check_login():
    # 获取请求中的 JSON 数据
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 查询用户
    user = User.query.filter_by(username=username).first()

    if user and User.verify_password(password, user.password_hash):
        session['user'] = {'user_id' : user.user_id, 'username': user.username}
        # 登录成功，返回用户信息
        return jsonify({
            'success': True,
            'username': user.username,
            'avatar_filepath': user.avatar_filepath,
            'profile': user.profile
        })
    else:
        # 登录失败
        return jsonify({'success': False, 'message': '用户名或密码错误'})

# 注册页面路由
@app.route('/registered')
def registered():
    return render_template('registered.html')

# 注册路由：接收注册信息
@app.route('/check_register', methods=['POST'])
def check_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    avatar_filepath = data.get('avatar_filepath', 'default-avatar.png')  # 默认头像
    profile = data.get('profile', '这个人暂时没有介绍')  # 可选的个人简介

    # 检查是否已经存在相同用户名
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'success': False, 'message': '用户名已存在'})  # 用户名已存在

    # 创建新用户并存入数据库
    new_user = User(username=username, password=password, avatar_filepath=avatar_filepath, profile=profile)
    db.session.add(new_user)
    db.session.commit()
    session['user'] = {'user_id' : new_user.user_id, 'username': new_user.username}
    return jsonify({'success': True, 'message': '注册成功'})

# 获取用户信息路由
@app.route('/get_user_data', methods=['GET'])
def get_user_data():
    user = session.get('user')
    if user:
        return jsonify({
            'success': True,
            'user': user
        })
    else:
        return jsonify({'success': False, 'message': 'No user logged in'})

# 退出登录路由
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)  # 清除 session 中的用户信息
    return jsonify({'success': True})

# 个人信息页面
@app.route('/person_information')
def person_information():
    return render_template('person_information.html')

AVATAR_UPLOAD_FOLDER = 'user_avatar_img'


app.config['AVATAR_UPLOAD_FOLDER'] = AVATAR_UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 上传头像路由
@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    # 处理文件上传逻辑
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        # 获取用户名并生成文件名
        username = session['user']['username']
        filename = f"{username}-avatar.{file.filename.rsplit('.', 1)[1].lower()}"

        # 获取目标目录路径
        upload_folder = app.config['AVATAR_UPLOAD_FOLDER']
        
        # 如果目录不存在则创建目录
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # 保存文件到指定目录
        file.save(os.path.join(upload_folder, filename))

        # 更新数据库
        user = User.query.filter_by(username=username).first()
        user.avatar_filepath = filename
        db.session.commit()

        # 更新 session 中的头像路径
        session['user']['avatar_filepath'] = filename

        return jsonify({'success': True, 'avatar_filepath': filename})
    return jsonify({'success': False, 'message': '上传失败'})

# 查询用户头像
@app.route('/avatars/<username>')
def get_avatar(username):
    # 使用用户名查询用户
    user = User.query.filter_by(username=username).first()
    print(user.avatar_filepath)
    if user and user.avatar_filepath:
        # 返回用户自定义头像
        return send_from_directory(app.config['AVATAR_UPLOAD_FOLDER'], user.avatar_filepath)
    else:
        # 返回默认头像
        return send_from_directory('static/images', 'default-avatar.png')

# 更新个人简介
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return jsonify({'success': False, 'message': '用户未登录'})

    user_id = session['user']['user_id']
    data = request.get_json()
    new_profile = data.get('profile', '').strip()

    if not new_profile:
        return jsonify({'success': False, 'message': '简历内容不能为空'})

    user = User.query.get(user_id)
    if user:
        user.profile = new_profile
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '用户不存在'})

# 获取用户字帖
@app.route('/get_copybooks')
def get_copybooks():
    # 获取请求参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search_query = request.args.get('search', '', type=str)
    
    user_id = session['user']['user_id']
    # 构建查询
    query = UserCopybook.query.filter_by(user_id=user_id)  # 只获取当前用户的字帖
    
    # 如果有搜索关键词，添加过滤条件
    if search_query:
        query = query.filter(
            UserCopybook.title.ilike(f'%{search_query}%')
        )
    
    
    # 按创建日期降序排序，最新的排在前面
    query = query.order_by(UserCopybook.creation_date.desc())
    
    # 执行分页查询
    paginated_copybooks = query.paginate(page=page, per_page=per_page)
    
    # 构建响应数据
    copybooks = []
    for copybook in paginated_copybooks.items:
        # 从文件路径中提取文件名
        filename = os.path.basename(copybook.img_filepath)
        
        copybook_data = {
            'copybook_id': copybook.copybook_id,
            'title': copybook.title,
            'creation_date': copybook.creation_date.isoformat(),
            'img_filepath': f"/uploads/{filename}" 
        }
        copybooks.append(copybook_data)
    
    # 返回JSON响应
    return jsonify({
        'copybooks': copybooks,
        'total_pages': paginated_copybooks.pages,
        'current_page': page,
        'total_items': paginated_copybooks.total
    })

# 删除用户收藏集字
@app.route('/delete_collection/<int:image_id>', methods=['DELETE'])
def delete_collection(image_id):
    collection = UserFavourite.query.filter_by(
        favourite_id=image_id
    ).first_or_404()
    print(collection)
    try:
        if collection:
            db.session.delete(collection)
            db.session.commit()
            return jsonify({"message": "删除成功"}), 200
        else:
            return jsonify({"message": "集字未找到"}), 404
    except Exception as e:
        print(e)
        return jsonify({"message": "删除失败"}), 500

# 删除用户字帖
@app.route('/delete_copybook/<int:copybook_id>', methods=['DELETE'])
def delete_copybook(copybook_id):
    copybook = UserCopybook.query.filter_by(
        copybook_id=copybook_id
    ).first_or_404()
    
    try:
        # 删除文件
        if copybook.img_filepath and os.path.exists(copybook.img_filepath):
            os.remove(copybook.img_filepath)
        
        # 删除数据库记录
        db.session.delete(copybook)
        db.session.commit()
        
        return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"删除失败: {e}")
        return jsonify({'message': '删除失败'}), 500

# 获取用户评定记录
@app.route('/get_evaluations')
def get_evaluations():
    # 获取请求参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    user_id = session['user']['user_id']
    
    # 构建查询
    query = EvaluateCharacter.query.filter_by(user_id=user_id)
    
    # 按上传日期降序排序，最新的排在前面
    query = query.order_by(EvaluateCharacter.upload_date.desc())
    
    # 执行分页查询
    paginated_evaluations = query.paginate(page=page, per_page=per_page)
    
    # 构建响应数据
    evaluations = []
    for evaluation in paginated_evaluations.items:
        filename = os.path.basename(evaluation.img_filepath)
        evaluation_data = {
            'evaluation_id': evaluation.evaluation_id,
            'upload_date': evaluation.upload_date.isoformat(),
            'evaluation_text': evaluation.evaluation_text,
            'img_filepath': url_for('get_evaluation_image', filename=filename)
        }
        evaluations.append(evaluation_data)
    
    return jsonify({
        'evaluations': evaluations,
        'total_pages': paginated_evaluations.pages,
        'current_page': page,
        'total_items': paginated_evaluations.total
    })


# 新增：获取评定图片的接口
app.config['EVALUATION_UPLOAD_FOLDER'] = 'evaluate_compare_images/uploads'
@app.route('/evaluation_images/<path:filename>')
def get_evaluation_image(filename):
    return send_from_directory(app.config['EVALUATION_UPLOAD_FOLDER'], filename)

# 删除用户评定记录
@app.route('/delete_evaluation/<int:evaluation_id>', methods=['DELETE'])
def delete_evaluation(evaluation_id):
    evaluation = EvaluateCharacter.query.filter_by(
        evaluation_id=evaluation_id
    ).first_or_404()
    
    try:
        # 删除文件
        if evaluation.img_filepath and os.path.exists(evaluation.img_filepath):
            os.remove(evaluation.img_filepath)
        
        # 删除数据库记录
        db.session.delete(evaluation)
        db.session.commit()
        
        return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"删除失败: {e}")
        return jsonify({'message': '删除失败'}), 500

# 获取用户识别记录
@app.route('/get_recognitions')
def get_recognitions():
    # 获取请求参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    user_id = session['user']['user_id']
    
    # 构建查询
    query = RecognitionRecord.query.filter_by(user_id=user_id)
    
    # 按上传日期降序排序，最新的排在前面
    query = query.order_by(RecognitionRecord.upload_date.desc())
    
    # 执行分页查询
    paginated_records = query.paginate(page=page, per_page=per_page)
    
    # 构建响应数据
    recognitions = []
    for record in paginated_records.items:
        record_data = {
            'record_id': record.record_id,
            'image_name': record.image_name,
            'original_image_name': record.original_image_name,
            'work_source': record.work_source,
            'work_author': record.work_author,
            'work_style': record.work_style,
            'work_layout': record.work_layout,
            'upload_date': record.upload_date.isoformat()
        }
        recognitions.append(record_data)

    print(recognitions)

    return jsonify({
        'recognitions': recognitions,
        'total_pages': paginated_records.pages,
        'current_page': page,
        'total_items': paginated_records.total
    })

# 删除识别记录
@app.route('/delete_recognition/<int:record_id>', methods=['DELETE'])
def delete_recognition(record_id):
    record = RecognitionRecord.query.filter_by(
        record_id=record_id
    ).first_or_404()
    
    try:
        # 删除数据库记录
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"删除失败: {e}")
        return jsonify({'message': '删除失败'}), 500

# 编辑OCR结果页面的路由
@app.route('/ocr_edit/<path:image_name>')
def ocr_edit(image_name):
    # 构建HTML文件路径
    print("image_name:", image_name)
    html_path = os.path.join('static', 'ocr_pages', f'proof_page_{image_name}.html')
    print(html_path)
    # 检查文件是否存在
    if not os.path.exists(html_path):
        abort(404)  # 如果文件不存在，返回404错误
    
    # 返回HTML文件
    return send_from_directory('static/ocr_pages', f'proof_page_{image_name}.html')

@app.route("/")
def index():
    return render_template("index.html")

#------------------------------------------------------------------------------------
# 大模型字形评定页面
@app.route("/img_evaluate_index", methods=["GET", "POST"])
def img_evaluate_index():
    return render_template("img_evaluate.html")

# 字形评定记录存储到数据库
def save_and_record_file(img_path, user_id, evaluation_text):
    try:
        # 保存信息到数据库
        new_record = EvaluateCharacter(
            user_id=user_id,
            img_filepath=img_path,
            evaluation_text=evaluation_text
        )
        db.session.add(new_record)
        db.session.commit()
        print("文件路径和相关信息已成功保存到数据库！")

    except FileNotFoundError:
        print("源文件不存在，请检查路径是否正确。")
    except Exception as e:
        print(f"发生错误: {e}")
        db.session.rollback()

# 大模型字形评定功能
@app.route("/img_evaluate", methods=["POST"])
def img_evaluate():
    try:
        uploaded_file = request.files.get("image")
        if not uploaded_file:
            return jsonify({"error": "未检测到有效的图像文件！"}), 400

        # 获取上传的文件扩展名
        file_extension = os.path.splitext(uploaded_file.filename)[1]

        # 使用时间戳生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}{file_extension}"

        # 设置文件保存路径
        target_directory = "evaluate_compare_images/uploads/"
        os.makedirs(target_directory, exist_ok=True)  # 确保目录存在

        # 构建完整文件路径
        file_path = os.path.join(target_directory, filename)

        # 保存文件到指定路径
        uploaded_file.save(file_path)
        
        # 读取文件并转为 Base64
        with open(file_path, "rb") as img_file:
            image_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # 请求大模型
        prompt = (
            "你是一位书法大师，拥有深厚的书法造诣。请对这张书法作品进行详细评定，"
            "包括字体的结构、笔画的流畅度、章法布局、气韵是否协调，以及艺术感染力。"
            "最后，给出专业的意见和具体改进建议。"
        )

        question = [
            {"role": "user", "content": image_base64, "content_type": "image"},
            {"role": "user", "content": prompt, "content_type": "text"}
        ]

        answer = []

        # 处理返回结果的回调函数
        def process_result(ws, message):
            data = json.loads(message)
            if data["header"]["code"] == 0:
                content = data["payload"]["choices"]["text"][0]["content"]
                answer.append(content)

        # 启动线程请求大模型
        thread = threading.Thread(target=main, args=(appid, api_key, api_secret, imageunderstanding_url, question), kwargs={'callback': process_result})
        thread.start()
        thread.join()

        # 整理最终结果
        full_answer = ''.join(answer)

        # 保存文件信息到数据库
        save_and_record_file(file_path, user_id=1, evaluation_text= full_answer)

        # 返回评估结果和图片路径
        return jsonify({"result": full_answer, "img_filepath": file_path})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 字形对比页面
@app.route("/evaluate_and_compare", methods=["POST"])
def evaluate_and_compare(): 
    try:
        uploaded_file = request.files.get("image")
        compare_file_path = os.path.join("evaluate_compare_images", "compare_image.png")
        print(uploaded_file)

        if not uploaded_file:
            return jsonify({"error": "请上传完整的两个文件！"}), 400
        
        uploaded_file_path = os.path.join("evaluate_compare_images", "uploaded_file.png")
        uploaded_file.save(uploaded_file_path)


        # 获取字体相似度
        sift_score, template_score, ssim_score, combined_score = combined_similarity(uploaded_file_path, compare_file_path)
        custom_similarity = f"{combined_score:.2f}"

        uploaded_file.seek(0)
        image_data = uploaded_file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        prompt = (
            "请假设你是一位书法大师，不用表明自己身份，你拥有深厚的书法造诣。请对这张书法作品进行详细评定，"
            "包括字体的结构、笔画的流畅度、章法布局、气韵是否协调，以及艺术感染力。"
            "最后，给出专业的意见和具体改进建议。"
        )

        question = [
            {"role": "user", "content": image_base64, "content_type": "image"},
            {"role": "user", "content": prompt, "content_type": "text"}
        ]

        answer = []

        def process_result(ws, message):
            data = json.loads(message)
            if data["header"]["code"] == 0:
                content = data["payload"]["choices"]["text"][0]["content"]
                answer.append(content)

        thread = threading.Thread(target=main, args=(appid, api_key, api_secret, imageunderstanding_url, question), kwargs={'callback': process_result})
        thread.start()
        thread.join()

        full_answer = ''.join(answer)

        # 生成以时间戳命名的文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        uploaded_file_name = f"{timestamp}.png"
        uploaded_file_path = os.path.join("evaluate_compare_images", "uploads", uploaded_file_name)

        # 保存文件
        uploaded_file.save(uploaded_file_path)
        # 保存文件信息到数据库
        save_and_record_file(uploaded_file_path, user_id=1, evaluation_text= full_answer)

        return jsonify({
            "result": full_answer,
            "customSimilarity": custom_similarity,
            "siftScore": f"{sift_score:.2f}%",
            "templateScore": f"{template_score:.2f}%",
            "ssimScore": f"{ssim_score:.2f}%",
            "combinedScore": f"{combined_score:.2f}%"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 保存对比图
@app.route('/save_comparison_image', methods=['POST'])
def save_comparison_image():
    try:
        # 获取上传的文件
        uploaded_file = request.files.get('compare-file')
        if not uploaded_file:
            return jsonify({"error": "没有接收到文件"}), 400

        # 直接指定文件夹路径，确保文件夹存在
        compare_folder = os.path.join(os.getcwd(), 'evaluate_compare_images')  # 在当前工作目录下创建一个文件夹
        os.makedirs(compare_folder, exist_ok=True)  # 如果文件夹不存在，则创建它

        # 设置文件保存路径
        file_path = os.path.join(compare_folder, 'compare_image.png')

        # 保存文件到服务器指定的文件夹
        uploaded_file.save(file_path)

        return jsonify({"success": True, "message": f"文件已保存: {file_path}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#------------------------------------------------------------------------------------

"""书法识别页面"""
@app.route("/img_ocr", methods=["POST", "GET"])
def img_ocr():
    # 处理文件上传
    if request.method == "POST":
        timestamp = request.form.get("timestamp")
        print(timestamp)

        if "file" not in request.files:
            return "No file part"
        file = request.files["file"]
        if file.filename == "":
            return "No selected file"
        if file and allowed_file(file.filename):

            filename = f"{timestamp}.{file.filename.rsplit('.', 1)[1].lower()}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            # 调用OCR接口
            api_key = "fk30GzIOCXdSBfOHY0Nka6av"
            secret_key = "5WQu7UFBRcdXmWFVVjWI7m7QOCLyld2a"
            result = ocr_recognize(save_path, api_key, secret_key)
            parsed_result = parse_ocr_result(result)

            # 创建切割后的图片保存路径
            cutted_imgs_dir = os.path.join(app.config["CUTTED_SINGLE_CHAR"], timestamp)
            if not os.path.exists(cutted_imgs_dir):  # 检查目录是否存在
                os.makedirs(cutted_imgs_dir)  # 如果不存在，创建目录

            img_to_cut = cv2.imread(save_path)
            # 遍历OCR结果并切割每个字
            for line in parsed_result:
                for char_info in line.get("chars", []):
                    char = char_info["char"]
                    loc = char_info["location"]

                    # 获取切割区域
                    top, left, width, height = (
                        loc["top"],
                        loc["left"],
                        loc["width"],
                        loc["height"],
                    )
                    cropped_img = img_to_cut[top : top + height, left : left + width]

                    # 保存切割后的图片
                    char_unicode = "_".join(
                        f"{ord(c):04x}" for c in char
                    )  # 将字符转为 Unicode 编码
                    char_filename = f"{char_unicode}_{top}_{left}.png"
                    char_path = os.path.join(cutted_imgs_dir, char_filename)
                    cv2.imwrite(char_path, cropped_img)

            # 保存OCR数据为 JSON 文件
            ocr_data_filename = f"{timestamp}.json"
            ocr_data_path = os.path.join(
                app.config["OCR_DATA_FOLDER"], ocr_data_filename
            )
            with open(ocr_data_path, "w", encoding="utf-8") as f:
                json.dump(
                    parsed_result, f, ensure_ascii=False, indent=4
                )  # 保存为JSON格式

            # 生成校对页面
            proof_page_html = generate_proof_page_html(filename, ocr_data_filename)

            # 保存校对页面
            proof_page_dir = app.config["OCR_PAGES_FOLDER"]  # 获取目录路径
            # 保存校对页面
            proof_page_filename = f"proof_page_{timestamp}.html"
            proof_page_path = os.path.join(proof_page_dir, proof_page_filename)
            with open(proof_page_path, "w", encoding="utf-8") as f:
                f.write(proof_page_html)

            return redirect(url_for("proof_page", filename=proof_page_filename))

    return render_template("img_ocr.html")

def generate_proof_page_html(filename, ocr_data_filename):
    return render_template(
        "proof_page_template.html",
        image_filename=filename,
        ocr_data_filename=ocr_data_filename,
    )

"""动态生成校对页面"""
@app.route("/proof_page/<filename>", methods=["GET"])
def proof_page(filename):
    # 读取校对页面
    proof_page_path = os.path.join(app.config["OCR_PAGES_FOLDER"], filename)
    if not os.path.exists(proof_page_path):
        return "Page not found", 404

    with open(proof_page_path, "r", encoding="utf-8") as f:
        proof_page_html = f.read()

    return proof_page_html

"""将ocr数据保存到本地"""
@app.route("/save_ocr_data", methods=["POST"])
def save_ocr_data():
    try:
        # 获取前端发送的数据
        data = request.json

        # 获取原始 OCR 数据文件名
        original_filename = data.get("original_filename")

        # 构建完整的文件路径
        file_path = os.path.join("static", "ocr_data", original_filename)

        # 读取原始数据
        with open(file_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)

        # 更新特定字符
        line_index = data.get("line_index")
        char_index = data.get("char_index")
        new_char = data.get("new_char")

        # 更新对应行的字符
        original_data[line_index]["chars"][char_index]["char"] = new_char

        # 重新计算行文本
        line_chars = [char["char"] for char in original_data[line_index]["chars"]]
        original_data[line_index]["line_text"] = "".join(line_chars)

        # 保存修改后的数据
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(original_data, f, ensure_ascii=False, indent=4)

        return jsonify({"status": "success", "message": "OCR 数据已成功保存"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

"""上传至平台审核文字信息"""
@app.route("/upload_char_info", methods=["POST"])
def upload_char_info():
    # 获取前端传递的数据
    data = request.get_json()

    char = data.get("char")
    top = data.get("top")
    left = data.get("left")

    # 获取字的详细信息
    char_content = data.get("char_content")
    char_author = data.get("char_author")
    char_font = data.get("char_font")
    char_source = data.get("char_source")

    # 确保字符和位置信息存在
    if not (char and top is not None and left is not None):
        return jsonify({"status": "failure", "message": "字符或位置信息缺失"}), 400

    # 确保字的信息完整
    if not all([char_content, char_author, char_font, char_source]):
        return jsonify({"status": "failure", "message": "缺少必要信息"}), 400

    # 打印接收到的字的信息（用于调试）
    print(f"Received character: {char}, top: {top}, left: {left}")
    print(f"字的内容: {char_content}")
    print(f"字的作者: {char_author}")
    print(f"字的字体: {char_font}")
    print(f"字的来源: {char_source}")

    # 这里可以加入保存到数据库或其他操作的逻辑

    # 返回成功的响应
    return jsonify({"status": "success", "message": "信息上传成功"})

"""前端回传上传图片信息"""
@app.route("/upload_work_info", methods=["POST"])
def upload_work_info():
    data = request.get_json()

    img_name = data.get("img_name")
    work_source = data.get("work_source")
    work_author = data.get("work_author")
    work_style = data.get("work_style")
    work_layout = data.get("work_layout")
    timestamp = data.get("timestamp")  # 前端传来的时间戳
    user_id = session.get("user", {}).get("user_id")
    
     # 检查必要字段
    if not all([img_name, work_source, work_author, work_style, work_layout, timestamp, user_id]):
        return jsonify({"status": "failure", "message": "缺少必要信息"}), 400

    print(f"图片名称: {img_name}")
    print(f"作品来源: {work_source}")
    print(f"作者信息: {work_author}")
    print(f"字体风格: {work_style}")
    print(f"排版方式: {work_layout}")
    print(f"上传时间: {timestamp}")
    print(f"用户ID: {user_id}")
    

    nowtimestamp = int(timestamp) // 1000
    upload_datetime = datetime.fromtimestamp(nowtimestamp)
    print(f"格式化后的日期: {upload_datetime}")
    
    try:
        # 创建记录
        new_record = RecognitionRecord(
            user_id=user_id,
            image_name=str(timestamp),
            original_image_name=img_name,
            work_source=work_source,
            work_author=work_author,
            work_style=work_style,
            work_layout=work_layout,
            upload_date=upload_datetime
        )
        print(new_record)

        # 保存到数据库
        db.session.add(new_record)
        db.session.commit()

        return jsonify({"status": "success", "message": "信息上传成功", "file_name": timestamp})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "failure", "message": "数据库保存失败", "error": str(e)}), 500

#------------------------------------------------------------------------------------

# 论坛主页面
@app.route('/forum')
def forum():
    # 获取用户签到天数
    checkin_days = 0
    if 'user' in session:
        checkin = UserCheckin.query.get(session['user']['user_id'])
        if checkin:
            checkin_days = checkin.checkin_days
    
    # 获取帖子列表
    posts = Post.query.order_by(Post.creation_date.desc()).limit(10).all()
    
    # 获取热门帖子
    hot_posts = Post.query.order_by(Post.post_likes.desc()).limit(5).all()
    
    # 获取活跃用户
    active_users = User.query.order_by(User.user_likes.desc()).limit(5).all()
    
    # 为每条帖子添加对应的用户名
    for post in posts:
        user = User.query.get(post.user_id)  # 根据 user_id 获取 User
        post.username = user.username   # 添加用户名属性

    return render_template('forum.html',
        checkin_days=checkin_days,
        posts=posts,
        hot_posts=hot_posts,
        active_users=active_users
    )

# 加载更多帖子
@app.route('/posts')
def get_posts():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    posts = Post.query.order_by(Post.creation_date.desc())\
        .paginate(page=page, per_page=size, error_out=False)
    
    return jsonify({
        'posts': [{
            'post_id': post.post_id,
            'username': User.query.get(post.user_id).username,
            'content': post.content,
            'creation_date': post.creation_date.isoformat(),
            'post_likes': post.post_likes,
            'post_comments': post.post_comments,
            'image_paths': post.image_paths
        } for post in posts.items]
    })

# 帖子详情页面
@app.route('/post_detail/<post_id>')
def post_detail(post_id):
    print(f"访问帖子ID：{post_id}")  # 确认是否正确触发路由
    # 查询帖子详情
    post = Post.query.get(post_id)
    print(f"帖子图片路径：{post.image_paths}")
    if not post:
        print("帖子未找到")  # 调试信息，确认是否能找到对应的帖子
        return redirect(url_for('index'))  # 如果帖子不存在，重定向到首页

    # 获取帖主信息
    post_user = User.query.get(post.user_id) if post else None

    # 查询评论详情
    comments = PostComment.query.order_by(PostComment.creation_date.desc()).filter_by(post_id=post_id).all()
    
    # 为每条帖子添加对应的用户名
    for comment in comments:
        user = User.query.get(comment.user_id)  # 根据 user_id 获取 User
        comment.username = user.username   # 添加用户名属性

    print(f"查询到的评论：{comments}")

    print(f"评论数：{len(comments)}")  # 打印评论数量，确认是否有评论
    # 处理评论提交
    if request.method == 'POST':
        if 'like_button' in request.form:  # 点赞按钮被点击
            post.post_likes += 1
            db.session.commit()
            return redirect(url_for('post_detail', post_id=post_id))

        comment_text = request.form.get('comment_text', '').strip()
        # 输出评论内容，确认是否传递正确
        print(f"提交的评论内容: {comment_text}")

        if comment_text:  # 如果评论内容不为空
            user_id = session['user']['user_id'] 
            image_path = ''
            new_comment = PostComment(post_id=post_id, user_id=user_id, content=comment_text, image_path=image_path)
            db.session.add(new_comment)
            post.post_comments += 1
            db.session.commit()
            print(f"评论保存成功，ID为：{new_comment.comment_id}")
            return redirect(url_for('post_detail', post_id=post_id))

    return render_template('post_detail.html', post=post, post_user=post_user, comments=comments)

# 添加评论
@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    # 检查请求是否包含评论文本
    if not request.json or 'comment_text' not in request.json:
        return jsonify({'message': '评论内容不能为空'}), 400

    comment_text = request.json['comment_text']

    post = Post.query.get(post_id)
    post.post_comments += 1

    # 创建新的评论
    new_comment = PostComment(
        post_id=post_id,
        user_id=session['user']['user_id'],
        content=comment_text
    )
    db.session.add(new_comment)
    db.session.commit()

    # 查询帖子下的所有评论
    comments = PostComment.query.filter_by(post_id=post_id).all()
    
    # 获取评论及用户信息
    comment_list = []
    for comment in comments:
        user = User.query.get(comment.user_id)  # 根据 user_id 获取用户信息
        comment_list.append({
            'username': user.username if user else '未知用户',
            'content': comment.content,
            'creation_date': comment.creation_date.strftime('%Y-%m-%d %H:%M:%S'),
            'avatar_path': user.avatar_path if user and user.avatar_path else None
        })

    return jsonify({'success': True, 'comments': comment_list}), 201

# 帖子点赞逻辑
@app.route('/post/like/<post_id>', methods=['POST'])
def like_post(post_id):
    user_id = session['user']['user_id']
    
    # 获取当前帖子
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'message': '帖子未找到'})
    
    # 获取帖主用户ID
    post_user_id = post.user_id
    
    # 检查是否已点赞
    user_like = UserLikes.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if user_like:
        # 取消点赞
        db.session.delete(user_like)
        db.session.commit()
        
        # 减少该帖子的点赞数
        post.post_likes -= 1
        # 减少帖主的被点赞数
        post_user = User.query.get(post_user_id)
        post_user.user_likes -= 1
        
        db.session.commit()
        
        return jsonify({'success': True, 'likes': post.post_likes, 'is_liked': False, 'user_likes': post_user.user_likes})
    else:
        # 点赞
        new_like = UserLikes(user_id=user_id, post_id=post_id)
        db.session.add(new_like)
        db.session.commit()
        
        # 增加该帖子的点赞数
        post.post_likes += 1
        # 增加帖主的被点赞数
        post_user = User.query.get(post_user_id)
        post_user.user_likes += 1
        
        db.session.commit()
        
        return jsonify({'success': True, 'likes': post.post_likes, 'is_liked': True, 'user_likes': post_user.user_likes})

app.config['POST_UPLOAD_FOLDER'] = 'static/post_images'  # 上传图片文件夹
if not os.path.exists(app.config['POST_UPLOAD_FOLDER']):
    os.makedirs(app.config['POST_UPLOAD_FOLDER'])

# 发布帖子路由
@app.route('/post/create', methods=['POST'])
def post_create():
    if 'user' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    content = request.form.get('content')
    images = request.files.getlist('images')
    print(f"提交的图片: {images}")
    
    # 处理图片上传
    image_paths = []
    for image in images:
        if image and allowed_file(image.filename):
            print(f"提交的图片: {image}")
            filename = f"{int(time.time() * 1000)}_{secure_filename(image.filename)}"  # 使用时间戳+原文件名
            # 使用相对路径，添加 /static 前缀
            filepath = f'/static/post_images/{filename}'
            # 保存时使用完整系统路径
            save_path = os.path.join(app.root_path, 'static/post_images', filename)
            image.save(save_path)
            image_paths.append(filepath)

    new_post = Post(
        user_id=session['user']['user_id'],
        content=content,
        image_paths=image_paths,
        user_avatar=f"/avatars/{session['user']['username']}"
    )
    db.session.add(new_post)
    db.session.commit()

    return jsonify({'success': True})

# 打卡页面显示
@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    user_id = session.get('user', {}).get('user_id')  # 从session获取用户ID
    return render_template('checkin.html', user_id=user_id)

# 获取用户打卡记录
@app.route('/checkin/records', methods=['GET'])
def get_checkin_records():
    """
    获取用户的打卡记录，按时间倒序排列。
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        records = UserClock.query.filter_by(user_id=user_id).order_by(UserClock.creation_date.desc()).all()
        result = [
            {
                'clock_id': r.clock_id,
                'clock_char': r.clock_char,
                'creation_date': r.creation_date.strftime('%Y-%m-%d %H:%M:%S'),
                'img_filepath': r.img_filepath,
            }
            for r in records
        ]
        return jsonify(result)
    except Exception as e:
        print(f"获取打卡记录出错: {e}")
        return jsonify({'error': '获取打卡记录失败，请稍后再试'}), 500

app.config['CHECKIN_UPLOAD_FOLDER'] = 'static/checkin_images'  # 上传图片文件夹
if not os.path.exists(app.config['CHECKIN_UPLOAD_FOLDER']):
    os.makedirs(app.config['CHECKIN_UPLOAD_FOLDER'])

# 打卡记录上传接口
@app.route('/checkin/upload', methods=['POST'])
def upload_checkin():
    user_id = request.form.get('user_id')
    clock_char = request.form.get('clock_char')
    img_file = request.files.get('img_file')

    if not all([user_id, clock_char, img_file]):
        return jsonify({'error': 'User ID, character, and image file are required'}), 400

    # 保存图片到服务器
    img_filename = secure_filename(img_file.filename)  # 防止文件名不安全
    img_filepath = os.path.join(app.config['CHECKIN_UPLOAD_FOLDER'],  img_filename)  # 保存到指定目录
    img_file.save(img_filepath)

    try:
        # 创建打卡记录
        new_record = UserClock(
            user_id=user_id,
            clock_char=clock_char,
            img_filepath=f'checkin_images/{img_filename}'  # 存储相对路径
        )
        db.session.add(new_record)

        # 更新用户签到天数
        user_checkin = UserCheckin.query.get(user_id)
        if user_checkin:
            user_checkin.checkin_days += 1
        else:
            user_checkin = UserCheckin(user_id=user_id, checkin_days=1)
            db.session.add(user_checkin)

        db.session.commit()
        return jsonify({'message': 'Upload successful', 'clock_id': new_record.clock_id, 'img_filepath': new_record.img_filepath})
    except Exception as e:
        db.session.rollback()
        print(f"插入打卡记录出错: {e}")
        return jsonify({'error': '打卡记录插入失败，请稍后再试'}), 500

# 从字库中随机选择字体传入
@app.route('/get-random-char', methods=['GET'])
def get_random_char():
    # 获取随机字的逻辑
    character = db.session.query(Character).filter(Character.character == '飞').first()
    # 或者使用随机查询：
    # character = db.session.query(Character).order_by(func.random()).first()
    
    if not character:
        return jsonify({'error': 'No character found'}), 404
        
    image_data = {
        'id': character.character_id,
        'character': character.character,  # 添加字符本身
        'description': f'{character.author_name} {character.style} {character.character}',
        'is_svg': character.is_svg
    }

    if character.is_svg:
        image_data['svg'] = character.svg
    else:
        image_data['image_url'] = url_for('get_collection_image',
                                         library='system',
                                         image_id=character.character_id)

    return jsonify({'image_data': image_data})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
