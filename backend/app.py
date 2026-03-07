import os
import flask
from flask_mail import Mail, Message
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
import json
import re
import math
import datetime
from gtts import gTTS  # for voice responses
import base64
from io import BytesIO
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

app = flask.Flask(__name__)
bcrypt = Bcrypt(app)

app.config['SECRET_KEY'] = 'a_very_secret_key_for_session_management_12345'

# FIXED MONGODB CONNECTION
app.config["MONGO_URI"] = "mongodb://localhost:27017/studentloan"

mongo = PyMongo(app)
# --- Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vinayacharvinu282004@gmail.com'
app.config['MAIL_PASSWORD'] = 'llyr kcou mrkh pmlt'  # App password
app.config['MAIL_DEFAULT_SENDER'] = ('Loan Recommender', 'vinayacharvinu282004@gmail.com')

mail = Mail(app)



# ---------------- RULE-BASED BANK DATA ---------------- #
BANKS = [
    {
        "name": "State Bank of India", "min_amount": 0, "max_amount": 1000000, "interest_rate": 8.55,
        "package": "SBI Student Loan", "min_income": 0, "min_score": 55,
        "url": "https://sbi.co.in/web/personal-banking/loans/education-loans",
        "details": "SBI offers education loans with an interest rate of 8.55%, up to ₹10 lakh, and flexible repayment."
    },
    {
        "name": "HDFC", "min_amount": 100000, "max_amount": 15000000, "interest_rate": 10.50,
        "package": "HDFC Loan", "min_income": 150000, "min_score": 60,
        "url": "https://www.hdfcbank.com/personal/borrow/popular-loans/education-loan",
        "details": "HDFC provides education loans up to ₹15 lakh with an interest rate of 10.50%. Quick approval and easy EMI."
    },
    {
        "name": "Bank of Baroda", "min_amount": 0, "max_amount": 1500000, "interest_rate": 8.85,
        "package": "Baroda Scholar", "min_income": 100000, "min_score": 60,
        "url": "https://www.bankofbaroda.in/personal-banking/loans/education-loan/baroda-scholar",
        "details": "Bank of Baroda’s Baroda Scholar scheme offers loans up to ₹15 lakh with 8.85% interest."
    },
    {
        "name": "Canara Bank", "min_amount": 100000, "max_amount": 2000000, "interest_rate": 9.25,
        "package": "Vidya Turant", "min_income": 250000, "min_score": 65,
        "url": "https://canarabank.com/personal-banking/loans/education-loan",
        "details": "Canara Bank Vidya Turant provides education loans up to ₹20 lakh at 9.25% interest."
    },
    {
        "name": "Union Bank of India", "min_amount": 200000, "max_amount": 2500000, "interest_rate": 9.0,
        "package": "Union Education", "min_income": 300000, "min_score": 70,
        "url": "https://www.unionbankofindia.co.in/english/education-loan.aspx",
        "details": "Union Bank’s Union Education scheme offers loans up to ₹25 lakh with a 9.0% interest rate."
    },
    {
        "name": "Karnataka Bank", "min_amount": 400000, "max_amount": 2000000, "interest_rate": 9.18,
        "package": "KBL Vidhyanidhi", "min_income": 250000, "min_score": 80,
        "url": "https://www.google.com/search?q=apply+for+scholar+loan",
        "details": "Karnataka Bank’s KBL Vidhyanidhi provides loans up to ₹20 lakh with 9.18% interest rate."
    }
]

# ---------------- Validation Helpers ---------------- #
def validate_name(name):
    return bool(re.match(r"^[A-Za-z\s]+$", name))

def validate_phone(phone):
    return bool(re.match(r"^[0-9]{10,15}$", phone))

def validate_aadhaar(aadhaar):
    return bool(re.match(r"^[0-9]{12}$", aadhaar))

# ---------------- Academic & Recommendation Logic ---------------- #
def get_academic_score(data):
    study_type = data.get('study_type')
    try:
        if study_type == 'university':
            level = data.get('univ_level')
            if level == 'ug':
                total = float(data.get('t12_total') or 0)
                obtained = float(data.get('t12_obtained') or 0)
                return (obtained / total) * 100 if total > 0 else 0
            elif level == 'pg':
                cgpa = float(data.get('ug_cgpa') or 0)
                return cgpa * 9.5
        elif study_type == 'college':
            total = float(data.get('t10_total') or 0)
            obtained = float(data.get('t10_obtained') or 0)
            return (obtained / total) * 100 if total > 0 else 0
    except:
        return 0
    return 0

def recommend_banks(amount, income, score):
    matches = []
    for b in BANKS:
        # Calculate score difference
        score_gap = max(0, b['min_score'] - score)
        income_gap = max(0, b['min_income'] - income)
        amount_ok = b['min_amount'] <= amount <= b['max_amount']

        # If loan amount fits, compute suitability
        if amount_ok:
            match_score = (
                (income / (b['min_income'] + 1)) * 0.4 +
                (score / (b['min_score'] + 1)) * 0.4 +
                (1 / (b['interest_rate'] + 1)) * 0.2
            )
            matches.append((b, match_score))

    # Sort by best match score
    matches.sort(key=lambda x: x[1], reverse=True)

    # Return top 3 matches
    return [m[0] for m in matches[:3]]


# ---------------- RULE-BASED CHATBOT ---------------- #
@app.route('/chat', methods=['POST'])
def chat():
    data = flask.request.get_json() or {}
    message = data.get('message', '').strip().lower()

    if not message:
        return flask.jsonify({"response": "Please type a message.", "voice": None})

    response_text = ""

    # --- Common queries ---
    if any(word in message for word in ['hi', 'hello', 'hey']):
        response_text = "Hello! I’m your loan assistant. You can ask about bank loans, eligibility, or say 'list banks'."
    elif 'list' in message and 'bank' in message:
        names = ', '.join([b['name'] for b in BANKS])
        response_text = f"Our partner banks are: {names}."
    elif any(word in message for word in ['best', 'lowest interest']):
        best_bank = min(BANKS, key=lambda x: x['interest_rate'])
        response_text = f"The best bank with the lowest interest rate is {best_bank['name']} offering {best_bank['interest_rate']}% under the {best_bank['package']} package."
    elif 'loan' in message and 'apply' in message:
        response_text = "To apply for a loan, first fill your details in the recommendation form, then choose a bank and click 'Apply'."
    else:
        for b in BANKS:
            if b['name'].lower() in message:
                response_text = (
                    f"{b['name']} offers the {b['package']} package.\n"
                    f"Interest rate: {b['interest_rate']}%\n"
                    f"Eligible loan range: ₹{b['min_amount']:,} to ₹{b['max_amount']:,}\n"
                    f"Minimum income: ₹{b['min_income']:,}\n"
                    f"Minimum academic score: {b['min_score']}\n"
                    f"More info: {b['url']}\n\n"
                    f"{b['details']}"
                )
                break

    if not response_text:
        response_text = "I didn't understand that. Please ask about a specific bank, or say 'list banks' to see available options."

    # --- Convert text to speech safely ---
    try:
        tts = gTTS(text=response_text, lang='en')
        voice_bytes = BytesIO()
        tts.write_to_fp(voice_bytes)
        voice_bytes.seek(0)
        voice_base64 = base64.b64encode(voice_bytes.read()).decode('utf-8')
    except Exception as e:
        print("Voice generation error:", e)
        voice_base64 = None

    return flask.jsonify({"response": response_text, "voice": voice_base64})

# ---------------- AUTH ---------------- #
# ---------------- FORGOT & RESET PASSWORD ---------------- #
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Create secure serializer (place near app.config)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


# 1️⃣ Forgot Password page (GET)
@app.route('/forgot_password', methods=['GET'])
def forgot_password_page():
    return flask.render_template('forgot_password.html')


# 2️⃣ Forgot Password submit (POST)
@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = flask.request.get_json() or {}
    email = data.get('email')
    if not email:
        return flask.jsonify({"error": "Email is required"}), 400
    
    user = mongo.db.users.find_one({"email": email})
    if not user:
        return flask.jsonify({"error": "No account found with that email."}), 404

    try:
        # Generate secure token valid for 15 minutes
        token = serializer.dumps(email, salt='password-reset-salt')
        reset_url = f"http://127.0.0.1:5000/reset_password/{token}"

        msg = Message(
            subject="Password Reset Request - Student Loan Recommender",
            recipients=[email],
            body=(
                f"Hello {user['name']},\n\n"
                f"You requested a password reset. Click the link below:\n\n{reset_url}\n\n"
                f"This link is valid for 15 minutes.\n"
                f"If you didn’t request this, please ignore this email."
            )
        )
        mail.send(msg)
        return flask.jsonify({"message": "Password reset link sent to your email."}), 200
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500


# 3️⃣ Reset Password page (GET)
@app.route('/reset_password/<token>', methods=['GET'])
def reset_password_page(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=900)
        return flask.render_template('reset_password.html', token=token)
    except SignatureExpired:
        return "The reset link has expired.", 400
    except BadSignature:
        return "Invalid reset link.", 400


# 4️⃣ Reset Password submit (POST)
@app.route('/reset_password/<token>', methods=['POST'])
def reset_password_submit(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=900)
    except (SignatureExpired, BadSignature):
        return flask.jsonify({"error": "Invalid or expired reset link."}), 400

    data = flask.request.get_json() or {}
    new_password = data.get('password')
    if not new_password:
        return flask.jsonify({"error": "Password cannot be empty"}), 400

    hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
    mongo.db.users.update_one({"email": email}, {"$set": {"password": hashed_pw}})

    return flask.jsonify({"message": "Password reset successful! You can now log in."}), 200

@app.route('/register', methods=['POST'])
def register():
    data = flask.request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return flask.jsonify({"error": "Missing fields"}), 400
    if not validate_name(name):
        return flask.jsonify({"error": "Invalid name (only letters allowed)."}), 400
    if mongo.db.users.find_one({"email": email}):
        return flask.jsonify({"error": "Email already registered"}), 409

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    user_id = mongo.db.users.insert_one({
        "name": name, "email": email, "password": hashed_pw,
        "created_at": datetime.datetime.utcnow()
    }).inserted_id
    flask.session['user_id'] = str(user_id)
    flask.session['user_name'] = name
    return flask.jsonify({"message": "Registration successful!", "name": name}), 201

@app.route('/login', methods=['POST'])
def login():
    data = flask.request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    user = mongo.db.users.find_one({"email": email})
    if user and bcrypt.check_password_hash(user['password'], password):
        flask.session['user_id'] = str(user['_id'])
        flask.session['user_name'] = user['name']
        return flask.jsonify({"message": "Login successful!", "name": user['name']})
    return flask.jsonify({"error": "Invalid credentials"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    flask.session.clear()
    return flask.jsonify({"message": "Logged out"}), 200

@app.route('/check_session', methods=['GET'])
def check_session():
    if 'user_id' in flask.session:
        return flask.jsonify({"logged_in": True, "name": flask.session.get('user_name')}), 200
    else:
        return flask.jsonify({"logged_in": False}), 200

@app.route('/')
def index():
    return flask.render_template('index.html')

# ---------------- RECOMMENDATION ---------------- #
@app.route('/recommend', methods=['POST'])
def recommend():
    if 'user_id' not in flask.session:
        return flask.jsonify({"error": "You must be logged in"}), 401

    data = flask.request.get_json() or {}

    # Input validation
    if not validate_name(data.get('student_name', '')):
        return flask.jsonify({"error": "Invalid name. Only letters allowed."}), 400
    if not validate_phone(data.get('phone', '')):
        return flask.jsonify({"error": "Invalid phone. Only digits allowed."}), 400
    if not validate_aadhaar(data.get('aadhaar', '')):
        return flask.jsonify({"error": "Invalid Aadhaar. Must be 12 digits."}), 400

    try:
        fee = float(data.get('college_fee', 0))
        years = int(data.get('loan_years', 0))
        income = float(data.get('family_income', 0))
    except:
        return flask.jsonify({"error": "Numeric input error"}), 400

    total_amount = fee * years
    score = get_academic_score(data)
    banks = recommend_banks(total_amount, income, score)

    # ✅ FIX: Save the form data so /apply can access it
    flask.session['form_data'] = data

    return flask.jsonify({
        "total_amount": total_amount,
        "recommended_banks": banks
    })

# ---------------- APPLY ---------------- #
# ---------------- APPLY ---------------- #
@app.route('/apply', methods=['POST'])
def apply():
    if 'user_id' not in flask.session:
        return flask.jsonify({"error": "You must be logged in"}), 401

    bank_data = flask.request.get_json() or {}
    bank_name = bank_data.get('bank_name')
    loan_package = bank_data.get('loan_package')

    form_data = flask.session.get('form_data')
    if not form_data:
        return flask.jsonify({"error": "No form data found"}), 400

    student_name = form_data.get('student_name')
    student_email = form_data.get('email')
    if not all([student_name, student_email, bank_name, loan_package]):
        return flask.jsonify({"error": "Incomplete data"}), 400

    bank_url = next((b['url'] for b in BANKS if b['name'] == bank_name), "https://google.com")

    try:
        fee = float(form_data.get('college_fee', 0))
        years = int(form_data.get('loan_years', 0))
        total_loan_amount = fee * years
        score = get_academic_score(form_data)

        # Save application in database
        mongo.db.applications.insert_one({
            **form_data,
            'user_id': ObjectId(flask.session['user_id']),
            'applied_at': datetime.datetime.utcnow(),
            'selected_bank_name': bank_name,
            'selected_loan_package': loan_package,
            'total_loan_amount': total_loan_amount,
            'academic_score': score,
            'status': 'Pending'
        })

        # ---------------- Compose Detailed Email ---------------- #
        details = [
            f"Dear {student_name},",
            "",
            f"You have successfully applied for the {loan_package} from {bank_name}.",
            "",
            "Here are your full application details:",
            "-----------------------------------------",
            f"👤 Student Name: {form_data.get('student_name', 'N/A')}",
            f"📧 Email: {form_data.get('email', 'N/A')}",
            f"📞 Phone: {form_data.get('phone', 'N/A')}",
            f"🆔 Aadhaar: {form_data.get('aadhaar', 'N/A')}",
            f"🏠 Family Income: ₹{float(form_data.get('family_income', 0)):,.0f}",
            "",
            f"🎓 Study Type: {form_data.get('study_type', 'N/A').capitalize()}",
            f"📚 University Level: {form_data.get('univ_level', 'N/A').upper()}",
            f"🏫 10th Total Marks: {form_data.get('t10_total', 'N/A')} | Obtained: {form_data.get('t10_obtained', 'N/A')}",
            f"🏫 12th Total Marks: {form_data.get('t12_total', 'N/A')} | Obtained: {form_data.get('t12_obtained', 'N/A')}",
            f"📊 UG CGPA: {form_data.get('ug_cgpa', 'N/A')}",
            f"📈 Academic Score (calculated): {score:.2f}",
            "",
            f"💰 College Fee (per year): ₹{fee:,.0f}",
            f"📆 Loan Duration (years): {years}",
            f"💵 Total Loan Amount: ₹{total_loan_amount:,.0f}",
            "",
            f"🏦 Selected Bank: {bank_name}",
            f"📄 Loan Package: {loan_package}",
            f"🌐 Bank Website: {bank_url}",
            "",
            "-----------------------------------------",
            "Thank you for using our Student Loan Recommendation System!",
            "",
            "— Loan Recommender Team"
        ]

        subject = f"Loan Application Confirmation - {bank_name}"
        body = "\n".join(details)

        msg = Message(subject=subject, recipients=[student_email], body=body)
        mail.send(msg)

        return flask.jsonify({"message": "Application submitted & detailed email sent."})
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500
@app.route("/")
def home():
    return {"message": "Student Loan Recommendation API is running"}

if __name__ == '__main__':
    app.run(debug=True)

