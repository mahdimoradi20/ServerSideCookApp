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
    db  = get_database_connection(config.LOG_DB_PATH);
    cur = db.cursor()
    cur.execute("INSERT INTO logs (title , content) values(? , ?)" , (title,content))
    db.commit()
    db.close()


def addToPoll(ids):
    db = get_database_connection()
    cur = db.cursor()
    for food_id in ids:
        try:
            cur.execute(f"INSERT INTO sendPoll (id) VALUES ({food_id})" )
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

def PushNotifForMessaging(content):
    to = content['token']
    data = { 'type' : 'message'  , 'messageid' : content['messageid']}
    myobj = {'to': to , 'data' : data }
    baseURLforPush = 'https://fcm.googleapis.com/fcm/send'
    x = requests.post(baseURLforPush, json = myobj, headers = {"Content-Type": "application/json" , "Authorization" : "Key=" + config.SERVER_KEY})
    wLog("info" , "a push notofication has been sended with return text ->" + x.text)
    return x.text



def get_database_connection(pathforDB=config.DATABASE_PATH):
    """Connect to the sqlite database and return this connection"""
    conn = sqlite3.connect( database = pathforDB)
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


@app.route("/sendMessages/<apiKey>" , methods = ['GET' , 'POST'])
def getMessages(apiKey):
    if apiKey == config.API_KEY:
        if request.method == 'POST':
            u_token = request.form['token']
            u_text= request.form['text']
            u_time = request.form['time']
            try:
                db = get_database_connection()
                cur = db.cursor()
                cur.execute("INSERT INTO Messages (token,text , time,sender) values (?,?,? , 'user')" , (u_token , u_text , u_time))
                db.commit()
                db.close()
                return "OK"
            except Exception as e:
                return "Error"
        else:
            return "Send a post Request"
    else:
        return "Wrong Api Key"



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




@app.route('/sendMessageToUser' , methods = ['GET' , 'POST'])
@login_required
def sendMessageToUser():
    if request.method == 'POST':
        try:
            db = get_database_connection()
            c = db.cursor()
            text = request.form['text']
            now = request.form['time']
            u_token = request.form['token']
            c.execute("INSERT INTO Messages (text , time , sender, token) VALUES (?,?,'server',?)" , (text,now , u_token))
            db.commit()
            c.execute("select last_insert_rowid();")
            mid = c.fetchall()[0][0]
            ret = PushNotifForMessaging({'token' : "/topics/getUpdates" , 'messageid' : str(mid) })
            db.close()
            return ret
        except Exception as e:
            return "ERROR"
    else:
        return render_template("SendMessage.html")



@app.route('/getMessage/<apikey>/<mid>/<u_token>')
def getMessageByID(apikey, mid, u_token):
    if apikey ==config.API_KEY:
        try:
            db = get_database_connection()
            c = db.cursor()
            query = f"SELECT text,time FROM Messages WHERE id = {mid} and sender = 'server'"
            c.execute(query)
            msg = c.fetchall()
            db.close()
            content = list(msg[0])
            return jsonify({'msg' : {'body' : content[0] , 'time' : content[1]} })

        except Exception as e:
            return "ERROR"
    else:
        return "WrongAPIKEY"


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

@app.route("/users")
def usersPage():
    return render_template("users.html")

def getRecipes():
    db = get_database_connection()
    cur = db.cursor()
    cur.execute("SELECT id ,title, catid , ing , rec , isPolling FROM Recipes")
    dt = cur.fetchall()
    db.close()
    return dt

def getRecipesById(fid):
    db = get_database_connection()
    cur = db.cursor()
    cur.execute(f"SELECT id ,title, catid , pic , ing , rec , isPolling FROM Recipes WHERE id = {fid}")
    dt = cur.fetchone()
    db.close()
    return dt


@app.route("/sendStatic/<apiKey>/<key>/<value>")
def getStatic(apiKey , key , value):
    if apiKey == config.API_KEY:
        try:
            if key == "addCountRecipes":
                db = get_database_connection()
                c = db.cursor()
                c.execute("UPDATE sendPoll SET cRecived = cRecived + 1 where id = ?" , (value))
                db.commit()
                db.close()
                return "OKGOTIT"
            return "WrongAPIKEY"
        except Exception as e:
            wLog("error" , f"while we wanted to add statistics about counting recivers of recipe {value} we got this : {e}")
            return "There was an error"

@app.route("/editrec/<fid>" , methods = ['GET' , 'POST'])
@login_required
def editrec(fid):
    if request.method == 'POST':
        title = request.form['title']
        pic = request.form['pic']
        cat = request.form['cat']
        ing = request.form['ing']
        rec = request.form['rec']
        db = get_database_connection()
        try:
            cur = db.cursor()
            cur.execute("""UPDATE Recipes set title = ? , pic = ? , catid = ?, ing = ? , rec = ? , isPolling = ?
                        WHERE id = ? """ , (title , pic , cat , ing , rec , 'false' , fid))
            db.commit()

            wLog("info",f"user updated recipe with title '{title}' in data base")
            flash("ویرایش شد" , "info")
            return render_template("edit.html" , data = {"fid" : fid , 'recipe' : getRecipesById(fid)})
        except Exception as e:
            wLog("error" , f"when user wanted to update recipe this error happend -> {e} ")
            flash("خطایی رخ داد و درج نشد" , "danger")
            return render_template( "edit.html" , data = {"fid" : fid , 'recipe' : getRecipesById(fid)})
        finally:
            db.close()
    elif request.method == 'GET':

        return render_template('edit.html' , data = {"fid" : fid , 'recipe' : getRecipesById(fid)})


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


def getPool():

    db  = get_database_connection();
    cur = db.cursor()
    cur.execute("SELECT Recipes.id , Recipes.title, sendPoll.cRecived FROM Recipes  , sendPoll where Recipes.id = sendPoll.id and Recipes.isPolling = 'true'")
    dt = cur.fetchall()
    db.close()
    return dt

@app.route("/delFromPoll/<fid>")
def delFromPoll(fid):
    flash("با موفقیت از صف حذف شد" , "info")
    db = get_database_connection()
    cur = db.cursor()
    cur.execute(f"Update Recipes set isPolling = 'false' where id = {fid}")
    cur.execute(f"DELETE FROM sendPoll where id = {fid}")
    db.commit()
    db.close()
    return redirect("/recPoll")


@app.route("/recPoll")
def getRecPool():
    dt = getPool()
    return render_template("recpool.html" , data = {"data" : dt})

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
    CREATE TABLE IF NOT EXISTS sendPoll (
    id INTEGER PRIMARY KEY,
    cRecived INTEGER DEFAULT 0 ,
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT ,
    text TEXT,
    sender TEXT,
    time TEXT
    );
    """)
    db.close()
    app.run(host="0.0.0.0" , port= "8080" , debug=True)