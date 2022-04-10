from datetime import timezone,datetime
import time
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import joblib,cv2,base64,numpy as np
from flask import Flask,render_template,request,redirect,url_for
import pyrebase

app = Flask(__name__)
model = joblib.load("captcha_model.pk1")   #model for captcha

firebaseConfig = {'apiKey': "AIzaSyBombDbD34sdAgyCZ245Uoe7QTxVgdpQgo",
  'authDomain': "vtop-course-page.firebaseapp.com",
  'projectId': "vtop-course-page",
  'storageBucket': "vtop-course-page.appspot.com",
  'databaseURL' : "https://vtop-course-page-default-rtdb.firebaseio.com/"
}
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

def b64_to_image(b64):
    b64_data = b64.split(',')[1]
    image = np.frombuffer(base64.b64decode(b64_data), np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
    return image

def get_captcha(base64_url):
    result = ""
    test_image = b64_to_image(base64_url)
    threshold, test_image = cv2.threshold(test_image,0.001,10**9,cv2.THRESH_BINARY)
    iterator = [0,30,60,90,120,150]
    for i in iterator:
        temp_img = test_image[10:,i:i+25]
        temp_img = temp_img.reshape(1,(temp_img.shape[0]*temp_img.shape[1]))
        prediction = model.predict(temp_img)[0]
        if prediction >= 10:
            result += chr(prediction)
        else:
            result += str(prediction)
    return result

#//div[@class="rc-imageselect-payload"]   # for selecting images to check if human


# **** Just for referring the format of url for downloading files ****
# https://vtop.vit.ac.in/vtop/downloadPdf/VL20212205/VL2021220504762/19/22-02-2022?authorizedID=21BIT0175&x=Tue,%2015%20Mar%202022%2018:48:00%20GMT
# https://vtop.vit.ac.in/vtop/downloadPdf/VL20212205/VL2021220504762/19/01-03-2022?authorizedID=21bit0175&x=Wed,%2016%20Mar%202022%2018:56:03%20UTC

def change_link(initial_link,reg_no):
    raw_data = str(datetime.now(timezone.utc)).split(".")[0]   # extracting time and formatting it for doc link
    raw_data2 = raw_data.split("-")
    year = raw_data2[0]
    date = raw_data2[2].split()[0]
    utc_time = raw_data.split()[1]
    month_num = raw_data2[1]
    day_name = datetime.now(timezone.utc).strftime("%A")[:3]
    month_name = datetime.now(timezone.utc).strptime(month_num, "%m").strftime("%b")
    time_component = day_name + ", " + date + " " + month_name + " " + year + " " + utc_time + " UTC"
    ans = "https://vtop.vit.ac.in/vtop/"+initial_link+"?authorizedID="+reg_no+"&x="+time_component   # final doc link
    return ans

def get_time_table_data(reg_no,vtop_password,sem_code):
    # **** until sign in ****
    ext = webdriver.ChromeOptions()
    ext.add_argument("--headless")
    driver = webdriver.Chrome(options=ext)
    wait = WebDriverWait(driver, 20)
    wait1 = WebDriverWait(driver, 2)
    wait2 = WebDriverWait(driver, 0.5)
    website = "https://vtop.vit.ac.in/vtop/initialProcess"
    driver.get(website)
    wait.until(ec.element_to_be_clickable((By.LINK_TEXT, "Login to VTOP"))).click()  # first log-in button
    wait.until(ec.element_to_be_clickable((By.XPATH, '//button[@onclick="openPage()"]'))).click()  # second log-in button
    username = wait.until(ec.element_to_be_clickable((By.ID, "uname")))  # entering username
    password = wait.until(ec.element_to_be_clickable((By.ID, "passwd")))  # entering password
    signinbn = wait.until(ec.element_to_be_clickable((By.ID, "captcha")))  # for clicking sign-in button
    try:
        decoded_captcha = get_captcha(driver.find_element(By.XPATH, '//img[@alt="vtopCaptcha"]').get_attribute("src"))
        captcha = wait.until(ec.element_to_be_clickable((By.ID, "captchaCheck")))
        captcha.send_keys(decoded_captcha)
    except:
        pass
    username.send_keys(reg_no)
    password.send_keys(vtop_password)
    signinbn.click()
    #until sign in end
    while True:
        try:
            wait2.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="menu-toggle"]'))).click()  # clicking on menu button
            break
        except:
            try:
                wait2.until(ec.element_to_be_clickable((By.XPATH, '// p[text() = "Invalid User Id / Password "]'))).click()
                return "Invalid ID/Password. Please Visit Home and enter the correct password"
            except:
                try:
                    wait2.until(ec._element_if_visible((By.XPATH, '//img[@alt="vtopCaptcha"]'))).click()
                    continue
                except:
                    try:
                        wait2.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="menu-toggle"]'))).click()
                        break
                    except:
                        return "Please Try Again!! Are You a Human Test Popped up !!"

    # time table
    data = {}
    # wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="menu-toggle"]'))).click()  # clicking on menu button
    wait.until(ec.element_to_be_clickable((By.XPATH, '//a[@href="#MenuBody6"]'))).click()  # clicking on academics
    wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="ACD0034"]'))).click()  # clicking on time table
    wait.until(ec.element_to_be_clickable((By.XPATH, '//option[@value="' + sem_code + '"]'))).click()  # selecting Winter Semester
    wait.until(ec.element_to_be_clickable((By.XPATH, '//div[@class="table-responsive"]//table')))
    class_numbers = driver.find_elements(By.XPATH, '//div[@class="table-responsive"]//table//tr//td[7]//p')
    course_names = driver.find_elements(By.XPATH, '//div[@class="table-responsive"]//table//tr//td[3]//p[1]')
    for i in range(len(class_numbers)):
        data[course_names[i].text] = class_numbers[i].text
    # wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="ACD0045"]'))).click()  # clicking on course page
    # time.sleep(1)
    # wait.until(ec.element_to_be_clickable((By.XPATH, '//option[@value="' + sem_code + '"]'))).click()  # selecting Winter Semester
    # time table end
    data["sem_code"] = sem_code
    db.child(reg_no.upper()).update(data)
    return 1

def get_course_page(reg_no,vtop_password,sem_code,course_details,class_number):

    # **** until sign in ****
    ext = webdriver.ChromeOptions()
    ext.add_argument("--headless")
    driver = webdriver.Chrome(options=ext)
    wait = WebDriverWait(driver, 20)
    wait1 = WebDriverWait(driver, 2)
    wait2 = WebDriverWait(driver, 0.5)
    website = "https://vtop.vit.ac.in/vtop/initialProcess"
    driver.get(website)
    wait.until(ec.element_to_be_clickable((By.LINK_TEXT, "Login to VTOP"))).click()  # first log-in button
    wait.until(ec.element_to_be_clickable((By.XPATH, '//button[@onclick="openPage()"]'))).click()  # second log-in button
    username = wait.until(ec.element_to_be_clickable((By.ID, "uname")))  # entering username
    password = wait.until(ec.element_to_be_clickable((By.ID, "passwd")))  # entering password
    signinbn = wait.until(ec.element_to_be_clickable((By.ID, "captcha")))  # for clicking sign-in button
    try:
        decoded_captcha = get_captcha(driver.find_element(By.XPATH, '//img[@alt="vtopCaptcha"]').get_attribute("src"))
        captcha = wait.until(ec.element_to_be_clickable((By.ID, "captchaCheck")))
        captcha.send_keys(decoded_captcha)
    except:
        pass
    username.send_keys(reg_no)
    password.send_keys(vtop_password)
    signinbn.click()
    # until sign in end
    while True:
        try:
            wait2.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="menu-toggle"]'))).click()  # clicking on menu button
            break
        except:
            try:
                wait2.until(ec.element_to_be_clickable((By.XPATH, '// p[text() = "Invalid User Id / Password "]'))).click()
                return "Invalid ID/Password. Please Visit Home and enter the correct password"
            except:
                try:
                    wait2.until(ec._element_if_visible((By.XPATH, '//img[@alt="vtopCaptcha"]'))).click()
                    continue
                except:
                    try:
                        wait2.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="menu-toggle"]'))).click()
                        break
                    except:
                        return "Please Try Again!! Are You a Human Test Popped up !!"

    wait.until(ec.element_to_be_clickable((By.XPATH, '//a[@href="#MenuBody6"]'))).click()  # clicking on academics
    wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="ACD0045"]'))).click()  # clicking on course page
    wait.until(ec.element_to_be_clickable((By.XPATH, '//option[@value="' + sem_code + '"]'))).click()  # selecting Winter Semester

    # final_data = list()
    check = True
    while True:
        try:
            wait.until(ec.element_to_be_clickable((By.XPATH, '//option[contains(text(),"--Choose Course --")]')))
            try:
                wait1.until(ec.element_to_be_clickable((By.XPATH, '//option[contains(text(),"' + course_details[:9].strip() + '")]'))).click() #selecting course
                break
            except:
                check = False
                break
        except:
            continue
    if check is False:
        return "Course not found under Course Page !!"
    while True:
        try:
            wait.until(ec.element_to_be_clickable((By.XPATH, '//tr//button')))
            try:
                wait1.until(ec.element_to_be_clickable((By.XPATH, '//tr[td="'+class_number+'"]//button'))).click()   #selecting professor
                # get data from course page
                res = {}
                counter = 1
                wait.until(ec.element_to_be_clickable((By.XPATH, '//table//a')))
                while True:
                    try:
                        wait2.until(ec.element_to_be_clickable((By.XPATH, '//table//tr[td="' + str(counter) + '"]')))
                    except:
                        break
                    try:
                        links = driver.find_elements(By.XPATH, '//table//tr[td="' + str(counter) + '"]//a')  # going through each row of table
                        document_name = driver.find_element(By.XPATH, '//table//tr[td="' + str(counter) + '"]//td[4]').text  # extracting document name
                        if document_name not in res.keys() and len(links) != 0:
                            res[document_name] = []
                        for link in links:
                            if "https://" not in link.get_attribute("href"):
                                res[document_name].append(link.get_attribute("href").split("('")[-1][:-2])  # extracting links
                            else:
                                res[document_name].append(link.get_attribute("href"))
                        counter += 1
                    except:
                        counter += 1
                        continue
                # get data from course page end
                # final_data.append([i.split("-")[1].strip(),res])
                wait.until(ec.element_to_be_clickable((By.XPATH, '//a[text()="Go Back"]'))).click()  #click on Go Back
                break
            except:
                return "Professor not found !!"
                break
        except:
            continue
    return res
    #return format --> {'Organometallic Chemistry- Introduction, Electron count, Hapticity and Oxidation State Determination': ['downloadPdf/VL20212205/VL2021220504762/19/22-02-2022'], 'Metals in Biology - Chlorophyll and Hemoglobin': ['downloadPdf/VL20212205/VL2021220504762/19/01-03-2022'], 'Stability, Structure and Applications of Heterocyclic Compounds': ['downloadPdf/VL20212205/VL2021220504762/19/10-03-2022'], 'Module-3: Introduction to Thermodynamics': ['downloadPdf/VL20212205/VL2021220504762/19/15-03-2022'], 'Third law of thermodynamics': ['downloadPdf/VL20212205/VL2021220504762/19/24-03-2022']}



def check_registration_number(reg_no):
    reg_no = reg_no.upper()
    data = db.child(reg_no).get()
    if data.each() is None:
        return False
    else:
        return True

def get_course_details(reg_no):
    sem_code = ""
    reg_no = reg_no.upper()
    data = db.child(reg_no).get()
    res = dict()
    for i in data.each():
        if i.key() != "sem_code":
            res[i.key()] = i.val()
        else:
            sem_code = i.val()
    return [res,sem_code]


@app.route("/",methods=["POST","GET"])
def main_app():
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        password = request.form["password"]
        # sem_code = request.form["sem_code"]
        # res = get_course_page(reg_no,password,sem_code,"BMAT102L - Differential Equations and Transforms","VL2021220504154")
        if (check_registration_number(reg_no)):
            output = get_course_details(reg_no)
            return render_template("course_selection.html",reg_no=reg_no,vtop_password=password,sem_code=output[1],course_list=output[0],check=0)
        else:
            return render_template("index.html", error= "Please Enroll first to use the services !!" )
    else:
        return render_template("index.html")

@app.route("/enroll",methods=["POST","GET"])
def enroll():
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        password = request.form["password"]
        sem_code = request.form["sem_code"]
        # res = get_course_page(reg_no,password,sem_code,"BMAT102L - Differential Equations and Transforms","VL2021220504154")
        output = get_time_table_data(reg_no, password, sem_code)
        if output == 1:
            return render_template("index.html",success_message = "Successfully Enrolled !! Go ahead and access Course Page !!")
        else:
            return render_template("enroll.html",error = output)
    else:
        return render_template("enroll.html")

@app.route("/course-selection",methods=["POST","GET"])
def course_selection():
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        password = request.form["password"]
        # sem_code = request.form["sem_code"]
        selected_course = request.form["course_selection"]
        course_details = selected_course.split("!")[1]
        class_number = selected_course.split("!")[0]
        details = get_course_details(reg_no)
        course_list = details[0]
        sem_code = details[1]
        output = get_course_page(reg_no, password, sem_code, course_details, class_number)
        errors = ["Professor not found !!", "Course not found under Course Page !!","Please Try Again!! Are You a Human Test Popped up !!", "Invalid ID/Password. Please Visit Home and enter the correct password"]
        if output in errors:
            return render_template("course_selection.html",reg_no=reg_no,vtop_password = password,sem_code = sem_code,course_list = course_list,error = output,check=0)
        return render_template("course_selection.html",reg_no=reg_no,vtop_password = password,sem_code = sem_code,course_list = course_list,check=1,selected_course_name = course_details,res = output)
    else:
        return render_template("index.html")


@app.route("/downloadPDF",methods=["POST","GET"])
def download():
    if request.method == "POST":
        reg_no = request.form["reg_no"].upper()
        initial_link = request.form["initial_link"]
        changed_link = change_link(initial_link,reg_no)
        return redirect(changed_link)
    else:
        return render_template("index.html")


if __name__ == "__main__":
    app.run()