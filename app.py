from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import markdown2
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import time
import re
from sqlalchemy import extract, func, desc
from bs4 import BeautifulSoup  # Import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse

app = Flask(__name__)
app.config.update(
    JSON_AS_ASCII=False,
    SQLALCHEMY_DATABASE_URI=get_database_url(),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key'),
    UPLOAD_FOLDER='/tmp/uploads'
)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# 在创建所有模型类之后，确保数据库表结构是最新的
def init_db():
    with app.app_context():
        # 创建所有表（如果不存在）
        db.create_all()
        
        # 创建默认分类（如果不存在）
        if not Category.query.first():
            categories = [
                Category(name='日记', description='记录生活点滴和心情感悟'),
                Category(name='学习', description='学习笔记和知识总结'),
                Category(name='旅行', description='旅行见闻和精彩瞬间')
            ]
            db.session.add_all(categories)
            db.session.commit()
            
        # 创建默认标签（如果不存在）
        if not Tag.query.first():
            tags = [
                Tag(name='Python'),
                Tag(name='Flask'),
                Tag(name='Web开发'),
                Tag(name='数据库'),
                Tag(name='前端')
            ]
            db.session.add_all(tags)
            db.session.commit()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 文章-标签关联表
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# 关注者关联表
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy=True)
    bio = db.Column(db.Text)
    location = db.Column(db.String(64))
    website = db.Column(db.String(120))
    avatar = db.Column(db.String(200))  # 存储头像文件名
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    comments = db.relationship('Comment', backref='author', lazy=True)
    likes = db.relationship('PostLike', backref='user', lazy='dynamic')
    
    # 新增：关注者关系
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # 新增：消息关系
    messages_sent = db.relationship('Message',
        foreign_keys='Message.sender_id',
        backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message',
        foreign_keys='Message.recipient_id',
        backref='recipient', lazy='dynamic')
    
    # 新增：通知关系
    notifications = db.relationship('Notification',
        backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            notification = Notification(
                user_id=user.id,
                message=f'{self.username} 开始关注了你',
                type='follow',
                related_id=self.id
            )
            db.session.add(notification)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)
        ).filter(followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.date_posted.desc())

    def new_messages(self):
        return Message.query.filter_by(recipient=self, read=False).count()

    def new_notifications(self):
        return Notification.query.filter_by(user_id=self.id, read=False).count()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    posts = db.relationship('Post', backref='category', lazy=True)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', secondary=post_tags, backref=db.backref('tags', lazy='dynamic'))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(200))  # 添加文章摘要
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, onupdate=datetime.utcnow)  # 添加最后修改时间
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('PostLike', backref='post', lazy='dynamic')
    views = db.Column(db.Integer, default=0)  # 添加访问量统计
    image = db.Column(db.String(200))  # New field for storing image path

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        return self.likes.filter_by(user_id=user.id).first() is not None
        
    def increment_views(self):
        self.views += 1
        
    def generate_summary(self):
        # 从content生成摘要
        plain_text = markdown2.markdown(self.content)
        # 移除HTML标签
        plain_text = re.sub(r'<[^>]+>', '', plain_text)
        # 取前200个字符作为摘要
        self.summary = plain_text[:200] + '...' if len(plain_text) > 200 else plain_text
        
    def get_read_time(self):
        """估计文章阅读时间（分钟）"""
        # 假设阅读速度为每分钟300个汉字
        text = re.sub(r'<[^>]+>', '', markdown2.markdown(self.content))
        words = len(text)
        minutes = round(words / 300)
        return max(1, minutes)  # 最少1分钟

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_like_uc'),)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(250), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(20))  # 'follow', 'like', 'comment', 'message'
    related_id = db.Column(db.Integer)  # 相关内容的ID

# 允许的图片格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 确保数据库表创建
init_db()

# 添加上下文处理器，使所有模板都能访问分类
@app.context_processor
def inject_categories():
    categories = Category.query.all()
    return dict(categories=categories)

def extract_toc(html_content):
    """从HTML内容中提取目录"""
    toc = []
    soup = BeautifulSoup(html_content, 'html.parser')
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(heading.name[1])
        text = heading.get_text()
        # 为标题添加ID
        heading_id = f"heading-{len(toc)}"
        heading['id'] = heading_id
        toc.append({
            'level': level,
            'text': text,
            'id': heading_id
        })
    return toc, str(soup)

@app.route('/')
@app.route('/page/<int:page>')
def home(page=1):
    per_page = 10
    # 使用 with_entities 只选择需要的字段
    posts = Post.query.with_entities(
        Post.id, Post.title, Post.content, Post.date_posted,
        Post.category_id, Post.user_id, Post.summary
    ).order_by(Post.date_posted.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    # 获取热门文章
    try:
        popular_posts = Post.query.order_by(Post.views.desc()).limit(5).all()
    except:
        popular_posts = []
    
    # 获取最新评论
    recent_comments = Comment.query.order_by(Comment.date_posted.desc()).limit(5).all()
    
    # 获取所有分类
    categories = Category.query.all()
    
    return render_template('home.html', 
                         posts=posts,
                         popular_posts=popular_posts,
                         recent_comments=recent_comments,
                         categories=categories)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    try:
        post.increment_views()
        db.session.commit()
    except:
        db.session.rollback()
    
    # 转换Markdown并提取目录
    html_content = markdown2.markdown(post.content, extras=['fenced-code-blocks', 'tables'])
    toc, content = extract_toc(html_content)
    
    return render_template('post.html', 
                         post=post, 
                         content=content,
                         toc=toc)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    if content:
        comment = Comment(content=content, post=post, author=current_user)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!')
    return redirect(url_for('post', post_id=post_id))

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        flash('You cannot delete this comment!')
        return redirect(url_for('post', post_id=comment.post_id))
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!')
    return redirect(url_for('post', post_id=comment.post_id))

@app.route('/category/<int:category_id>')
def category_posts(category_id):
    category = Category.query.get_or_404(category_id)
    posts = Post.query.filter_by(category_id=category_id).order_by(Post.date_posted.desc()).all()
    categories = Category.query.all()
    return render_template('home.html', posts=posts, category=category, categories=categories)

@app.route('/tag/<int:tag_id>')
def tag_posts(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    return render_template('tag.html', tag=tag)

@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({'status': 'unliked', 'count': post.like_count()})
    
    like = PostLike(user_id=current_user.id, post_id=post_id)
    db.session.add(like)
    db.session.commit()
    return jsonify({'status': 'liked', 'count': post.like_count()})

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    categories = Category.query.all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category')
        
        if not title or not content:
            flash('标题和内容不能为空', 'danger')
            return render_template('create_post.html', categories=categories)
        
        # Handle image upload
        image = request.files.get('image')
        image_path = None
        if image and allowed_file(image.filename):
            try:
                filename = secure_filename(image.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # Create uploads directory if it doesn't exist
                os.makedirs('static/uploads', exist_ok=True)
                
                # Save image
                full_path = os.path.join('static/uploads', filename)
                image.save(full_path)
                image_path = f"uploads/{filename}"
                
            except Exception as e:
                flash('图片上传失败', 'danger')
                return render_template('create_post.html', categories=categories)
            
        post = Post(
            title=title,
            content=content,
            author=current_user,
            category_id=category_id if category_id else None,
            image=image_path
        )
            
        # 生成摘要
        post.generate_summary()
        
        try:
            db.session.add(post)
            db.session.commit()
            flash('文章发布成功！', 'success')
            return redirect(url_for('post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            flash('发布失败，请稍后重试', 'danger')
            app.logger.error(f'Error creating post: {str(e)}')
            
    return render_template('create_post.html', categories=categories)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!')
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.category_id = request.form.get('category_id', None)
        
        # 处理标签
        post.tags = []
        tag_names = request.form.get('tags', '').split(',')
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                post.tags.append(tag)
        
        # 处理特色图片
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                post.image = 'uploads/' + filename
        
        try:
            db.session.commit()
            flash('文章更新成功！', 'success')
            return redirect(url_for('post', post_id=post.id))
        except:
            db.session.rollback()
            flash('更新失败，请稍后重试。', 'error')
    
    categories = Category.query.all()
    return render_template('edit_post.html', post=post, categories=categories)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('home'))
        
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 在标题、内容和标签中搜索
    pagination = Post.query.filter(
        db.or_(
            Post.title.ilike(f'%{query}%'),
            Post.content.ilike(f'%{query}%'),
            Post.tags.any(Tag.name.ilike(f'%{query}%'))
        )
    ).order_by(Post.date_posted.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    posts = pagination.items
    
    return render_template('search.html', 
                         posts=posts,
                         pagination=pagination,
                         query=query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            flash('Logged in successfully')
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully')
    return redirect(url_for('home'))

@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).all()
    return render_template('profile.html', user=user, posts=posts)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        try:
            # 检查用户名是否已被使用
            if request.form.get('username') != current_user.username:
                existing_user = User.query.filter_by(username=request.form.get('username')).first()
                if existing_user:
                    flash('用户名已被使用，请选择其他用户名。', 'error')
                    return redirect(url_for('settings'))
            
            # 检查邮箱是否已被使用
            if request.form.get('email') != current_user.email:
                existing_email = User.query.filter_by(email=request.form.get('email')).first()
                if existing_email:
                    flash('邮箱已被注册，请使用其他邮箱。', 'error')
                    return redirect(url_for('settings'))
            
            # 更新基本信息
            current_user.username = request.form.get('username', current_user.username)
            current_user.email = request.form.get('email', current_user.email)
            current_user.bio = request.form.get('bio', '')
            current_user.location = request.form.get('location', '')
            current_user.website = request.form.get('website', '')
            
            # 更新密码（如果提供）
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if current_password and new_password and confirm_password:
                if not current_user.check_password(current_password):
                    flash('当前密码不正确。', 'error')
                    return redirect(url_for('settings'))
                    
                if new_password != confirm_password:
                    flash('新密码和确认密码不匹配。', 'error')
                    return redirect(url_for('settings'))
                    
                if len(new_password) < 6:
                    flash('新密码长度必须至少为6个字符。', 'error')
                    return redirect(url_for('settings'))
                    
                current_user.set_password(new_password)
                flash('密码已成功更新！', 'success')
            
            db.session.commit()
            flash('个人信息更新成功！', 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Settings update error: {str(e)}')
            flash('更新失败，请稍后重试。', 'error')
            
        return redirect(url_for('settings'))
    
    return render_template('settings.html')

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('没有选择文件', 'error')
        return redirect(url_for('settings'))
    
    file = request.files['avatar']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('settings'))
    
    if file and allowed_file(file.filename):
        # 删除旧的头像文件（如果存在）
        if current_user.avatar:
            old_avatar = os.path.join(app.static_folder, 'uploads', current_user.avatar)
            if os.path.exists(old_avatar):
                os.remove(old_avatar)
        
        # 保存新的头像文件
        filename = secure_filename(file.filename)
        # 使用用户ID和时间戳确保文件名唯一
        filename = f"avatar_{current_user.id}_{int(time.time())}_{filename}"
        file.save(os.path.join(app.static_folder, 'uploads', filename))
        
        # 更新数据库中的头像信息
        current_user.avatar = filename
        db.session.commit()
        
        flash('头像上传成功！', 'success')
    else:
        flash('不支持的文件格式。请上传 PNG、JPG 或 GIF 格式的图片。', 'error')
    
    return redirect(url_for('settings'))

@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('你不能关注自己！')
        return redirect(url_for('profile', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(f'你已经成功关注 {username}！')
    return redirect(url_for('profile', username=username))

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('你不能取消关注自己！')
        return redirect(url_for('profile', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'你已经取消关注 {username}。')
    return redirect(url_for('profile', username=username))

@app.route('/messages')
@login_required
def messages():
    # 获取用户的所有消息
    messages_received = current_user.messages_received.order_by(
        Message.timestamp.desc()
    ).all()
    messages_sent = current_user.messages_sent.order_by(
        Message.timestamp.desc()
    ).all()
    
    # 将未读消息标记为已读
    for message in messages_received:
        if not message.read:
            message.read = True
    db.session.commit()
    
    return render_template('messages.html', 
                         messages_received=messages_received,
                         messages_sent=messages_sent)

@app.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            msg = Message(
                sender=current_user,
                recipient=user,
                content=content
            )
            db.session.add(msg)
            db.session.commit()
            
            # 创建通知
            notification = Notification(
                user_id=user.id,
                message=f'你收到了来自 {current_user.username} 的新消息'
            )
            db.session.add(notification)
            db.session.commit()
            
            flash('消息已发送！', 'success')
            return redirect(url_for('messages'))
    return render_template('send_message.html', recipient=user)

@app.route('/api/messages/unread')
@login_required
def get_unread_messages():
    unread_messages = current_user.messages_received.filter_by(read=False).all()
    messages_data = [{
        'id': msg.id,
        'sender': msg.sender.username,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
        'read': msg.read
    } for msg in unread_messages]
    return jsonify(messages_data)

@app.route('/api/messages/recent')
@login_required
def get_recent_messages():
    # 获取最近的10条消息
    recent_messages = current_user.messages_received.order_by(
        Message.timestamp.desc()
    ).limit(10).all()
    messages_data = [{
        'id': msg.id,
        'sender': msg.sender.username,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
        'read': msg.read
    } for msg in recent_messages]
    return jsonify(messages_data)

@app.route('/api/messages/mark_read/<int:message_id>')
@login_required
def mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)
    if message.recipient_id != current_user.id:
        abort(403)
    message.read = True
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/notifications')
@login_required
def notifications():
    # 将所有未读通知标记为已读
    current_user.notifications.filter_by(read=False).update({'read': True})
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    notifications = current_user.notifications.order_by(
        Notification.timestamp.desc()).paginate(
            page=page, per_page=10, error_out=False)
    return render_template('notifications.html', notifications=notifications)

@app.route('/archives')
def archives():
    # 获取所有文章按年月分组
    posts = db.session.query(
        extract('year', Post.date_posted).label('year'),
        extract('month', Post.date_posted).label('month'),
        func.count(Post.id).label('count')
    ).group_by(
        extract('year', Post.date_posted),
        extract('month', Post.date_posted)
    ).order_by(desc('year'), desc('month')).all()
    
    # 组织数据结构
    archives = {}
    for year, month, count in posts:
        if year not in archives:
            archives[year] = []
        archives[year].append({
            'month': month,
            'count': count,
            'url': url_for('archive_posts', year=int(year), month=int(month))
        })
    
    return render_template('archives.html', archives=archives)

@app.route('/archives/<int:year>/<int:month>')
def archive_posts(year, month):
    # 获取指定年月的文章
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
        
    posts = Post.query.filter(
        Post.date_posted >= start_date,
        Post.date_posted < end_date
    ).order_by(Post.date_posted.desc()).all()
    
    return render_template('archive_posts.html', 
                         year=year, 
                         month=month, 
                         posts=posts)

@app.route('/sitemap.xml')
def sitemap():
    """Generate sitemap.xml."""
    pages = []
    
    # 设置10分钟前的时间作为最后修改时间
    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
    
    # 添加静态页面
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:
            pages.append([url_for(rule.endpoint, _external=True), ten_minutes_ago])
    
    # 添加文章页面
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    for post in posts:
        url = url_for('post', post_id=post.id, _external=True)
        modified_time = post.last_modified or post.date_posted
        pages.append([url, modified_time])
    
    # 添加分类页面
    categories = Category.query.all()
    for category in categories:
        url = url_for('category_posts', category_id=category.id, _external=True)
        pages.append([url, ten_minutes_ago])
    
    # 添加标签页面
    tags = Tag.query.all()
    for tag in tags:
        url = url_for('tag_posts', tag_id=tag.id, _external=True)
        pages.append([url, ten_minutes_ago])
        
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    
    return response

@app.route('/api/posts')
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    posts_data = []
    for post in posts.items:
        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content[:200] + '...',
            'date_posted': post.date_posted.strftime('%Y-%m-%d'),
            'views': post.views,
            'comments_count': len(post.comments) if post.comments else 0
        }
        
        if post.category:
            post_data['category_id'] = post.category_id
            post_data['category_name'] = post.category.name
            
        posts_data.append(post_data)
    
    return jsonify({'posts': posts_data})

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({'success': False, 'message': '请提供密码'})
            
        if not current_user.check_password(data['password']):
            return jsonify({'success': False, 'message': '密码不正确'})
            
        # 删除用户的所有内容
        Comment.query.filter_by(user_id=current_user.id).delete()
        Post.query.filter_by(user_id=current_user.id).delete()
        Message.query.filter(
            (Message.sender_id == current_user.id) | 
            (Message.recipient_id == current_user.id)
        ).delete()
        Notification.query.filter_by(user_id=current_user.id).delete()
        PostLike.query.filter_by(user_id=current_user.id).delete()
        
        # 删除头像文件
        if current_user.avatar:
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
        
        # 删除用户账号
        db.session.delete(current_user)
        db.session.commit()
        
        logout_user()
        flash('你的账号已被永久删除。', 'info')
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Account deletion error: {str(e)}')
        return jsonify({'success': False, 'message': '删除失败，请稍后重试'})

def get_database_url():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./db.sqlite3')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return database_url

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
