from flask import Flask, render_template

app = Flask(__name__)
temp = 5
@app.route('/')
def index():
    return render_template('index.html', temp=temp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    
