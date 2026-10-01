from flask import Flask, escape, session, request, render_template, send_from_directory, redirect, url_for
from flask_triangle import Triangle
from flask_caching import Cache


app = Flask(__name__)
app.config['CACHE_TYPE'] = 'SimpleCache'
cache = Cache()
cache.init_app(app)
Triangle(app)
app.secret_key = 'sdf78dfsSsdf78sdf'

from src import routes
from src import api
