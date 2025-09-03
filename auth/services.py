import jwt
import datetime
from flask import jsonify, redirect, session
from config import JWT_SECRET_KEY
from auth import bcrypt
from auth.models import find_user_by_email, create_user

# def handle_signup(form):
#     name = form['name']
#     email = form['email']
#     password = form['password']

#     if find_user_by_email(email):
#         return "Email already exists", 400

#     hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
#     create_user(name, email, hashed_pw)
#     return redirect('/login')

def handle_signup(data):
    name = data['name']
    email = data['email']
    password = data['password']
    confirm_password = data.get('confirm_password')

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    if find_user_by_email(email):
        return jsonify({'error': 'Email already exists'}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    create_user(name, email, hashed_pw)

    user = find_user_by_email(email)

    # Optional: session (for navbar display)
    session['user'] = {
        'id': user[0],
        'name': user[1],
        'email': user[2]
    }

    payload = {
        'id': user[0],
        'name': user[1],
        'email': user[2],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return jsonify({'token': token})


# def handle_login(form):
#     email = form['email']
#     password = form['password']

#     user = find_user_by_email(email)
#     if not user:
#         return "Invalid credentials", 401

#     if not bcrypt.check_password_hash(user[3], password):  
#         return "Invalid credentials", 401

#     session['user'] = {'id': user[0], 'name': user[1], 'email': user[2]}
#     return redirect('/')



def handle_login(data):
    email = data['email']
    password = data['password']

    user = find_user_by_email(email)
    if not user or not bcrypt.check_password_hash(user[3], password):
        return "Invalid credentials", 401

    # Set user info in session (for template rendering)
    session['user'] = {
        'id': user[0],
        'name': user[1],
        'email': user[2]
    }

    # Create JWT token (for APIs or frontend)
    payload = {
        'id': user[0],
        'name': user[1],
        'email': user[2],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    return jsonify({
        'message': 'Login successful',
        'token': token
    })