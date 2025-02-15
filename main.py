from playwright.sync_api import sync_playwright
import os
import json
import re
import calendar
from datetime import datetime, timedelta
import pandas as pd
import time
from fuzzywuzzy import fuzz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from gspread_pandas import Spread, Client

cred_path = "/Users/nguyenbaothaitu9a8/Scrape_ratings/googleauth2.json"  # Đường dẫn chính xác cho macOS

# Thiết lập đường dẫn từ biến môi trường CHROMIUM_PATH
os.environ["CHROMIUM_PATH"] = "/Users/nguyenbaothaitu9a8/Library/Caches/ms-playwright/chromium-1140/chrome-mac/Chromium.app/Contents/MacOS"

# Lấy đường dẫn từ biến môi trường
chromium_path = os.getenv("CHROMIUM_PATH")

# Đặt tên file thực thi
executable_file = "Chromium"  # Chỉ định tên file thực thi của Chromium

# Kết hợp đường dẫn
executable_path = os.path.join(chromium_path, executable_file)

# Kiểm tra xem đường dẫn thực thi có hợp lệ không
if not os.path.isfile(executable_path):
    raise ValueError(f"Executable not found at {executable_path}. Please check the path.")

headless_option = False

chosen_cookies = "laz_cookies.txt"
sort_option = 'recent'

# Value need to prepared
spreadsheet_name = "UNIQUE_SCRAPE"
worksheet_name = "Sheet4"

web_socket_path = 'ws://localhost:9222/devtools/browser/10394cf0-43a2-4cc6-8db2-e0b83260643b'

# These are requires paramaters
# Day range
start_date = '2024-12-01'
end_date = '2025-01-08'
# Row range
start_rows = 129
end_rows = 200
get_current_rating = True  # (True, Flase)


# Not used
def read_cookies():
    with open(chosen_cookies, 'r') as file:
        file_contents = file.read()
    cookies_data = json.loads(file_contents)
    for data in cookies_data:
        data['sameSite'] = "None"
    return cookies_data


# Not used
def to_navigate(page):
    initial_access = True
    while True:
        try:
            if initial_access is True:
                initial_access = False
                page.goto('https://www.lazada.com.ph', wait_until='load')
                page.wait_for_load_state('load')
                print('The page has fully loaded')
                break
            else:
                page.wait_for_load_state('load')
                print('The page has fully loaded')
                break
        except Exception as e:
            print(f'Error occurred while navigating the page: {e}')
            continue


# Not used
def date_generator(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    generated_dates = []
    current_date = start_date
    while current_date <= end_date:
        generated_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    return generated_dates


def get_text_map():
    text_map = {
        'weeks': 7,
        'minutes': 1 / 1440,
        'minute': 1 / 1440,
        'week': 7,
        'hour': 1 / 24,
        'hours': 1 / 24,
        'days': 1,
        'day': 1
    }
    return text_map


def get_month_map():
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    return month_map


# Not used
def search_product(page, input_product):
    while True:
        try:
            page.wait_for_selector('div.search-box__bar--29h6')
            search_bar = page.query_selector('div.search-box__bar--29h6 input')
            if search_bar:
                search_bar.fill(input_product)
            page.keyboard.press("Enter")
            print(f'Product {input_product} has been searched')
            break
        except Exception as e:
            print(f'Error occured while searching the products {e}')
            continue


# Not used
def click_product(page, product_url):
    try:
        page.wait_for_selector('div.ant-modal-content')
        over18_button = page.query_selector(
            'div.ant-modal-content button.ant-btn.css-1bkhbmc.app.ant-btn-primary.uVxk9')
        if over18_button:
            over18_button.click()
            print('Clicked the "Over 18" button')
    except Exception as e:
        print(f'No over 18 button found')
    similarity_raito = 80
    while True:
        try:
            page.wait_for_selector('button.ant-pagination-item-link')
            trim_pattern = r'//(.*)'
            page.wait_for_selector('div._17mcb')
            all_products = page.query_selector('div._17mcb').query_selector_all('div.Bm3ON div._95X4G')
            for product in all_products:
                laz_product_url = product.query_selector('a').get_attribute('href')
                laz_clean_url = re.search(trim_pattern, laz_product_url).group(1)
                if fuzz.ratio(laz_clean_url, product_url) >= similarity_raito:
                    product.click()
                    print('The product has been clicked')
                    return
            next_button = page.query_selector_all('button.ant-pagination-item-link')[1]
            if next_button:
                next_button.click()
        except Exception as e:
            print(f'Error occured while click the product as {e}')
            continue


# Used to get total ratings
def get_total_ratings(page):
    matching_pattern = r'(\d+\.?\d*)'
    page.wait_for_selector('div.pdp-review-summary')
    rating_div = page.query_selector('div.pdp-review-summary a')
    if rating_div:
        rating_text = rating_div.text_content()
        if "k" in rating_text:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1)) * 1000
        else:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return re_found.group(1)
            else:
                return 0
    else:
        return 0

# Used to get ratings 1 star
def get_ratings_one_star(page):
    matching_pattern = r'(\d+\.?\d*)'

    # Wait until the entire rating section is loaded
    page.wait_for_selector('div.detail')

    # Select the one-star rating element specifically using nth-child (assuming it's always in the last <li>)
    one_star_element = page.query_selector('div.detail ul li:nth-child(5) span.percent')

    if one_star_element:
        # Extract the text content of the one-star rating
        rating_text = one_star_element.text_content()

        # Check if the rating has a "k" in it (e.g., "1.5k" means 1500)
        if "k" in rating_text:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1)) * 1000
        else:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1))

    # Return 0 if the element or data is not found
    return 0

def get_ratings_second_star(page):
    matching_pattern = r'(\d+\.?\d*)'

    # Wait until the entire rating section is loaded
    page.wait_for_selector('div.detail')

    # Select the one-star rating element specifically using nth-child (assuming it's always in the last <li>)
    one_star_element = page.query_selector('div.detail ul li:nth-child(4) span.percent')

    if one_star_element:
        # Extract the text content of the one-star rating
        rating_text = one_star_element.text_content()

        # Check if the rating has a "k" in it (e.g., "1.5k" means 1500)
        if "k" in rating_text:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1)) * 1000
        else:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1))

    # Return 0 if the element or data is not found
    return 0

def get_ratings_third_star(page):
    matching_pattern = r'(\d+\.?\d*)'

    # Wait until the entire rating section is loaded
    page.wait_for_selector('div.detail')

    # Select the one-star rating element specifically using nth-child (assuming it's always in the last <li>)
    one_star_element = page.query_selector('div.detail ul li:nth-child(3) span.percent')

    if one_star_element:
        # Extract the text content of the one-star rating
        rating_text = one_star_element.text_content()

        # Check if the rating has a "k" in it (e.g., "1.5k" means 1500)
        if "k" in rating_text:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1)) * 1000
        else:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1))

    # Return 0 if the element or data is not found
    return 0

def get_ratings_fourth_star(page):
    matching_pattern = r'(\d+\.?\d*)'

    # Wait until the entire rating section is loaded
    page.wait_for_selector('div.detail')

    # Select the one-star rating element specifically using nth-child (assuming it's always in the last <li>)
    one_star_element = page.query_selector('div.detail ul li:nth-child(2) span.percent')

    if one_star_element:
        # Extract the text content of the one-star rating
        rating_text = one_star_element.text_content()

        # Check if the rating has a "k" in it (e.g., "1.5k" means 1500)
        if "k" in rating_text:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1)) * 1000
        else:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1))

    # Return 0 if the element or data is not found
    return 0

def get_ratings_fifth_star(page):
    matching_pattern = r'(\d+\.?\d*)'

    # Wait until the entire rating section is loaded
    page.wait_for_selector('div.detail')

    # Select the one-star rating element specifically using nth-child (assuming it's always in the last <li>)
    one_star_element = page.query_selector('div.detail ul li:nth-child(1) span.percent')

    if one_star_element:
        # Extract the text content of the one-star rating
        rating_text = one_star_element.text_content()

        # Check if the rating has a "k" in it (e.g., "1.5k" means 1500)
        if "k" in rating_text:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1)) * 1000
        else:
            re_found = re.search(matching_pattern, rating_text)
            if re_found:
                return float(re_found.group(1))

    # Return 0 if the element or data is not found
    return 0

# Used to get selling price
def get_selling_price(page):
    matching_pattern = r'(\d+[^a-zA-Z0-9]\d+)'
    page.wait_for_selector('div.pdp-product-price')
    price_text = page.query_selector('div.pdp-product-price span')
    if price_text:
        price_value = re.search(matching_pattern, price_text.text_content())
        if price_value:
            return price_value.group(1)
        else:
            return "Not found"
    else:
        return "Not found"


def convert_to_datetime(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        return datetime.strptime(date_string, "%y-%m-%d")


def to_sort(page, sort_option, get_current_rating):
    if get_current_rating is True:
        page.wait_for_timeout(3000)
        page_height = page.evaluate('() => window.innerHeight')
        total_height = page.evaluate('() => document.body.scrollHeight')
        earlier_point = (page_height + total_height) / 1.7
        page.evaluate(f'window.scrollTo(0, {earlier_point})')
        time.sleep(0.3)
        scroll_up = earlier_point - 200
        page.evaluate(f'window.scrollTo(0, {scroll_up})')
        time.sleep(0.3)
        page.evaluate(f'window.scrollTo(0, {earlier_point})')
        return "Found"
    else:
        return "Not found"


def next_page(page):
    page.wait_for_selector('button.next-btn.next-btn-normal.next-btn-medium.next-pagination-item.next')
    next_button = page.query_selector('button.next-btn.next-btn-normal.next-btn-medium.next-pagination-item.next')
    if next_button:
        next_button.click()


def check_continue(page, temp_list):
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    previous_month = start_date_obj - timedelta(days=1)
    previous_start_date = previous_month.replace(day=1)
    previous_end_date = previous_month.replace(day=calendar.monthrange(previous_month.year, previous_month.month)[1])
    try:
        next_button_availability = page.query_selector(
            'button.next-btn.next-btn-normal.next-btn-medium.next-pagination-item.next').get_attribute('disabled')
        if next_button_availability == '':
            return False
    except Exception as e:
        print(f'Find no next button to press, resolved error {e}')
        return False
    for datetime_obj in temp_list:
        if (datetime_obj >= previous_start_date and datetime_obj <= previous_end_date) or \
                (datetime_obj < previous_start_date):
            temp_list = []
            return False
    temp_list = []
    return True


def get_clean_string(customore_string):
    clean_url = customore_string.replace(re.search(r'.*(-s\d+).*', customore_string).group(1), "")
    return clean_url


def read_dataframe():
    current_directory = os.getcwd()
    file_name = 'scrapping_laz.xlsx'
    file_path = os.path.join(current_directory, file_name)
    df = pd.read_excel(file_path)
    df['clean_url'] = df['products_url'].apply(lambda row: get_clean_string(row))
    df.drop(columns=['products_url'], inplace=True)
    return df.values.tolist()


# Not used
def get_ratings(page, sort_decision, get_current_rating):
    if get_current_rating is True and sort_decision == "Found":
        rating_count = 0
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        day_pattern = r'(\d+)\s+\w+'
        year_pattern = r'\w+\s+(\d+)'
        month_pattern = r'\d+\s+(\w+)\s+\d+'
        month_map = get_month_map()
        text_map = get_text_map()
        text_list = list(text_map.keys())
        total_pages = 60
        current_page = 0
        while current_page < total_pages:
            temp_list = []
            time.sleep(0.25)
            page.wait_for_selector('div.mod-reviews')
            ratings_div = page.query_selector('div.mod-reviews')
            if ratings_div:
                current_page += 1
                all_items = ratings_div.query_selector_all('div.item')
                for item in all_items:
                    to_use_text_map = False
                    date_string = item.query_selector('div.top span').text_content().lower()
                    for text in text_list:
                        if text in date_string:
                            to_use_text_map = True
                            break
                    if to_use_text_map is False:
                        day_string = re.search(day_pattern, date_string).group(1)
                        year_string = re.search(year_pattern, date_string).group(1)
                        month_string = month_map.get(re.search(month_pattern, date_string).group(1), "")
                        final_string = f'{year_string}-{month_string}-{day_string}'
                        datetime_obj = convert_to_datetime(final_string)
                        temp_list.append(datetime_obj)
                        if datetime_obj.date() >= start_date_obj.date() and datetime_obj.date() <= end_date_obj.date():
                            rating_count += 1
                    else:
                        current_date = datetime.now()
                        ago_pattern = r'(\d+)\s+\w+\s+\w+'
                        delay_pattern = r'\d+\s+(\w+)\s+\w+'
                        ago_value = int(re.search(ago_pattern, date_string).group(1))
                        delay_value = int(text_map.get(re.search(delay_pattern, date_string).group(1)))
                        delay_days = ago_value * delay_value
                        datetime_obj = current_date - timedelta(days=delay_days)
                        temp_list.append(datetime_obj)
                        if datetime_obj.date() >= start_date_obj.date() and datetime_obj.date() <= end_date_obj.date():
                            rating_count += 1
                to_continue = check_continue(page, temp_list)
                if to_continue is True:
                    next_page(page)
                else:
                    return rating_count
        return rating_count
    else:
        return 0


def check_captcha(page):
    print_flag = True
    while True:
        try:
            page.wait_for_selector("div.rc-anchor.rc-anchor-normal.rc-anchor-light", timeout=5000)
            captcha_box = page.query_selector("div.rc-anchor.rc-anchor-normal.rc-anchor-light")
            print(captcha_box)
        except Exception:
            print("No captcha found")
            break
        if captcha_box:
            captcha_content = captcha_box.text_content()
            if captcha_content == "I'm not a robot" and print_flag is True:
                print("Found captcha, waiting to click")
                print_flag = False
                continue
        else:
            print("No captcha found")
            break

def get_sku_full_informations(page, sort_option, get_current_rating):
    sort_decision = to_sort(page, sort_option, get_current_rating)
    rating_value = get_total_ratings(page)
    selling_price = get_selling_price(page)
    ratings = get_ratings(page, sort_decision, get_current_rating)
    ratings_one_star = get_ratings_one_star(page)
    ratings_second_star = get_ratings_second_star(page)
    ratings_third_star = get_ratings_third_star(page)
    ratings_fourth_star = get_ratings_fourth_star(page)
    ratings_fifth_star = get_ratings_fifth_star(page)
    print(f'Total ratings: {rating_value}')
    print(f'Selling price: {selling_price}')
    print(f'Rating this month: {ratings}')
    print(f'Rating one star: {ratings_one_star}')
    print(f'Rating one star: {ratings_second_star}')
    print(f'Rating one star: {ratings_third_star}')
    print(f'Rating one star: {ratings_fourth_star}')
    print(f'Rating one star: {ratings_fifth_star}')
    skus_map = {
        'total_rating': rating_value,
        # 'current_rating': ratings,
        'selling_price': selling_price,
        'rating_one_star': ratings_one_star,
        'rating_second_star': ratings_second_star,
        'rating_third_star': ratings_third_star,
        'rating_fourth_star': ratings_fourth_star,
        'rating_fifth_star': ratings_fifth_star
    }
    df = pd.DataFrame([skus_map])
    return df

def get_sku_informations(page, sort_option, get_current_rating):
    sort_decision = to_sort(page, sort_option, get_current_rating)
    rating_value = get_total_ratings(page)
    selling_price = get_selling_price(page)
    ratings = get_ratings(page, sort_decision, get_current_rating)
    print(f'Total ratings: {rating_value}')
    print(f'Selling price: {selling_price}')
    print(f'Rating this month: {ratings}')
    skus_map = {
        'total_rating': rating_value,
        'current_rating': ratings,
        'selling_price': selling_price
    }
    df = pd.DataFrame([skus_map])
    return df


def find_header_row(worksheet):
    existing_data = worksheet.get_all_values()
    for row_number, row in enumerate(existing_data):
        if 'clean_url' in row:
            return row_number, row


def initialize_client(spreadsheet_name, worksheet_name, cred_path):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(cred_path, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open(spreadsheet_name)
    worksheet = spreadsheet.worksheet(worksheet_name)
    return worksheet


def get_urls(worksheet, start_rows, end_rows):
    start_index_row = start_rows - 2
    end_index_row = end_rows - 2
    existing_data = worksheet.get_all_values()
    row_number, header_row = find_header_row(worksheet)
    df = pd.DataFrame(existing_data[row_number + 1:], columns=existing_data[row_number])
    url_df = df.loc[:, ['clean_url']]
    url_df['clean_url'] = url_df['clean_url'].apply(
        lambda url: "https://" + url if not url.startswith("https://") else url)
    if start_index_row == end_index_row:
        clean_urls = [url_df.iloc[start_index_row, :]['clean_url']]
    else:
        clean_urls = url_df.iloc[start_index_row:end_index_row, :]['clean_url'].values.tolist()
    return clean_urls


def index_to_excel_column(index):
    column_letter = ""
    while index > 0:
        index -= 1
        column_letter = chr(index % 26 + ord('A')) + column_letter
        index //= 26
    return column_letter


def to_spreadsheet(input_df, worksheet, url, spreadsheet_name):
    while True:
        try:
            worksheet_name = worksheet.title
            row_number, header_row = find_header_row(worksheet)
            total_rating_index = header_row.index('total_rating') + 1
            rating_column = index_to_excel_column(total_rating_index)
            # Get the latest row to paste the data
            existing_data = worksheet.get_all_values()
            checking_df = pd.DataFrame(existing_data[row_number + 1:], columns=existing_data[row_number])
            checking_df['clean_url'] = checking_df['clean_url'].apply(
                lambda url: "https://" + url if not url.startswith("https://") else url)
            row_index = checking_df.loc[checking_df['clean_url'] == url].index[0] + 2
            working_spreadsheet = Spread(spreadsheet_name)
            working_spreadsheet.get_sheet_dims(worksheet_name)
            print(f'Start pushing the data from rows {row_index}')
            working_spreadsheet.df_to_sheet(input_df, sheet=worksheet_name, start=f"{rating_column}{row_index}",
                                            index=False, headers=False)
            print('Done pushing the data to the spreadsheet')
            break
        except Exception as e:
            print(f"Error occured as {e},\n Sleeping for 5 seconds and retrying")
            time.sleep(5)
            continue


def check_exists(page):
    try:
        page.wait_for_selector("div.error-info", timeout=1000)
        error_message = page.query_selector("div.error-info").text_content()
        if error_message == 'Sorry! This product is no longer available':
            return False
    except Exception:
        return True


if __name__ == '__main__':
    with sync_playwright() as pw:
        worksheet = initialize_client(spreadsheet_name, worksheet_name, cred_path)
        print('Start connecting to the browser')
        browser = pw.chromium.connect_over_cdp(web_socket_path)
        context = browser.contexts[0]
        page = context.pages[0]
        urls_list = get_urls(worksheet, start_rows, end_rows)
        print(f'Get the total of {len(urls_list)} urls')
        for index, url in enumerate(urls_list):
            while True:
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    product_availability = check_exists(page)
                    if product_availability is True:
                        print(f'Job for url number {index}\nCurrent url: {url}')
                        final_map = get_sku_full_informations(page, sort_option, get_current_rating)
                    else:
                        skus_map = {
                            'total_rating': "Product not existed",
                            # 'current_rating': "Product not existed",
                            'selling_price': "Product not existed",
                            'rating_one_star': "Product not existed",
                            'rating_second_star': "Product not existed",
                            'rating_third_star': "Product not existed",
                            'rating_fourth_star': "Product not existed",
                            'rating_fifth_star': "Product not existed"
                        }
                        final_map = pd.DataFrame([skus_map])
                    to_spreadsheet(final_map, worksheet, url, spreadsheet_name)
                    break
                except Exception as e:
                    print(f"Error occured navigating to the page as {e}\n Retry connecting")
                    continue
        print("Done getting all the SKUs")