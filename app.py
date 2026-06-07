from flask import Flask, request
import requests
import urllib3

# ביטול אזהרות אבטחה על תעודות SSL חסרות
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def api_get(url):
    r = requests.get(url, verify=False)
    return r.json()

def login(user, password):
    r = api_get(f"https://call2all.co.il/ym/api/Login?path=ivr2:/&username={user}&password={password}")
    if r.get("responseStatus") != "OK":
        raise Exception("Login failed")
    return r["token"]

def upload_file(token, path, name, content):
    requests.post(
        f"https://call2all.co.il/ym/api/UploadFile?path={path}/{name}&token={token}",
        data=content,
        verify=False
    )

def copy_dir(src_token, dst_token, src_path, dst_path):
    data = api_get(f"https://call2all.co.il/ym/api/GetIVR2Dir?path=ivr2:{src_path}/&token={src_token}")
    if data.get("responseStatus") != "OK":
        return ""

    out = ""

    for f in data.get("files", []):
        content = requests.get(
            f"https://call2all.co.il/ym/api/DownloadFile?path={f['what']}&token={src_token}",
            verify=False
        ).content
        upload_file(dst_token, f"ivr2:{dst_path}", f["name"], content)
        out += f"הועתק קובץ: {f['name']}<br>"

    for d in data.get("dirs", []):
        out += copy_dir(
            src_token,
            dst_token,
            f"{src_path}/{d['name']}".strip("/"),
            f"{dst_path}/{d['name']}".strip("/")
        )

    return out

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        src_user = request.form["src_user"]
        src_pass = request.form["src_pass"]
        src_path = request.form["src_path"].strip("/")

        dst_user = request.form["dst_user"]
        dst_pass = request.form["dst_pass"]
        dst_path = request.form["dst_path"].strip("/")

        try:
            src_token = login(src_user, src_pass)
            dst_token = login(dst_user, dst_pass)
            result = copy_dir(src_token, dst_token, src_path, dst_path)
            api_get(f"https://call2all.co.il/ym/api/Logout?token={src_token}")
            api_get(f"https://call2all.co.il/ym/api/Logout?token={dst_token}")
            return "<h2 dir='rtl'>ההעתקה הושלמה</h2><div dir='rtl'>" + result + "</div>"
        except Exception as e:
            return "<h2 dir='rtl'>שגיאה בהעתקה או בהתחברות</h2>"

    return """
    <html dir="rtl"><body style="font-family: Arial;">
    <h2>העתקת מערכת (ימות המשיח)</h2>
    <form method="post">
    <h3>מערכת מקור</h3>
    מספר מערכת:<br><input name="src_user" required><br>
    סיסמה:<br><input type="password" name="src_pass" required><br>
    שלוחה (ריק = הכל):<br><input name="src_path"><br><br>

    <h3>מערכת יעד</h3>
    מספר מערכת:<br><input name="dst_user" required><br>
    סיסמה:<br><input type="password" name="dst_pass" required><br>
    שלוחה יעד:<br><input name="dst_path"><br><br>

    <button type="submit">התחל העתקה</button>
    </form>
    </body></html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
