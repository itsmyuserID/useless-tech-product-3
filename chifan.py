import sys
import json
import random
import os
import re
import hashlib
import time
import requests
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class RecipeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("今天吃什么")
        self.setMinimumSize(620, 720)
        self.resize(620, 720)
        
        self.dark_mode = True
        self.current = None
        self.favorites = self.load_favorites()
        self.showing_fast_food = False
        
        self.secret_id = ""
        self.secret_key = ""
        self.load_api_key()
        
        self.dishes_dir = "dishes"
        self.dish_files = self.scan_dishes()
        
        self.weekday_recommendations = {
            0: ("🍔 麦当劳", "周一会员日，麦辣鸡腿堡买一送一"),
            1: ("🍕 必胜客", "周二披萨半价，一个人吃刚好"),
            2: ("🍟 汉堡王", "周三皇堡日，9.9元一个皇堡"),
            3: ("🍗 肯德基", "疯狂星期四，吮指原味鸡9.9两块"),
            4: ("🍲 杨国福", "周五犒劳自己，麻辣烫随便点"),
            5: ("🥘 海底捞", "周末聚餐，大学生69折"),
            6: ("🍜 沙县小吃", "周日吃清淡，蒸饺加炖罐"),
        }
        
        self.setup_ui()
        self.apply_dark_theme()
        self.seasonal_recommend()
        self.random_recipe()
    
    def scan_dishes(self):
        files = []
        if os.path.exists(self.dishes_dir):
            for root, dirs, filenames in os.walk(self.dishes_dir):
                for f in filenames:
                    if f.endswith('.md'):
                        files.append(os.path.join(root, f))
        return files
    
    def seasonal_recommend(self):
        month = time.localtime().tm_mon
        if month in [12, 1, 2]:
            keywords = ["汤", "炖", "煲", "锅", "肉", "羊", "牛"]
        elif month in [3, 4, 5]:
            keywords = ["菜", "虾", "鱼", "蒸", "拌", "笋"]
        elif month in [6, 7, 8]:
            keywords = ["凉", "拌", "瓜", "虾", "鱼", "蒸"]
        else:
            keywords = ["汤", "炖", "菇", "鸡", "鸭", "煲"]
        
        seasonal_files = []
        for f in self.dish_files:
            name = os.path.basename(f)
            if any(k in name for k in keywords):
                seasonal_files.append(f)
        
        self.seasonal_files = seasonal_files if seasonal_files else None
    
    def load_api_key(self):
        if os.path.exists("apikey.json"):
            try:
                data = json.load(open("apikey.json", 'r'))
                self.secret_id = data.get("id", "")
                self.secret_key = data.get("key", "")
            except:
                pass
    
    def save_api_key(self):
        json.dump({"id": self.secret_id, "key": self.secret_key}, open("apikey.json", 'w'))
    
    def translate(self, text):
        if not self.secret_id or not self.secret_key:
            return None
        try:
            timestamp = int(time.time())
            nonce = random.randint(10000, 99999)
            sign_str = f"Action=TextTranslate&Nonce={nonce}&Region=ap-guangzhou&SecretId={self.secret_id}&Timestamp={timestamp}&Version=2018-03-21"
            sign = hashlib.sha1()
            sign.update(sign_str.encode())
            sign.update(self.secret_key.encode())
            params = {"Action":"TextTranslate","Version":"2018-03-21","Region":"ap-guangzhou","Timestamp":timestamp,"Nonce":nonce,"SecretId":self.secret_id,"Signature":sign.hexdigest(),"SourceText":text,"Source":"en","Target":"zh","ProjectId":0}
            resp = requests.post("https://tmt.tencentcloudapi.com", data=params, timeout=10)
            data = resp.json()
            return data.get("Response",{}).get("TargetText")
        except:
            return None
    
    def fetch_foreign(self, region):
        area_map = {"日本":"Japanese","韩国":"Korean","意大利":"Italian","法国":"French","东南亚":"Thai"}
        try:
            area = area_map.get(region)
            if not area:
                return None
            resp = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?a={area}", timeout=8)
            meals = resp.json().get('meals')
            if not meals:
                return None
            meal_id = random.choice(meals)['idMeal']
            detail = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}", timeout=8).json()['meals'][0]
            
            ingredients = []
            for i in range(1, 21):
                ing = detail.get(f'strIngredient{i}','').strip()
                mea = detail.get(f'strMeasure{i}','').strip()
                if ing:
                    ingredients.append(f"{ing} {mea}".strip())
            
            name_en = detail.get('strMeal','')
            steps_en = detail.get('strInstructions','')
            
            if self.secret_id:
                name_cn = self.translate(name_en) or name_en
                steps_cn = self.translate(steps_en)
                for i in range(len(ingredients)):
                    t = self.translate(ingredients[i])
                    if t:
                        ingredients[i] = t
            else:
                name_cn = name_en
                steps_cn = None
            
            steps_list = []
            if steps_cn:
                steps_list = [s.strip() for s in steps_cn.replace('\r\n','\n').split('\n') if s.strip()]
            else:
                steps_list = [s.strip() for s in steps_en.replace('\r\n','\n').split('\n') if s.strip() and len(s.strip())>10]
            
            return {"name":name_cn,"region":region,"taste":"","ingredients":ingredients,"steps":steps_list,"original":name_en if name_cn!=name_en else "","translated":bool(self.secret_id and name_cn!=name_en)}
        except:
            return None
    
    def load_favorites(self):
        if os.path.exists("fav.json"):
            try:
                return json.load(open("fav.json",'r',encoding='utf-8'))
            except:
                return []
        return []
    
    def save_favorites(self):
        json.dump(self.favorites, open("fav.json",'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.central_widget = central
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        toolbar = QFrame()
        toolbar.setFixedHeight(48)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(16,8,16,8)
        
        self.region_combo = QComboBox()
        self.region_combo.addItems(["随机","日本","韩国","意大利","法国","东南亚"])
        self.region_combo.setFixedWidth(90)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部","主食","饮料","甜品"])
        self.category_combo.setFixedWidth(80)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(54)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setToolTip("换一道")
        self.btn_refresh.setStyleSheet("font-size:18px;")
        self.btn_refresh.clicked.connect(self.random_recipe_with_animation)
        
        self.btn_copy = QPushButton("📝")
        self.btn_copy.setFixedWidth(54)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setToolTip("复制购物清单")
        self.btn_copy.setStyleSheet("font-size:18px;")
        self.btn_copy.clicked.connect(self.copy_shopping_list)
        
        self.theme_btn = QPushButton("☀️")
        self.theme_btn.setFixedWidth(54)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.setStyleSheet("font-size:18px;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        self.fav_btn = QPushButton("🤍")
        self.fav_btn.setFixedWidth(54)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.setToolTip("收藏")
        self.fav_btn.setStyleSheet("font-size:18px;")
        self.fav_btn.clicked.connect(self.toggle_fav)
        
        self.btn_favs = QPushButton("📋")
        self.btn_favs.setFixedWidth(54)
        self.btn_favs.setCursor(Qt.PointingHandCursor)
        self.btn_favs.setToolTip("收藏夹")
        self.btn_favs.setStyleSheet("font-size:18px;")
        self.btn_favs.clicked.connect(self.show_favs)
        
        tl.addWidget(self.region_combo)
        tl.addWidget(self.category_combo)
        tl.addStretch()
        tl.addWidget(self.btn_copy)
        tl.addWidget(self.theme_btn)
        tl.addWidget(self.fav_btn)
        tl.addWidget(self.btn_favs)
        tl.addWidget(self.btn_refresh)
        
        main_layout.addWidget(toolbar)
        
        recipe_container = QFrame()
        recipe_container.setFrameShape(QFrame.NoFrame)
        recipe_layout = QVBoxLayout(recipe_container)
        recipe_layout.setContentsMargins(0,0,0,0)
        recipe_layout.setSpacing(0)
        
        self.recipe_text = QTextEdit()
        self.recipe_text.setReadOnly(True)
        self.recipe_text.setStyleSheet("font-size:15px; line-height:1.6; padding:20px; border:none;")
        self.recipe_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.recipe_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        recipe_layout.addWidget(self.recipe_text)
        
        self.animation_label = QLabel(recipe_container)
        self.animation_label.setAlignment(Qt.AlignCenter)
        self.animation_label.setStyleSheet("font-size:100px; background:transparent; border:none; padding-bottom:60px;")
        self.animation_label.hide()
        
        main_layout.addWidget(recipe_container)
        
        self.weekday_btn = QPushButton("作\n者\n推\n荐", central)
        self.weekday_btn.setCursor(Qt.PointingHandCursor)
        self.weekday_btn.setToolTip("最有性价比的食物！")
        self.weekday_btn.setStyleSheet("""
            QPushButton {
                font-size:12px; padding:10px 8px; border:1px solid #555;
                border-radius:8px; background:rgba(0,0,0,0.3);
            }
            QPushButton:hover { background:rgba(255,255,255,0.1); }
        """)
        self.weekday_btn.clicked.connect(self.toggle_fast_food)
        self.weekday_btn.setFixedWidth(28)
        self.weekday_btn.adjustSize()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'weekday_btn'):
            btn_width = self.weekday_btn.width()
            btn_height = self.weekday_btn.height()
            x = self.width() - btn_width
            y = self.height() - btn_height - 100
            self.weekday_btn.move(x, y)
        if hasattr(self, 'animation_label'):
            self.animation_label.setGeometry(0, 18, self.width(), self.height() - 18)
    
    def toggle_fast_food(self):
        if self.showing_fast_food:
            self.showing_fast_food = False
            self.random_recipe()
        else:
            self.showing_fast_food = True
            weekday = datetime.now().weekday()
            fast_food, reason = self.weekday_recommendations.get(weekday, ("🍽️ 出去吃", "今天随便吃点"))
            self.recipe_text.setHtml(f"""
                <div style='text-align:center;padding-top:160px;'>
                    <div style='font-size:80px;margin-bottom:20px;'>{fast_food.split()[0]}</div>
                    <div style='font-size:28px;font-weight:bold;color:#e94560;'>{fast_food}</div>
                    <div style='font-size:13px;color:#888;margin-top:20px;line-height:1.8;'>{reason}</div>
                </div>
            """)
            self.current = None
            self.fav_btn.setText("🤍")

    def random_recipe_with_animation(self):
        self.showing_fast_food = False
        emojis = ["🥘","🍜","🍝","🍲","🍛","🦐","🥟","🍗","🥩","🧄","🥬","🍄"]
        self.animation_label.show()
        self.recipe_text.hide()
        for i in range(6):
            emoji = random.choice(emojis)
            self.animation_label.setText(emoji)
            QApplication.processEvents()
            QThread.msleep(180)
        self.animation_label.hide()
        self.recipe_text.show()
        self.random_recipe()
    
    def copy_shopping_list(self):
        if not self.current:
            return
        text = "\n".join([f"☐ {ing}" for ing in self.current.get('ingredients', [])])
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "已复制", "购物清单已复制到剪贴板")
    
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_btn.setText("☀️" if self.dark_mode else "🌙")
        self.apply_dark_theme() if self.dark_mode else self.apply_light_theme()
        if self.current:
            self.show_recipe(self.current)
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            *{font-family:"Microsoft YaHei"}
            QWidget{background:#1a1a2e;color:#e0e0e0;font-size:14px}
            QComboBox{background:#16213e;border:1px solid #0f3460;border-radius:8px;padding:6px 12px;min-height:30px}
            QComboBox::drop-down{border:none}
            QComboBox QAbstractItemView{background:#16213e;color:#e0e0e0;selection-background-color:#0f3460}
            QPushButton{background:#16213e;color:#e0e0e0;border:1px solid #0f3460;border-radius:8px;padding:8px;font-size:16px}
            QPushButton:hover{background:#0f3460}
            QTextEdit{background:#1a1a2e;color:#e0e0e0;font-size:15px;line-height:1.8}
            QLabel{background:transparent;color:#e0e0e0}
        """)
    
    def apply_light_theme(self):
        self.setStyleSheet("""
            *{font-family:"Microsoft YaHei"}
            QWidget{background:#fef9ef;color:#2c3e50;font-size:14px}
            QComboBox{background:#fff;border:1px solid #e8d5b7;border-radius:8px;padding:6px 12px;min-height:30px}
            QComboBox::drop-down{border:none}
            QComboBox QAbstractItemView{background:#fff;color:#2c3e50;selection-background-color:#f5e6d3}
            QPushButton{background:#fff;color:#2c3e50;border:1px solid #e8d5b7;border-radius:8px;padding:8px;font-size:16px}
            QPushButton:hover{background:#f5e6d3}
            QTextEdit{background:#fef9ef;color:#2c3e50;font-size:15px;line-height:1.8}
            QLabel{background:transparent;color:#2c3e50}
        """)
    
    def random_recipe(self):
        self.recipe_text.setHtml("<p style='color:#888;'>寻找美食中...</p>")
        QTimer.singleShot(50, self._fetch)
    
    def _fetch(self):
        region = self.region_combo.currentText()
        category = self.category_combo.currentText()
        
        if region in ["日本","韩国","意大利","法国","东南亚"]:
            recipe = self.fetch_foreign(region)
        else:
            recipe = self.pick_local(region, category)
        
        if recipe:
            self.show_recipe(recipe)
        else:
            self.recipe_text.setHtml("<p style='color:#888;'>未找到菜谱，请检查dishes文件夹</p>")
    
    def pick_local(self, region="随机", category="全部"):
        if not self.dish_files:
            return None
        
        candidates = []
        
        if category != "全部":
            category_keywords = {
                "主食": ["staple-food", "rice", "noodle"],
                "饮料": ["drink", "beverage"],
                "甜品": ["dessert", "sweet"],
            }
            keywords = category_keywords.get(category, [])
            for f in self.dish_files:
                folder = os.path.basename(os.path.dirname(f)).lower()
                if any(k in folder for k in keywords):
                    candidates.append(f)
        else:
            candidates = self.dish_files.copy()
        
        if not candidates:
            return None
        
        if hasattr(self, 'seasonal_files') and self.seasonal_files and region == "随机" and category == "全部" and random.random() < 0.7:
            seasonal_in_candidates = [f for f in self.seasonal_files if f in candidates]
            if seasonal_in_candidates:
                f = random.choice(seasonal_in_candidates)
            else:
                f = random.choice(candidates)
        else:
            f = random.choice(candidates)
        
        try:
            content = open(f, 'r', encoding='utf-8').read()
            name = os.path.basename(f).replace('.md','')
            folder = os.path.basename(os.path.dirname(f))
            
            ingredients = []
            steps = []
            lines = content.split('\n')
            
            step_start = -1
            for i, line in enumerate(lines):
                if re.match(r'##\s*(烹饪步骤|操作|步骤)', line):
                    step_start = i
                    break
            
            seen = set()
            for line in (lines[:step_start] if step_start > 0 else lines):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    item = line[2:].strip()
                    if item and not item.startswith('#') and item not in seen:
                        ingredients.append(item)
                        seen.add(item)
            
            if step_start > 0:
                for line in lines[step_start:]:
                    line = line.strip()
                    if re.match(r'\d+\.\s+', line):
                        step = re.sub(r'\d+\.\s*', '', line).strip()
                        step = re.sub(r'\*\*([^*]+)\*\*', r'\1', step)
                        if step and len(step) > 2:
                            steps.append(step)
            
            return {
                "name": name,
                "region": folder,
                "taste": "",
                "ingredients": ingredients if ingredients else ["解析失败"],
                "steps": steps if steps else ["解析失败"],
                "original": "",
                "translated": True
            }
        except:
            return None
    
    def show_recipe(self, recipe):
        self.current = recipe
        cn = "#e94560" if self.dark_mode else "#c0392b"
        ci = "#888" if self.dark_mode else "#999"
        cs = "#0f3460" if self.dark_mode else "#2c3e50"
        ct = "#ddd" if self.dark_mode else "#333"
        
        h = f"<div style='font-size:24px;font-weight:bold;color:{cn};margin-bottom:6px;'>{recipe['name']}</div>"
        h += f"<div style='font-size:13px;color:{ci};margin-bottom:16px;'>{recipe['region']}</div>"
        
        if recipe.get('translated') == False:
            h += "<div style='font-size:12px;color:#FFB74D;margin-bottom:12px;'>未翻译</div>"
        
        h += f"<div style='font-size:16px;font-weight:bold;color:{cs};margin-top:16px;margin-bottom:8px;'>购物清单</div>"
        for ing in recipe.get('ingredients',[]):
            h += f"<div style='color:{ct};margin-left:8px;line-height:1.8;'>- {ing}</div>"
        
        h += f"<br/><div style='font-size:16px;font-weight:bold;color:{cs};margin-bottom:8px;'>制作步骤</div>"
        for i, step in enumerate(recipe.get('steps',[]), 1):
            h += f"<div style='color:{ct};margin-left:8px;line-height:1.8;margin-bottom:4px;'>{i}. {step}</div>"
        
        self.recipe_text.setHtml(h)
        is_fav = any(f['name']==recipe['name'] for f in self.favorites)
        self.fav_btn.setText("❤️" if is_fav else "🤍")
    
    def toggle_fav(self):
        if not self.current:
            return
        name = self.current['name']
        for i, f in enumerate(self.favorites):
            if f['name'] == name:
                del self.favorites[i]
                self.save_favorites()
                self.fav_btn.setText("🤍")
                return
        self.favorites.append(self.current)
        self.save_favorites()
        self.fav_btn.setText("❤️")
    
    def show_favs(self):
        if not self.favorites:
            QMessageBox.information(self, "收藏夹", "还没有收藏")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("收藏夹")
        dlg.setFixedSize(400, 450)
        dlg.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20,16,20,16)
        
        label = QLabel("我的收藏")
        label.setStyleSheet("font-size:18px;font-weight:bold;padding:8px;")
        layout.addWidget(label)
        
        lst = QListWidget()
        lst.setCursor(Qt.PointingHandCursor)
        lst.setStyleSheet("font-size:15px;")
        for f in self.favorites:
            lst.addItem(f"  {f['name']}  -  {f['region']}")
        layout.addWidget(lst)
        
        bl = QHBoxLayout()
        bv = QPushButton("查看")
        bd = QPushButton("删除")
        bv.setMinimumHeight(36)
        bd.setMinimumHeight(36)
        bv.setStyleSheet("font-size:14px;")
        bd.setStyleSheet("font-size:14px;")
        bv.clicked.connect(lambda: (self.show_recipe(self.favorites[lst.currentRow()]), dlg.accept()) if lst.currentRow()>=0 else None)
        bd.clicked.connect(lambda: (self.favorites.pop(lst.currentRow()), self.save_favorites(), lst.takeItem(lst.currentRow())) if lst.currentRow()>=0 else None)
        bl.addWidget(bv)
        bl.addWidget(bd)
        layout.addLayout(bl)
        dlg.exec_()


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    w = RecipeApp()
    w.show()
    sys.exit(app.exec_())