from flask import Flask, render_template
import os

app = Flask(__name__)

files = []

directory = 'C:\\Users\\Cyril\\Desktop\\FriendLens\\static\\assets\\Eternals 4K Wallpaper'

#for now, '/' is the home page, and not the login page
@app.route('/')
def index():
    return render_template('index.html', files=files)

@app.route('/feed')
def feed():
    return render_template('feed.html')

if __name__ == '__main__':
    app.run(debug=True)
