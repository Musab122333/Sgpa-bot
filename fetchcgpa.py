import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------
# CONFIG
# -----------------------
BASE_URL = "https://vnrvjietexams.net/eduprime3exam/results#"

ROLL_SERIES = [
    ("23071A", 6701, 6717), 
]

# -----------------------
# DRIVER SETUP
# -----------------------
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 20)

# -----------------------
# OPEN MAIN PAGE
# -----------------------
try:
    driver.get(BASE_URL)
    time.sleep(2)
    
    # Click the correct exam link
    exam_link = wait.until(
        EC.element_to_be_clickable(
            (By.LINK_TEXT, "III B.TECH. I SEMESTER (UG-R22) Regular")
        )
    )
    exam_link.click()
    time.sleep(2)
    
except Exception as e:
    print(f"Failed to click exam link: {e}")
    driver.quit()
    exit()

records = []

# -----------------------
# HELPER FUNCTION: SELECT EXAM LINK
# -----------------------
def select_exam_link():
    """Navigate to base URL and select the exam link"""
    try:
        driver.get(BASE_URL)
        time.sleep(5)  # Wait longer for JS to load
        
        # Debug: Print page source to see structure
        print("\nDebug: Waiting for page to fully load...")
        
        # Try to find the link using multiple selectors
        exam_link = None
        
        # Approach 1: Wait for any element containing the text
        try:
            exam_link = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(), 'III B.TECH')]")
                )
            )
            print("Found exam link using XPath")
        except:
            pass
        
        # Approach 2: Look for clickable divs or spans with the text
        if exam_link is None:
            try:
                exam_link = driver.find_element(
                    By.XPATH, "//a[contains(text(), 'III B.TECH')]"
                )
                print("Found exam link using a tag")
            except:
                pass
        
        # Approach 3: Try to find by ID or class patterns
        if exam_link is None:
            try:
                # Look through all elements that might be exam links
                potential_links = driver.find_elements(By.XPATH, "//*[@onclick or @class*='link' or tagname='a']")
                for link in potential_links:
                    if "III B.TECH" in link.text and "UG-R22" in link.text:
                        exam_link = link
                        break
            except:
                pass
        
        if exam_link is None:
            print("Could not find exam link using standard methods.")
            print("Page source snippet:")
            page_source = driver.page_source
            # Print lines containing exam-related text
            for i, line in enumerate(page_source.split('\n')):
                if any(keyword in line.lower() for keyword in ['b.tech', 'semester', 'ug-r22']):
                    print(f"  Line {i}: {line[:150]}")
            return False
        
        print(f"Clicking exam link: {exam_link.text}")
        # Scroll to element and click
        driver.execute_script("arguments[0].scrollIntoView(true);", exam_link)
        time.sleep(1)
        try:
            exam_link.click()
        except:
            # If normal click fails, use JavaScript click
            driver.execute_script("arguments[0].click();", exam_link)
        time.sleep(3)
        
        # Wait for input field to be available
        wait.until(
            EC.presence_of_element_located((By.ID, "HTNO"))
        )
        print("Input field found - ready for roll entry")
        return True
    except Exception as e:
        print(f"Error selecting exam link: {e}")
        import traceback
        traceback.print_exc()
        return False

# -----------------------
# SCRAPING LOOP
# -----------------------
for prefix, start, end in ROLL_SERIES:
    for num in range(start, end + 1):
        roll_no = f"{prefix}{num}"

        try:
            # Step 1: Navigate to main page and select exam link
            if not select_exam_link():
                print(f"[FAIL] Failed for {roll_no} : Could not select exam link")
                continue
            
            # Step 2: Enter roll number
            roll_input = wait.until(
                EC.presence_of_element_located((By.ID, "HTNO"))
            )
            # Clear the field using JavaScript to avoid stale element issues
            driver.execute_script("arguments[0].value = '';", roll_input)
            time.sleep(0.3)
            # Set the value using JavaScript
            driver.execute_script(f"arguments[0].value = '{roll_no}';", roll_input)
            time.sleep(0.5)

            # Step 3: Click Go button
            go_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Go')]"))
            )
            go_button.click()
            time.sleep(2)

            # Step 4: Wait for result page content
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table")
                )
            )
            time.sleep(1)

            # Step 5: Extract Hall Ticket Number
            extracted_roll = driver.find_element(
                By.XPATH, "//th[contains(text(),'Hall Ticket Number')]/following-sibling::td | //td[contains(text(),'Hall Ticket Number')]/following-sibling::td"
            ).text.strip()
            # Clean up the extracted data
            extracted_roll = extracted_roll.replace(":", "").replace("Hall Ticket Number", "").strip()

            # Step 6: Extract Student Name
            name = driver.find_element(
                By.XPATH, "//th[contains(text(),'Student Name')]/following-sibling::td | //td[contains(text(),'Student Name')]/following-sibling::td"
            ).text.strip()
            # Clean up the extracted data
            name = name.replace(":", "").replace("Student Name", "").strip()

            # Step 7: Extract SGPA - more robust extraction
            try:
                # Try multiple approaches to extract SGPA
                sgpa = ""
                
                # Approach 1: Look for SGPA text followed by value
                sgpa_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'SGPA')]")
                if sgpa_elements:
                    # Get the parent row and find the value
                    for element in sgpa_elements:
                        parent = element.find_element(By.XPATH, "..")
                        text = parent.text
                        if ":" in text:
                            sgpa = text.split(":")[-1].strip()
                            break
                        # Try next sibling
                        try:
                            sgpa = element.find_element(By.XPATH, "./following-sibling::*[1]").text.strip()
                            if sgpa:
                                break
                        except:
                            pass
                
                if not sgpa:
                    # Approach 2: Look for numeric value in a specific pattern
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    sgpa_match = re.search(r'SGPA\s*:\s*([\d.]+)', page_text)
                    if sgpa_match:
                        sgpa = sgpa_match.group(1)
            except Exception as sgpa_e:
                print(f"  Warning: Could not extract SGPA properly: {sgpa_e}")
                sgpa = "N/A"
            
            # Step 8: Store data
            print(f"[OK] {extracted_roll} | {name} | {sgpa}")

            records.append({
                "Roll No": extracted_roll,
                "Name": name,
                "SGPA": sgpa
            })

        except Exception as e:
            print(f"[FAIL] Failed for {roll_no} : {e}")
            continue

# -----------------------
# EXPORT CSV
# -----------------------
df = pd.DataFrame(records)
df.to_csv("SGPA_RESULTS.csv", index=False)

print("CSV Generated Successfully")

driver.quit()