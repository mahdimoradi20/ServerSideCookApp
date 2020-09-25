from flask import Flask,jsonify ,request,render_template,redirect, flash
import config
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user
)
import requests
import sqlite3




def wLog(title , content):
    db  = get_database_connection();
    cur = db.cursor()
    cur.execute("INSERT INTO logs (title , content) values(? , ?)" , (title,content))
    db.commit()
    db.close()


def addToPoll(ids):
    db = get_database_connection()
    cur = db.cursor()
    for food_id in ids:
        try:
            cur.execute("INSERT INTO sendPoll (id) VALUES (?)" , (food_id))
            db.commit()
        except Exception as e:
            wLog("error" , f"when we wanted to insert data to sendPoll we got this error{e}")
    
    for food_id in ids:
        try:
            cur.execute("UPDATE recipes set isPolling='true' where id={0}".format(food_id))
            db.commit()
        except Exception as e:
            wLog("error" , f"when we wanted to update reciped after polling we got this error {e}")
    db.close()




def PushNotif(content_for_push):
    
    addToPoll(content_for_push['items'])
    to = "/topics/getUpdates"
    data = { 'type' : 'getNewRecipe'  , 'content' : "newFoods" , 'count' : str(len(content_for_push['items']))}
    print(to , data)
    baseURLforPush = 'https://fcm.googleapis.com/fcm/send'
    myobj = {'to': to , 'data' : data }
    x = requests.post(baseURLforPush, json = myobj, headers = {"Content-Type": "application/json" , "Authorization" : "Key=" + config.SERVER_KEY})
    wLog("info" , "a push notofication has been sended with return text ->" + x.text)
    return x.text

def getRecipes():
    db = get_database_connection()
    cur = db.cursor()
    cur.execute("SELECT id ,title, catid , ing , rec , isPolling FROM Recipes")
    dt = cur.fetchall()
    db.close()
    return dt

def get_database_connection():
    """Connect to the sqlite database and return this connection"""
    conn = sqlite3.connect(database= "databases/server.db")
    return conn


app = Flask(__name__ , static_url_path="")
app.secret_key = config.APP_SECRET
login_manager = LoginManager()
login_manager.init_app(app)

#this starts here

# Our mock database.
class User(UserMixin):
    """ A minimal and singleton user class used only for administrative tasks """
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return "%d" % (self.id)
user = User(0)

@app.errorhandler(401)
def unauthorized(error):
    """ handling login failures"""
    wLog("unauthorized" , str(error))
    return redirect('/login')

@login_manager.user_loader
def load_user(userid):
    return User(userid)

@app.route("/login" , methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect('/panel')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if password == config.PASSWORD and username == config.USERNAME:
            login_user(user)
            wLog("login" , f"a user with username {username} logged in ")
            return redirect('/panel')
        else:
            flash("نام کاربری یا رمز عبور اشتباه است" , "warning")
            return redirect("/login")
    else:
        return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    """ logs out the admin user"""
    logout_user()
    wLog("logout" , "user logged out")
    return redirect('/login')

#*******This ends here

@app.route("/panel")
@login_required
def panel():
    data = []
    for rec in getRecipes():
        title = rec[0]
        name = rec[1][:20]
        cat = rec[2]
        ing = rec[3][:30]
        rec_t = rec[4][:40]
        isPolling = rec[5]
        data.append([title , name , cat , ing , rec_t , isPolling])
    wLog("info" , "user wanted to see the recipes list")
    return render_template("index.html" ,recipes = data)

@app.route("/insertNew")
@login_required
def insertNew():
    return render_template("insertNew.html")


@app.route("/sendPushNotif" , methods = ["GET" , "POST"])
@login_required
def sendPushNotif():
    if request.method == 'POST':
        items = []
        for i in request.form:
           items.append(request.form[i])
        PushNotif({'items' : items})
    return redirect('/recipes')

@app.route("/recipes")
@login_required
def ret_receipes():
    data = []
    for rec in getRecipes():
        title = rec[0]
        name = rec[1][:20]
        cat = rec[2]
        ing = rec[3][:30]
        rec_t = rec[4][:40]
        isPolling = rec[5]
        data.append([title , name , cat , ing , rec_t , isPolling])
    wLog("info" , "user wanted to see the recipes list")
    return render_template("recipes.html" , recipes = data)


@app.route("/getNewFoods/<apikey>")
def getNewFoods(apikey):
    if apikey == config.API_KEY:
        recipes = []
        db = get_database_connection()
        cur = db.cursor()
        cur.execute("SELECT id from sendPoll")
        ids = [str(x[0]) for x in cur.fetchall()]
        sql = "SELECT id , catid , ing , rec, title , pic, res1 ,res2 FROM recipes WHERE id IN ({0})".format(','.join(ids))
        cur.execute(sql)
        foods = list(cur.fetchall())
        db.close()
        for food in foods:
            recipes.append({"id": food[0] , "catid" : food[1] ,"ing":food[2] , "rec":food[3] , "name":food[4] ,"pic" :food[5] , "res1":food[6] , "res2":food[7] })
        
        return jsonify({'recipes' : recipes})
    else:
        return jsonify({'error' : 'not a valid api key, please send us a valid one, maybe you just enter the wrong key'})



@app.route('/insertRec' , methods  = ['GET' , 'POST'])
@login_required
def insertRec():
    if request.method == "POST":
        title = request.form['title']
        pic = request.form['pic']
        cat = request.form['cat']
        ing = request.form['ing']
        rec = request.form['rec']
        db = get_database_connection()
        try:
            cur = db.cursor()
            cur.execute("""INSERT INTO Recipes (title , pic , catid , ing , rec , isPolling) VALUES
                            (? ,? , ? , ? ,? ,?) """ , (title , pic , cat , ing , rec , 'false'))
            db.commit()
            
            wLog("info",f"user insrted recipe with title '{title}' in data base")
            flash("با موفقیت درج شد" , "info")
            return render_template("insertNew.html")
        except Exception as e:
            wLog("error" , f"when user wanted to insert recipe this error happend -> {e} ")
            flash("خطایی رخ داد و درج نشد" , "danger")
            return render_template( "insertNew.html")
        finally:
            db.close()

@app.route("/")
def indexPage():
    return redirect("/login")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')

@app.route('/saveUserToken/<apikey>/<token>')
def get_token(apikey,token):
    if apikey == config.API_KEY:
        if saveToken(token) == "well":
            return "OK"
        else:
            return "ERR"
    else:
        return "wrongApiKey"

def saveToken(token):

    arguments =(token , "")
    db = get_database_connection()
    try:
        
        cur = db.cursor()
        cur.execute("INSERT INTO Users (token,username) values (?,?)" , arguments)
        db.commit()
        return "well"
    except Exception as e:
        return "ERR"
    finally:
        db.close()




if __name__ == "__main__":
    db = get_database_connection()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Recipes (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT ,
    pic TEXT,
    catid INT,
    ing TEXT,
    rec TEXT,
    res1 TEXT,
    res2 TEXT,
    isPolling TEXT,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT ,
    content TEXT,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sendPoll (
    id INTEGER PRIMARY KEY,
    cRecived TEXT ,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Users (
    id INTEGR PRIMARY KEY,
    token TEXT ,
    username TEXT,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    db.close()
    app.run(host="0.0.0.0" , port= "8080" , debug=True)