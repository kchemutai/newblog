import os, secrets
from PIL import Image
from blog import app, bcrypt, db, mail
from blog.forms import LoginForm,RegistrationForm, AccountUpdateForm,PostForm, ResetPasswordForm, RequestResetPasswordForm 
from blog.models import User, Post
from flask import render_template, url_for, flash, redirect, request, abort
from datetime import datetime
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.urls import url_parse
from flask_mail import Message



@app.route('/')
@app.route('/home')
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('index.html', posts=posts)

@app.route('/about')
def about():
    return render_template('about.html', title="About")

@app.route('/register', methods=['get','post'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))  
    form = RegistrationForm()
    if form.validate_on_submit():
        hashedPassword = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashedPassword)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}. You can now Login', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title="Register Me", form=form)

@app.route('/login', methods=['get', 'post'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('home')
            return redirect(next_page)
        else:
            flash('Login Unsuccessful, Please check your username and Password', 'danger')
    return render_template('login.html', title="Sign In", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

# saves the picture from the form to the images folder in our app
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)  # generates a random string to be used as file name
    _, file_extension = os.path.splitext(form_picture.filename)  #splits the name and extension into 2 parts
    picture_filename = random_hex + file_extension # combines the randomly generated file name to the extension go above
    picture_path = os.path.join(app.root_path, 'static/images', picture_filename) # concats the path from the root directory of the app to images folder and the appends the filename
    
    #resize the picture to 125X125
    output_size=(125,125)
    img = Image.open(form_picture)
    img.thumbnail(output_size)

    img.save(picture_path) #saves the resized picture in the picture path

    return picture_filename    # this can be used in the database Model to point to the picture
    
 

@app.route('/account', methods=['post', 'get'])
@login_required
def account():
    form = AccountUpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data) # returns the picture filename
            current_user.image_file = picture_file # updates the image filename in the Account Model
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your Account has been Updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='images/'+current_user.image_file)
    return render_template('account.html', title="Account", image_file=image_file, form=form)


@app.route('/post/new', methods=['get','post'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('You post has successfully been created!', 'success')
        return redirect(url_for('home'))
    return render_template('new_post.html', title='New Post', form=form, legend='New Post')

@app.route('/post/<int:post_id>')
def post(post_id):
    post =Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route('/post/<int:post_id>/update', methods=['get', 'post'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your Post has been Updated', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == "GET":
        form.title.data = post.title
        form.content.data = post.content
    return render_template('new_post.html', title='Update Post', form=form, legend='Update Post')


@app.route('/post/<int:post_id>/delete', methods=['post'])
@login_required
def delete_post(post_id):
    post =Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your Post has been Deleted', 'success')
    return redirect(url_for('home'))


@app.route('/user/<string:username>')
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='kchemutai2@gmail.com', recipients=[user.email])
    msg.body = f''' To reset your password, visit the following link:
    {url_for('reset_token', token=token, _external=True)}
    If you did not make this request, Please ignore this email and no change will be made.
    '''
    mail.send(msg)

@app.route('/reset_password', methods=['post', 'get'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None:
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password', 'info')
            return redirect(url_for('login'))
    return render_template('reset_request.html', form=form, title='Reset Password')


@app.route('/reset_password/<token>', methods=['post', 'get'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashedPassword = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashedPassword
        db.session.commit()
        flash(f'Your Password has been updated. You can now Login', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', form=form, title='Reset Password')