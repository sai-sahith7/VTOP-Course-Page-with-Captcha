import os
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

app = Flask(__name__)
model = joblib.load("captcha_model.pk1")   #model for captcha
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
def get_complete_data(reg_no,vtop_password,sem_code):
    # **** until sign in ****
    ext = webdriver.ChromeOptions()
    ext.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    ext.add_argument("--headless")
    ext.add_argument("--no-sandbox")
    ext.add_argument("--disable-dev-sh-usage")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"),chrome_options=ext)
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
    wait.until(ec.element_to_be_clickable((By.ID, "uname"))).send_keys(reg_no)
    wait.until(ec.element_to_be_clickable((By.ID, "passwd"))).send_keys(vtop_password)
    time.sleep(2) #trying to avoid recaptcha
    wait.until(ec.element_to_be_clickable((By.ID, "captcha"))).click()
    #until sign in end
    # time table
    data = {}
    time.sleep(2)
    wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="menu-toggle"]'))).click()  # clicking on menu button
    wait.until(ec.element_to_be_clickable((By.XPATH, '//a[@href="#MenuBody6"]'))).click()  # clicking on academics
    wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="ACD0034"]'))).click()  # clicking on time table
    wait.until(ec.element_to_be_clickable((By.XPATH, '//option[@value="' + sem_code + '"]'))).click()  # selecting Winter Semester
    wait.until(ec.element_to_be_clickable((By.XPATH, '//div[@class="table-responsive"]//table')))
    class_numbers = driver.find_elements(By.XPATH, '//div[@class="table-responsive"]//table//tr//td[7]//p')
    course_names = driver.find_elements(By.XPATH, '//div[@class="table-responsive"]//table//tr//td[3]//p[1]')
    for i in range(len(class_numbers)):
        data[course_names[i].text] = class_numbers[i].text
    wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="ACD0045"]'))).click()  # clicking on course page
    time.sleep(1)
    wait.until(ec.element_to_be_clickable((By.XPATH, '//option[@value="' + sem_code + '"]'))).click()  # selecting Winter Semester
    # time table end
    final_data = list()
    for i in data.keys():
        check = True
        while True:
            try:
                wait.until(ec.element_to_be_clickable((By.XPATH, '//option[contains(text(),"--Choose Course --")]')))
                try:
                    wait1.until(ec.element_to_be_clickable((By.XPATH, '//option[contains(text(),"' + i[:9].strip() + '")]'))).click() #selecting course
                    break
                except:
                    check = False
                    break
            except:
                continue
        if check is False:
            continue
        while True:
            try:
                wait.until(ec.element_to_be_clickable((By.XPATH, '//tr//button')))
                try:
                    wait1.until(ec.element_to_be_clickable((By.XPATH, '//tr[td="'+data[i]+'"]//button'))).click()   #selecting professor
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
                    final_data.append([i.split("-")[1].strip(),res])
                    wait.until(ec.element_to_be_clickable((By.XPATH, '//a[text()="Go Back"]'))).click()  #click on Go Back
                    break
                except:
                    break
            except:
                continue
    return final_data
@app.route("/",methods=["POST","GET"])
def main_app():
    if request.method == "POST":
        reg_no = request.form["reg_no"]
        password = request.form["password"]
        sem_code = request.form["sem_code"]
        res = get_complete_data(reg_no,password,sem_code)
        return render_template("index.html",res=res,reg_no=reg_no)
    else:
        return render_template("index.html")
@app.route("/downloadPDF",methods=["POST","GET"])
def download():
    if request.method == "POST":
        reg_no = request.form["reg_no"].upper()
        initial_link = request.form["initial_link"]
        changed_link = change_link(initial_link,reg_no)
        print(changed_link)
        return redirect(changed_link)
    else:
        return render_template("index.html")
if __name__ == "__main__":
    app.run()
