from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from time import time

app = Flask(__name__)
CORS(app)  # Включаем CORS для всех запросов

# Путь к данным
DATA_FILE_PATH = "./data/data.json"
BACKUP_FILE_PATH = "./data/backup.json"
SETTINGS_FILE_PATH = "./data/settings.json"


# Проверка, пусты ли обязательные поля
def is_required_fields_empty(data_to_check):
    main_data = data_to_check["main_data"]
    cleaning_schedule = main_data["cleaning_schedule"]

    if (
        not data_to_check.get("people") or
        not main_data or
        not main_data.get("trash_schedule_order") or
        not main_data.get("kitchen_cleaning_order") or
        not main_data.get("house_cleaning_order") or
        not cleaning_schedule.get("house_cleaning_schedule") or
        not cleaning_schedule.get("kitchen_cleaning_schedule") or
        not cleaning_schedule.get("trash_throw_out_schedule")
    ):
        return True

    return False


# Обработка обновления данных
@app.route('/update', methods=['POST'])
def process_data_update():
    raw_data = request.get_data(as_text=True)
    try:
        data_to_update = json.loads(raw_data)
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Invalid JSON data provided"}), 400

    if is_required_fields_empty(data_to_update):
        return jsonify({"status": "error", "message": "Required field is missing or empty"}), 400

    # Сохранение бэкапа
    if os.path.exists(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            backup_data = f.read()

        with open(BACKUP_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(backup_data)

    # Обновление данных
    with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data_to_update, f, ensure_ascii=False, indent=4)

    return jsonify({"status": "success", "message": "Data successfully updated"})


# Получение данных
@app.route('/data', methods=['GET'])
def get_data():
    with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


# Генерация данных для расписания
def generate_data(last_day_time, names_order, last_person_index):
    schedule = []
    time_val = last_day_time if last_day_time else int(time())

    for i in range(1, 32):
        person_index = last_person_index if last_person_index else (i - 1) % len(names_order)

        day = {
            "date": time_val,
            "name": names_order[person_index],
            "person_index": person_index
        }

        time_val += 86400  # следующий день

        schedule.append(day)

    return schedule


# Обработка всех данных
def process_all_data(data):
    cleaning_schedule = data["main_data"]["cleaning_schedule"]
    
    # Пример обработки данных
    # Добавим новые данные для уборки
    last_house_cleaning_schedule = cleaning_schedule["house_cleaning_schedule"][-1] if cleaning_schedule["house_cleaning_schedule"] else {}
    last_person_index = last_house_cleaning_schedule.get("person_index", 0)
    last_day_time = last_house_cleaning_schedule.get("date", 0)

    house_cleaning_order = data["main_data"]["house_cleaning_order"]
    cleaning_schedule["house_cleaning_schedule"].extend(generate_data(last_day_time, house_cleaning_order, last_person_index))

    return data


@app.route('/process', methods=['GET'])
def update_and_get_data():
    with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'update-schedule' in request.args:
        data = process_all_data(data)
        with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return jsonify(data)


# Авторизация
@app.route('/login', methods=['GET'])
def check_login_info():
    login_info = {}

    with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
        login_info = json.load(f)

    login_from_client = request.args.get("login", "")
    password_from_client = request.args.get("password", "")

    if not login_from_client or not password_from_client:
        return jsonify({"status": "error", "message": "Invalid data. Login or password is empty"}), 400

    if login_info["admin"]["login"] == login_from_client and login_info["admin"]["password"] == password_from_client:
        return jsonify({"access": True})
    else:
        return jsonify({"access": False})


# Обновление информации администратора
@app.route('/update-admin-info', methods=['POST'])
def update_admin_info():
    data = request.get_json()

    with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
        login_info = json.load(f)

    info_to_update = data.get("info_to_update")
    if info_to_update == "both":
        login_info["admin"] = data["admin"]
    elif info_to_update == "password":
        login_info["admin"]["password"] = data["admin"]["password"]
    else:
        login_info["admin"]["login"] = data["admin"]["login"]

    with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(login_info, f, ensure_ascii=False, indent=4)

    return jsonify({"status": "success", "message": "Admin info updated successfully"})


if __name__ == '__main__':
    app.run(debug=True)
