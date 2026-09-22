import os
import csv
from io import StringIO
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
#from weasyprint import HTML

app = Flask(__name__)
app.secret_key = 'school_repair_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///repair_system.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class RepairRequest(db.Model):
    __tablename__ = 'repair_requests'
    id = db.Column(db.Integer, primary_key=True)
    request_no = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    building = db.Column(db.String(50), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    problem_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    urgency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='pending')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    cost = db.Column(db.Float)
    images = db.relationship('RepairImage', backref='request', lazy=True)

class RepairImage(db.Model):
    __tablename__ = 'repair_images'
    id = db.Column(db.Integer, primary_key=True)
    repair_id = db.Column(db.Integer, db.ForeignKey('repair_requests.id'), nullable=False)
    image_type = db.Column(db.String(10), nullable=False)
    image_path = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_request_no():
    now = datetime.now()
    count = RepairRequest.query.count() + 1
    return f"RP-{now.strftime('%Y%m')}-{str(count).zfill(3)}"


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_images(files, image_type, repair_id):
    """บันทึกรูปภาพที่อัปโหลดลง static/uploads และเพิ่มลงตาราง repair_images"""
    saved = 0
    for f in files:
        if not f or not f.filename or not allowed_file(f.filename):
            continue
        fname = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{repair_id}_{secure_filename(f.filename)}"
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        db.session.add(RepairImage(
            repair_id=repair_id,
            image_type=image_type,
            image_path=f'uploads/{fname}'
        ))
        saved += 1
    return saved


@app.route('/')
def index():
    # หน้าแรกสาธารณะ: ไม่ต้อง login ก็ดูรายการแจ้งซ่อมและสถานะภาพรวมได้
    total = RepairRequest.query.count()
    pending = RepairRequest.query.filter_by(status='pending').count()
    in_progress = RepairRequest.query.filter_by(status='in_progress').count()
    completed = RepairRequest.query.filter_by(status='completed').count()
    recent = RepairRequest.query.order_by(RepairRequest.id.desc()).limit(10).all()
    return render_template('index.html', total=total, pending=pending,
                           in_progress=in_progress, completed=completed, recent=recent)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('เข้าสู่ระบบสำเร็จ!', 'success')
            return redirect(url_for('dashboard'))
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    total = RepairRequest.query.count()
    pending = RepairRequest.query.filter_by(status='pending').count()
    in_progress = RepairRequest.query.filter_by(status='in_progress').count()
    completed = RepairRequest.query.filter_by(status='completed').count()
    recent = RepairRequest.query.order_by(RepairRequest.id.desc()).limit(10).all()
    return render_template('dashboard.html', total=total, pending=pending, in_progress=in_progress, completed=completed, recent=recent)

@app.route('/repair/create', methods=['GET', 'POST'])
@login_required
def create_repair():
    if request.method == 'POST':
        req_no = generate_request_no()
        new_req = RepairRequest(
            request_no=req_no,
            user_id=current_user.id,
            building=request.form.get('building'),
            room=request.form.get('room'),
            problem_type=request.form.get('problem_type'),
            description=request.form.get('description'),
            urgency=request.form.get('urgency')
        )
        db.session.add(new_req)
        db.session.commit()

        # บันทึกรูปภาพก่อนซ่อมที่อัปโหลดมาพร้อมฟอร์ม
        save_images(request.files.getlist('images_before'), 'before', new_req.id)
        db.session.commit()

        flash('สร้างใบแจ้งซ่อมเรียบร้อยแล้ว!', 'success')
        return redirect(url_for('repair_detail', repair_id=new_req.id))
    return render_template('repair_create.html')


@app.route('/repair/<int:repair_id>', methods=['GET', 'POST'])
@login_required
def repair_detail(repair_id):
    req = RepairRequest.query.get_or_404(repair_id)
    if request.method == 'POST':
        image_type = request.form.get('image_type', 'after')
        if image_type not in ('before', 'after'):
            image_type = 'after'
        saved = save_images(request.files.getlist('images'), image_type, req.id)
        db.session.commit()
        if saved:
            flash(f'อัปโหลดรูปภาพ {saved} รูป เรียบร้อยแล้ว', 'success')
        else:
            flash('ไม่พบไฟล์ หรือไฟล์ไม่ใช่รูปภาพที่รองรับ (png, jpg, jpeg, gif, webp)', 'danger')
        return redirect(url_for('repair_detail', repair_id=req.id))
    before_images = [i for i in req.images if i.image_type == 'before']
    after_images = [i for i in req.images if i.image_type == 'after']
    return render_template('repair_detail.html', req=req,
                           before_images=before_images, after_images=after_images)

@app.route('/export/csv')
@login_required
def export_csv():
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Request No', 'Building', 'Room', 'Type', 'Status'])
    for r in RepairRequest.query.all():
        writer.writerow([r.id, r.request_no, r.building, r.room, r.problem_type, r.status])
    res = make_response(si.getvalue())
    res.headers["Content-Disposition"] = "attachment; filename=repairs.csv"
    res.headers["Content-type"] = "text/csv"
    return res

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)