from flask import Flask

app = Flask(__name__)

@app.route("/")
def inicio():
    return "SkillMatch funcionando"

if __name__ == "__main__":
    app.run(debug=True)